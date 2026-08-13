# SCRIPT 02: INGENIERÍA DE CARACTERÍSTICAS (DESCRIPTORES Y SMARTS)
"""
Este script toma el dataset limpio (dataset_limpio_ESTE.csv), calcula
descriptores moleculares generales con RDKit y, además, añade
características específicas basadas en patrones SMARTS para
capturar información posicional de grupos funcionales clave
(especialmente grupos hidroxilo fenólicos).
"""

# IMPORTACIONES 
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, Lipinski, QED
import numpy as np
import os # Para manejo de rutas

print(" Iniciando Ingeniería de Características Avanzada (Descriptores + SMARTS)...")

# 1. CARGAR EL DATASET LIMPIO
ruta_dataset_limpio = os.path.join('data', 'dataset_limpio_ESTE.csv')
try:
    dataframe_limpio = pd.read_csv(ruta_dataset_limpio)
    print(f" El Dataset limpio cargado desde '{ruta_dataset_limpio}'. Contiene {dataframe_limpio.shape[0]} filas.")
except FileNotFoundError:
    print(f" ERROR: No se encontró '{ruta_dataset_limpio}'. Asegúrate de ejecutar el script 01 primero.")
    exit()
except Exception as e:
    print(f" ERROR inesperado al cargar el dataset limpio: {e}")
    exit()

# 2. CREAR OBJETOS MOLÉCULA DE RDKit 
# Es necesario convertir los SMILES a objetos RDKit para trabajar con ellos.
# Se Guardan también los índices originales para poder manejar errores.
indices_originales = dataframe_limpio.index
dataframe_limpio['molecula'] = dataframe_limpio['smiles'].apply(Chem.MolFromSmiles)

# Verificamos cuántos SMILES no pudieron ser interpretados
smiles_invalidos = dataframe_limpio['molecula'].isnull().sum()
if smiles_invalidos > 0:
    print(f" Advertencia: {smiles_invalidos} SMILES no pudieron ser interpretados por RDKit y serán descartados!!!.")
    # Eliminamos las filas con SMILES inválidos para evitar errores posteriores
    dataframe_limpio = dataframe_limpio.dropna(subset=['molecula'])
    # Actualizamos los índices si hemos eliminado filas
    indices_actualizados = dataframe_limpio.index   

# 3. CALCULAR DESCRIPTORES MOLECULARES GENERALES 
# Usamos la lista de descriptores fisicoquímicos.
lista_de_descriptores_curada = [

    # 1. Características Fenólicas
        ('fragmentos_fenol', Descriptors.fr_phenol),
        ('fragmentos_ar_oh', Descriptors.fr_Ar_OH),

        # 2. Aromaticidad y Conjugación
        ('NroAnilloAromatico', Lipinski.NumAromaticRings),
        ('NroAnilloNoAromatico', Lipinski.NumAliphaticRings),

        # 3. Propiedades Electrónicas y de Polaridad
        ('TPSA', Descriptors.TPSA),  # Área de Superficie Polar
        ('donadores_puente_hidrogeno', Lipinski.NumHDonors),
        ('aceptores_puente_hidrogeno', Lipinski.NumHAcceptors),
        ('MolLogP', Crippen.MolLogP),

        # 4. Propiedades Estructurales Generales 
        ('enlaces_rotables', Descriptors.NumRotatableBonds),
        ('fraccion_carbono_sp3', Descriptors.FractionCSP3),

        # 5. Propiedades Físico-Químicas Globales 
        ('conteo_atomos_pesados', Descriptors.HeavyAtomCount),
        ('refractividad_molar', Crippen.MolMR),
        ('alfa_hall_kier', Descriptors.HallKierAlpha),

        # 6. Cargas Parciales (relevantes para donación de e–)
        ('carga_parcial_maxima', Descriptors.MaxPartialCharge),
        ('carga_parcial_minima', Descriptors.MinPartialCharge),
        ('carga_parcial_abs_maxima', Descriptors.MaxAbsPartialCharge),
        ('carga_parcial_abs_minima', Descriptors.MinAbsPartialCharge),

        # 7. Índices Topológicos / de Conectividad 
        ('kappa_1', Descriptors.Kappa1),
        ('kappa_3', Descriptors.Kappa3),
        ('chi_0v', Descriptors.Chi0v),
        ('chi_2v', Descriptors.Chi2v),
        ('chi_4v', Descriptors.Chi4v),

        # 8. Indicador de Drug-Likeness / Compacidad
        ('coeficiente_qed', QED.qed)

]

def calcular_descriptores_generales(molecula):
    """Calcula la lista de descriptores generales para una molécula RDKit."""
    if molecula is None:
        return [np.nan] * len(lista_de_descriptores_curada)
    try:
        return [funcion(molecula) for nombre, funcion in lista_de_descriptores_curada]
    except Exception as e:
        # Capturar errores inesperados durante el cálculo de descriptores
        print(f" se produjo un ERROR calculando descriptor general: {e}. Se devolverá NaN.") 
        return [np.nan] * len(lista_de_descriptores_curada)

# Aplicamos la función para calcular los descriptores generales
nombres_descriptores_generales = [nombre for nombre, funcion in lista_de_descriptores_curada]
# Usamos apply con una lambda para pasar la columna 'molecula'
# Convertimos el resultado a una lista y luego a DataFrame para asignar nombres
descriptores_calculados = dataframe_limpio['molecula'].apply(
    lambda mol: calcular_descriptores_generales(mol)
)
df_descriptores = pd.DataFrame(
    descriptores_calculados.tolist(), 
    index=dataframe_limpio.index, # Aseguramos que los índices coincidan
    columns=nombres_descriptores_generales
)

