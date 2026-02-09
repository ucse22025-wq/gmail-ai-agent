import streamlit as st
import base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from openai import OpenAI
from urllib.parse import urlparse, parse_qs

# ----------------------------
# Configuration
# ----------------------------
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# OpenAI client from Streamlit Secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ----------------------------
# Setup OAuth flow
# ----------------------------
def get_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets["GOOGLE_CLIENT_ID"],
                "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [st.secrets["REDIRECT_URI"]],
            }
        },
        scopes=SCOPES,
        redirect_uri=st.secrets["REDIRECT_URI"]
    )

# ----------------------------
# Authenticate user
# ----------------------------
def gmail_auth():
    # Already authenticated
    if "creds" in st.session_state:
        return st.session_state.creds

    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt="consent")
    st.markdown(f"### 🔐 [Login with Gmail]({auth_url})")

    # Get OAuth code from URL
    query_params = st.experimental_get_query_params()  # Works with latest Streamlit
    code = query_params.get("code")
    if not code:
        st.stop()

    flow.fetch_token(code=code[0])
    creds = flow.credentials
    st.session_state.creds = creds
    return creds

# ----------------------------
# Gmail service
# ----------------------------
def get_gmail_service():
    creds = gmail_auth()
    return build("gmail", "v1", credentials=creds)

# ----------------------------
# Fetch emails
# ----------------------------
def get_emails(service, max_results=5):
    results = service.users().messages().list(userId="me", maxResults=max_results).execute()
    messages = results.get("messages", [])

    emails = []
    for msg in messages:
        txt = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        payload = txt["payload"]
        headers = payload.get("headers", [])

        subject = sender = "Unknown"
        for h in headers:
            if h["name"] == "Subject":
                subject = h["value"]
            if h["name"] == "From":
                sender = h["value"]

        body = ""
        parts = payload.get("parts", [])
        if parts:
            for part in parts:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
                        break

        emails.append({"subject": subject, "sender": sender, "body": body[:2000]})
    return emails

# ----------------------------
# AI classify
# ----------------------------
def classify_email(text):
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Classify this email into: Important, Work, Spam, Personal, Other"},
            {"role": "user", "content": text}
        ],
        max_tokens=10
    )
    return response.choices[0].message.content.strip()

# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Gmail AI Agent", layout="wide")
st.title("📧 Gmail AI Agent")

service = get_gmail_service()

if service:
    emails = get_emails(service, 5)
    for i, e in enumerate(emails, 1):
        st.subheader(f"{i}. {e['subject']}")
        st.caption(e["sender"])
        st.write(e["body"])
        if st.button(f"🤖 Classify {i}", key=i):
            st.success(classify_email(e["subject"] + "\n" + e["body"]))




