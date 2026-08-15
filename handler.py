"""
Handler del Modelo de IA
Este script se encarga de toda la lógica
para cargar el modelo de IA y realizar predicciones.
Está diseñado para ser completamente agnóstico de la aplicación web (Flask).
"""

#  0-> IMPORTACIONES 
import joblib
import numpy as np
import pandas as pd 
import os
import re         # Para expresiones regulares (detectar CAS)
import requests   # Para llamar a la API de PubChem
import sys
from functools import partial # Para funciones parciales (caché de SMILES)

# Importaciones de RDKit
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, Crippen, QED

# Importaciones para la caché de SMILES
from cache_smiles import inicializar_cache, buscar_smiles_con_cache


# ***** 1-> CONSTANTES Y CONFIGURACIÓN *****

# Expresión regular para detectar un número CAS
PATRON_CAS = re.compile(r'^\d{2,7}-\d{2}-\d$')

# URL de la API de PubChem
URL_API_PUBCHEM_NOMBRE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/property/CanonicalSMILES,ConnectivitySMILES/JSON"

# Límite de longitud para el input (nombre, CAS o SMILES)
# Cubre con margen cualquier molécula real; evita procesar strings absurdos
MAX_LONGITUD_ENTRADA = 200 

# **** LISTA COMPLETA DE TODOS LOS DESCRIPTORES Y SMARTS ****
# Es la lista de todo lo que el script 02 calculó.
LISTA_DESCRIPTORES_GENERALES = [
    
    # Características Fenólicas (grupos activos principales)
        ('fragmentos_fenol', Descriptors.fr_phenol),
        ('fragmentos_ar_oh', Descriptors.fr_Ar_OH),

        # Aromaticidad y Conjugación
        ('NroAnilloAromatico', Lipinski.NumAromaticRings),
        ('NroAnilloNoAromatico', Lipinski.NumAliphaticRings),

        # Propiedades Electrónicas y de Polaridad 
        ('TPSA', Descriptors.TPSA),  # Área de Superficie Polar
        ('donadores_puente_hidrogeno', Lipinski.NumHDonors),
        ('aceptores_puente_hidrogeno', Lipinski.NumHAcceptors),
        ('MolLogP', Crippen.MolLogP),

        # Propiedades Estructurales Generales 
        ('enlaces_rotables', Descriptors.NumRotatableBonds),
        ('fraccion_carbono_sp3', Descriptors.FractionCSP3),

        # Propiedades Físico-Químicas Globales
        ('conteo_atomos_pesados', Descriptors.HeavyAtomCount),
        ('refractividad_molar', Crippen.MolMR),
        ('alfa_hall_kier', Descriptors.HallKierAlpha),

        # Cargas Parciales (relevantes para donación de e–) 
        ('carga_parcial_maxima', Descriptors.MaxPartialCharge),
        ('carga_parcial_minima', Descriptors.MinPartialCharge),
        ('carga_parcial_abs_maxima', Descriptors.MaxAbsPartialCharge),
        ('carga_parcial_abs_minima', Descriptors.MinAbsPartialCharge),

        # Índices Topológicos / de Conectividad (estructura molecular)
        ('kappa_1', Descriptors.Kappa1),
        ('kappa_3', Descriptors.Kappa3),
        ('chi_0v', Descriptors.Chi0v),
        ('chi_2v', Descriptors.Chi2v),
        ('chi_4v', Descriptors.Chi4v),

        # Indicador de Drug-Likeness / Compacidad 
        ('coeficiente_qed', QED.qed)

]

PATRONES_SMARTS_COMPLETOS = {
    'num_catecoles': Chem.MolFromSmarts('c1([OH])c([OH])cccc1'),
    'num_resorcinoles': Chem.MolFromSmarts('c1([OH])cc([OH])ccc1'),
    'num_hidroquinonas': Chem.MolFromSmarts('c1([OH])ccc([OH])cc1'),
    'oh_vecino_a_metoxi': Chem.MolFromSmarts('[#6a](-[OX2H1])-[#6a](-[OX2H0]-[#6])')
}

# 2-> VARIABLES GLOBALES (SINGLETON)

# Patrón Singleton: Almacenar el modelo y la lista de características en
# una variable global para cargarlos solo una vez.
_datos_modelo_cargados = None

# 3-> FUNCIONES AUXILIARES

