import os

def safe_remove(path):
    """
    file ko safely delete karta hai bina error throw kiye.
    agar file exist nahi karti ya koi issue aaye to silently ignore kar deta hai.
    Args: path (str)= file ka location
    """
    try:
        os.remove(path)
    except Exception:
        pass
