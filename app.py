import streamlit as st
import base64
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = "http://localhost:8501"

st.set_page_config(page_title="Gmail AI Agent")
st.title("📧 Gmail AI Agent")

# ---------- LOGIN ----------
if "creds" not in st.session_state:

    if "code" in st.query_params:
        flow = Flow.from_client_secrets_file(
            "credentials.json",
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(code=st.query_params["code"])
        st.session_state.creds = flow.credentials
        st.rerun()


    else:
        flow = Flow.from_client_secrets_file(
            "credentials.json",
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        auth_url, _ = flow.authorization_url(prompt="consent")
        st.link_button("🔐 Login with Google", auth_url)
        st.stop()

# ---------- GMAIL ----------
service = build("gmail", "v1", credentials=st.session_state.creds)
st.success("✅ Logged in")

def get_email_body(msg):
    payload = msg["payload"]

    def walk(parts):
        for part in parts:
            if part["mimeType"] == "text/plain" and "data" in part["body"]:
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            if "parts" in part:
                text = walk(part["parts"])
                if text:
                    return text
        return ""

    if "parts" in payload:
        return walk(payload["parts"])
    elif "data" in payload["body"]:
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    return ""

# ---------- YOUR AI LOGIC ----------
def classify_email(text):
    if "invoice" in text.lower():
        return "Finance"
    elif "meeting" in text.lower():
        return "Work"
    else:
        return "General"

# ---------- UI ----------
if st.button("Fetch Emails"):
    results = service.users().messages().list(userId="me", maxResults=5).execute()
    for m in results.get("messages", []):
        msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
        body = get_email_body(msg)
        label = classify_email(body)

        with st.expander(f"{label}"):
            st.write(body[:2000])

if st.button("Logout"):
    del st.session_state["creds"]
    st.experimental_rerun()
