"""ALL model calls live here. Tests replace generate_study_material with a mock."""
import json
import os
import urllib.request
from io import BytesIO

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

# One constant for the cloud model. Use the free-tier Flash model name shown in AI Studio.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "gemma3:1b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")

PROMPT = """You are a study assistant for university students. Use ONLY the lecture content provided.
Never add facts that are not in the lecture. Write everything in Greek.
Return:
- summary: 6-8 bullets, each with the page where it appears
- flashcards: exactly 10 (question on the front, short answer on the back)
- quiz: exactly 5 multiple-choice questions, each with 4 options, the index of the
  correct option (0-3), a short explanation and the source page."""


class SummaryPoint(BaseModel):
    text: str
    page: int


class Flashcard(BaseModel):
    front: str
    back: str


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=2)
    correct_index: int
    explanation: str
    page: int


class StudyMaterial(BaseModel):
    summary: list[SummaryPoint]
    flashcards: list[Flashcard]
    quiz: list[QuizQuestion]


def parse_material(raw: str) -> dict:
    """Validate the model's JSON. Raises ValueError when it is broken or incomplete."""
    try:
        material = StudyMaterial.model_validate_json(raw)
    except ValidationError as err:
        raise ValueError(f"Model returned invalid JSON: {err.error_count()} problem(s)") from err
    if not material.flashcards or not material.quiz:
        raise ValueError("Model returned no flashcards or no quiz")
    for q in material.quiz:
        if not 0 <= q.correct_index < len(q.options):
            raise ValueError("Quiz question has an invalid correct_index")
    return material.model_dump()


def _gemini(pdf_bytes: bytes) -> str:
    from google import genai
    from google.genai import types

    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError("Missing GEMINI_API_KEY (check your .env and restart)")
    client = genai.Client(api_key=key)
    models_to_try = [GEMINI_MODEL]
    if "gemini-flash-lite-latest" not in models_to_try:
        models_to_try.append("gemini-flash-lite-latest")

    last_err = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"), PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=StudyMaterial
                ),
            )
            return response.text
        except Exception as err:
            last_err = err
            if "503" in str(err) or "UNAVAILABLE" in str(err):
                continue
            raise
    if last_err:
        raise last_err


def _extract_text(pdf_bytes: bytes) -> str:
    from pypdf import PdfReader

    pages = PdfReader(BytesIO(pdf_bytes)).pages
    text = "\n".join(f"[Page {i}]\n{p.extract_text() or ''}" for i, p in enumerate(pages, 1))
    if len(text.replace("\n", "").strip()) < 50:
        raise ValueError("No text found in the PDF (it may be scanned)")
    return text


def _ollama(pdf_bytes: bytes) -> str:
    body = {
        "model": LOCAL_MODEL,
        "stream": False,
        "format": StudyMaterial.model_json_schema(),
        "messages": [{"role": "user", "content": PROMPT + "\n\nLECTURE:\n" + _extract_text(pdf_bytes)}],
    }
    req = urllib.request.Request(
        OLLAMA_URL, json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read())["message"]["content"]


def generate_study_material(pdf_bytes: bytes, private: bool = False) -> dict:
    raw = _ollama(pdf_bytes) if private else _gemini(pdf_bytes)
    return parse_material(raw)
