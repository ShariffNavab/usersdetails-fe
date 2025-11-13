import re

def is_valid_email(email: str) -> bool:
    pattern = r"[^@]+@[^@]+\.[^@]+"
    return re.match(pattern, email) is not None
