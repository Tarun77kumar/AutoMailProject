import json
import base64
from flask import request, jsonify
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from db import get_user, is_processed, mark_processed
from utils import safe_remove
import os
from googleapiclient.http import MediaFileUpload


CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]


def handle_webhook():
    """
    Gmail Pub/Sub se aayi webhook notification ko handle karta hai.
    flow:
    1. Pub/Sub payload decode karta hai
    2. user identify karta hai
    3. refresh token se Gmail + Drive client banata hai
    4. latest attachment wala email fetch karta hai
    5. duplicate prevent karta hai using DB
    6. attachment download karta hai
    7. sender ke naam ka Drive folder create/locate karta hai
    8. file upload karta hai Drive par
    9. temp file delete karta hai
    """
    data = request.get_json(force=True)
    msg = data.get("message", {})
    raw = msg.get("data")

    if not raw:
        return jsonify({"ok": True}), 200

    payload = json.loads(base64.urlsafe_b64decode(raw).decode())
    email = payload.get("emailAddress")

    user = get_user(email)
    if not user:
        print("Unknown user:", email)
        return jsonify({"ok": True}), 200

    refresh_token = user[1]

    creds = Credentials(
        None, refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES
    )

    gmail = build("gmail", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)

    res = gmail.users().messages().list(userId="me", q="has:attachment", maxResults=1).execute()
    msgs = res.get("messages", [])

    if not msgs:
        return jsonify({"ok": True}), 200

    mid = msgs[0]["id"]

    if is_processed(email, mid):
        print("⚠️ Already processed:", mid)
        return jsonify({"ok": True}), 200

    mark_processed(email, mid)

    msg = gmail.users().messages().get(userId="me", id=mid).execute()

    headers = msg["payload"].get("headers", [])
    sender = next((h["value"] for h in headers if h["name"] == "From"), None)
    sender_email = sender.split("<")[-1].strip(">") if "<" in sender else sender

    for part in msg["payload"].get("parts", []):
        if not part.get("filename"):
            continue

        att_id = part["body"].get("attachmentId")
        if not att_id:
            continue

        att = gmail.users().messages().attachments().get(
            userId="me", messageId=mid, id=att_id
        ).execute()

        data = base64.urlsafe_b64decode(att["data"])
        fname = part["filename"]
        tmp = f"tmp_{mid}_{fname}"

        with open(tmp, "wb") as f:
            f.write(data)

        q = f"name='{sender_email}' and mimeType='application/vnd.google-apps.folder'"
        folders = drive.files().list(q=q, fields="files(id)").execute().get("files", [])

        if folders:
            folder_id = folders[0]["id"]
        else:
            folder = drive.files().create(
                body={"name": sender_email, "mimeType": "application/vnd.google-apps.folder"},
                fields="id"
            ).execute()
            folder_id = folder["id"]

        media = MediaFileUpload(tmp, resumable=False)
        drive.files().create(
            body={"name": fname, "parents": [folder_id]},
            media_body=media,
            fields="id"
        ).execute()

        safe_remove(tmp)

        print(f"✅ Uploaded {fname} for {email}")

    return jsonify({"ok": True}), 200
