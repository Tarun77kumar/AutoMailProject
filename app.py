from flask import Flask, render_template
from auth import authorize_user, oauth_callback
from gmail_handler import handle_webhook
from db import init_db
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET")

init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/authorize", methods=["POST"])
def authorize():
    return authorize_user()


@app.route("/oauth2callback")
def oauth2callback():
    return oauth_callback()


@app.route("/webhook", methods=["POST"])
def webhook():
    return handle_webhook()


if __name__ == "__main__":
    """
    Flask app ko run karta hai
    host 0.0.0.0 rakha gaya hai taa ki ngrok use kar sake.
    """
    print("🚀 AutoMailDrive running on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000)


