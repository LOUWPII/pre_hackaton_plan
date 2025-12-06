from fastapi import APIRouter, UploadFile, File, HTTPException
import io
import hashlib

from ..supabase import insert_material, insert_chunks, upload_pdf_to_storage
from ..gemini import get_embedding
from ..config import EMBEDDING_DIM
from ..pypdf_utils import extract_text_from_bytes
from ..text_processing import split_text_simple

router = APIRouter()

@router.post("/upload_pdf")
async def upload_pdf(user_id: str, title: str, file: UploadFile = File(...)):
    
    #1.Recibe el PDF. 2. Guarda en Storage. 3. Extrae texto. 4. Guarda Material. 5. Crea Chunks.
    
    try:
        content = await file.read()
        pdf_bytes = io.BytesIO(content)
        
        # 1. Guarda en Supabase Storage
        public_url = upload_pdf_to_storage(user_id, file.filename, pdf_bytes)
        if not public_url: 
            raise HTTPException(status_code=500, detail="Fallo al subir el archivo a Supabase Storage.")
        
        # 2. Extraer texto (volvemos a leer desde el inicio del buffer)
        pdf_bytes.seek(0)
        raw_text = extract_text_from_bytes(pdf_bytes.read())
        
        if not raw_text or len(raw_text.strip()) < 100:
             raise HTTPException(status_code=400, detail="El PDF no contiene suficiente texto extraíble.")

        # 3. Inserta registro de material (obtenemos el material_id)
        material_id = insert_material(user_id, title, public_url, raw_text)
        if not material_id:
            raise HTTPException(status_code=500, detail="Fallo al insertar el registro del material.")

        # 4. Chunking: Dividir el texto
        chunks = split_text_simple(raw_text)
        
        # 5. Preparar Chunks para inserción (Opcional: Generación de embeddings AQUÍ para mayor velocidad)
        chunks_to_insert = []
        for c in chunks:
            chunk_hash = hashlib.sha256(c.encode('utf-8')).hexdigest()
            # NOTA: Por ahora, solo insertamos texto y hash. Los embeddings se crean en /create_embeddings.
            chunks_to_insert.append({
                "chunk_text": c,
                "chunk_hash": chunk_hash,
                # "embedding": get_embedding(c) # <- Descomentar para pre-computar (más rápido)
            })

        # 6. Insertar chunks
        count = insert_chunks(material_id, chunks_to_insert)

        return {
            "material_id": material_id, 
            "message": "Archivo procesado y chunks creados.",
            "chunks_count": count
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error general en upload_pdf: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")