"""Full-window Streamlit interface for Lecture Notes Q&A."""
import hashlib
import os
from pathlib import Path

import pymupdf
import streamlit as st
from openai import OpenAIError

from ai import generate_answer
from notes import find_passages, read_pdf


st.set_page_config(page_title="Lecture Notes Q&A", page_icon="📚", layout="wide")
st.html("""
<style>
.stApp {
  color-scheme: dark;
  background: radial-gradient(ellipse at top right, #211648, #090d23 55%);
  color: #f5f3ff;
}
[data-testid="stHeader"] { background: transparent; height: 2.25rem; }
[data-testid="stMainBlockContainer"] {
  max-width: none; width: 100%; min-height: 100dvh;
  padding: 2.5rem clamp(.75rem, 1.5vw, 1.5rem) 1rem;
}
.study-banner {
  padding: .9rem clamp(1rem, 3vw, 2rem); border-radius: 1.1rem;
  background: radial-gradient(ellipse at 100% -70%, #8546ff, transparent 65%),
              linear-gradient(115deg, #141639, #2d1764);
  border: 1px solid #51418a;
}
.study-banner h1 { padding: 0; font-size: clamp(1.65rem, 4vw, 3rem); }
.stApp h1, .stApp h2, .stApp h3, .stApp label, .stApp p { color: #f5f3ff; }
.st-key-document, .st-key-chat {
  background: #10152f; border: 1px solid #33345d; border-radius: 1rem;
}
.st-key-question_card, .st-key-answer_card {
  position: relative; margin-left: 3.25rem;
  border: 1px solid #4a487e; border-radius: .9rem;
}
.st-key-question_card::before, .st-key-answer_card::before {
  position: absolute; left: -3.2rem; top: .3rem;
  display: grid; place-items: center; width: 2.4rem; height: 2.4rem;
  border-radius: 50%; color: #fff; font-size: 1.2rem;
}
.st-key-question_card::before { content: "●" / ""; background: #343b76; }
.st-key-answer_card::before { content: "✦" / ""; background: #6937ec; }
.st-key-source_evidence {
  background: #141838; border: 1px solid #383969; border-radius: .9rem;
}
.st-key-question_card [data-testid="stText"], .st-key-answer_card [data-testid="stText"] {
  font-size: 1.08rem; font-weight: 600;
}
.st-key-question_card { background: #222753; }
.st-key-answer_card { background: #2b205b; }
[data-testid="stFileUploaderDropzone"] {
  background: #181c40; border: 1px dashed #a58af5;
}
[data-testid="stFileUploaderDropzone"] button {
  background: #292453; border: 1px solid #5d4c97; color: #fff;
}
[data-testid="stForm"] { border: 0; padding: 0; }
.st-key-find_answer button {
  background: #6b36ef; border-color: #8459f7; color: #fff;
}
.st-key-find_answer button:hover { background: #5329be; }
.st-key-sample_questions button {
  color: #f5f3ff; background: #222650; border-color: #51418a;
}
.st-key-sample_questions button:hover { background: #35276b; border-color: #a58af5; }
.stApp input, .stApp textarea { color: #fff; background: #181c40; }
.stApp input::placeholder, .stApp textarea::placeholder { color: #c3b9df; opacity: 1; }
[data-testid="stText"], [data-testid="stText"] pre {
  color: #f5f3ff; white-space: pre-wrap; overflow-wrap: anywhere;
}
[data-testid="stExpander"] details { background: #222650; border-color: #413e70; }
[data-testid="stExpander"] summary { color: #f5f3ff; }
[data-testid="stAlert"] { background: #20254a; color: #fff; }

@media (min-width: 901px) {
  /* Let the workspace fill the space below the header without capping answers. */
  [data-testid="stMainBlockContainer"],
  [data-testid="stMainBlockContainer"] :has(.study-banner):has(.st-key-workspace),
  .st-key-workspace,
  .st-key-workspace :has(.st-key-chat):has(.st-key-document):not([data-testid="stHorizontalBlock"]),
  [data-testid="stLayoutWrapper"]:has(> .st-key-workspace) {
    display: flex;
    flex-direction: column;
    flex: 1 0 auto;
  }
  .st-key-workspace [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-chat) {
    flex: 1 0 auto;
    align-items: stretch;
    flex-wrap: nowrap;
  }
  .st-key-workspace [data-testid="stColumn"]:has(.st-key-chat, .st-key-document),
  .st-key-workspace [data-testid="stColumn"] :has(.st-key-chat, .st-key-document),
  .st-key-chat, .st-key-document {
    display: flex;
    flex-direction: column;
    flex-grow: 1;
  }
}
@media (max-width: 900px) {
  .st-key-workspace [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-chat) {
    flex-wrap: wrap;
  }
  .st-key-workspace [data-testid="stColumn"]:has(.st-key-chat, .st-key-document) {
    min-width: 100%;
  }
}
@media(max-width: 640px) {
  .st-key-question_card, .st-key-answer_card { margin-left: 0; }
  .st-key-question_card::before, .st-key-answer_card::before { display: none; }
  [data-testid="stMainBlockContainer"] { padding-inline: .75rem; }
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
  [data-testid="stColumn"] { min-width: 100%; }
}
</style>
<header class="study-banner"><h1>📚 Lecture Notes Q&amp;A</h1></header>
""")

