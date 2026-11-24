# Lecture Notes Q&A

A Python and Streamlit study app that searches lecture PDFs and shows the matching excerpts with their original page numbers. Optional AI mode generates an answer from the retrieved excerpts and displays the sources selected by the model.

## Run on Windows

Install Python 3.11 or 3.12. Extract the ZIP and open PowerShell inside the folder containing app.py.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL printed by Streamlit. The included sample is selected automatically. Ask “What is regression testing?” and check the excerpt on PDF page 2. Ask “How do volcanoes erupt?” to see the message for a question with no keyword matches.

## Answer modes

- **Local search** runs on your computer and requires no API key. It ranks passages by shared words and shows excerpts, which may be related without fully answering the question.
- **AI answer** requires an OpenAI API key with API access. Enter it in the sidebar or set OPENAI_API_KEY before starting the app. API usage can incur charges. This mode sends your question and up to four excerpts to OpenAI. Try it with the included sample before using personal notes. Check the displayed excerpts to verify generated answers.

## Project files

- **app.py** provides the upload, question form, and results.
- **notes.py** extracts page text and ranks passages.
- **ai.py** requests a grounded answer and validates the returned source IDs.
- **sample-sqa-notes.pdf** contains two pages of original demo notes.

The app supports one PDF at a time, up to 20 MB and 200 pages. It reads selectable text. Scanned pages require OCR before upload. Keyword search works best when questions and notes share wording.
