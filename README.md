# ⬡ FIAQ — Modelo de IA capaz de predecir la capacidad antioxidante de moléculas

Aplicación web para la predicción de la capacidad antioxidante de moléculas
mediante aprendizaje automático, desarrollada como Proyecto Final de Carrera
de la Licenciatura en Sistemas de Información en la FaCENA - UNNE.

---

## ¿Qué hace?

Dado el nombre en inglés, número CAS o notación SMILES de una molécula, FIAQ predice
su capacidad antioxidante clasificándola en **Alta**, **Media** o **Baja**,
junto con un porcentaje de confianza del modelo.

Las predicciones son orientativas y representan una **clasificación relativa/potencial**
dentro del dominio de entrenamiento. No reemplazan la validación experimental.

---

## Demo

🔗 

---

## Características

- Acepta entrada por **nombre en inglés**, **número CAS** o **notación SMILES**
- Resolución automática de nombres/CAS a SMILES vía **API de PubChem**
- Caché local SQLite para optimizar consultas recurrentes
- Interfaz responsiva con modo día/noche
- Indicador visual de confianza y termómetro de la capacidad antioxidante potencial

---

## Stack tecnológico

| Capa | Tecnologías |
|---|---|
| Backend | Python · Flask |
| Modelo ML | Scikit-Learn · Random Forest · Joblib |
| Quimioinformática | RDKit |
| Frontend | HTML · CSS · JavaScript |
| Animaciones | tsParticles · Anime.js |
| Datos externos | PubChem API |
| Despliegue | Docker · Render |

---

## Instalación local

```bash
# 1. Clonar el repositorio
git clone https://github.com/AyelenFL/PFC_FIAQ.git
cd pfc_fiaq

# 2. Crear entorno virtual e instalar dependencias
pip install -r requirements.txt

# 3. Correr la app
flask run
```

### Con Docker

```bash
docker build -t fiaq .
docker run -p 7860:7860 fiaq
# Acceder en http://localhost:7860
```

---

## Estructura del proyecto

```
pfc_fiaq/           
├── main.py
├── handler.py
├── cache_smiles.py
├── datos_modelo_clasificacion09.joblib
├── requirements.txt
├── Dockerfile
├── static/
│   ├── logo.ico
│   ├── script.js
│   └── style.css
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── quienesSomos.html
│   ├── preguntasFrecuentes.html
│   └── terminos.html
├── data/
└── scripts/
```

---

## Modelo

- **Algoritmo:** Random Forest Classifier
- **Dataset:** 169 compuestos con valores experimentales de TEAC
- **Features:** 27 descriptores físico-químicos y estructurales - patrones SMARTS (RDKit)
- **AUC-ROC ponderado:** 0.83
- **AUC-ROC clases Baja - Media - Alta:** 0,98, 0,71 y 0,80

---

## Limitaciones

- El modelo fue entrenado con una familia química específica.
  Moléculas de familias muy distintas pueden tener menor precisión.
- Las categorías son relativas al dominio de entrenamiento,
  no valores absolutos de actividad antioxidante.
- El porcentaje de confianza es un indicador auxiliar útil
  para evaluar la certeza de cada predicción.

---

## Contacto

ayelenleiva.f@gmail.com