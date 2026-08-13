# HOLA
# SCRIPT 03: PRUEBA DE CLASIFICACIÓN

import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score, roc_curve, auc, roc_auc_score
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from sklearn.preprocessing import label_binarize

print(" Iniciando el modelo  de Clasificación...")

# 1. CARGA DE DATOS 
ruta_X = os.path.join('data', 'X_features_avanzado1.csv')
ruta_y = os.path.join('data', 'y_target_avanzado1.csv')

try:
    X = pd.read_csv(ruta_X)
    y = pd.read_csv(ruta_y).squeeze()
    print(f" Datos cargados: {X.shape[0]} muestras, {X.shape[1]} características.")
except FileNotFoundError:
    print(" ERROR: No se encontraron los archivos en 'data/'. Ejecuta el script 02 primero.")
    exit()

# 2. CONVERSIÓN A CLASIFICACIÓN (Definir el Umbral)
# Calculamos los dos umbrales clave
umbral_medio = np.percentile(y, 33)
umbral_alto  = np.percentile(y, 66)

def clasificar_multiclase(valor):
    if valor < umbral_medio:
        return 0  # Baja
    elif valor < umbral_alto:
        return 1  # Media
    else:
        return 2  # Alta

y_clasificacion = y.apply(clasificar_multiclase)

print(f"\n Umbral definido (Percentil 75): TEAC > {umbral_alto:.2f}")
print(f"\n Umbral definido (Percentil 50): TEAC > {umbral_medio:.2f} para distinguir Baja vs Media/Alta")

print("\nDistribución de Clases:")
print(y_clasificacion.value_counts(normalize=True).apply(lambda x: f"{x:.1%}"))

# 3. DIVISIÓN DE DATOS 
# Usamos stratify=y_clasificacion para asegurar que ambas clases 
# estén representadas en el conjunto de prueba
X_train, X_test, y_train, y_test = train_test_split(
    X, y_clasificacion, test_size=0.2, random_state=42, stratify=y_clasificacion
)

# 4. ENTRENAMIENTO
print("\n Entrenando Random Forest Classifier...")
clf = RandomForestClassifier(
    n_estimators=200, 
    max_depth=10,
    class_weight='balanced', 
    random_state=42,
    n_jobs=-1
)
clf.fit(X_train, y_train)

# 5. EVALUACIÓN 
print("\n Evaluando el modelo...")
y_pred = clf.predict(X_test)

# average = 'weighted' para respetar la proporción de 50% 25% 25% 
f1 = f1_score(y_test, y_pred, average='weighted') 
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, average='weighted') 
recall = recall_score(y_test, y_pred, average='weighted')

print(f"\n--- RESULTADOS DE CLASIFICACIÓN ---")
print(f"F1-Score: {f1:.2%}")
print(f"Exactitud (Accuracy): {accuracy:.2%}")
print(f"Precisión (Precision): {precision:.2%}")
print(f"Recall (Sensibilidad): {recall:.2%}")

print("\nReporte Detallado:")
nombres_clases = ['Baja (0)', 'Media (1)', 'Alta (2)']
print(classification_report(y_test, y_pred, target_names=nombres_clases))

# 6. MATRIZ DE CONFUSIÓN
plt.figure(figsize=(7, 6))
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Predicción: Baja', 'Predicción: Media', 'Predicción: Alta'],
            yticklabels=['Real: Baja', 'Real: Media', 'Real: Alta'])
plt.title('Matriz de Confusión')
plt.ylabel('Valor Real')
plt.xlabel('Predicción del Modelo')
plt.tight_layout()
plt.show()

caracteristicas_nombres = X_train.columns.tolist()
# 9. GUARDADO DEL MODELO 
# se guarda el diccionario completo para que funcione con handler.py
datos_del_modelo = {
    'modelo': clf,
    'lista_caracteristicas': caracteristicas_nombres
}


ruta_modelo = os.path.join('model', 'datos_modelo_clasificacion09.joblib')
joblib.dump(datos_del_modelo, ruta_modelo)

print(f"\n ¡Éxito! Modelo CLASIFICACIÓN Multiclase guardado en: '{ruta_modelo}'")

# Generación de Curva ROC y cálculo del AUC

print("\n Generando el Análisis ROC-AUC...")

# Binarizamos las etiquetas reales (ej: la clase 2 se vuelve [0, 0, 1])
y_test_bin = label_binarize(y_test, classes=[0, 1, 2])
n_classes = y_test_bin.shape[1]

# Obtenemos las probabilidades para las 3 clases
y_pred_prob = clf.predict_proba(X_test)

# Calculamos el AUC global (Estrategia One-vs-Rest, promedio ponderado)
roc_auc_global = roc_auc_score(y_test, y_pred_prob, multi_class='ovr', average='weighted')
print(f" AUC-ROC Score Global (Weighted OvR): {roc_auc_global:.4f}")

# Graficar la Curva ROC para cada clase
plt.figure(figsize=(9, 7))
colores = ['blue', 'green', 'darkorange']

for i, color, nombre in zip(range(n_classes), colores, nombres_clases):
    # Calculamos FPR y TPR para la clase específica 'i'
    fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_pred_prob[:, i])
    roc_auc_clase = auc(fpr, tpr)
    
    plt.plot(fpr, tpr, color=color, lw=2, 
             label=f'ROC de clase {nombre} (AUC = {roc_auc_clase:.2f})')

# Línea base aleatoria
plt.plot([0, 1], [0, 1], 'k--', lw=2, label='Modelo Aleatorio')

plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('Tasa de Falsos Positivos')
plt.ylabel('Tasa de Verdaderos Positivos')
plt.title('Curvas ROC Multiclase (One-vs-Rest)')
plt.legend(loc="lower right")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

print(" Análisis ROC-AUC finalizado.")
