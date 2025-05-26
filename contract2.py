import streamlit as st
import requests
import smtplib
from email.message import EmailMessage

# ───────────────────────────────────────────────────────────────
# Page Config
st.set_page_config(
    page_title="AI Document Comparison Agent",
    page_icon="🤖",
    layout="wide"
)

# ───────────────────────────────────────────────────────────────
# Sidebar: Configuration
st.sidebar.header("🔧 Configuration")
ocr_api_url = "https://ocr-api-03n6.onrender.com/upload-pdf/"
webhook_url = "https://n8n.sofiatechnology.ai/webhook/480b1d1a-d58f-498f-997f-304cf50253ac"

# ───────────────────────────────────────────────────────────────
# Sidebar: Email settings
# ───────────────────────────────────────────────────────────────
# Sidebar: Email settings para Outlook
st.sidebar.header("📧 Email Configuration (Outlook)")
smtp_server     = "smtp.gmail.com"
smtp_port       = 587
email_sender    = "liznel4444@gmail.com"
email_pass      = "ysnq zpzr uimk uycq"
email_recipient = st.sidebar.text_input("Recipient email address")

# ───────────────────────────────────────────────────────────────
# Main header
st.markdown(
    """
    # 🤖 AI Agent for Purchase Order Validation

    Harness the power of AI to automatically compare purchase documents and identify mismatches in real time.  
    Upload your files, let our intelligent agent do the work, and receive clear, actionable insights.

    ---
    """,
    unsafe_allow_html=True
)

# Initialize session state
if "messages"   not in st.session_state: st.session_state["messages"] = []
if "ocr_texts"  not in st.session_state: st.session_state["ocr_texts"] = []

# ───────────────────────────────────────────────────────────────
# File upload area
col1, col2 = st.columns(2)
with col1:
    pdf1 = st.file_uploader("📄 Upload Purchase Order", type="pdf", key="pdf1")
with col2:
    pdf2 = st.file_uploader("📄 Upload Order Confirmation", type="pdf", key="pdf2")

# ───────────────────────────────────────────────────────────────
# Process button
process_col, _ = st.columns([1, 3])
with process_col:
    if st.button("▶️ Start Processing", use_container_width=True):
        if not (pdf1 and pdf2):
            st.error("Please upload both PDF Documents.")
        else:
            # Limpia datos previos
            st.session_state["messages"].clear()
            st.session_state["ocr_texts"].clear()

            # 1) Log user action
            st.session_state["messages"].append({
                "role": "user",
                "content": f"Uploaded **{pdf1.name}** & **{pdf2.name}** for OCR & analysis."
            })

            # 2) Perform OCR on cada PDF
            for pdf in (pdf1, pdf2):
                with st.spinner(f"🔍 Sending {pdf.name} to OCR…"):
                    files = {"file": (pdf.name, pdf.getvalue(), "application/pdf")}
                    try:
                        resp = requests.post(ocr_api_url, files=files, timeout=60)
                        resp.raise_for_status()
                        try:
                            data = resp.json()
                        except ValueError:
                            text = resp.text
                        else:
                            if isinstance(data, dict):
                                text = data.get("text") or data.get("result") or str(data)
                            elif isinstance(data, list):
                                parts = []
                                for item in data:
                                    if isinstance(item, dict):
                                        parts.append(item.get("text") or item.get("result") or str(item))
                                    else:
                                        parts.append(str(item))
                                text = "\n\n".join(parts)
                            else:
                                text = str(data)
                    except Exception as e:
                        text = f"⚠️ OCR error for {pdf.name}: {e}"

                    st.session_state["ocr_texts"].append({
                        "filename": pdf.name,
                        "ocr_text": text
                    })

            # 3) Send OCR results to n8n
            with st.spinner("🚀 Sending OCR results to n8n…"):
                payload = {"documents": st.session_state["ocr_texts"]}
                try:
                    r2 = requests.post(webhook_url, json=payload, timeout=60)
                    r2.raise_for_status()
                    try:
                        resp_json = r2.json()
                        analysis = resp_json.get("reply") or resp_json.get("output") or r2.text
                    except ValueError:
                        analysis = r2.text
                except Exception as e:
                    analysis = f"⚠️ Error calling n8n: {e}"

                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": analysis
                })

            # 4) Envío de correo si se configuró
            if email_sender and email_pass and email_recipient:
                msg = EmailMessage()
                msg["Subject"] = f"OCR Results: {pdf1.name} & {pdf2.name}"
                msg["From"]    = email_sender
                msg["To"]      = email_recipient

                # Construye el cuerpo del correo
                body = f"""
                Dear recipient,

                An automated comparison has been performed between the Purchase Order and the Order Confirmation documents. Below you will find a summary of the analysis:

                -----------------------------------------------------------
                Summary of Comparison
                - Document 1: {st.session_state['ocr_texts'][0]['filename']}
                - Document 2: {st.session_state['ocr_texts'][1]['filename']}

                -----------------------------------------------------------
                Discrepancies Identified
                {analysis}
            
                """

                msg.set_content(body)

                try:
                    with smtplib.SMTP(smtp_server, smtp_port) as server:
                        server.starttls()
                        server.login(email_sender, email_pass)
                        server.send_message(msg)
                    st.success("📧 Email sent successfully!")
                except Exception as e:
                    st.error(f"⚠️ Error sending email: {e}")

# ───────────────────────────────────────────────────────────────
# Results Dashboard
exp1, exp2, analysis_col = st.columns([1, 1, 2])

with exp1:
    st.subheader("📝 OCR Text #1")
    if st.session_state["ocr_texts"]:
        st.expander(st.session_state["ocr_texts"][0]["filename"], expanded=False).write(
            st.session_state["ocr_texts"][0]["ocr_text"]
        )
with exp2:
    st.subheader("📝 OCR Text #2")
    if len(st.session_state["ocr_texts"]) > 1:
        st.expander(st.session_state["ocr_texts"][1]["filename"], expanded=False).write(
            st.session_state["ocr_texts"][1]["ocr_text"]
        )
with analysis_col:
    st.subheader("🔎 Comparison Analysis")
    if st.session_state["messages"]:
        for msg in st.session_state["messages"]:
            if msg["role"] == "assistant":
                st.markdown(msg["content"])
