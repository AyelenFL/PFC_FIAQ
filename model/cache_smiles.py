"""
Caché persistente en SQLite para resultados de PubChem.
Funcionamiento:
  - Primera vez que se busca "aspirina" → llama a PubChem y guarda el resultado.
  - Segunda vez en adelante → devuelve el resultado guardado, sin red.
  - Los resultados None (no encontrado) también se cachean, para no
    volver a consultar PubChem por moléculas que no existen.

Estructura de la base de datos (un solo archivo .db):
  Tabla: smiles_cache
    ┌─────────────────┬──────────────────────┬──────────────────────┬───────────────┐
    │ identificador   │ smiles               │ encontrado           │ fecha_consulta│
    │ TEXT (PK)       │ TEXT / NULL          │ INTEGER (0 o 1)      │ TEXT          │
    └─────────────────┴──────────────────────┴──────────────────────┴───────────────┘

  - identificador: la clave normalizada (minúsculas, sin espacios extra)
  - smiles:        el SMILES devuelto por PubChem, o NULL si no se encontró
  - encontrado:    1 si PubChem lo encontró, 0 si devolvió None (cachea el "no")
  - fecha_consulta: cuándo se hizo la consulta (útil para debug y estadísticas)
"""

import sqlite3
import threading
import os
from datetime import datetime
from functools import partial 


def _alertas():
    """
    Importación lazy del módulo de alertas.
    Si alertas.py no está disponible... o el .env no está configurado,
    la caché sigue funcionando sin enviar emails.
    """ 
    try:
        import alertas
        return alertas
    except ImportError:
        return None 

# 
# ************************ CONFIGURACIÓN ************************
# 

# El archivo .db se guarda en la misma carpeta que este módulo.
DB_PATH = os.path.join(os.path.dirname(__file__), 'smiles_cache.db')

# Lock para acceso thread-safe (Flask puede manejar requests concurrentes)
_lock = threading.Lock()


# 
# ************************ INICIALIZACIÓN ************************
# 

def _get_connection():
    """
    Devuelve una conexión SQLite con timeout para evitar bloqueos.
    check_same_thread=False porque Flask puede llamar
    desde distintos threads.
    """
    return sqlite3.connect(DB_PATH, timeout=5, check_same_thread=False)


def inicializar_cache():
    """
    Crea la tabla si no existe. Llamar una vez al arrancar la app.
    Si la tabla ya existe, no hace nada.
    La columna tipo_busqueda distingue si la clave es un nombre = 'name'
    o un nro CAS = 'cas', para estadísticas y debug.
    """
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smiles_cache (
                identificador   TEXT PRIMARY KEY,
                smiles          TEXT,
                encontrado      INTEGER NOT NULL DEFAULT 0,
                tipo_busqueda    TEXT NOT NULL DEFAULT 'name',
                fecha_consulta  TEXT    NOT NULL
            )
        """)
        # Índice para búsquedas rápidas: aunque la PK ya lo hace, es explícito
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_identificador
            ON smiles_cache (identificador)
        """)
        conn.commit()
    print(f"[Cache] Base de datos inicializada en: {DB_PATH}")


#
# ************************ OPERACIONES CRUD ************************
# 

def _normalizar_clave(identificador: str) -> str:
    """
    Normaliza el identificador antes de guardar/buscar.
    'Aspirina', 'ASPIRINA', '  aspirina  ' → 'aspirina'
    Esto evita duplicados por diferencias de mayúsculas o espacios.
    """
    return identificador.strip().lower()


def buscar_en_cache(identificador: str):
    """
    Busca el identificador en la caché local.
    Returns:
        (True,  smiles_str)  -> encontrado en PubChem, SMILES disponible
        (True,  None)        -> consultado antes, PubChem no lo encontró
        (False, None)        -> no está en caché, hay que consultar PubChem
    """
    clave = _normalizar_clave(identificador)

    with _lock:
        with _get_connection() as conn:
            cursor = conn.execute(
                "SELECT smiles, encontrado FROM smiles_cache WHERE identificador = ?",
                (clave,)
            )
            fila = cursor.fetchone()

    if fila is None:
        # No está en caché -> hay que ir a PubChem
        return False, None

    smiles, encontrado = fila
    # Está en caché: devuelve True + el SMILES; que puede ser None si no existe
    return True, (smiles if encontrado else None)


