import re

def split_text_simple(text: str, max_chars: int = 1200, overlap: int = 200) -> list[str]:
    """
    Divide el texto en chunks de un tamaño aproximado, con solapamiento.
    Esta es una técnica simple de chunking por caracteres.
    """
    # Limpiamos espacios múltiples y saltos de línea para un procesamiento más limpio.
    text = re.sub(r'\s+', ' ', text).strip()
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + max_chars
        
        # Aseguramos que el chunk no se extienda más allá del final del texto
        chunk = text[start:min(end, text_length)].strip()
        
        if chunk:
            chunks.append(chunk)
            
        # Movemos el inicio del próximo chunk al punto de solapamiento
        start = end - overlap
        
        # Si el solapamiento es mayor o igual al chunk size (o si ya terminamos)
        if start <= 0 or start >= text_length: 
            break
            
    return chunks