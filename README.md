# Restaurant API

API REST para la gestión de pedidos, facturación y reportes en un restaurante. Desarrollada con Flask y SQLite.

## Características

- Gestión de productos y categorías.
- Administración de mesas y su estado (libre, ocupada, en proceso de pago).
- Creación y seguimiento de pedidos con estado (pendiente, en preparación, listo, entregado, facturado).
- Facturación con servicio voluntario y registro de pagos.
- Reportes de ventas por rango de fechas (ingresos totales, platos más vendidos).

## Tecnologías

- Python 3.8+
- Flask
- Flask-SQLAlchemy
- SQLite
- Flask-CORS

## Instalación y ejecución local
1. Crear y activar un entorno virtual
  python -m venv venv
venv\Scripts\activate
2. Instalar dependencias
  pip install -r requirements.txt
3. Ejecutar el archivo init_db.py
   python init_db.py
5. Ejecutar el archivo app.py
   python app.py
6. Probar los endpoints
Puedes usar Postman, Insomnia, cURL para probar los diferentes endpoints.

Ejemplos de peticiones
Listar todos los productos
GET http://127.0.0.1:5000/api/productos

Crear un nuevo producto
POST http://127.0.0.1:5000/api/productos
Body (JSON):
  
