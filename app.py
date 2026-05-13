import os
import datetime
from functools import wraps
from flask import (
    Flask, jsonify, request, make_response,
    render_template, redirect, url_for
)
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from pymongo import MongoClient
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

# Crear la aplicación Flask
app = Flask(__name__)
CORS(app)

# Configuración de la base de datos SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'RestauranteNoSQL.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------- CONFIGURACIÓN MONGODB (NoSQL) --------------------
load_dotenv()
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client['restaurante_mensajes']
mensajes_collection = mongo_db['mensajes']

# ============================================================
# CONFIGURACIÓN JWT
# ============================================================
SECRET_KEY = "mi_clave_super_secreta_cambiar_en_produccion"
ALGORITHM = "HS256"
TOKEN_EXP_HOURS = 2
COOKIE_NAME = "jwt_token"

# -------------------- MODELOS SQL --------------------
class Usuario(db.Model):
    __tablename__ = 'Usuario'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100))
    telefono = db.Column(db.String(15))
    rol = db.Column(db.String(20), nullable=False)  # admin, mesero, cocinero, cajero
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # hash
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Categoria(db.Model):
    __tablename__ = 'Categoria'
    IdCategoria = db.Column(db.Integer, primary_key=True)
    NombreCategoria = db.Column(db.String(50), unique=True, nullable=False)

class Producto(db.Model):
    __tablename__ = 'Producto'
    IdProducto = db.Column(db.Integer, primary_key=True)
    IdCategoria = db.Column(db.Integer, db.ForeignKey('Categoria.IdCategoria'), nullable=False)
    NombreProducto = db.Column(db.String(100), nullable=False)
    Precio = db.Column(db.Numeric(10,2), nullable=False)
    categoria = db.relationship('Categoria', backref='productos')

class Mesa(db.Model):
    __tablename__ = 'Mesa'
    IdMesa = db.Column(db.Integer, primary_key=True)
    Capacidad = db.Column(db.Integer, nullable=False)
    Estado = db.Column(db.String(20), default='libre')

class Pedido(db.Model):
    __tablename__ = 'Pedido'
    IdPedido = db.Column(db.Integer, primary_key=True)
    IdMeso = db.Column(db.Integer, db.ForeignKey('Usuario.id'), nullable=False)
    IdMesa = db.Column(db.Integer, db.ForeignKey('Mesa.IdMesa'), nullable=False)
    Notas = db.Column(db.Text)
    FechaHora = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    Estado = db.Column(db.String(20), default='pendiente')
    TotalPedido = db.Column(db.Numeric(10,2), default=0)
    mesero = db.relationship('Usuario', foreign_keys=[IdMeso])
    mesa = db.relationship('Mesa')

class DetallePedido(db.Model):
    __tablename__ = 'DetallePedido'
    IdDetalle = db.Column(db.Integer, primary_key=True)
    IdPedido = db.Column(db.Integer, db.ForeignKey('Pedido.IdPedido'), nullable=False)
    IdProducto = db.Column(db.Integer, db.ForeignKey('Producto.IdProducto'), nullable=False)
    Cantidad = db.Column(db.Integer, nullable=False)
    Subtotal = db.Column(db.Numeric(10,2), default=0)
    pedido = db.relationship('Pedido', backref='detalles')
    producto = db.relationship('Producto')

class Cliente(db.Model):
    __tablename__ = 'Clientes'
    IdCliente = db.Column(db.Integer, primary_key=True)
    TipoDocumento = db.Column(db.String(20), nullable=False)
    NumeroDocumento = db.Column(db.String(50), unique=True, nullable=False)
    RazonSocial = db.Column(db.String(150))
    Nombre = db.Column(db.String(100), nullable=False)
    Apellido = db.Column(db.String(100))
    Email = db.Column(db.String(100))
    Telefono = db.Column(db.String(20))
    Direccion = db.Column(db.String(200))
    Ciudad = db.Column(db.String(100))

class Factura(db.Model):
    __tablename__ = 'Factura'
    IdFactura = db.Column(db.Integer, primary_key=True)
    IdPedido = db.Column(db.Integer, db.ForeignKey('Pedido.IdPedido'), nullable=False)
    IdCliente = db.Column(db.Integer, db.ForeignKey('Clientes.IdCliente'), nullable=False)
    FechaHora = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    MetodoPago = db.Column(db.String(20))
    ServicioVoluntario = db.Column(db.Numeric(10,2), default=0)
    TotalFactura = db.Column(db.Numeric(10,2), nullable=False)
    Estado = db.Column(db.String(20), default='pendiente')  # pendiente, pagada, anulada
    pedido = db.relationship('Pedido', backref='facturas')
    cliente = db.relationship('Cliente', backref='facturas')

