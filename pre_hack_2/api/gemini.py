import os
import json
from google import genai
from google.genai import types
from google.genai.errors import APIError

from .config import GEMINI_API_KEY, EMBEDDING_MODEL, GENERATION_MODEL
from .supabase import vector_search

# Inicialización del cliente de Gemini
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Error al inicializar el cliente Gemini: {e}")
    client = None

# Función para generar embeddings usando Gemini
def get_embedding(text: str) -> list[float]:
    #Genera el vector embedding (768 dimensiones) para el chunk de texto dado
    #Se usa el modelo text-embedding-004 de Gemini
    if not client:
        raise ConnectionError("El cliente Gemini no está inicializado.")
    try:
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[text]
        )
        return list(response.embeddings[0].values)  # Retorna el primer (y único) embedding generado
    except APIError as e:
        print(f"Error en la API de gemini al generar embedding: {e}")
        return []
    except Exception as e:
        print(f"Error inesperado al generar embedding: {e}")
        return []

def generate_flashcards(context: str, query: str = "Create study flashcards", num_flashcards: int = 6) -> dict:
    #Llama al LLM (gemini-2.5-flash) para generar flashcards basadas en el contexto recuperado
    if not client:
        raise ConnectionError("El cliente Gemini no está inicializado.")
    
    # Definición del Esquema JSON (Structured Output)
    # Esto garantiza que el modelo DEVUELVA un JSON parseable y con la estructura correcta.
    schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "flashcards": types.Schema(
                type=types.Type.ARRAY,
                description=f"A list of exactly {num_flashcards} flashcards.",
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "question": types.Schema(type=types.Type.STRING, description="The question strictly derived from the context."),
                        "answer": types.Schema(type=types.Type.STRING, description="The detailed answer to the question derived from the context.")
                    },
                    required=["question", "answer"]
                )
            )
        },
        required=["flashcards"]
    )
    
    # 2. Prompt
    prompt = f"""
Eres un educador experto. Tu tarea es ayudar al estudiante a memorizar el contenido.
Dada la siguiente consulta del usuario: "{query}" y la información proporcionada en el CONTEXTO (fragmentos del material del estudiante), crea exactamente {num_flashcards} flashcards de alta calidad (pregunta/respuesta) que estén ESTRICTAMENTE BASADAS en la información del contexto.

CONTEXTO:
{context}

Devuelve SOLAMENTE el JSON válido con el formato solicitado.
"""
    
    # 3. Llamada a Gemini con JSON Mode
    try:
        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=[
                {"role":"user", "parts":[{"text": prompt}]}
            ],
            config=types.GenerateContentConfig(
                # Forzamos la salida JSON
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2, # Baja temperatura para respuestas consistentes
            )
        )
        
        # El texto de la respuesta debería ser un JSON válido
        return json.loads(response.text)
        
    except APIError as e:
        raise Exception(f"Error de API de Gemini al generar flashcards: {e}")
    except json.JSONDecodeError:
        # Esto ocurre si, a pesar de usar response_schema, el modelo devuelve texto inválido
        print(f"El modelo devolvió un JSON inválido: {response.text}")
        raise Exception("Fallo al generar flashcards: El modelo devolvió JSON no parseable.")
    except Exception as e:
        raise Exception(f"Error inesperado durante la generación: {e}")
    

def generate_feynman_feedback_from_context(context: str, topic: str, user_explanation: str) -> dict:
    """
    Genera feedback tipo Feynman a partir de un CONTEXTO ya recuperado.
    Esta función asume que la recuperación (embeddings + vector search) se hizo
    fuera de ella y únicamente se encarga de formular el prompt y llamar al LLM.
    """
    if not client:
        raise ConnectionError("El cliente Gemini no está inicializado.")

    system_prompt = (
        "Eres un tutor experto y amable especializado en la Técnica de Feynman. "
        "Tu tarea es evaluar la 'Explicación del Usuario' basándote en el 'Contexto del Documento'. "
        "Proporciona feedback constructivo, conciso y en un tono alentador, identificando las lagunas de conocimiento o errores. "
        "Tu respuesta debe ser solo el texto del feedback, sin encabezados de tipo 'Feedback:'."
    )

    feynman_prompt = f"""
    Contexto del Documento (Información de la base de datos RAG):
    ---
    {context}
    ---

    Tema Específico: {topic}
    Explicación del Usuario (Transcrita por Voz): {user_explanation}

    Instrucciones: Evalúa la explicación del usuario en español:
    1. Identifica si el usuario capturó el concepto principal.
    2. Señala y corrige cualquier imprecisión o error basándote estrictamente en el Contexto.
    3. Menciona un punto crucial del contexto que el usuario omitió (la 'laguna') para completar su entendimiento.
    """

    try:
        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=[
                {"role":"user", "parts":[{"text": feynman_prompt}]}
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
            )
        )

        return {"feedback": response.text}

    except APIError as e:
        raise Exception(f"Error de API de Gemini al generar feedback: {e}")
    except Exception as e:
        raise Exception(f"Error inesperado durante la generación del feedback: {e}")
    
