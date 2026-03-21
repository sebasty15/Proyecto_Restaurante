import sqlite3

def setup_database():
    try:
        conn = sqlite3.connect("RestauranteFinal.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Tabla Categoría
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

        # Tabla Mesero
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Mesero (
                IdMesero INTEGER PRIMARY KEY AUTOINCREMENT,
                NombreMesero VARCHAR(50) NOT NULL,
                ApellidoMesero VARCHAR(50) NOT NULL,
                TelefonoMesero VARCHAR(15)
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
                FOREIGN KEY (IdMeso) REFERENCES Mesero(IdMesero) ON DELETE RESTRICT,
                FOREIGN KEY (IdMesa) REFERENCES Mesa(IdMesa) ON DELETE RESTRICT
            )
        ''')

        # Tabla DetallePedido con clave primaria simple (IdDetalle) y foreign keys
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

        # Tabla Factura (relación muchos a uno con Pedido)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Factura (
                IdFactura INTEGER PRIMARY KEY AUTOINCREMENT,
                IdPedido INTEGER NOT NULL,
                FechaHora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                MetodoPago TEXT CHECK(MetodoPago IN ('efectivo', 'tarjeta', 'transferencia')),
                ServicioVoluntario DECIMAL(10,2) DEFAULT 0 CHECK(ServicioVoluntario >= 0),
                TotalFactura DECIMAL(10,2) NOT NULL CHECK(TotalFactura >= 0),
                FOREIGN KEY (IdPedido) REFERENCES Pedido(IdPedido) ON DELETE RESTRICT
            )
        ''')

        seed_data(cursor)
        conn.commit()
        print("Base de datos creada exitosamente con las nuevas tablas.")

    except sqlite3.Error as e:
        print(f"Error al crear la base de datos: {e}")
    finally:
        if conn:
            conn.close()

def seed_data(cursor):
    # Limpiar tablas (orden inverso por dependencias)
    cursor.execute("DELETE FROM Factura")
    cursor.execute("DELETE FROM DetallePedido")
    cursor.execute("DELETE FROM Pedido")
    cursor.execute("DELETE FROM Producto")
    cursor.execute("DELETE FROM Categoria")
    cursor.execute("DELETE FROM Mesa")
    cursor.execute("DELETE FROM Mesero")

    # Reiniciar contadores autoincrementales
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='Categoria'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='Producto'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='Mesa'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='Mesero'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='Pedido'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='DetallePedido'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='Factura'")

    # --- Categorías ---
    categorias = [
        ("Entradas",),
        ("Platos fuertes",),
        ("Bebidas",),
        ("Postres",)
    ]
    for (nombre,) in categorias:
        cursor.execute('''
            INSERT INTO Categoria (NombreCategoria)
            VALUES (?)
        ''', (nombre,))

    # Obtener IDs de categorías
    cursor.execute("SELECT IdCategoria, NombreCategoria FROM Categoria")
    cat_map = {nombre: id for id, nombre in cursor.fetchall()}

    # --- Productos ---
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
        cursor.execute('''
            INSERT INTO Producto (NombreProducto, IdCategoria, Precio)
            VALUES (?, ?, ?)
        ''', (nombre, id_cat, precio))

    # --- Mesas ---
    mesas = [
        (4, 'libre'),
        (2, 'libre'),
        (6, 'libre'),
        (4, 'libre'),
        (8, 'libre')
    ]
    for capacidad, estado in mesas:
        cursor.execute('''
            INSERT INTO Mesa (Capacidad, Estado)
            VALUES (?, ?)
        ''', (capacidad, estado))

    # --- Meseros ---
    meseros = [
        ("Juan", "Pérez", "3001111111"),
        ("Ana", "Gómez", "3002222222")
    ]
    for nombre, apellido, telefono in meseros:
        cursor.execute('''
            INSERT INTO Mesero (NombreMesero, ApellidoMesero, TelefonoMesero)
            VALUES (?, ?, ?)
        ''', (nombre, apellido, telefono))

    # --- Pedido de ejemplo ---
    # Obtener IDs de mesero y mesa
    cursor.execute("SELECT IdMesero FROM Mesero LIMIT 1")
    mesero_id = cursor.fetchone()[0]
    cursor.execute("SELECT IdMesa FROM Mesa WHERE Estado = 'libre' LIMIT 1")
    mesa_id = cursor.fetchone()[0]

    cursor.execute('''
        INSERT INTO Pedido (IdMeso, IdMesa, Notas, Estado, TotalPedido)
        VALUES (?, ?, ?, 'entregado', 0)
    ''', (mesero_id, mesa_id, "Ejemplo de pedido"))
    pedido_id = cursor.lastrowid

    # --- Detalles del pedido (usando IdDetalle como PK) ---
    # Hamburguesa Clásica (2 unidades)
    cursor.execute("SELECT IdProducto, Precio FROM Producto WHERE NombreProducto = 'Hamburguesa Clásica'")
    prod_id, precio = cursor.fetchone()
    cantidad = 2
    subtotal = cantidad * precio
    cursor.execute('''
        INSERT INTO DetallePedido (IdPedido, IdProducto, Cantidad, Subtotal)
        VALUES (?, ?, ?, ?)
    ''', (pedido_id, prod_id, cantidad, subtotal))

    # Refresco de cola (1 unidad)
    cursor.execute("SELECT IdProducto, Precio FROM Producto WHERE NombreProducto = 'Refresco de cola'")
    prod_id, precio = cursor.fetchone()
    cantidad = 1
    subtotal = cantidad * precio
    cursor.execute('''
        INSERT INTO DetallePedido (IdPedido, IdProducto, Cantidad, Subtotal)
        VALUES (?, ?, ?, ?)
    ''', (pedido_id, prod_id, cantidad, subtotal))

    # Actualizar TotalPedido sumando subtotales de los detalles
    cursor.execute('''
        UPDATE Pedido SET TotalPedido = (
            SELECT SUM(Subtotal) FROM DetallePedido WHERE IdPedido = ?
        )
        WHERE IdPedido = ?
    ''', (pedido_id, pedido_id))

    # --- Factura de ejemplo ---
    cursor.execute('''
        INSERT INTO Factura (IdPedido, MetodoPago, ServicioVoluntario, TotalFactura)
        VALUES (?, 'efectivo', 0.0, (SELECT TotalPedido FROM Pedido WHERE IdPedido = ?))
    ''', (pedido_id, pedido_id))

    print("Datos de ejemplo insertados correctamente.")

if __name__ == "__main__":
    setup_database()