# run.py
from app import create_app
import os

# Llama a la fábrica para crear la instancia de la aplicación
app = create_app()

# Esta parte solo se ejecuta si corres 'python run.py' localmente para pruebas
if __name__ == '__main__':
    # El puerto se puede tomar de una variable de entorno, útil para algunos despliegues
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)