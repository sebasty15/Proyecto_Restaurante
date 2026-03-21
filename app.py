import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import datetime
from dotenv import load_dotenv

# Crear la aplicación Flask
app = Flask(__name__)
CORS(app)

# Configuración de la base de datos SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'RestauranteFinal.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------- MODELOS (adaptados al esquema SQLite) --------------------
class Usuario(db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100))
    telefono = db.Column(db.String(15))
    rol = db.Column(db.String(20), nullable=False)  # mesero, cocinero, cajero, admin
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Categoria(db.Model):
    __tablename__ = 'categoria'
    IdCategoria = db.Column(db.Integer, primary_key=True)
    NombreCategoria = db.Column(db.String(50), unique=True, nullable=False)

class Producto(db.Model):
    __tablename__ = 'producto'
    IdProducto = db.Column(db.Integer, primary_key=True)
    IdCategoria = db.Column(db.Integer, db.ForeignKey('categoria.IdCategoria'), nullable=False)
    NombreProducto = db.Column(db.String(100), nullable=False)
    Precio = db.Column(db.Numeric(10,2), nullable=False)

    categoria = db.relationship('Categoria', backref='productos')

class Mesa(db.Model):
    __tablename__ = 'mesa'
    IdMesa = db.Column(db.Integer, primary_key=True)
    Capacidad = db.Column(db.Integer, nullable=False)
    Estado = db.Column(db.String(20), default='libre')

class Pedido(db.Model):
    __tablename__ = 'pedido'
    IdPedido = db.Column(db.Integer, primary_key=True)
    IdMeso = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    IdMesa = db.Column(db.Integer, db.ForeignKey('mesa.IdMesa'), nullable=False)
    Notas = db.Column(db.Text)
    FechaHora = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    Estado = db.Column(db.String(20), default='pendiente')
    TotalPedido = db.Column(db.Numeric(10,2), default=0)

    mesero = db.relationship('Usuario', foreign_keys=[IdMeso])
    mesa = db.relationship('Mesa')

class DetallePedido(db.Model):
    __tablename__ = 'detallepedido'
    IdDetalle = db.Column(db.Integer, primary_key=True)
    IdPedido = db.Column(db.Integer, db.ForeignKey('pedido.IdPedido'), nullable=False)
    IdProducto = db.Column(db.Integer, db.ForeignKey('producto.IdProducto'), nullable=False)
    Cantidad = db.Column(db.Integer, nullable=False)
    Subtotal = db.Column(db.Numeric(10,2), default=0)

    pedido = db.relationship('Pedido', backref='detalles')
    producto = db.relationship('Producto')

class Factura(db.Model):
    __tablename__ = 'factura'
    IdFactura = db.Column(db.Integer, primary_key=True)
    IdPedido = db.Column(db.Integer, db.ForeignKey('pedido.IdPedido'), nullable=False)
    FechaHora = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    MetodoPago = db.Column(db.String(20))
    ServicioVoluntario = db.Column(db.Numeric(10,2), default=0)
    TotalFactura = db.Column(db.Numeric(10,2), nullable=False)

    pedido = db.relationship('Pedido', backref='facturas')

# -------------------- RUTAS (sin autenticación) --------------------
@app.route('/')
def inicio():
    return jsonify({"mensaje": "API de Restaurante funcionando 🍽️ (sin autenticación)"})

# ----- Productos -----
@app.route('/api/productos', methods=['GET'])
def obtener_productos():
    productos = Producto.query.all()
    return jsonify([{
        "IdProducto": p.IdProducto,
        "NombreProducto": p.NombreProducto,
        "Precio": float(p.Precio),
        "IdCategoria": p.IdCategoria,
        "Categoria": p.categoria.NombreCategoria if p.categoria else None
    } for p in productos]), 200

@app.route('/api/productos', methods=['POST'])
def crear_producto():
    data = request.get_json()
    if not data or 'NombreProducto' not in data or 'Precio' not in data or 'IdCategoria' not in data:
        return jsonify({"error": "Datos inválidos"}), 400

    categoria = Categoria.query.get(data['IdCategoria'])
    if not categoria:
        return jsonify({"error": "Categoría no encontrada"}), 404

    nuevo = Producto(
        NombreProducto=data['NombreProducto'],
        Precio=data['Precio'],
        IdCategoria=data['IdCategoria']
    )
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({
        "IdProducto": nuevo.IdProducto,
        "NombreProducto": nuevo.NombreProducto,
        "Precio": float(nuevo.Precio),
        "mensaje": "Producto creado"
    }), 201