def cargar_modelo_y_caracteristicas():
    """
    Carga el modelo y la lista de características desde el archivo .joblib.
    Utiliza un patrón singleton para evitar cargarlo en cada predicción.
    También inicializa la caché de SMILES
    """
    global _datos_modelo_cargados
    
    # Si ya está cargado, lo devuelve directamente
    if _datos_modelo_cargados is not None:
        return _datos_modelo_cargados

    print("INFO: Cargando el modelo y la lista de características por primera vez")
    # Construye la ruta al archivo del modelo
    ruta_modelo = os.path.join(os.path.dirname(__file__), 'datos_modelo_clasificacion09.joblib')
    
    try:  
        if not os.path.exists(ruta_modelo):
            print(f"ERROR CRÍTICO: El archivo del modelo no se encuentra en: {ruta_modelo}")
            sys.exit(1) # Detiene la aplicación si el modelo no existe

        # Carga el diccionario completo desde el archivo
        datos_cargados = joblib.load(ruta_modelo)
        
        # Validación del archivo cargado
        if 'modelo' not in datos_cargados or 'lista_caracteristicas' not in datos_cargados:
            print(f"ERROR CRÍTICO: El archivo '{ruta_modelo}' está corrupto o no tiene las claves 'modelo' y 'lista_caracteristicas'.")
            sys.exit(1)
            
        _datos_modelo_cargados = datos_cargados
        print(" INFO: Modelo y lista de características cargados exitosamente")

        # Inicializar caché de SMILES (crea la DB/tabla si no existe)
        #inicializar_cache()

        return _datos_modelo_cargados
        
    except Exception as e:
        print(f"ERROR CRÍTICO: Fallo al cargar el archivo del modelo '{ruta_modelo}'. Error: {e}")
        sys.exit(1)

def buscar_smiles_en_pubchem(identificador, tipo_busqueda='name'):
    """
    Obtiene el SMILES desde PubChem usando un identificador (nombre o CAS).

    NOTA: PubChem indexa los números CAS como sinónimos del compuesto,
    por lo que el mismo endpoint /compound/name/ funciona para ambos casos.
    El parámetro tipo_busqueda se mantiene solo para logging y para que
    la caché registre cómo se originó la consulta.
    """

    url = URL_API_PUBCHEM_NOMBRE.format(requests.utils.quote(identificador))
        
    print(f"DEBUG: Consultando PubChem para ({tipo_busqueda}) para '{identificador}'")
    headers = {'User-Agent': 'FIAQ/1.0'}
    
    try:
        respuesta = requests.get(url, headers=headers, timeout=10)
        respuesta.raise_for_status() # Lanza un error si el estado no es 2xx
        
        datos = respuesta.json()
        
        tabla_propiedades = datos.get('PropertyTable')
        if not tabla_propiedades:
            return None
            
        propiedades_lista = tabla_propiedades.get('Properties')
        if not propiedades_lista or not isinstance(propiedades_lista, list) or len(propiedades_lista) == 0:
            return None
            
        primer_resultado = propiedades_lista[0]
        if not isinstance(primer_resultado, dict):
             return None

        #  Buscamos ambas claves, CanonicalSMILES y ConnectivitySMILES
        smiles = primer_resultado.get('CanonicalSMILES')
        if not smiles:
            smiles = primer_resultado.get('ConnectivitySMILES')
        
        return smiles if smiles else None
             
    except requests.exceptions.Timeout:
        raise ValueError(f"No se pudo contactar a PubChem (timeout) para buscar '{identificador}'")
    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 404:
            print(f"INFO: El identificador '{identificador}' no fue encontrado en PubChem.")
            return None # Devolvemos None en lugar de lanzar un error
        raise ValueError(f"PubChem devolvió un error ({http_err.response.status_code}) al buscar '{identificador}'") 
    except Exception as e:
        raise ValueError(f"Error inesperado al procesar la búsqueda de '{identificador}': {e}")
    

def calcular_caracteristicas_completas(molecula):
    """
    Calcula TODAS las características (generales + SMARTS) para una molécula RDKit dada.
    Devuelve un diccionario. Los descriptores que fallan quedan como NaN
    (se valida más adelante antes de realizar la predicción)
    """
    caracteristicas_calculadas = {}
    
    # Calcular Descriptores Generales
    for nombre, funcion in LISTA_DESCRIPTORES_GENERALES:
        try:
            caracteristicas_calculadas[nombre] = funcion(molecula)
        except Exception as e:
            print(f"Advertencia: No se pudo calcular el descriptor '{nombre}' para la molécula. Error: {e}")
            caracteristicas_calculadas[nombre] = np.nan # Asignar NaN si el cálculo falla
            
    # Calcular Patrones SMARTS 
    for nombre, patron in PATRONES_SMARTS_COMPLETOS.items():
        try:
            caracteristicas_calculadas[nombre] = len(molecula.GetSubstructMatches(patron))
        except Exception as e:
            print(f"Advertencia: No se pudo calcular el patrón SMARTS '{nombre}' para la molécula. Error: {e}")
            caracteristicas_calculadas[nombre] = np.nan
            
    return caracteristicas_calculadas

