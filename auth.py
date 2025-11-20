import os
from flask import redirect, request
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from db import save_user
from db import get_user

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
PROJECT_ID = os.getenv("PROJECT_ID")
NGROK_BASE = os.getenv("NGROK_BASE")
FLASK_SECRET = os.getenv("FLASK_SECRET")

REDIRECT_URI = NGROK_BASE.rstrip("/") + "/oauth2callback"
TOPIC_NAME = f"projects/{PROJECT_ID}/topics/gmail-notifications"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]


def authorize_user():
    """
    Google OAuth ka flow start karta hai.
    Pahle check karta hai ki user pehle se exist karta hai ya nahi.
    """
    email = request.form.get("email")
    if not email:
        return "Email is required", 400

    #  Check if user already exists
    user = get_user(email)
    if user:
        # User already connected
        return f"<h3>⚠️ This service is already started on this <b>{email}</b></h3>"

    # NEW USER → Start OAuth
    flow = Flow.from_client_config({
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI]
        }
    }, scopes=SCOPES, redirect_uri=REDIRECT_URI)

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="false",
        prompt="consent select_account",
        state=email
    )

    return redirect(auth_url)



def oauth_callback():
    """
    Google OAuth callback ko handle karta hai.
    Steps:
    1. code + email validate karta hai
    2. Google se token fetch karta hai
    3. refresh token DB me save karta hai
    4. Gmail pub/sub watch setup karta hai real time notifications ke liye
    """
    code = request.args.get("code")
    email = request.args.get("state")

    if not code or not email:
        return "Missing parameters", 400

    flow = Flow.from_client_config({
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI]
        }
    }, scopes=SCOPES, redirect_uri=REDIRECT_URI)

    flow.fetch_token(code=code)
    creds = flow.credentials

    if not creds.refresh_token:
        return "No refresh token returned. Try again.", 400

    save_user(email, creds.refresh_token)

    try:
        gmail = build("gmail", "v1", credentials=creds)
        watch_req = {"labelIds": ["INBOX"], "topicName": TOPIC_NAME}
        gmail.users().watch(userId="me", body=watch_req).execute()
        print("📡 Gmail watch created for", email)
    except Exception as e:
        print("❌ Watch failed:", e)

    return f"<h3>✅ {email} connected successfully! You may close this tab.</h3>"