def guardar_en_cache(identificador: str, smiles, tipo_busqueda: str = 'name'):
    """
    Guarda el resultado de una consulta PubChem en la caché.
    Args:
        identificador: el nombre/CAS buscado
        smiles:        el SMILES encontrado, o None si PubChem no lo encontró
        tipo_busqueda: 'name' para los nombres comunes y 'cas' para los números CAS
    Después de guardar ejecuta en segundo plano:
        - Verificación de tamaño de la DB
        - Contador de resumen periódico
    Usa INSERT OR REPLACE para que si ya existía, lo actualice.
    """
    clave     = _normalizar_clave(identificador)
    encontrado = 1 if smiles is not None else 0
    fecha     = datetime.now().isoformat(sep=' ', timespec='seconds')

    try:
        with _lock:
            with _get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO smiles_cache
                        (identificador, smiles, encontrado, tipo_busqueda, fecha_consulta)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (clave, smiles, encontrado, tipo_busqueda, fecha)
                )
                conn.commit()
 
        estado = f"SMILES guardado: {smiles[:40]}..." if smiles else "guardado como 'no encontrado'"
        print(f"[Cache] '{identificador}' ({tipo_busqueda}) → {estado}")
 
        # Ejecuta alertas en segundo plano: no bloquean el guardado
        mod = _alertas()
        if mod:
            stats = estadisticas_cache()
            mod.verificar_tamano_db(DB_PATH, stats)
            mod.registrar_consulta_nueva(stats)
 
    except Exception as e:
        print(f"[Cache] ERROR al guardar '{identificador}': {e}") 
        mod = _alertas()
        if mod:
            mod.alerta_error_grave("guardar_en_cache", e)
        raise


# 
# FUNCIÓN PRINCIPAL — reemplaza la llamada directa a PubChem
# 

def buscar_smiles_con_cache(identificador: str, fn_pubchem, tipo_busqueda: str = 'name'):
    """
    Punto de entrada principal. Busca el SMILES con caché intermedia.
    Lógica:
      1. Buscar en caché SQLite  -> si está, devolver sin llamar a PubChem
      2. Si no está -> llamar a fn_pubchem (función buscar_smiles_en_pubchem)
      3. Guardar el resultado (sea SMILES o None) en la caché
      4. Devolver el resultado
    Args:
        identificador: nombre, CAS o cualquier string que va a PubChem
        fn_pubchem:    función buscar_smiles_en_pubchem (se pasa como argumento
                       para que este módulo no dependa del handler)
    Returns:
        str con el SMILES, o None si no se encontró
    Raises:
        ValueError: si PubChem lanza un error (timeout, HTTP error, etc.)
                    Los errores NO se cachean — se reintentará la próxima vez.
    """
    #  Paso 1: buscar en caché
    en_cache, smiles_cacheado = buscar_en_cache(identificador)

    if en_cache:
        if smiles_cacheado:
            print(f"[Cache] HIT '{identificador}' → {smiles_cacheado[:40]}...")
        else:
            print(f"[Cache] HIT (no encontrado) '{identificador}'")
        return smiles_cacheado

    #  Paso 2: no está en caché -> consultar PubChem
    print(f"[Cache] MISS — consultando PubChem para '{identificador}'...")

    try:
        smiles = fn_pubchem(identificador)
        # Paso 3: guardar resultado, incluyendo None = disparar alertas
        guardar_en_cache(identificador, smiles, tipo_busqueda=tipo_busqueda)
        return smiles

    except ValueError:
        # Error de red o HTTP → NO cachear, que reintente la próxima vez
        print(f"[Cache] ERROR al consultar PubChem — NO se guarda en caché.")
        mod = _alertas()
        if mod:
            mod.alerta_error_grave(
                f"buscar_smiles_con_cache (PubChem)",
                ValueError(f"Fallo al consultar '{identificador}' ({tipo_busqueda})")
            )
        raise


# 
# Para debug y mantenimiento
# 

def estadisticas_cache():
    """
    Devuelve un dict con estadísticas de la caché, incluyendo desglose
    por tipo de búsqueda (nombre vs CAS) y tamaño del archivo en disco.
    """
    try:
        with _get_connection() as conn:
            total       = conn.execute("SELECT COUNT(*) FROM smiles_cache").fetchone()[0]
            encontrados = conn.execute("SELECT COUNT(*) FROM smiles_cache WHERE encontrado = 1").fetchone()[0]
            no_encontr  = conn.execute("SELECT COUNT(*) FROM smiles_cache WHERE encontrado = 0").fetchone()[0]
            por_nombre  = conn.execute("SELECT COUNT(*) FROM smiles_cache WHERE tipo_busqueda = 'name'").fetchone()[0]
            por_cas     = conn.execute("SELECT COUNT(*) FROM smiles_cache WHERE tipo_busqueda = 'cas'").fetchone()[0]
 
        tamano_mb = os.path.getsize(DB_PATH) / (1024 * 1024) if os.path.exists(DB_PATH) else 0
 
        return {
            'total_entradas':    total,
            'encontrados':       encontrados,
            'no_encontrados':    no_encontr,
            'por_nombre':        por_nombre,
            'por_cas':           por_cas,
            'tamano_mb':         round(tamano_mb, 3),
            'db_path':           DB_PATH,
        }
    except Exception as e:
        return {'error': str(e)}


def limpiar_no_encontrados():
    """
    Elimina las entradas donde PubChem no encontró el compuesto.
    Útil si PubChem antes fallaba pero ahora podría tenerlos.
    Llamar manualmente cuando sea necesario.
    """
    with _lock:
        with _get_connection() as conn:
            cursor = conn.execute("DELETE FROM smiles_cache WHERE encontrado = 0")
            conn.commit()
            print(f"[Cache] Eliminadas {cursor.rowcount} entradas 'no encontrado'.")


# Llamar al inicializador al importar el módulo, para asegurar que la tabla exista.
inicializar_cache() 