from fastapi import FastAPI
from api import routes
from api.routes import upload, generate
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Pre-Hack 2 RAG backend",
    description="API para subir PDFs, procesarlos y generar herramientas de estudio basadas en RAG usando Gemini y Supabase."
)

origins = [
    # Permite el origen del servidor de desarrollo de React (Vite)
    "http://localhost:5173", 
    "http://127.0.0.1:5173",
    # Puedes añadir cualquier otro origen si lo necesitas
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,             # Lista de orígenes permitidos
    allow_credentials=True,            # Permite cookies/autenticación
    allow_methods=["*"],               # Permite todos los métodos (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],               # Permite todos los headers
)

#incluir los routers de la aplicación
#Las rutas de 'upload' estarán en /api/upload y las de 'generate' en /api/generate

app.include_router(upload.router, prefix="/api", tags=["Upload & Chunking"])
app.include_router(generate.router, prefix="/api", tags=["RAG & Generation"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
