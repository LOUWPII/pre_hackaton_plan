import os
from dotenv import load_dotenv

# Carga las variables de entorno del archivo .env
load_dotenv()

# Variables de Supabase y Gemini
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME", "materiales")

# Configuración del modelo de embeddings (768 dimensiones)
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768

# Configuración del modelo de generación 
GENERATION_MODEL = "gemini-2.5-flash"