@app.route('/api/productos/<int:id>', methods=['PUT'])
def actualizar_producto(id):
    producto = Producto.query.get(id)
    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos inválidos"}), 400

    if 'NombreProducto' in data:
        producto.NombreProducto = data['NombreProducto']
    if 'Precio' in data:
        producto.Precio = data['Precio']
    if 'IdCategoria' in data:
        if not Categoria.query.get(data['IdCategoria']):
            return jsonify({"error": "Categoría no encontrada"}), 404
        producto.IdCategoria = data['IdCategoria']

    db.session.commit()
    return jsonify({
        "IdProducto": producto.IdProducto,
        "NombreProducto": producto.NombreProducto,
        "Precio": float(producto.Precio),
        "IdCategoria": producto.IdCategoria
    }), 200

@app.route('/api/productos/<int:id>', methods=['DELETE'])
def eliminar_producto(id):
    producto = Producto.query.get(id)
    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404
    try:
        db.session.delete(producto)
        db.session.commit()
        return jsonify({"mensaje": "Producto eliminado"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "No se puede eliminar, tiene dependencias"}), 400

# ----- Pedidos -----
@app.route('/api/pedidos', methods=['POST'])
def crear_pedido():
    data = request.get_json()
    id_mesa = data.get('IdMesa')
    id_mesero = data.get('IdMeso')  # Ahora se envía en el cuerpo
    items = data.get('productos')
    notas = data.get('Notas', '')
    if not id_mesa or not items or not id_mesero:
        return jsonify({"mensaje": "Mesa, mesero y productos requeridos"}), 400

    mesa = Mesa.query.get(id_mesa)
    if not mesa:
        return jsonify({"mensaje": "Mesa no encontrada"}), 404
    if mesa.Estado != 'libre':
        return jsonify({"mensaje": "La mesa no está libre"}), 400

    # Verificar que el mesero existe
    mesero = Usuario.query.get(id_mesero)
    if not mesero or mesero.rol != 'mesero':
        return jsonify({"mensaje": "Mesero inválido"}), 400

    # Crear pedido
    pedido = Pedido(
        IdMeso=id_mesero,
        IdMesa=id_mesa,
        Notas=notas,
        Estado='pendiente',
        TotalPedido=0
    )
    db.session.add(pedido)
    db.session.flush()

    total = 0
    for item in items:
        producto = Producto.query.get(item['IdProducto'])
        if not producto:
            db.session.rollback()
            return jsonify({"mensaje": f"Producto {item['IdProducto']} no encontrado"}), 400
        cantidad = item['Cantidad']
        subtotal = cantidad * producto.Precio
        detalle = DetallePedido(
            IdPedido=pedido.IdPedido,
            IdProducto=producto.IdProducto,
            Cantidad=cantidad,
            Subtotal=subtotal
        )
        db.session.add(detalle)
        total += subtotal

    pedido.TotalPedido = total

    # Cambiar estado de mesa a ocupada
    mesa.Estado = 'ocupada'

    db.session.commit()
    return jsonify({
        "IdPedido": pedido.IdPedido,
        "Estado": pedido.Estado,
        "TotalPedido": float(total),
        "mensaje": "Pedido creado"
    }), 201

@app.route('/api/pedidos/cocina', methods=['GET'])
def pedidos_cocina():
    pedidos = Pedido.query.filter(Pedido.Estado.in_(['pendiente', 'en preparación'])).all()
    resultado = []
    for p in pedidos:
        mesa = Mesa.query.get(p.IdMesa)
        detalles = []
        for d in p.detalles:
            detalles.append({
                "IdProducto": d.IdProducto,
                "NombreProducto": d.producto.NombreProducto,
                "Cantidad": d.Cantidad,
                "Subtotal": float(d.Subtotal)
            })
        resultado.append({
            "IdPedido": p.IdPedido,
            "Mesa": mesa.IdMesa if mesa else None,
            "FechaHora": p.FechaHora.isoformat(),
            "Estado": p.Estado,
            "Notas": p.Notas,
            "TotalPedido": float(p.TotalPedido),
            "items": detalles
        })
    return jsonify(resultado), 200

