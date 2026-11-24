"""Streamlit interface for Lecture Notes Q&A."""
import os
from pathlib import Path

import pymupdf
import streamlit as st
from openai import OpenAIError

from ai import generate_answer
from notes import find_passages, read_pdf


st.set_page_config(page_title="Lecture Notes Q&A", page_icon="📚", layout="wide")

# The page keeps Streamlit's native controls for keyboard and mobile use.
st.html("""
<style>
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { max-width: 1080px; padding-top: 3rem; }
.study-hero {
  background: linear-gradient(115deg, #103a31, #185b4b);
  border-radius: 22px;
  padding: clamp(1.5rem, 5vw, 3.2rem);
  margin-bottom: 1rem;
  color: #f7fff9;
}
.study-hero h1 {
  color: inherit;
  font-size: clamp(2rem, 5vw, 3.7rem);
  line-height: 1.08;
  letter-spacing: -.045em;
  margin: 0 0 .65rem;
  padding: 0;
}
.study-hero p { color: #d9ede4; margin: 0; font-size: 1.05rem; }
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stForm"], [data-testid="stExpander"] {
  background: color-mix(in srgb, currentColor 3%, transparent);
  border: 1px solid color-mix(in srgb, currentColor 15%, transparent);
  border-radius: 16px;
}
[data-testid="stFormSubmitButton"] button {
  background: #17664f;
  border-color: #17664f;
  color: white;
}
[data-testid="stFormSubmitButton"] button:hover { background: #124b3c; color: white; }
[data-testid="stText"] { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
<div class="study-hero">
  <h1>Lecture Notes Q&amp;A</h1>
  <p>Ask a question and check the relevant pages in your lecture notes.</p>
</div>
""")

@st.cache_data(show_spinner=False, max_entries=8)
def load_sample():
    return read_pdf(Path(__file__).with_name("sample-sqa-notes.pdf").read_bytes())


document_column, study_column = st.columns([2, 3], gap="medium")

with document_column, st.container(border=True):
    st.subheader("Study material")
    upload = st.file_uploader("Lecture PDF", type=["pdf"], max_upload_size=20)
    sample = st.checkbox("Use the included SQA sample", value=True, disabled=upload is not None)
    mode = st.radio("Answer mode", ["Local search", "AI answer"], horizontal=True)
    key = ""
    model = ""
    if mode == "AI answer":
        st.caption("Your question and matching excerpts are sent to OpenAI.")
        key = os.environ.get("OPENAI_API_KEY") or st.text_input("OpenAI API key", type="password")
        model = st.text_input("OpenAI model", value="gpt-5-mini")

with study_column:
    if upload is None and not sample:
        st.info("Upload a lecture PDF or select the SQA sample.")
        st.stop()

    try:
        passages = read_pdf(upload.getvalue()) if upload is not None else load_sample()
    except (pymupdf.FileDataError, ValueError) as error:
        st.error(str(error))
        st.stop()

    filename = upload.name if upload is not None else "sample-sqa-notes.pdf"
    with st.form("ask"):
        st.subheader("Ask your notes")
        text_page_count = len({passage.page for passage in passages})
        st.caption(f"{filename} · {text_page_count} page(s) with selectable text")
        question = st.text_input(
            "Your question", placeholder="What is regression testing?", max_chars=500,
        )
        submitted = st.form_submit_button("Find answer", type="primary", width="stretch")

    if not submitted:
        st.stop()
    if not question.strip():
        st.warning("Enter a question first.")
        st.stop()

    sources = find_passages(question, passages)
    if not sources:
        st.info("I couldn’t find enough information in these notes.")
        st.stop()

    if mode == "AI answer":
        if not key or not model.strip():
            st.warning("Enter an API key and model under Study material.")
            st.stop()
        try:
            with st.spinner("Reading matching passages…"):
                answer, sources = generate_answer(question, sources, key, model.strip())
        except (OpenAIError, ValueError, KeyError, TypeError):
            st.error("AI answer unavailable. Check your API key and model, or use Local search.")
            st.stop()
        if not answer or not sources:
            st.info("I couldn’t find enough information in these notes.")
            st.stop()
        with st.container(border=True):
            st.subheader("Answer")
            st.text(answer)

    st.subheader("Matching excerpts" if mode == "Local search" else "Sources")
    for index, passage in enumerate(sources):
        with st.expander(f"{filename} · PDF page {passage.page}", expanded=index == 0):
            st.text(passage.text)
