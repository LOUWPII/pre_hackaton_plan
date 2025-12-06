import io
from supabase import create_client, Client
from .config import SUPABASE_URL, SUPABASE_API_KEY, SUPABASE_BUCKET_NAME

# 1. Inicialización del Cliente Supabase
# Se crea una única instancia del cliente de Supabase para toda la aplicación, esto siguiendo el patrón singleton.
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)
except Exception as e:
    # Manejo básico de errores si la conexión falla al inicio
    print(f"Error creating Supabase client: {e}")
    supabase = None

# Funciones de storage de Supabase
# api/supabase.py

def upload_pdf_to_storage(user_id: str, file_name: str, file_content: io.BytesIO):
    storage_path = f"{user_id}/{file_name}"

    try: 
        # 1. OBTENEMOS LA REFERENCIA AL BUCKET
        bucket_client = supabase.storage.from_("materials") 
        
        # 2. Subida (Si esto falla, el 'except' lo captura)
        bucket_client.upload(
            file=file_content.read(),
            path=storage_path,
            file_options={"content-type": "application/pdf"}
        )

        # -----------------------------------------------------------
        # 3. ¡SOLUCIÓN! CONSTRUCCIÓN MANUAL DE LA URL PÚBLICA
        # Patrón: {SUPABASE_URL}/storage/v1/object/public/{bucket_name}/{path}

        # Extraemos solo el dominio (quitamos /rest/v1 o /auth/v1)
        base_url = SUPABASE_URL.replace("/rest/v1", "").replace("/auth/v1", "")

        public_url = f"{base_url}/storage/v1/object/public/{"materials"}/{storage_path}"
        # -----------------------------------------------------------
        
        return public_url

    except Exception as e:
        # Esto capturará cualquier error de la API (403, 404, etc. DE LA SUBIDA)
        print(f"Error al subir el PDF a Supabase Storage: {e}")
        raise Exception("Fallo al subir el archivo a Supabase Storage.")

#Funciones de Database (Supabase - PostgreSQL y pgvector)
def insert_material(user_id: str, title: str, pdf_url: str, raw_text: str):
    #Inserta el registro del documento principal en la tabla 'materials
    data, count = supabase.table("materials").insert({
        "user_id": user_id,
        "title": title,
        "pdf_url": pdf_url,
        "raw_text": raw_text
    }).execute()
    
    # El resultado de execute() tiene la estructura (data, count), data[1] contiene la fila insertada
    if data and len(data[1]) > 0:
        return data[1][0]['id'] # Retorna el ID del material recién creado
    return None

def insert_chunks(material_id: int, chunks_to_insert: list):
    # Inserta los fragmentos (chunk_text, hash y embedding) en la tabla 'material_chunks'.
    # chunks_to_insert es una lista de diccionarios, cada uno con 'chunk_text', 'chunk_hash', 'embedding'
    
    # Obtenemos la cantidad de chunks que vamos a insertar
    num_chunks = len(chunks_to_insert) # Guardamos el número

    # Añadimos el material_id a cada diccionario
    data_to_insert = [{"material_id": material_id, **chunk} for chunk in chunks_to_insert]
    
    try:
        # Ejecutamos la inserción sin intentar capturar el recuento directamente
        supabase.table('material_chunks').insert(data_to_insert).execute()
        
        # Devolvemos el número de elementos que SABEMOS que insertamos
        return num_chunks # Devolvemos el entero
    
    except Exception as e:
        # Manejo de errores en la inserción
        print(f"Error al insertar chunks: {e}")
        return 0 # Devuelve 0 en caso de fallo

def get_chunks_without_embeddings(material_id: int):
    # Obtiene todos los chunks para un material dado cuyo campo 'embedding' es NULL
    response = (
        supabase.table('material_chunks')
        .select('id, chunk_text')
        .eq('material_id', material_id)
        .is_('embedding', None)  # Esta línea busca los valores NULL
        .execute()
    )
    
    # El resultado de execute() tiene la estructura (data, count), data[1] contiene las filas
    if response.data and response.data[1]:
        # data[1] es la lista de chunks. Retornamos la lista de diccionarios.
        return response.data[1] 
    return []

def vector_search(query_embedding: list, material_id: int, limit: int = 4):
    """
    Realiza la búsqueda de similitud vectorial (RAG) en la base de datos.
    Usa el operador de distancia coseno (<->) en el vector 'embedding'
    para encontrar los chunks más similares al query_embedding proporcionado.
    """
    
    data, count = supabase.rpc('match_material_chunks', {
        'query_embedding': query_embedding,
        'match_material_id': material_id,
        'match_threshold': 0.5, # Umbral de similitud opcional para filtrar
        'match_count': limit
    }).execute()
    
    # El resultado de execute() tiene la estructura (data, count), data[1] contiene las filas
    if data and len(data[1]) > 0:
        # Extraemos solo el texto de los chunks para enviarlo al LLM
        return [item['chunk_text'] for item in data[1]]
    return []

def get_raw_text(material_id: int):
    #Obtiene el texto sin procesar de un material.
    data, count = supabase.table('materials').select('raw_text').eq('id', material_id).single().execute()
    
    if data and data[1]:
        return data[1]['raw_text']
    return None

def insert_tool(material_id: int, tool_type: str, data: dict):
    try:
        supabase.table('tools').insert({
            "material_id": material_id,
            "tool_type": tool_type,
            "data": data
        }).execute()
        return 1 # Retornamos 1 porque siempre insertamos una herramienta a la vez
    except Exception as e:
        print(f"Error al guardar tool: {e}")
        return 0