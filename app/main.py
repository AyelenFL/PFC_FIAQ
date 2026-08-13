"""
Rutas y lógica del servidor Flask para manejar las peticiones del frontend y comunicarse con el handler de IA.
Rutas de la aplicación Flask. 
"""

import sys
import os
from flask import Flask, render_template, request, jsonify, send_from_directory

#  Configuración de la Ruta 
# Para que Python pueda encontrar la carpeta 'model' que está un nivel arriba.
# Agrega la ruta del directorio raíz del proyecto al sys.path.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  

#  Importación del Módulo de IA 
# Ahora que la ruta está configurada, podemos importar el handler.
try:
    from model import handler as model_handler
except ImportError as e:
    print(f"Error real de importación: {e}")
    sys.exit(1)
# except ImportError:
#     # Proporciona un mensaje de error claro si el handler no se puede importar.
#     print("Error: No se pudo importar 'model/handler.py'. Asegúrate de que el archivo exista y no tenga errores de sintaxis.")
#     sys.exit(1)


#  Inicialización de la Aplicación Flask 
app = Flask(__name__)

#  Definición de las Rutas (Endpoints) 
@app.route('/favicon.ico')
def favicon():
    """
    Ruta para servir el favicon de la aplicación.
    Esto evita que el navegador intente buscar un favicon en la raíz del servidor y genere un error 404.
    Flask buscará automáticamente 'logo.ico' en la carpeta 'static'.
    """
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'logo.ico',
        mimetype='image/x-icon',
        #max_age=31536000 # <-- Le dice al navegador: "Guarda esto en caché por 1 año"
        )

@app.route('/') 
def index():
    """
    Ruta principal que sirve la página de inicio (index.html).
    Flask buscará automáticamente este archivo en la carpeta 'templates'.
    """
    return render_template('index.html')

@app.route('/quienesSomos', endpoint='quienesSomos')
def quienesSomos():
    """
    Ruta para la página "Quiénes Somos".
    Flask buscará automáticamente 'quienesSomos.html' en la carpeta 'templates'.
    """
    return render_template('quienesSomos.html')

@app.route('/preguntasFrecuentes', endpoint='preguntasFrecuentes')
def preguntasFrecuentes():
    """
    Ruta para la página de Preguntas Frecuentes.
    Flask buscará automáticamente 'preguntasFrecuentes.html' en la carpeta 'templates'.
    """
    return render_template('preguntasFrecuentes.html')

@app.route('/terminos', endpoint='terminos')
def terminos():
    return render_template('terminos.html')


# API de predicción: este endpoint se activa cuando el frontend envía una petición POST con los datos del usuario.
@app.route('/predict', methods=['POST'])
def predict():
    """
    Endpoint de la API para realizar predicciones.
    Se activa cuando el JavaScript del frontend le envía una petición POST.
    """
    try:
        # 1. Recibir y validar los datos del frontend
        data = request.get_json()
        
        # Validación: verifica que data no sea nulo Y que contenga la clave correcta.
        if not data or 'molecule_input' not in data:
            return jsonify({'error': 'Petición inválida. Falta la clave "molecule_input".'}), 400
        
        # Obtenemos el valor enviado por el usuario.
        user_input = data['molecule_input']
        
        # 2. Llamar al handler para obtener la predicción
        # Toda la lógica de la IA está encapsulada en el handler.
        # AHORA ESTO DEVUELVE UN DICCIONARIO
        resultado_prediccion = model_handler.predecir_capacidad_antioxidante(user_input)
        
        # 3. Devolver una respuesta de éxito al frontend
        # Extraemos los datos del diccionario y los enviamos como JSON
        return jsonify({
            'prediction': resultado_prediccion['clase_texto'], # Ej: "Alta Capacidad Antioxidante"
            'confidence': resultado_prediccion['confianza_porcentaje'], # Ej: 85.5
            'class_id': resultado_prediccion['clase_numerica'] # Ej: 2 Nos sirve para cambiar los colores en el frontend
        })
        
    except ValueError as ve:
        # Captura errores controlados del handler (ej. SMILES inválido, nombre no encontrado)
        return jsonify({'error': str(ve)}), 400
        
    except Exception as e:
        # Captura cualquier otro error inesperado para que la app no se caiga.
        print(f"Error inesperado en /predict: {e}")
        return jsonify({'error': 'Ocurrió un error interno en el servidor. Por favor, contacta al administrador.'}), 500


# ERRORES PERSONALIZADOS: Manejo de errores comunes para mejorar la experiencia del usuario y facilitar la depuración.
@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404


#  Para Ejecutar el Servidor 
if __name__ == '__main__':
    # debug=True para desarrollo, el servidor se reinicia automáticamente con cada cambio.
    app.run(host='127.0.0.1', port=5000, debug=True)
