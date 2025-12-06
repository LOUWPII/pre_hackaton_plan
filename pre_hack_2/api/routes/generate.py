from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File
import json
import numpy as np

from ..gemini import get_embedding, generate_flashcards, generate_feynman_feedback_from_context
from ..speech import transcribe_audiofile
from ..supabase import vector_search, get_raw_text, insert_chunks, insert_tool

router = APIRouter()

@router.post("/material/{material_id}/create_embeddings")
def create_embeddings(material_id: int):
    """
    Genera y guarda los embeddings para todos los chunks de un material
    que aún no los tienen.
    """
    # NOTA: En la práctica, se necesitaría una función en supabase.py
    # que recupere solo los chunks SIN embeddings.
    # Por simplicidad y enfoque en el flujo, usamos la función get_raw_text
    # y re-chunking (lo cual es ineficiente, pero sirve para el hackathon si la BD falla).
    
    # En un sistema real, se debería:
    # 1. chunks = supabase.get_chunks_without_embeddings(material_id)
    # 2. for chunk in chunks:
    # 3.    emb = get_embedding(chunk['chunk_text'])
    # 4.    supabase.update_chunk(chunk['id'], emb)
    
    try:
        from ..supabase import supabase # Acceso directo al cliente

        response = supabase.table("material_chunks").select("id, chunk_text, embedding").eq("material_id", material_id).is_("embedding", None).execute()

        # La librería supabase-py, cuando se usa sin el cliente 'Postgrest', devuelve una tupla donde [1] es la lista de resultados.
        if isinstance(response, tuple) and len(response) > 1:
            chunks = response[1] # <--- La lista de dicts (los chunks)
        elif hasattr(response, 'data') and response.data is not None:
             chunks = response.data
        else:
            chunks = []
            
    except Exception as e:
        raise HTTPException(500, detail=f"Fallo al recuperar chunks: {e}")
        
    if not chunks:
        return {"status": "ok", "message": "No hay chunks sin embeddings para procesar."}
    
    processed_count = 0
    for ch in chunks:
        try:
            emb = get_embedding(ch["chunk_text"])
            if emb:
                # Actualiza la columna 'embedding' en la fila específica
                supabase.table("material_chunks").update({"embedding": emb}).eq("id", ch["id"]).execute()
                processed_count += 1
        except Exception as e:
            print(f"Error procesando chunk {ch['id']}: {e}")
            continue
            
    return {"status": "ok", "count": processed_count, "message": f"Embeddings generados para {processed_count} chunks."}


# --- 2. Generación de Flashcards (Flujo RAG Completo) ---

