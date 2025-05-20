import streamlit as st
import requests

# ───────────────────────────────────────────────────────────────
# Page Config
st.set_page_config(
    page_title="OCR & Invoice Comparator",
    page_icon="🤖",
    layout="wide"
)

# ───────────────────────────────────────────────────────────────
# Sidebar: Configuration
st.sidebar.header("🔧 Configuration")
ocr_api_url = "https://ocr-api-03n6.onrender.com/upload-pdf/"
webhook_url = "https://n8n.sofiatechnology.ai/webhook-test/480b1d1a-d58f-498f-997f-304cf50253ac"

# ───────────────────────────────────────────────────────────────
# Main header
st.markdown(
    """
    # 🤖 PDF OCR & Invoice Comparator Dashboard
    Upload two invoices, run OCR, and get policy-vs-client analysis in one place.
    ---
    """,
    unsafe_allow_html=True
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "ocr_texts" not in st.session_state:
    st.session_state["ocr_texts"] = []

# ───────────────────────────────────────────────────────────────
# File upload area
col1, col2 = st.columns(2)
with col1:
    pdf1 = st.file_uploader("📄 Upload Invoice #1 (Client)", type="pdf", key="pdf1")
with col2:
    pdf2 = st.file_uploader("📄 Upload Invoice #2 (Policy)", type="pdf", key="pdf2")

# ───────────────────────────────────────────────────────────────
# Process button
process_col, _ = st.columns([1, 3])
with process_col:
    if st.button("▶️ Start Processing", use_container_width=True):
        if not (pdf1 and pdf2):
            st.error("Please upload both PDF invoices.")
        else:
            # Clear previous data
            st.session_state["messages"].clear()
            st.session_state["ocr_texts"].clear()

            # 1) Log user action
            st.session_state["messages"].append({
                "role": "user",
                "content": f"Uploaded **{pdf1.name}** & **{pdf2.name}** for OCR & analysis."
            })

            # 2) Perform OCR on each PDF
            for pdf in (pdf1, pdf2):
                with st.spinner(f"🔍 Sending {pdf.name} to OCR…"):
                    files = {"file": (pdf.name, pdf.getvalue(), "application/pdf")}
                    try:
                        resp = requests.post(ocr_api_url, files=files, timeout=60)
                        resp.raise_for_status()
                        # parse JSON or fallback to plain text
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

# ───────────────────────────────────────────────────────────────
# Results Dashboard
exp1, exp2, analysis_col = st.columns([1, 1, 2])

# OCR Text Expanders
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

# Analysis Panel
with analysis_col:
    st.subheader("🔎 Comparison Analysis")
    if st.session_state["messages"]:
        # show only the assistant’s markdown
        for msg in st.session_state["messages"]:
            if msg["role"] == "assistant":
                st.markdown(msg["content"])

