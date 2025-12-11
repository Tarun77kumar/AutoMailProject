import sqlite3

DB = "data/automail.db"


def init_db():
    """DB ko initial setup karne ke liye function.
    users aur processed naam ki 2 tables banata hai agar already exist na ho.

    users table:
        - email
        - refresh_token

    processed table:
        - msg_id (already processed emails)
        - email (kis user ka msg process hua)

    basically yeh ensure karta hai ki app smoothly run ho aur duplicate emails na process ho.
    """ 
    with sqlite3.connect(DB) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, refresh_token TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS processed (msg_id TEXT, email TEXT)")
        conn.commit()


def save_user(email, refresh_token):
    """
    user ka refresh token DB me save/update karta hai.
    Args:
        email (str): user ka Gmail
        refresh_token (str): Google OAuth refresh token, agar user pehle se hai to update ho jayega.
    """
    with sqlite3.connect(DB) as conn:
        conn.execute("REPLACE INTO users (email, refresh_token) VALUES (?, ?)", (email, refresh_token))
        conn.commit()


def get_user(email):
    """
    DB se user ki details fetch karta hai.
    Args:
        email (str): Gmail ID
    Returns:
        tuple or None = (email, refresh_token)
    """
    with sqlite3.connect(DB) as conn:
        return conn.execute("SELECT email, refresh_token FROM users WHERE email=?", (email,)).fetchone()


def mark_processed(email, msg_id):
    """
    kis email ka konsa Gmail message process ho chuka hai, isko save karta hai
    taa ki dobara same email process na ho.
    Args:email (str),msg_id (str)
    """
    with sqlite3.connect(DB) as conn:
        conn.execute("INSERT INTO processed (msg_id,email) VALUES (?,?)", (msg_id, email))
        conn.commit()


def is_processed(email, msg_id):
    """
    check karta hai ki kya yeh message ID pehle process ho chuki hai ya nahi.

    Args:email (str),msg_id (str)
    Returns:bool
    """
    with sqlite3.connect(DB) as conn:
        return conn.execute(
            "SELECT 1 FROM processed WHERE msg_id=? AND email=?",
            (msg_id, email)
        ).fetchone() is not None
