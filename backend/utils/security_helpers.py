import re
import html

def sanitize_text(text: str) -> str:
    """
    Strips HTML tags and escapes special characters to prevent XSS.
    """
    if not text:
        return text
        
    # Remove HTML tags using simple regex
    clean = re.sub(r'<[^>]*>', '', text)
    
    # Escape HTML special characters
    clean = html.escape(clean)
    
    return clean

def validate_symptom_name(symptom: str) -> bool:
    """
    Checks if a symptom name only contains letters, numbers, and underscores.
    """
    return bool(re.match(r'^[a-zA-Z0-9_]+$', symptom))
