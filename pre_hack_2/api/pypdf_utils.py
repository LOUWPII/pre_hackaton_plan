from pypdf import PdfReader
from io import BytesIO

def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """Extrae texto de un archivo PDF en formato bytes."""
    # Usamos BytesIO para tratar los bytes como un archivo en memoria.
    reader = PdfReader(BytesIO(pdf_bytes))
    texts = []
    for page in reader.pages:
        # Extraemos texto de cada página. Usamos or "" para manejar páginas vacías.
        texts.append(page.extract_text() or "") 
    return "\n".join(texts)