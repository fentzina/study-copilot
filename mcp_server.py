"""Model Context Protocol (MCP) server for Study Copilot.

Exposes tools for AI agents to analyze lecture PDFs:
- summarize_lecture: Generates structured summary points with page references.
- make_flashcards: Generates interactive question/answer flashcards.
- make_quiz: Generates multiple-choice quiz questions with explanations.
"""
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

import llm_client

# Ensure .env from the project directory is loaded
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

mcp = FastMCP("study-copilot")


def _read_pdf(pdf_path: str) -> bytes:
    p = Path(pdf_path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    data = p.read_bytes()
    if not data.startswith(b"%PDF"):
        raise ValueError(f"File is not a valid PDF: {pdf_path}")
    return data


@mcp.tool(
    name="summarize_lecture",
    description="Summarize a university lecture PDF into key bullet points with page citations. Set private=True to process completely locally using Gemma/Ollama without cloud calls.",
)
def summarize_lecture(pdf_path: str, private: bool = False) -> list[dict]:
    """Extract key takeaways and summary points with page numbers from a lecture PDF."""
    pdf_bytes = _read_pdf(pdf_path)
    material = llm_client.generate_study_material(pdf_bytes, private=private)
    return material["summary"]


@mcp.tool(
    name="make_flashcards",
    description="Generate study flashcards (front question, back answer) from a lecture PDF. count specifies maximum cards to return (default 10). Set private=True for local Gemma/Ollama processing.",
)
def make_flashcards(pdf_path: str, count: int = 10, private: bool = False) -> list[dict]:
    """Generate study flashcards from a lecture PDF."""
    pdf_bytes = _read_pdf(pdf_path)
    material = llm_client.generate_study_material(pdf_bytes, private=private)
    return material["flashcards"][:count]


@mcp.tool(
    name="make_quiz",
    description="Generate multiple-choice quiz questions with options, correct answer index, explanations, and slide citations from a lecture PDF. questions specifies count (default 5). Set private=True for local Gemma/Ollama processing.",
)
def make_quiz(pdf_path: str, questions: int = 5, private: bool = False) -> list[dict]:
    """Generate multiple-choice quiz questions from a lecture PDF."""
    pdf_bytes = _read_pdf(pdf_path)
    material = llm_client.generate_study_material(pdf_bytes, private=private)
    return material["quiz"][:questions]


if __name__ == "__main__":
    mcp.run(transport="stdio")