with st.container(key="workspace"):
    chat_column, document_column = st.columns([2, 1], gap="medium")

with document_column:
    with st.container(border=True, key="document"):
        st.subheader("Study material")
        upload = st.file_uploader("Lecture PDF", type=["pdf"], max_upload_size=20)
        sample = st.checkbox("Use the SQA sample", value=True, disabled=upload is not None)
        mode = st.radio("Answer mode", ["Local search", "AI answer"], horizontal=True)
        api_key = ""
        model = ""
        if mode == "AI answer":
            st.caption("Your question and matching excerpts are sent to OpenAI.")
            api_key = os.getenv("OPENAI_API_KEY") or st.text_input("OpenAI API key", type="password")
            model = st.text_input("OpenAI model", value="gpt-5-mini").strip()

        passages = []
        document_id = None
        filename = None
        if upload is not None or sample:
            if upload is None:
                sample_path = Path(__file__).with_name("sample-sqa-notes.pdf")
                data = sample_path.read_bytes()
                filename = sample_path.name
            else:
                data = upload.getvalue()
                filename = upload.name
            try:
                passages = read_pdf(data)
                with pymupdf.open(stream=data, filetype="pdf") as pdf:
                    page_count = pdf.page_count
            except (pymupdf.FileDataError, ValueError) as error:
                passages = []
                st.error(str(error))
            else:
                document_id = (filename, hashlib.sha256(data).hexdigest(), mode)
                st.divider()
                st.text(filename)
                st.caption(f"{page_count} page(s) · PDF · {len(data) / 1024:,.1f} KB")

def set_sample_question(example):
    st.session_state.question = example


with chat_column, st.container(border=True, key="chat"):
    example_submitted = False
    with st.form("ask"):
        st.subheader("Ask your notes")
        if document_id is not None:
            st.caption(f"Searching in: {filename}")
        field, button = st.columns([4, 1.35], vertical_alignment="bottom")
        with field:
            question = st.text_area(
                "Your question", placeholder="Type or paste your question here",
                height=112, max_chars=4000, label_visibility="collapsed", key="question",
            )
        with button, st.container(key="find_answer"):
            submitted = st.form_submit_button("Find answer", type="primary", width="stretch")
        if sample and upload is None and passages:
            with st.container(key="sample_questions"):
                st.caption("Try an SQA sample question")
                for example in (
                    "What is regression testing?",
                    "What should a defect report include?",
                ):
                    clicked = st.form_submit_button(
                        example, on_click=set_sample_question, args=(example,),
                    )
                    example_submitted = example_submitted or clicked

    submitted = submitted or example_submitted

    if st.session_state.get("active_document") != document_id:
        st.session_state.active_document = document_id
        st.session_state.pop("study_result", None)

    with st.container():
        if submitted:
            st.session_state.pop("study_result", None)
            if not passages:
                st.warning("Choose a PDF or use the SQA sample first.")
            elif not question.strip():
                st.warning("Enter a question first.")
            else:
                sources = find_passages(question, passages)
                answer = ""
                if sources and mode == "AI answer":
                    if not api_key or not model:
                        st.warning("Enter an API key and model under Study material.")
                        st.stop()
                    try:
                        with st.spinner("Reading matching passages…"):
                            answer, sources = generate_answer(question, sources, api_key, model)
                    except (OpenAIError, ValueError, KeyError, TypeError):
                        st.error("AI answer unavailable. Check your API key and model, or use Local search.")
                        st.stop()
                    if not answer:
                        sources = []
                st.session_state.study_result = (question.strip(), answer, sources)

        result = st.session_state.get("study_result")
        if result is None:
            if not submitted:
                if passages:
                    st.info("Ask a question to see the answer and supporting pages here.")
                else:
                    st.info("Upload a lecture PDF or use the SQA sample.")
        else:
            asked, answer, sources = result
            with st.container(border=True, key="question_card"):
                st.caption("You")
                st.text(asked)
            if sources:
                with st.container(border=True, key="answer_card"):
                    st.caption("AI answer" if mode == "AI answer" else "Best matching excerpt")
                    st.text(answer or sources[0].text)
                    page_numbers = sorted({source.page for source in sources})
                    st.caption("PDF " + " · ".join(f"Page {page}" for page in page_numbers))
                with st.container(border=True, key="source_evidence"):
                    st.subheader("Source evidence")
                    for index, source in enumerate(sources):
                        with st.expander(f"Page {source.page} · {filename}", expanded=index == 0):
                            st.text(source.text)
            else:
                st.info("I couldn’t find enough information in these notes.")
