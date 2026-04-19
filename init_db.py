import sqlite3
import datetime

def setup_database():
    try:
        conn = sqlite3.connect("RestauranteNoSQL.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Tabla Usuario (reemplaza a Mesero)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Usuario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre VARCHAR(100) NOT NULL,
                apellido VARCHAR(100),
                telefono VARCHAR(15),
                rol VARCHAR(20) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla Categoria
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Categoria (
                IdCategoria INTEGER PRIMARY KEY AUTOINCREMENT,
                NombreCategoria VARCHAR(50) NOT NULL UNIQUE
            )
        ''')

        # Tabla Producto
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Producto (
                IdProducto INTEGER PRIMARY KEY AUTOINCREMENT,
                IdCategoria INTEGER NOT NULL,
                NombreProducto VARCHAR(100) NOT NULL,
                Precio DECIMAL(10,2) NOT NULL CHECK(Precio >= 0),
                FOREIGN KEY (IdCategoria) REFERENCES Categoria(IdCategoria) ON DELETE RESTRICT
            )
        ''')

        # Tabla Mesa
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Mesa (
                IdMesa INTEGER PRIMARY KEY AUTOINCREMENT,
                Capacidad INTEGER NOT NULL CHECK(Capacidad > 0),
                Estado TEXT DEFAULT 'libre' CHECK(Estado IN ('libre', 'ocupada', 'en proceso de pago'))
            )
        ''')

        # Tabla Pedido
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Pedido (
                IdPedido INTEGER PRIMARY KEY AUTOINCREMENT,
                IdMeso INTEGER NOT NULL,
                IdMesa INTEGER NOT NULL,
                Notas TEXT,
                FechaHora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                Estado TEXT DEFAULT 'pendiente' CHECK(Estado IN ('pendiente', 'en preparación', 'listo', 'entregado', 'facturado')),
                TotalPedido DECIMAL(10,2) DEFAULT 0 CHECK(TotalPedido >= 0),
                FOREIGN KEY (IdMeso) REFERENCES Usuario(id) ON DELETE RESTRICT,
                FOREIGN KEY (IdMesa) REFERENCES Mesa(IdMesa) ON DELETE RESTRICT
            )
        ''')

        # Tabla DetallePedido
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS DetallePedido (
                IdDetalle INTEGER PRIMARY KEY AUTOINCREMENT,
                IdPedido INTEGER NOT NULL,
                IdProducto INTEGER NOT NULL,
                Cantidad INTEGER NOT NULL CHECK(Cantidad > 0),
                Subtotal DECIMAL(10,2) NOT NULL DEFAULT 0,
                FOREIGN KEY (IdPedido) REFERENCES Pedido(IdPedido) ON DELETE CASCADE,
                FOREIGN KEY (IdProducto) REFERENCES Producto(IdProducto) ON DELETE RESTRICT
            )
        ''')

        # Tabla Clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Clientes (
                IdCliente INTEGER PRIMARY KEY AUTOINCREMENT,
                TipoDocumento VARCHAR(20) NOT NULL,
                NumeroDocumento VARCHAR(50) NOT NULL UNIQUE,
                RazonSocial VARCHAR(150),
                Nombre VARCHAR(100) NOT NULL,
                Apellido VARCHAR(100),
                Email VARCHAR(100),
                Telefono VARCHAR(20),
                Direccion VARCHAR(200),
                Ciudad VARCHAR(100)
            )
        ''')

        # Tabla Factura
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Factura (
                IdFactura INTEGER PRIMARY KEY AUTOINCREMENT,
                IdPedido INTEGER NOT NULL,
                IdCliente INTEGER NOT NULL,
                FechaHora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                MetodoPago TEXT CHECK(MetodoPago IN ('efectivo', 'tarjeta', 'transferencia')),
                ServicioVoluntario DECIMAL(10,2) DEFAULT 0 CHECK(ServicioVoluntario >= 0),
                TotalFactura DECIMAL(10,2) NOT NULL CHECK(TotalFactura >= 0),
                FOREIGN KEY (IdPedido) REFERENCES Pedido(IdPedido) ON DELETE RESTRICT,
                FOREIGN KEY (IdCliente) REFERENCES Clientes(IdCliente) ON DELETE RESTRICT
            )
        ''')

        seed_data(cursor)
        conn.commit()
        print("Base de datos creada exitosamente con las tablas corregidas.")
    except sqlite3.Error as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

def seed_data(cursor):
    # Limpiar tablas (orden inverso)
    cursor.execute("DELETE FROM Factura")
    cursor.execute("DELETE FROM DetallePedido")
    cursor.execute("DELETE FROM Pedido")
    cursor.execute("DELETE FROM Producto")
    cursor.execute("DELETE FROM Categoria")
    cursor.execute("DELETE FROM Mesa")
    cursor.execute("DELETE FROM Usuario")
    cursor.execute("DELETE FROM Clientes")

    # Reiniciar secuencias
    for tabla in ['Usuario', 'Categoria', 'Producto', 'Mesa', 'Pedido', 'DetallePedido', 'Clientes', 'Factura']:
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{tabla}'")

    # Categorías
    categorias = [("Entradas",), ("Platos fuertes",), ("Bebidas",), ("Postres",)]
    for (nombre,) in categorias:
        cursor.execute("INSERT INTO Categoria (NombreCategoria) VALUES (?)", (nombre,))

    cursor.execute("SELECT IdCategoria, NombreCategoria FROM Categoria")
    cat_map = {nombre: id for id, nombre in cursor.fetchall()}

    # Productos
    productos = [
        ("Ensalada César", cat_map["Entradas"], 9.90),
        ("Papas fritas", cat_map["Entradas"], 5.50),
        ("Hamburguesa Clásica", cat_map["Platos fuertes"], 12.50),
        ("Lomo saltado", cat_map["Platos fuertes"], 15.00),
        ("Refresco de cola", cat_map["Bebidas"], 3.50),
        ("Agua mineral", cat_map["Bebidas"], 2.00),
        ("Tarta de manzana", cat_map["Postres"], 6.00)
    ]
    for nombre, id_cat, precio in productos:
        cursor.execute("INSERT INTO Producto (NombreProducto, IdCategoria, Precio) VALUES (?, ?, ?)",
                       (nombre, id_cat, precio))

    # Mesas
    mesas = [(4, 'libre'), (2, 'libre'), (6, 'libre'), (4, 'libre'), (8, 'libre')]
    for capacidad, estado in mesas:
        cursor.execute("INSERT INTO Mesa (Capacidad, Estado) VALUES (?, ?)", (capacidad, estado))

    # Usuarios (meseros y cajero)
    usuarios = [
        ("Juan", "Pérez", "3001111111", "mesero", "juan@resto.com", "1234"),
        ("Ana", "Gómez", "3002222222", "mesero", "ana@resto.com", "1234"),
        ("Carlos", "López", "3003333333", "cajero", "carlos@resto.com", "1234")
    ]
    for nombre, apellido, telefono, rol, email, pwd in usuarios:
        cursor.execute('''
            INSERT INTO Usuario (nombre, apellido, telefono, rol, email, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, apellido, telefono, rol, email, pwd))

    # Cliente ejemplo
    cursor.execute('''
        INSERT INTO Clientes (TipoDocumento, NumeroDocumento, Nombre, Apellido, Email, Telefono, Direccion, Ciudad)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('Cédula', '12345678', 'Carlos', 'López', 'carlos@mail.com', '3003334444', 'Calle Falsa 123', 'Bogotá'))
    id_cliente = cursor.lastrowid

    # Pedido ejemplo
    cursor.execute("SELECT id FROM Usuario WHERE rol='mesero' LIMIT 1")
    mesero_id = cursor.fetchone()[0]
    cursor.execute("SELECT IdMesa FROM Mesa WHERE Estado='libre' LIMIT 1")
    mesa_id = cursor.fetchone()[0]

    cursor.execute('''
        INSERT INTO Pedido (IdMeso, IdMesa, Notas, Estado, TotalPedido)
        VALUES (?, ?, ?, 'entregado', 0)
    ''', (mesero_id, mesa_id, "Ejemplo de pedido"))
    pedido_id = cursor.lastrowid

    # Detalles
    cursor.execute("SELECT IdProducto, Precio FROM Producto WHERE NombreProducto = 'Hamburguesa Clásica'")
    prod_id, precio = cursor.fetchone()
    cantidad = 2
    subtotal = cantidad * precio
    cursor.execute("INSERT INTO DetallePedido (IdPedido, IdProducto, Cantidad, Subtotal) VALUES (?, ?, ?, ?)",
                   (pedido_id, prod_id, cantidad, subtotal))

    cursor.execute("SELECT IdProducto, Precio FROM Producto WHERE NombreProducto = 'Refresco de cola'")
    prod_id, precio = cursor.fetchone()
    cantidad = 1
    subtotal = cantidad * precio
    cursor.execute("INSERT INTO DetallePedido (IdPedido, IdProducto, Cantidad, Subtotal) VALUES (?, ?, ?, ?)",
                   (pedido_id, prod_id, cantidad, subtotal))

    # Actualizar total pedido
    cursor.execute('''
        UPDATE Pedido SET TotalPedido = (SELECT SUM(Subtotal) FROM DetallePedido WHERE IdPedido = ?)
        WHERE IdPedido = ?
    ''', (pedido_id, pedido_id))

    # Factura ejemplo
    cursor.execute('''
        INSERT INTO Factura (IdPedido, IdCliente, MetodoPago, ServicioVoluntario, TotalFactura)
        VALUES (?, ?, 'efectivo', 0.0, (SELECT TotalPedido FROM Pedido WHERE IdPedido = ?))
    ''', (pedido_id, id_cliente, pedido_id))

    print("Datos de ejemplo insertados correctamente.")

if __name__ == "__main__":
    setup_database()
