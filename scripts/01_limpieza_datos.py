import pandas as pd

# Cargar el archivo 
archivo = 'D:/VSC_PFC_IAQ/data/TEAC_measured_with_DPPH_test_in_the_lab.xlsx' 
print(archivo)
df = pd.read_excel(archivo)

# Visualización de los datos
print(df.head(), end="") # Muestra las primeras 5 filas
print('=============================================================')
print(df.info(), end=""), #Muestra qué tipo de dato hay en cada columna y si hay valores nulos
print('=============================================================')
print(df.describe()) # Muestra estadísticas básicas de las columnas numéricas
print('=============================================================')
print(df.columns) # Muestra los nombres de las columnas
print('=============================================================')
print(df.shape) # Muestra el número de filas y columnas
print('=============================================================')
print(df.isnull().sum()) # Muestra el número de valores nulos por columna
print('=============================================================')

# Visualización de los datos
print(f"El dataset contiene: {df.shape[0]} filas, {df.shape[1]} columnas") # Muestra el número de filas y columnas
print('=============================================================')
# Muestra los nombres de las columnas:
print('Nombres de las columnas:')
for i, col in enumerate(df.columns):
    print(f"{i}: {col}")
print('=============================================================')


# Limpia los nombres de las columnas para que sean fáciles de usar. RENOMBRAR COLUMNAS
# Reemplaza espacios por guiones bajos, convierte a minúsculas y elimina corchetes y guiones
# Ejemplo: 'standard deviation of TEAC [molTE/mol]' -> 'standard_deviation_of_teac_molte_mol'
columnas_limpias = [col.lower().replace(' ', '_').replace('[','').replace(']','').replace('-','') for col in df.columns]
df.columns = columnas_limpias

# Imprime las columnas limpias
print('Nombres de las columnas:')
for col in enumerate(df.columns):
    print(col)

# Contar filas duplicadas
print("Número de filas duplicadas:", df.duplicated().sum())

# Contar valores nulos por columna
print("\nConteo de valores nulos por columna:")
print(df.isnull().sum())

# Lista de columnas a eliminar
columnas_a_eliminar = ['category','manuscript_table_3_entry', 'cas_no.', 
                       'synthetic_or_reagents', 'reagents_company', 'reagents_no',
                       'ic50_mg/l', 'standard_deviation_of_ic50_mg/l', 'stoichio_num._', 
                       'standard_deviation_of_stoichiometry_number_',  'teac_gte/g',
                        'standard_deviation_of_teac_gte/g', 'teac_molte/mol.1', 
                       ]

# Eliminar las columnas del DataFrame
df.drop(columns=columnas_a_eliminar, inplace=True)

# Verificar que las columnas fueron eliminadas
print("Columnas restantes:", df.columns)
print("Forma del DataFrame después de eliminar columnas:", df.shape)

# Ahora: limpiar la columna 'teac_molte_mol' que es de tipo 'object'
# 1. Seleccionamos la columna de tipo 'object'
target_col = df['teac_molte/mol'].astype(str).copy()
print(target_col)

# 2. Revisar cuántos valores con '>' 
print(f"Los número con '>' son: {target_col.str.contains('>', na=False).sum()}")

# 3. Limpiar los valores: Reemplaza el '>' por una cadena vacía
target_col_cleaned = target_col.str.replace('>', '', regex=False) # Reemplazar solo si hay '>'
print(target_col_cleaned)

# 4. Convertir la columna limpia a tipo numérico
# 'errors='coerce'' si no se puede convertir, lo transforma en Nulo (NaN)
target_col_numeric = pd.to_numeric(target_col_cleaned, errors='coerce')
print(target_col_numeric)

# 5. Revisar si se generaron nuevos nulos
print(f"Nulos DESPUÉS de la conversión: {target_col_numeric.isnull().sum()}")

# 6. Finalmente, asigna esta columna limpia y numérica al DataFrame
df['teac_molte_mol_limpio'] = target_col_numeric

# Ahora eliminar la columna original
df = df.drop(columns=['teac_molte/mol'])

# Ahora 'teac_molte_mol_limpio' es la columna objetivo.
print("\nDescripción de la columna target final:")
print(df['teac_molte_mol_limpio'].describe())

# Guardar el DataFrame limpio en un nuevo archivo CSV
#df.to_csv('data/dataset_limpio.csv', index=False) # Comentado para evitar sobreescritura
print("\nDataset limpio guardado como 'dataset_limpio.csv'en la carpeta data")