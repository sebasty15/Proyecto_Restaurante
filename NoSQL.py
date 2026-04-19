#Conexion
from pymongo import MongoClient
mongo_con = MongoClient('mongodb+srv://sebasty1508_db_user:juan123@cluster0.khyr9yh.mongodb.net/?appName=Cluster0')
print(mongo_con.list_database_names())

#Seleccionar bd 
 #Seleccionar base de datos 'prueba'
db_pruebas = mongo_con['restaurante_mensajes']
#Listar las colecciones de la base de datos 'prueba'
print(db_pruebas.list_collection_names())

#Sentencias CRUD
#crear colección
db_pruebas.create_collection('mensajes')
print(db_pruebas.list_collection_names())

#Eliminar colección
db_pruebas.drop_collection('empleados')
print(db_pruebas.list_collection_names())

#Seleccionar colección 'mensajes' de la base de datos 'prueba'
coleccion_mensajes = db_pruebas['mensajes']

coleccion_mensajes.insert_one({
  "_id": "m001",
  "idCliente": 123,
  "canal": "email",
  "campana": "verano2026",
  "asunto": "20% de descuento",
  "contenido": {
    "texto": "Ven con tu familia...",
    "codigo": "VERANO20"
  }
})

mensajes = coleccion_mensajes.find({})
for asv in mensajes:
  print(f"{asv.get('_id')} : {asv.get('campana')} - {asv.get('asunto')} - {asv.get('contenido', {}).get('texto')}")
  
mensajes.update_one(
  {"asunto": "20% de descuento"},
  {"$set": {"asunto": "35% de descuento"}}
)