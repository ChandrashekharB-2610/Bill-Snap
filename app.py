import re
import time
import html
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE, SUMMARY_REQUEST_PROMPT

st.set_page_config(page_title="BillSnap", page_icon="🧾", layout="centered")

def inject_ui_styles():
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(135deg, #f5f7ff 0%, #eef4ff 100%);
            color: #1f2937;
        }
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1150px;
        }
        div[data-testid="stChatMessage"] {
            border-radius: 18px;
            padding: 0.7rem 0.9rem;
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(148,163,184,0.25);
            box-shadow: 0 4px 12px rgba(15,23,42,0.06);
        }
        [data-testid="stChatInput"] {
            border-radius: 16px;
            border: 1px solid #dbeafe;
            background: white;
        }
        .stButton > button {
            border-radius: 12px;
            background: linear-gradient(135deg, #2563eb, #4f46e5);
            color: white;
            border: none;
            font-weight: 600;
            padding: 0.7rem 1.2rem;
        }
        .stTextInput > div > div > input,
        .stSelectbox > div > div > div,
        .stTextArea > div > div > textarea {
            border-radius: 12px;
            background: white;
            border: 1px solid #dbeafe;
        }
        .glass-card {
            background: rgba(255,255,255,0.7);
            border: 1px solid rgba(148,163,184,0.25);
            border-radius: 18px;
            padding: 1rem 1.2rem;
            box-shadow: 0 10px 30px rgba(15,23,42,0.06);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

inject_ui_styles()

def markdown_table_to_html(md_text):
    lines = [line.rstrip() for line in (md_text or "").splitlines() if line.strip()]
    if not lines:
        return "<p>No summary available.</p>"

    for i in range(len(lines) - 1):
        if "|" in lines[i] and "|" in lines[i + 1]:
            header = lines[i]
            separator = lines[i + 1]
            if re.search(r"-{3,}", separator.replace("|", "").replace(":", "")):
                rows = [lines[j] for j in range(i, len(lines)) if "|" in lines[j]]
                if len(rows) >= 2:
                    table_rows = []
                    for row in rows:
                        cells = [cell.strip() for cell in row.split("|")]
                        cells = [c for c in cells if c != ""]
                        if cells:
                            table_rows.append(cells)

                    if len(table_rows) >= 2:
                        header_cells = table_rows[0]
                        body_rows = table_rows[2:] if len(table_rows) > 2 else []

                        html_rows = []
                        html_rows.append(
                            "<tr>" + "".join(f"<th style='padding:10px 12px; border:1px solid #dbeafe; background:#eff6ff; text-align:left;'>{html.escape(c)}</th>" for c in header_cells) + "</tr>"
                        )

                        for row in body_rows:
                            html_rows.append(
                                "<tr>" + "".join(f"<td style='padding:10px 12px; border:1px solid #e5e7eb; text-align:left;'>{html.escape(c)}</td>" for c in row) + "</tr>"
                            )

                        return (
                            "<table style='width:100%; border-collapse:collapse; border:1px solid #dbeafe; font-size:14px; color:#1f2937;'>"
                            + "".join(html_rows)
                            + "</table>"
                        )

    return "<div style='font-size:15px; line-height:1.8; color:#1f2937;'>" + html.escape(md_text).replace("\\n", "<br>") + "</div>"

def format_email_html(name, summary):
    safe_name = html.escape(name or "there")
    safe_summary = markdown_table_to_html(summary)
    return f"""
    <html>
      <body style="margin:0; padding:0; background:#f5f7ff; font-family:Arial, sans-serif;">
        <div style="max-width:700px; margin:32px auto; background:#ffffff; border-radius:18px; overflow:hidden; border:1px solid #e5e7eb;">
          <div style="background:linear-gradient(135deg,#2563eb,#4f46e5); padding:28px 32px; color:#ffffff;">
            <h2 style="margin:0; font-size:26px;">BillSnap Summary</h2>
            <p style="margin:10px 0 0 0; font-size:14px; opacity:0.9;">Hi {safe_name}, here's your cleaned bill breakdown.</p>
          </div>

          <div style="padding:28px 32px; color:#1f2937;">
            <div style="background:#eef6ff; border:1px solid #dbeafe; border-radius:12px; padding:16px 18px; margin-bottom:18px;">
              <p style="margin:0; font-size:13px; color:#374151; text-transform:uppercase; letter-spacing:0.08em;">
                Receipt Summary
              </p>
            </div>

            <div style="font-size:15px; line-height:1.8; color:#1f2937;">
              {safe_summary}
            </div>
          </div>

          <div style="padding:18px 32px 30px; font-size:12px; color:#6b7280; text-align:center; border-top:1px solid #eef2f7;">
            Sent from BillSnap • Receipt & split summary
          </div>
        </div>
      </body>
    </html>
    """

def send_email(to_address, subject, body):
    gmail_address = st.secrets.get("GMAIL_ADDRESS")
    gmail_app_password = st.secrets.get("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_app_password:
        st.error("Missing Gmail credentials in .streamlit/secrets.toml")
        return False

    html_body = format_email_html(st.session_state.get("name", "there"), body)
    message = MIMEText(html_body, "html")
    message["Subject"] = subject
    message["From"] = gmail_address
    message["To"] = to_address

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.send_message(message)

    return True

st.title("BillSnap 🧾")
st.caption("Your instant receipt & bill-splitting buddy")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False

@st.cache_resource
def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("Missing Gemini API key in .streamlit/secrets.toml")
        st.stop()
    return genai.Client(api_key=api_key)

gemini_client = get_gemini_client()
MODEL_NAME = "gemini-2.5-flash-lite"

def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.markdown(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"], caption="Receipt", use_container_width=True)

def add_message(role, kind, content):
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})
    render_message(st.session_state.messages[-1])

def ask_gemini(parts):
    for attempt in range(3):
        try:
            if "chat" not in st.session_state:
                st.session_state.chat = gemini_client.chats.create(
                    model=MODEL_NAME,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                )
            return st.session_state.chat.send_message(parts).text
        except Exception as error:
            msg = str(error)
            if "503" in msg or "UNAVAILABLE" in msg:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return "Gemini is temporarily overloaded. Please try again in a minute."
            return f"Sorry, something went wrong: {error}"

if not st.session_state.onboarded:
    st.markdown(
        """
        <div class="glass-card">
            <h3 style="margin-top:0; margin-bottom:10px;">Welcome aboard 👋</h3>
            <p style="margin:0;">Set up your profile and start sending polished receipt summaries.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("onboarding_form"):
        name = st.text_input("Your Name", placeholder="e.g., Alex")
        currency = st.selectbox(
            "Currency",
            options=["₹ INR", "$ USD", "€ EUR", "£ GBP", "AED", "Other"],
            index=0,
        )
        recipient_handle = st.text_input(
            "Email address for summaries",
            placeholder="you@example.com",
            help="Where bill breakdowns should be sent.",
        )

        submitted = st.form_submit_button("Get Started 🚀", use_container_width=True)

    if submitted:
        if not name.strip() or not recipient_handle.strip():
            st.warning("Please provide both your name and email address.")
        else:
            st.session_state.name = name.strip()
            st.session_state.currency = currency
            st.session_state.share_channel = "Email"
            st.session_state.recipient_handle = recipient_handle.strip()
            st.session_state.chat = gemini_client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            st.session_state.receipt_history = []
            st.session_state.onboarded = True
            st.rerun()

    st.stop()

if "name" not in st.session_state:
    st.warning("Session not initialized properly.")
    st.stop()

if not st.session_state.messages:
    welcome_text = WELCOME_MESSAGE_TEMPLATE.format(
        name=st.session_state.name,
        channel=st.session_state.share_channel,
        recipient_handle=st.session_state.recipient_handle,
    )
    add_message("assistant", "text", welcome_text)
else:
    for message in st.session_state.messages:
        render_message(message)

user_input = st.chat_input(
    "Ask a question, split instructions, or attach a receipt photo",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text.strip()
    parts = []

    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))

    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        currency = st.session_state.get("currency", "your currency")
        parts.append(
            f"Read this receipt and extract all line items, their individual prices, "
            f"taxes/charges, and the final total in {currency}. "
            f"Present the breakdown in a clean markdown table and summarize the total."
        )

    if parts:
        with st.spinner("Scanning receipt and calculating totals..."):
            answer = ask_gemini(parts)

        if answer and answer.strip():
            add_message("assistant", "text", answer)

            email_sent = send_email(
                st.session_state.recipient_handle,
                "Your bill summary",
                answer,
            )

            if email_sent:
                st.success("Summary sent to email.")
            else:
                st.warning("Summary generated, but email was not sent.")
        else:
            st.warning("No summary was returned by the model.")
            import streamlit as st

st.set_page_config(
    page_title="BillSnap",
    page_icon="🧾",
    layout="centered"
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f8fbff 0%, #eef4ff 100%);
        color: #111827;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stChatMessage"] {
        border-radius: 18px;
        background: rgba(255,255,255,0.86);
        border: 1px solid rgba(148,163,184,0.25);
        box-shadow: 0 6px 18px rgba(15,23,42,0.05);
        padding: 0.8rem 0.9rem;
    }
    [data-testid="stChatInput"] {
        border-radius: 14px;
        border: 1px solid #dbeafe;
        background: white;
    }
    .stButton > button {
        background: linear-gradient(135deg, #2563eb, #4f46e5);
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)