#  4 ->FUNCIÓN PRINCIPAL

def predecir_capacidad_antioxidante(entrada_molecula):
    """
    Función principal que orquesta la predicción (SMILES, Nombre o CAS).
    """
    # Validación de Entrada
    if not isinstance(entrada_molecula, str) or not entrada_molecula.strip():
        raise ValueError("La entrada de la molécula no puede estar vacía.")
    
    input_limpio = entrada_molecula.strip()
    
    # Límite de longitud para evitar procesar inputs muy largos
    if len(input_limpio) > MAX_LONGITUD_ENTRADA:
        raise ValueError(
            f"La entrada es demasiado larga ({len(input_limpio)} caracteres)."
            f"El máximo permitido es: {MAX_LONGITUD_ENTRADA}"
        )

    smiles = None
    molecula = None # Objeto Mol de RDKit

    # Determinar el tipo de entrada
    
    #  Intentar parsear como SMILES primero
    molecula = Chem.MolFromSmiles(input_limpio)
    
    if molecula is not None:
        # La entrada SÍ era un SMILES válido.
        smiles = input_limpio
    else:
        # La entrada NO es un SMILES.         
        # ¿Es un número CAS?
        if PATRON_CAS.match(input_limpio):
            print(f"DEBUG: Entrada parece un nro CAS '{input_limpio}'. Buscando con caché...")
            smiles = buscar_smiles_con_cache(
                input_limpio,
                partial(buscar_smiles_en_pubchem, tipo_busqueda='cas'),
                tipo_busqueda='cas'
            )
            if not smiles:
                raise ValueError(
                    f"No se pudo encontrar un SMILES válido para el número CAS '{input_limpio}'"
                    )

        # Si no es SMILES ni CAS, asumimos que es un nombre
        else:
            print(f"DEBUG: Entrada parece ser un nombre '{input_limpio}'. Buscando con caché...")
            smiles = buscar_smiles_con_cache(
                input_limpio,
                buscar_smiles_en_pubchem, # default tipo_busqueda='name' en la función buscar_smiles_en_pubchem
                tipo_busqueda='name'
            )
            if not smiles:
                raise ValueError(
                    f"No se pudo encontrar un SMILES válido para la molécula"
                    f"'{input_limpio}', verificar el nombre"
                )
        
        # Validar el SMILES obtenido de PubChem o de la caché
        molecula = Chem.MolFromSmiles(smiles)
        if not molecula:
            raise ValueError(f"La estructura química (SMILES: '{smiles}') obtenida no pudo ser interpretada por RDKit.")
            
    # 4 -> Carga, Cálculo y Predicción 
    
    # Cargar el modelo y la lista de características requeridas
    datos_cargados = cargar_modelo_y_caracteristicas()
    modelo = datos_cargados['modelo']
    lista_caracteristicas_requeridas = datos_cargados['lista_caracteristicas']
    
    # Calcular TODAS las características para la molécula de entrada
    todas_las_caracteristicas_dict = calcular_caracteristicas_completas(molecula)
    
    #  Crear un DataFrame de Pandas con un solo renglón
    # Para que scikit-learn reciba los nombres de las características
    df_caracteristicas = pd.DataFrame([todas_las_caracteristicas_dict])
    
    # FILTRAR Y REORDENAR el DataFrame según lo que el modelo espera
    # Seleccionamos solo las columnas que el modelo necesita, en el orden correcto
    try:
        df_para_modelo = df_caracteristicas[lista_caracteristicas_requeridas]
    except KeyError as e:
        raise ValueError(f"Error interno: Falta la característica requerida '{e}'.")
    
    # Verificar que no haya NaN antes de realizar la predicción
    # si algún descriptor no se pudo calcular; se lanza un error controlado que devolver una predicción errónea
    columnas_con_nan = df_para_modelo.columns[df_para_modelo.isna().any()].tolist()
    if columnas_con_nan:
        raise ValueError(
            f"Advertencia: No se pudieron calcular todos los descriptores necesarios"
            f"({', '.join(columnas_con_nan)}). La molécula podría tener una"
            f"estructura no soportada o atípica. Por favor, verifica la entrada o prueba con otra molécula."
        )


    # Realizar la predicción (Clasificación)
    # predict() devuelve un array, ej: [2]. Tomamos el primer elemento [0]
    clase_predicha = modelo.predict(df_para_modelo)[0] 
    
    # Obtener las probabilidades
    # predict_proba devuelve las probabilidades para [Baja, Media, Alta]
    probabilidades = modelo.predict_proba(df_para_modelo)[0]
    probabilidad_max = max(probabilidades) * 100 # Sacamos el % más alto
    # Mapear el número a texto descriptivo
    mapa_clases = {
        0: "BAJA Capacidad Antioxidante",
        1: "MEDIA Capacidad Antioxidante",
        2: "ALTA Capacidad Antioxidante"
    }
    resultado_texto = mapa_clases.get(clase_predicha, "Clase Desconocida")

    # Devolvemos un diccionario 
    return {
        "clase_texto": resultado_texto,
        "clase_numerica": int(clase_predicha),
        "confianza_porcentaje": round(probabilidad_max, 2)
    }

