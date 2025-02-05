from fastapi import FastAPI, File, UploadFile, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from py2neo import Graph, Node, NodeMatcher
import ollama
import os

app = FastAPI()

# ✅ Configurar CORS correctamente
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Conexión a Neo4j
NEO4J_URI = "bolt://localhost:7687"  # Ajusta según tu configuración
try:
    graph = Graph(NEO4J_URI)
    matcher = NodeMatcher(graph)
    print("✅ Conexión a Neo4j exitosa")
except Exception as e:
    print(f"❌ Error al conectar a Neo4j: {e}")
    raise HTTPException(status_code=500, detail="No se pudo conectar a la base de datos")

# ✅ Modelo para preguntas
class QuestionRequest(BaseModel):
    question: str

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de MediStruct"}

# ✅ 🔥 Solución definitiva para OPTIONS
@app.options("/{full_path:path}")
async def preflight_request(full_path: str):
    return Response(status_code=200, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })

@app.post("/ask/")
async def ask_question(request: QuestionRequest):
    try:
        # ✅ Recuperar documentos almacenados en Neo4j
        documentos = list(matcher.match("Documento"))
        if not documentos:
            return {"response": "No hay documentos almacenados en la base de datos."}
        
        # ✅ Construir el contexto con los documentos almacenados
        contexto = "\n".join([f"Documento: {doc['nombre']}, Ruta: {doc['ruta']}" for doc in documentos])

        # ✅ Enviar la pregunta a Phi-3.5 con el contexto
        mensaje = f"Contexto:\n{contexto}\n\nPregunta: {request.question}"
        respuesta = ollama.chat(model="phi3.5", messages=[{"role": "user", "content": mensaje}])

        return {"response": respuesta["message"]["content"]}

    except Exception as e:
        print(f"❌ Error en la consulta: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# ✅ Endpoint para subir archivos y guardarlos en Neo4j
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # 🔥 Crea la carpeta si no existe

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # ✅ Guardar el archivo en el sistema
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # ✅ Guardar en Neo4j
    try:
        node = Node("Documento", nombre=file.filename, ruta=file_path)
        graph.create(node)
        print(f"✅ Archivo '{file.filename}' guardado en Neo4j")
    except Exception as e:
        print(f"❌ Error guardando en Neo4j: {e}")
        raise HTTPException(status_code=500, detail="Error guardando en la base de datos")

    return {"filename": file.filename, "message": "Archivo subido exitosamente y guardado en Neo4j"}

# ✅ Confirmación en consola
print("✅ FastAPI iniciado con CORS y Neo4j correctamente")
