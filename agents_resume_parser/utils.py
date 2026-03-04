import fitz  # PyMuPDF
import io

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extracts text from a PDF file using PyMuPDF.
    """
    text = ""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text() + "\n"
    except Exception as e:
        raise ValueError(f"Failed to read PDF file: {e}")
    return text
    
def extract_text_from_txt(txt_bytes: bytes) -> str:
    """
    Extracts text from a TXT file.
    """
    try:
        return txt_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to read TXT file: {e}")