# Unimos los descriptores calculados al dataframe principal
dataframe_enriquecido = pd.concat([dataframe_limpio, df_descriptores], axis=1)
print(f" Descriptores generales calculados y añadidos ({len(nombres_descriptores_generales)} columnas).")


# 4. CALCULAR CARACTERÍSTICAS BASADAS EN PATRONES SMARTS
# Definimos patrones SMARTS para identificar subestructuras específicas
# relacionadas con la posición de los grupos -OH fenólicos.
patrones_smarts = {
    'num_catecoles': Chem.MolFromSmarts('c1([OH])c([OH])cccc1'), # Grupo Catecol (orto-dihidroxi)
    'num_resorcinoles': Chem.MolFromSmarts('c1([OH])cc([OH])ccc1'), # Grupo Resorcinol (meta-dihidroxi) - Aproximación SMARTS
    'num_hidroquinonas': Chem.MolFromSmarts('c1([OH])ccc([OH])cc1'), # Grupo Hidroquinona (para-dihidroxi) - Aproximación SMARTS
    'oh_vecino_a_metoxi': Chem.MolFromSmarts('[#6a](-[OX2H1])-[#6a](-[OX2H0]-[#6])') # Fenol con grupo metoxi (-OCH3) adyacente NO
}

# Verificamos que los SMARTS sean válidos
patrones_validos = {}
for nombre, patron in patrones_smarts.items():
    if patron is None:
        print(f" Advertencia: El patrón SMARTS '{nombre}' no es válido y será ignorado.")
    else:
        patrones_validos[nombre] = patron

def calcular_caracteristicas_smarts(molecula):
    """Cuenta las ocurrencias de cada patrón SMARTS en una molécula."""
    if molecula is None:
        return [0] * len(patrones_validos) # Devolvemos 0 si la molécula es inválida
    
    conteo_patrones = []
    for nombre, patron in patrones_validos.items():
        try:
            # GetSubstructMatches devuelve una tupla de tuplas con los índices de los átomos que coinciden
            conteo = len(molecula.GetSubstructMatches(patron))
            conteo_patrones.append(conteo)
        except Exception as e:
            # Captura errores si la búsqueda falla por alguna razón
            print(f" ERROR buscando patrón SMARTS '{nombre}': {e}. Se devolverá 0.")
            conteo_patrones.append(0)
    return conteo_patrones

# Aplicamos la función para calcular las características SMARTS
nombres_caracteristicas_smarts = list(patrones_validos.keys())
smarts_calculados = dataframe_enriquecido['molecula'].apply(
    lambda mol: calcular_caracteristicas_smarts(mol)
)
df_smarts = pd.DataFrame(
    smarts_calculados.tolist(), 
    index=dataframe_enriquecido.index, # Aseguramos que los índices coincidan
    columns=nombres_caracteristicas_smarts
)

# Unimos las características SMARTS al dataframe principal
dataframe_enriquecido = pd.concat([dataframe_enriquecido, df_smarts], axis=1)
print(f" Características basadas en SMARTS calculadas y añadidas ({len(nombres_caracteristicas_smarts)} columnas).")

# 5. PREPARACIÓN FINAL Y GUARDADO 
# Seleccionamos la variable objetivo
columna_objetivo = 'teac_molte_mol_limpio'
objetivo = dataframe_enriquecido[columna_objetivo]

# Definimos todas las columnas que serán las características finales
columnas_de_caracteristicas = nombres_descriptores_generales + nombres_caracteristicas_smarts
caracteristicas = dataframe_enriquecido[columnas_de_caracteristicas]

# Creamos el DataFrame final completo para limpieza sincronizada
dataframe_final_completo = caracteristicas.copy()
dataframe_final_completo[columna_objetivo] = objetivo

# Eliminamos filas donde falte el objetivo o alguna característica
filas_antes = len(dataframe_final_completo)
dataframe_final_completo = dataframe_final_completo.dropna()
filas_despues = len(dataframe_final_completo)
if filas_antes > filas_despues:
    print(f" Se eliminaron {filas_antes - filas_despues} filas debido a valores nulos en características u objetivo.")

# Separamos de nuevo en características y objetivo finales
caracteristicas_finales = dataframe_final_completo[columnas_de_caracteristicas]
objetivo_final = dataframe_final_completo[columna_objetivo]

print(f" ¡Proceso completado!. El dataset final para el modelo tiene {caracteristicas_finales.shape[0]} muestras y {caracteristicas_finales.shape[1]} características.")

# Guardamos los DataFrames finales en archivos separados
ruta_guardado_X = os.path.join('data', 'X_features_avanzado1.csv')
ruta_guardado_y = os.path.join('data', 'y_target_avanzado1.csv')

try:
    caracteristicas_finales.to_csv(ruta_guardado_X, index=False)
    objetivo_final.to_csv(ruta_guardado_y, index=False, header=[columna_objetivo]) # Aseguramos el nombre correcto del header
    print(f" Los archivos '{os.path.basename(ruta_guardado_X)}' y '{os.path.basename(ruta_guardado_y)}' guardados en la carpeta /data.")
except Exception as e:
    print(f"Se produjo un ERROR al guardar los archivos CSV finales: {e}")

print("\n====================== Ingeniería de Características Finalizada ======================")
