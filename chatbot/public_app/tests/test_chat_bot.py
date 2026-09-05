import pytest
from public_app.src.chat_bot import chat

def test_chat_execution_fallback(monkeypatch):
    # Mock run_agno_chat response
    def mock_run_agno_chat(*args, **kwargs):
        return {
            "answer": "پاسخ نمونه ایجنت Agno",
            "tokens": {"input_tokens": 150, "output_tokens": 80},
            "price": 0.0000705,
            "error": None
        }

    monkeypatch.setattr("public_app.src.chat_bot.run_agno_chat", mock_run_agno_chat)

    response = chat(
        user_input="وضعیت بیت کوین چگونه است؟",
        model="gpt-4o-mini"
    )

    assert "answer" in response
    assert response["answer"] == "پاسخ نمونه ایجنت Agno"
    assert response["price"] == 0.0000705
    assert response["error"] is None