@router.post("/material/{material_id}/generate_flashcards")
def generate_flashcards_route(
    material_id: int, 
    query: str = Query(default="Create study flashcards on key concepts"),
    top_k: int = 4
):
    """
    Ejecuta el flujo RAG: 
    1. Genera embedding de la query. 
    2. Busca chunks relevantes. 
    3. Llama a Gemini con el contexto. 
    4. Guarda las flashcards.
    """
    try:
        # 1. Generar embedding de la consulta del usuario
        query_embedding = get_embedding(query)
        if not query_embedding:
            raise HTTPException(500, "Fallo al generar el embedding de la consulta.")

        # 2. Recuperar top-k chunks relevantes (R: Retrieval)
        # Esto llama a la función match_material_chunks en Supabase
        context_chunks = vector_search(query_embedding, material_id, top_k)
        
        if not context_chunks:
            raise HTTPException(404, "No se encontraron fragmentos relevantes. ¿Se crearon los embeddings?")
            
        # 3. Construir el contexto para el LLM (A: Augmented)
        context = "\n\n---\n\n".join(context_chunks)

        # 4. Generación de Flashcards (G: Generation)
        flashcards_data = generate_flashcards(context=context, query=query, num_flashcards=6)
        
        if not flashcards_data.get('flashcards'):
            raise HTTPException(500, "El modelo no devolvió la estructura de flashcards esperada.")

        # 5. Guardar la herramienta generada
        save_count = insert_tool(material_id, "flashcards", flashcards_data)
        
        return {
            "status": "success",
            "material_id": material_id,
            "query": query,
            "flashcards": flashcards_data,
            "context_chunks_count": len(context_chunks),
            "save_count": save_count
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error en generate_flashcards_route: {e}")
        raise HTTPException(status_code=500, detail=f"Error en el proceso RAG: {str(e)}")


# --- 3. Feedback Feynman (Flujo RAG + evaluación por Gemini) ---
@router.post("/material/{material_id}/feynman_feedback")
def feynman_feedback_route(
    material_id: int,
    topic: str = Query(default="Tema"),
    user_explanation: str = Body(..., embed=True)
):
    """
    Recibe la explicación del usuario (texto) y devuelve feedback estilo Técnica de Feynman.
    Body JSON: { "user_explanation": "...", "topic": "..." }
    """
    try:
        # 1. Generar embedding para la explicación del usuario (combinada con topic)
        combined_query = f"Tema: {topic}. Explicación del usuario: {user_explanation}"
        query_embedding = get_embedding(combined_query)
        if not query_embedding:
            raise HTTPException(500, "Fallo al generar el embedding de la explicación del usuario.")

        # 2. Recuperar top-k chunks relevantes (R: Retrieval)
        context_chunks = vector_search(query_embedding, material_id, limit=4)
        if not context_chunks:
            raise HTTPException(404, "No se encontraron fragmentos relevantes. ¿Se crearon los embeddings?")

        # 3. Construir el contexto para el LLM
        context = "\n\n---\n\n".join(context_chunks)

        # 4. Llamar a Gemini (solo generación a partir del contexto recuperado)
        result = generate_feynman_feedback_from_context(context=context, topic=topic, user_explanation=user_explanation)

        # 5. Guardar la herramienta generada
        save_count = insert_tool(material_id, "feynman_feedback", result)

        return {
            "status": "success",
            "material_id": material_id,
            "feedback": result.get("feedback"),
            "context_chunks_count": len(context_chunks),
            "save_count": save_count
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error en feynman_feedback_route: {e}")
        raise HTTPException(status_code=500, detail=f"Error en el proceso Feynman: {str(e)}")


@router.post("/material/{material_id}/feynman_feedback_audio")
async def feynman_feedback_audio_route(
    material_id: int,
    file: UploadFile = File(...),
    topic: str = Query(default="Tema"),
    top_k: int = Query(default=4),
    model_name: str = Query(default="small")
):
    """
    Recibe un archivo de audio, lo transcribe con Whisper (server-side) y ejecuta el flujo Feynman.
    Requiere que 'openai-whisper' esté instalado en el servidor.
    """
    try:
        # 0. Transcribir audio a texto
        user_explanation = await transcribe_audiofile(file, model_name=model_name, language="es")
        if not user_explanation:
            raise HTTPException(status_code=400, detail="No se pudo transcribir el audio o el texto resultante está vacío.")

        # 1. Generar embedding para la explicación del usuario (combinada con topic)
        combined_query = f"Tema: {topic}. Explicación del usuario: {user_explanation}"
        query_embedding = get_embedding(combined_query)
        if not query_embedding:
            raise HTTPException(500, "Fallo al generar el embedding de la explicación del usuario.")

        # 2. Recuperar top-k chunks relevantes (R: Retrieval)
        context_chunks = vector_search(query_embedding, material_id, top_k)
        if not context_chunks:
            raise HTTPException(404, "No se encontraron fragmentos relevantes. ¿Se crearon los embeddings?")

        # 3. Construir el contexto para el LLM
        context = "\n\n---\n\n".join(context_chunks)

        # 4. Llamar a Gemini (solo generación a partir del contexto recuperado)
        result = generate_feynman_feedback_from_context(context=context, topic=topic, user_explanation=user_explanation)

        # 5. Guardar la herramienta generada
        save_count = insert_tool(material_id, "feynman_feedback", result)

        return {
            "status": "success",
            "material_id": material_id,
            "feedback": result.get("feedback"),
            "context_chunks_count": len(context_chunks),
            "save_count": save_count
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error en feynman_feedback_audio_route: {e}")
        raise HTTPException(status_code=500, detail=f"Error en el proceso Feynman (audio): {str(e)}")