# ============================================================
# UTILIDADES JWT
# ============================================================
def generar_token(user_id, email, rol, nombre):
    ahora = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub":    str(user_id),
        "email":  email,
        "rol":    rol,
        "nombre": nombre,
        "iat":    int(ahora.timestamp()),
        "exp":    int((ahora + datetime.timedelta(hours=TOKEN_EXP_HOURS)).timestamp()),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def obtener_payload_actual():
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

# ============================================================
# DECORADORES DE AUTORIZACIÓN (RBAC)
# ============================================================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        payload = obtener_payload_actual()
        if payload is None:
            return jsonify({"error": "Debes iniciar sesión"}), 401
        return f(payload, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        payload = obtener_payload_actual()
        if payload is None:
            return jsonify({"error": "Debes iniciar sesión"}), 401
        if payload.get("rol") != "admin":
            return jsonify({"error": "Acceso denegado. Se requiere rol de administrador"}), 403
        return f(payload, *args, **kwargs)
    return decorated

# ============================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================
@app.route('/api/registro', methods=['POST'])
def registro():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos requeridos"}), 400

    nombre = data.get("nombre", "").strip()
    apellido = data.get("apellido", "").strip()
    telefono = data.get("telefono", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    rol = data.get("rol", "").strip()

    if not nombre or not email or not password:
        return jsonify({"error": "Nombre, email y contraseña son obligatorios"}), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify({"error": "El email ya está registrado"}), 409

    roles_validos = ['mesero', 'cocinero', 'cajero', 'admin']
    if rol and rol not in roles_validos:
        return jsonify({"error": f"Rol no válido. Permisos: {', '.join(roles_validos)}"}), 400
    if not rol:
        rol = "mesero"

    hash_pw = generate_password_hash(password)
    nuevo_usuario = Usuario(
        nombre=nombre,
        apellido=apellido,
        telefono=telefono,
        email=email,
        password=hash_pw,
        rol=rol
    )
    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({
        "mensaje": "Usuario registrado correctamente",
        "id": nuevo_usuario.id,
        "email": nuevo_usuario.email,
        "rol": nuevo_usuario.rol
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos requeridos"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario or not check_password_hash(usuario.password, password):
        return jsonify({"error": "Correo o contraseña incorrectos"}), 401

    token = generar_token(
        user_id=usuario.id,
        email=usuario.email,
        rol=usuario.rol,
        nombre=usuario.nombre
    )

    response = make_response(jsonify({
        "mensaje": "Inicio de sesión exitoso",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol
        }
    }), 200)
    response.set_cookie(
        COOKIE_NAME, token,
        httponly=True,
        max_age=TOKEN_EXP_HOURS * 3600,
        samesite="Lax"
    )
    return response

@app.route('/api/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({"mensaje": "Sesión cerrada correctamente"}), 200)
    response.delete_cookie(COOKIE_NAME)
    return response

# ============================================================
# RUTAS DE LA API
# ============================================================
@app.route('/')
def inicio():
    return jsonify({"mensaje": "API de Restaurante funcionando 🍽️"})

# ---------- Productos ----------
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
@admin_required
def crear_producto(payload):
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
@admin_required
def actualizar_producto(payload, id):
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
@admin_required
def eliminar_producto(payload, id):
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

# ---------- Pedidos ----------
@app.route('/api/pedidos', methods=['POST'])
@login_required
def crear_pedido(payload):
    if payload['rol'] not in ('mesero', 'admin'):
        return jsonify({"error": "Solo meseros pueden crear pedidos"}), 403

    data = request.get_json()
    id_mesa = data.get('IdMesa')
    id_mesero = data.get('IdMeso', payload['sub'])
    items = data.get('productos')
    notas = data.get('Notas', '')

    if not id_mesa or not items:
        return jsonify({"mensaje": "Mesa y productos requeridos"}), 400

    mesa = Mesa.query.get(id_mesa)
    if not mesa:
        return jsonify({"mensaje": "Mesa no encontrada"}), 404
    if mesa.Estado not in ('libre', 'ocupada'):
        return jsonify({"mensaje": f"La mesa está en estado '{mesa.Estado}', no se pueden agregar pedidos"}), 400

    mesero = Usuario.query.get(id_mesero)
    if not mesero or mesero.rol not in ('mesero', 'admin'):
        return jsonify({"mensaje": "Mesero inválido"}), 400

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
    mesa.Estado = 'ocupada'
    db.session.commit()
    return jsonify({
        "IdPedido": pedido.IdPedido,
        "Estado": pedido.Estado,
        "TotalPedido": float(total),
        "mensaje": "Pedido creado"
    }), 201

@app.route('/api/pedidos/cocina', methods=['GET'])
@login_required
def pedidos_cocina(payload):
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

@app.route('/api/pedidos/mesero', methods=['GET'])
@login_required
def pedidos_mesero(payload):
    if payload['rol'] not in ('mesero', 'admin'):
        return jsonify({"error": "Acceso denegado"}), 403
    pedidos = Pedido.query.filter(
        Pedido.Estado.in_(['listo', 'entregado'])
    ).order_by(Pedido.FechaHora.desc()).all()
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
@login_required
def actualizar_estado_pedido(payload, id):
    data = request.get_json()
    nuevo_estado = data.get('estado')
    if not nuevo_estado:
        return jsonify({"mensaje": "Estado requerido"}), 400

    pedido = Pedido.query.get(id)
    if not pedido:
        return jsonify({"mensaje": "Pedido no encontrado"}), 404

    rol = payload['rol']

    # Cocinero (o admin) puede mover entre pendiente, en preparación y listo
    if rol in ('cocinero', 'admin'):
        if nuevo_estado not in ('pendiente', 'en preparación', 'listo'):
            return jsonify({"mensaje": "Solo puedes asignar los estados: pendiente, en preparación, listo"}), 403
        pedido.Estado = nuevo_estado
        db.session.commit()
        return jsonify({"IdPedido": id, "Estado": nuevo_estado, "mensaje": "Estado actualizado"}), 200

    # Mesero (o admin) solo puede cambiar de listo a entregado
    if rol in ('mesero', 'admin'):
        if pedido.Estado != 'listo':
            return jsonify({"mensaje": "Solo podés entregar pedidos que estén listos"}), 400
        if nuevo_estado != 'entregado':
            return jsonify({"mensaje": "Solo podés marcar el pedido como entregado"}), 403
        pedido.Estado = nuevo_estado
        db.session.commit()
        return jsonify({"IdPedido": id, "Estado": nuevo_estado, "mensaje": "Pedido entregado correctamente"}), 200

    return jsonify({"mensaje": "No tienes permiso para cambiar el estado"}), 403

# ---------- Facturación ----------
@app.route('/api/facturas', methods=['POST'])
@login_required
def generar_factura(payload):
    if payload['rol'] not in ('cajero', 'admin'):
        return jsonify({"error": "Solo cajeros pueden generar facturas"}), 403

    data = request.get_json()
    id_pedido = data.get('IdPedido')
    id_cliente = data.get('IdCliente')
    servicio_voluntario = data.get('ServicioVoluntario', 0)

    if not id_pedido or not id_cliente:
        return jsonify({"mensaje": "ID de pedido y cliente requeridos"}), 400

    pedido = Pedido.query.get(id_pedido)
    if not pedido:
        return jsonify({"mensaje": "Pedido no encontrado"}), 404
    if pedido.Estado not in ('entregado', 'listo'):
        return jsonify({"mensaje": "El pedido debe estar listo o entregado para facturar"}), 400

    cliente = Cliente.query.get(id_cliente)
    if not cliente:
        return jsonify({"mensaje": "Cliente no encontrado"}), 404

    total = float(pedido.TotalPedido) + servicio_voluntario

    factura = Factura(
        IdPedido=id_pedido,
        IdCliente=id_cliente,
        ServicioVoluntario=servicio_voluntario,
        TotalFactura=total,
        Estado='pendiente'
    )
    db.session.add(factura)

    pedido.Estado = 'facturado'
    mesa = Mesa.query.get(pedido.IdMesa)
    if mesa:
        mesa.Estado = 'en proceso de pago'

    db.session.commit()
    return jsonify({
        "IdFactura": factura.IdFactura,
        "TotalFactura": total,
        "mensaje": "Factura generada"
    }), 201

@app.route('/api/facturas/pendientes', methods=['GET'])
@login_required
def listar_facturas_pendientes(payload):
    if payload['rol'] not in ('cajero', 'admin'):
        return jsonify({"error": "Acceso denegado"}), 403
    facturas = Factura.query.filter(Factura.Estado == 'pendiente').all()
    resultado = []
    for f in facturas:
        pedido = Pedido.query.get(f.IdPedido)
        cliente = Cliente.query.get(f.IdCliente)
        resultado.append({
            "IdFactura": f.IdFactura,
            "IdPedido": f.IdPedido,
            "Mesa": pedido.IdMesa if pedido else None,
            "Cliente": cliente.Nombre if cliente else None,
            "TotalFactura": float(f.TotalFactura),
            "ServicioVoluntario": float(f.ServicioVoluntario) if f.ServicioVoluntario else 0,
            "FechaHora": f.FechaHora.isoformat() if f.FechaHora else None
        })
    return jsonify(resultado), 200

@app.route('/api/facturas/<int:id>/pagar', methods=['PUT'])
@login_required
def pagar_factura(payload, id):
    if payload['rol'] not in ('cajero', 'admin'):
        return jsonify({"error": "Solo cajeros pueden registrar pagos"}), 403

    data = request.get_json()
    metodo_pago = data.get('MetodoPago')
    monto_recibido = data.get('MontoRecibido')
    if not metodo_pago or not monto_recibido:
        return jsonify({"mensaje": "Método de pago y monto requeridos"}), 400

    factura = Factura.query.get(id)
    if not factura:
        return jsonify({"mensaje": "Factura no encontrada"}), 404

    factura.MetodoPago = metodo_pago
    factura.Estado = 'pagada'

    pedido = Pedido.query.get(factura.IdPedido)
    if pedido:
        mesa = Mesa.query.get(pedido.IdMesa)
        if mesa:
            otros_pedidos = Pedido.query.filter(
                Pedido.IdMesa == mesa.IdMesa,
                Pedido.Estado != 'facturado'
            ).count()
            if otros_pedidos == 0:
                mesa.Estado = 'libre'

    db.session.commit()
    return jsonify({
        "mensaje": "Pago registrado",
        "cambio": monto_recibido - float(factura.TotalFactura)
    }), 200

@app.route('/api/facturas/<int:id>/anular', methods=['PUT'])
@login_required
def anular_factura(payload, id):
    if payload['rol'] not in ('cajero', 'admin'):
        return jsonify({"error": "Solo cajeros pueden anular facturas"}), 403

    factura = Factura.query.get(id)
    if not factura:
        return jsonify({"mensaje": "Factura no encontrada"}), 404

    if factura.Estado != 'pendiente':
        return jsonify({"mensaje": "Solo se pueden anular facturas pendientes"}), 400

    factura.Estado = 'anulada'

    # Opcional: revertir pedido a 'entregado' para que se pueda facturar de nuevo
    pedido = Pedido.query.get(factura.IdPedido)
    if pedido and pedido.Estado == 'facturado':
        pedido.Estado = 'entregado'

    db.session.commit()
    return jsonify({"mensaje": "Factura anulada correctamente"}), 200

# ---------- Reportes ----------
@app.route('/api/reportes/ventas', methods=['GET'])
@login_required
def reporte_ventas(payload):
    if payload['rol'] not in ('admin', 'cajero'):
        return jsonify({"error": "Acceso no autorizado"}), 403

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    if not fecha_inicio or not fecha_fin:
        return jsonify({"mensaje": "fecha_inicio y fecha_fin requeridos"}), 400

    inicio = datetime.datetime.fromisoformat(fecha_inicio)
    fin = datetime.datetime.fromisoformat(fecha_fin) + datetime.timedelta(days=1, microseconds=-1)

    # Solo facturas pagadas (o anuladas? lo normal es contar solo pagadas)
    facturas = Factura.query.filter(
        Factura.FechaHora >= inicio,
        Factura.FechaHora <= fin,
        Factura.Estado == 'pagada'
    ).all()

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

# ---------- Gestión de usuarios (solo admin) ----------
@app.route('/api/usuarios', methods=['GET'])
@admin_required
def listar_usuarios(payload):
    usuarios = Usuario.query.all()
    return jsonify([{
        "id": u.id,
        "nombre": u.nombre,
        "apellido": u.apellido,
        "email": u.email,
        "telefono": u.telefono,
        "rol": u.rol,
        "created_at": u.created_at.isoformat() if u.created_at else None
    } for u in usuarios]), 200

@app.route('/api/usuarios/<int:id>', methods=['PUT'])
@admin_required
def actualizar_usuario(payload, id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos requeridos"}), 400

    # Campos editables
    if 'nombre' in data:
        usuario.nombre = data['nombre']
    if 'apellido' in data:
        usuario.apellido = data['apellido']
    if 'email' in data:
        # verificar que no exista otro con ese email
        email = data['email'].strip().lower()
        existente = Usuario.query.filter(Usuario.email == email, Usuario.id != id).first()
        if existente:
            return jsonify({"error": "El email ya está en uso"}), 409
        usuario.email = email
    if 'telefono' in data:
        usuario.telefono = data['telefono']
    if 'rol' in data:
        roles_validos = ['admin', 'mesero', 'cocinero', 'cajero']
        if data['rol'] not in roles_validos:
            return jsonify({"error": "Rol no válido"}), 400
        usuario.rol = data['rol']
    if 'password' in data and data['password']:
        usuario.password = generate_password_hash(data['password'])

    db.session.commit()
    return jsonify({"mensaje": "Usuario actualizado"}), 200

@app.route('/api/usuarios/<int:id>', methods=['DELETE'])
@admin_required
def eliminar_usuario(payload, id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # No permitir eliminar al propio admin?
    if usuario.id == int(payload['sub']):
        return jsonify({"error": "No puedes eliminar tu propio usuario"}), 403

    try:
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({"mensaje": "Usuario eliminado"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "No se pudo eliminar, tiene dependencias"}), 400

# ---------- Perfil combinado SQL + NoSQL ----------
@app.route('/api/clientes/<int:id_cliente>/perfil-completo', methods=['GET'])
@login_required
def perfil_completo_cliente(payload, id_cliente):
    cliente = Cliente.query.get(id_cliente)
    if not cliente:
        return jsonify({"error": "Cliente no encontrado"}), 404

    facturas = Factura.query.filter_by(IdCliente=id_cliente).all()
    facturas_list = [{
        "IdFactura": f.IdFactura,
        "IdPedido": f.IdPedido,
        "FechaHora": f.FechaHora.isoformat() if f.FechaHora else None,
        "MetodoPago": f.MetodoPago,
        "ServicioVoluntario": float(f.ServicioVoluntario) if f.ServicioVoluntario else 0,
        "TotalFactura": float(f.TotalFactura),
        "Estado": f.Estado
    } for f in facturas]

    mensajes = list(mensajes_collection.find({'idCliente': id_cliente}))
    for msg in mensajes:
        msg['_id'] = str(msg['_id'])

    return jsonify({
        "cliente": {
            "IdCliente": cliente.IdCliente,
            "TipoDocumento": cliente.TipoDocumento,
            "NumeroDocumento": cliente.NumeroDocumento,
            "RazonSocial": cliente.RazonSocial,
            "Nombre": cliente.Nombre,
            "Apellido": cliente.Apellido,
            "Email": cliente.Email,
            "Telefono": cliente.Telefono,
            "Direccion": cliente.Direccion,
            "Ciudad": cliente.Ciudad
        },
        "facturas": facturas_list,
        "mensajes_promocionales": mensajes
    })

# ============================================================
# RUTAS PARA LA INTERFAZ WEB
# ============================================================
@app.route('/login')
def login_page():
    if obtener_payload_actual():
        return redirect('/panel')
    return render_template('login.html')

@app.route('/registro')
def registro_page():
    if obtener_payload_actual():
        return redirect('/panel')
    return render_template('registro.html')

@app.route('/panel')
@login_required
def panel(payload):
    return render_template('dashboard.html', usuario=payload)

# ============================================================
# CREAR TABLAS Y ADMIN POR DEFECTO
# ============================================================
with app.app_context():
    db.create_all()

    admin_email = "admin@restaurante.com"
    admin_password = "admin123"
    if not Usuario.query.filter_by(email=admin_email).first():
        admin = Usuario(
            nombre="Admin",
            apellido="Principal",
            email=admin_email,
            password=generate_password_hash(admin_password),
            rol="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print(f"✅ Usuario administrador creado: {admin_email} / {admin_password}")
    else:
        print("ℹ️  Ya existe un usuario administrador.")
        print("Usuario: " + admin_email)
        print("Contraseña: " + admin_password)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
