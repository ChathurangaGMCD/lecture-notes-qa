"""PDF text extraction and local passage search."""
import re
from dataclasses import dataclass

import pymupdf


@dataclass(frozen=True)
class Passage:
    page: int
    text: str


STOP_WORDS = set(
    "a an and are as at be can could did do does for from how i in is it me of on "
    "or should tell that the their this to was were what when where which who why "
    "will with would you about explain define notes please".split()
)


def keywords(text):
    return set(re.findall(r"[^\W_]+", text.casefold())) - STOP_WORDS


def read_pdf(data):
    passages = []
    with pymupdf.open(stream=data, filetype="pdf") as document:
        if document.needs_pass:
            raise ValueError("Upload an unlocked PDF.")
        if document.page_count > 200:
            raise ValueError("Choose a PDF with at most 200 pages.")
        for number, page in enumerate(document, start=1):
            words = page.get_text(sort=True).split()
            for offset in range(0, len(words), 100):
                passages.append(Passage(number, " ".join(words[offset:offset + 120])))
                if offset + 120 >= len(words):
                    break
    if not passages:
        raise ValueError("No selectable text was found. Try a text-based PDF.")
    return passages


def find_passages(question, passages):
    query = keywords(question)
    ranked = []
    for passage in passages:
        score = len(query & keywords(passage.text))
        if score:
            ranked.append((score, passage))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [passage for _, passage in ranked[:4]]