@app.route('/api/pedidos/<int:id>/estado', methods=['PUT'])
def actualizar_estado_pedido(id):
    data = request.get_json()
    nuevo_estado = data.get('estado')
    if not nuevo_estado:
        return jsonify({"mensaje": "Estado requerido"}), 400
    estados_validos = ['pendiente', 'en preparación', 'listo', 'entregado', 'facturado']
    if nuevo_estado not in estados_validos:
        return jsonify({"mensaje": "Estado no válido"}), 400

    pedido = Pedido.query.get(id)
    if not pedido:
        return jsonify({"mensaje": "Pedido no encontrado"}), 404

    pedido.Estado = nuevo_estado
    db.session.commit()
    return jsonify({"IdPedido": id, "Estado": nuevo_estado, "mensaje": "Estado actualizado"}), 200

# ----- Facturación -----
@app.route('/api/facturas', methods=['POST'])
def generar_factura():
    data = request.get_json()
    id_pedido = data.get('IdPedido')
    id_cajero = data.get('IdCajero')
    servicio_voluntario = data.get('ServicioVoluntario', 0)
    metodo_pago = data.get('MetodoPago')

    if not id_pedido or not id_cajero:
        return jsonify({"mensaje": "ID de pedido y cajero requeridos"}), 400

    pedido = Pedido.query.get(id_pedido)
    if not pedido:
        return jsonify({"mensaje": "Pedido no encontrado"}), 404
    if pedido.Estado != 'entregado':
        return jsonify({"mensaje": "El pedido debe estar entregado para facturar"}), 400

    # Verificar cajero
    cajero = Usuario.query.get(id_cajero)
    if not cajero or cajero.rol != 'cajero':
        return jsonify({"mensaje": "Cajero inválido"}), 400

    total = float(pedido.TotalPedido) + servicio_voluntario

    factura = Factura(
        IdPedido=id_pedido,
        MetodoPago=metodo_pago,
        ServicioVoluntario=servicio_voluntario,
        TotalFactura=total
    )
    db.session.add(factura)

    # Cambiar estado del pedido a facturado
    pedido.Estado = 'facturado'

    # Cambiar estado de la mesa a 'en proceso de pago'
    mesa = Mesa.query.get(pedido.IdMesa)
    if mesa:
        mesa.Estado = 'en proceso de pago'

    db.session.commit()
    return jsonify({
        "IdFactura": factura.IdFactura,
        "TotalFactura": total,
        "mensaje": "Factura generada"
    }), 201

@app.route('/api/facturas/<int:id>/pagar', methods=['PUT'])
def pagar_factura(id):
    data = request.get_json()
    metodo_pago = data.get('MetodoPago')
    monto_recibido = data.get('MontoRecibido')
    if not metodo_pago or not monto_recibido:
        return jsonify({"mensaje": "Método de pago y monto requeridos"}), 400

    factura = Factura.query.get(id)
    if not factura:
        return jsonify({"mensaje": "Factura no encontrada"}), 404

    factura.MetodoPago = metodo_pago

    # Liberar mesa
    pedido = Pedido.query.get(factura.IdPedido)
    if pedido:
        mesa = Mesa.query.get(pedido.IdMesa)
        if mesa:
            mesa.Estado = 'libre'

    db.session.commit()
    return jsonify({
        "mensaje": "Pago registrado",
        "cambio": monto_recibido - float(factura.TotalFactura)
    }), 200

# ----- Reportes -----
@app.route('/api/reportes/ventas', methods=['GET'])
def reporte_ventas():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    if not fecha_inicio or not fecha_fin:
        return jsonify({"mensaje": "fecha_inicio y fecha_fin requeridos"}), 400

    inicio = datetime.datetime.fromisoformat(fecha_inicio)
    fin = datetime.datetime.fromisoformat(fecha_fin)

    facturas = Factura.query.filter(Factura.FechaHora >= inicio, Factura.FechaHora <= fin).all()

    ingresos_totales = sum(float(f.TotalFactura) for f in facturas)
    cantidad_facturas = len(facturas)

    platos = {}
    for f in facturas:
        pedido = Pedido.query.get(f.IdPedido)
        if pedido:
            for detalle in pedido.detalles:
                nombre = detalle.producto.NombreProducto
                platos[nombre] = platos.get(nombre, 0) + detalle.Cantidad

    platos_mas_vendidos = [{"producto": k, "cantidad": v} for k, v in sorted(platos.items(), key=lambda x: x[1], reverse=True)]

    return jsonify({
        "ingresos_totales": ingresos_totales,
        "cantidad_facturas": cantidad_facturas,
        "platos_mas_vendidos": platos_mas_vendidos
    }), 200

# -------------------- CREAR TABLAS (si no existen) --------------------
with app.app_context():
    db.create_all()

# -------------------- EJECUCIÓN --------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)