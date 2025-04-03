import re

def normalize_code(code: str) -> str:
    """
    Normalize code by:
    - Removing comments
    - Converting to lowercase
    - Normalizing indentation and whitespace
    """
    if not isinstance(code, str):
        code = str(code)

    # Remove single-line comments
    code = re.sub(r'(//.*?$)|(#.*?$)', '', code, flags=re.MULTILINE)
    
    # Remove multi-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    
    # Remove docstrings
    code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
    code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
    
    # Normalize indentation (convert to spaces, standardize)
    lines = [line.strip() for line in code.split('\n') if line.strip()]
    
    # Convert to lowercase
    lines = [line.lower() for line in lines]
    
    # Normalize indentation
    return '\n'.join(lines)