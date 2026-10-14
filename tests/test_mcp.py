import asyncio
from unittest.mock import patch

import mcp_server

GOOD = {
    "summary": [{"text": "Main Point", "page": 1}],
    "flashcards": [{"front": "Q1", "back": "A1"}],
    "quiz": [{"question": "Quiz1", "options": ["a", "b"], "correct_index": 0, "explanation": "exp", "page": 1}],
}


def test_mcp_tools_registered():
    tools = asyncio.run(mcp_server.mcp.list_tools())
    tool_names = {t.name for t in tools}
    assert "summarize_lecture" in tool_names
    assert "make_flashcards" in tool_names
    assert "make_quiz" in tool_names


@patch("llm_client.generate_study_material", return_value=GOOD)
def test_mcp_tools_callable(mock_gen, tmp_path):
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test content")

    summary = mcp_server.summarize_lecture(str(pdf_file), private=True)
    assert len(summary) == 1
    assert summary[0]["text"] == "Main Point"

    cards = mcp_server.make_flashcards(str(pdf_file), count=5, private=False)
    assert len(cards) == 1
    assert cards[0]["front"] == "Q1"

    quiz = mcp_server.make_quiz(str(pdf_file), questions=3, private=True)
    assert len(quiz) == 1
    assert quiz[0]["question"] == "Quiz1"
