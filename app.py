import streamlit as st
from google import genai
from google.genai import types
import smtplib
from email.mime.text import MIMEText

from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE, SUMMARY_REQUEST_PROMPT

MODEL_NAME = "gemini-3.5-flash"
GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]
st.set_page_config(page_title = "Studysnap AI", page_icon="📚")

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

def send_email(to_address,subject, body):
    message = MIMEText(body)

    message["subject"] = subject
    message["from"] = GMAIL_ADDRESS
    message["to"] = to_address

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(message)

        return True, None
    except Exception as error:
        return False, str(error)

def ask_gemini(parts):
    try:
        return st.session_state.chat.send_message(parts).text
    except Exception as error:
        return f"Sorry, something went wrong: {error}"

def render_messages(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message['content'])
        elif message["kind"] == "image":
            st.image(message["content"])


@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)
gemini_client = get_gemini_client()


if "onboarded" not in st.session_state:
    st.title("📚 Studysnap AI")
    st.caption("Snap it. Understand it. Save the explanation.")

    with st.form("onboarding_form"):
        name = st.text_input("Your name")
        email = st.text_input("Your email",placeholder="example@gmail.com")
        submitted = st.form_submit_button("Let's go 🚀")

        if submitted:
            if not name.strip() or not email.strip():
                st.warning("Please enter both your name and email.")
            else:
                st.session_state.name = name.strip()
                st.session_state.email = email.strip()

                st.session_state.chat = gemini_client.chats.create(
                    model = MODEL_NAME,
                    config = types.GenerateContentConfig(
                        system_instruction = SYSTEM_PROMPT
                    ),
                )
                st.session_state.messages = []
                st.session_state.onboarded = True

                st.rerun()
        st.stop()

st.title("📚 StudySnap AI")
st.caption(f"Logged in as {st.session_state.name}")
if not st.session_state.messages:
    st.session_state.messages.append(
        {"role": "assistant", "kind": "text", "content": WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name)}
    )
for message in st.session_state.messages:
    render_messages(message)

user_input = st.chat_input("Ask a question or upload an image...",accept_file = True, file_type= ["jpg", "jpeg", "png"])
if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text
    parts = []
    if photo is not None:
        photo_bytes = photo.getvalue()

        st.session_state.messages.append({"role": "user", "kind": "image", "content": photo_bytes})
        parts.append(types.Part.from_bytes(data = photo_bytes, mime_type = photo.type))
    if text:
        st.session_state.messages.append({"role": "user", "kind": "text", "content": text})
        parts.append(text)
    elif photo is not None:
        parts.append("Explain this study material in simple language")
        
    with st.spinner("Analyzing your study material..."):
        answer = ask_gemini(parts)
    st.session_state.messages.append(
    {"role": "assistant", "kind" : "text", "content": answer}
    )
    st.rerun()

send_disabled = len(st.session_state.messages) <= 1

if st.button("📧 Send Explanation to Email",
    disabled=send_disabled):
    with st.spinner("Preparing your study summary..."):
        summary = ask_gemini([SUMMARY_REQUEST_PROMPT])
    success , error = send_email(st.session_state.email, "Your studysnap AI summary", summary)

    if success:
        st.success("Study summary sent to your email! 📩")
    else:
        st.error(f"Could not send the email: {error}")