# 5 -> BLOQUE DE PRUEBAS AISLADAS 
if __name__ == '__main__':
    """
    Este bloque se ejecuta solo cuando se ejecuta este script directamente
    ( python model/handler.py) para probarlo.
    """
    print("\n" + "="*50)
    print(" EJECUTANDO PRUEBAS AISLADAS DEL HANDLER ".center(50, "="))
    print("="*50)

    # Prueba 1: Búsqueda en PubChem (con caché)
    print("\nPRUEBA 1: BÚSQUEDA EN PUBCHEM + CACHÉ")
    inicializar_cache()  

    pruebas_busqueda = {
        'aspirin': 'CC(=O)Oc1ccccc1C(=O)O',
        'caffeine': 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C',
        'glucose': 'C(C1C(C(C(C(O1)O)O)O)O)O',
        '50-78-2': 'CC(=O)Oc1ccccc1C(=O)O', # CAS de la aspirina
        'MoleculaInexistente123XYZ': None,
        '99999-99-9': None # CAS inválido
    }
    
    for identificador, esperado in pruebas_busqueda.items():
        try:
            if PATRON_CAS.match(identificador):
                smiles_obtenido = buscar_smiles_con_cache(
                    identificador,
                    partial(buscar_smiles_en_pubchem, tipo_busqueda='cas'),
                    tipo_busqueda='cas'
                )
            else:
                smiles_obtenido = buscar_smiles_con_cache(
                    identificador,
                    buscar_smiles_en_pubchem,
                    tipo_busqueda='name'
                )
 
            if smiles_obtenido == esperado:
                print(f"OK: '{identificador}' -> '{smiles_obtenido}'")
            elif esperado is None and smiles_obtenido is None:
                print(f"OK (no encontrado, esperado): '{identificador}'")
            else:
                print(f"FALLO: '{identificador}'. Esperado: '{esperado}', "
                      f"Obtenido: '{smiles_obtenido}'")
        except Exception as e:
            print(f"FALLO con excepción para '{identificador}': {e}")
             
    # Prueba 2: Predicción Completa 
    print("\n PRUEBA 2: PREDICCIÓN DE PUNTA A PUNTA")
    pruebas_prediccion = [
        ('CC(=O)Oc1ccccc1C(=O)O', 'SMILES válido'),
        ('caffeine', 'Nombre válido'),
        ('50-78-2', 'CAS válido'),
        ('EstoNoEsUnSmile', 'Error controlado'),
        ('MoleculaInexistente123XYZ', 'Error controlado'),
        ('',                           'Error controlado — vacío'),
        ('X' * 250,                    'Error controlado — demasiado largo')
    ]
    
    # El modelo ej.: 'datos_modelo.joblib' debe existir en la carpeta 'model' antes de correr las prueba.
    for entrada, tipo in pruebas_prediccion:
        print(f"\n Probando: '{entrada[:40]}{'...' if len(entrada) > 40 else ''}' ({tipo})")
        try:
            prediccion = predecir_capacidad_antioxidante(entrada)
            
            print(
                f"Éxito: '{entrada[:40]}' -> "
                f"{prediccion['clase_texto']} "
                f"(confianza: {prediccion['confianza_porcentaje']}%)"
            )
        except ValueError as e:
            if 'Error controlado' in tipo:
                print(f"OK, error controlado esperado: {e}")
            else:
                print(f"FALLO con excepción inesperada: {e}")
        except Exception as e:
            print(f"FALLO CRÍTICO inesperado: {e}")
