import pytest
from public_app.src.agno_agents.orchestrator import (
    estimate_tokens,
    format_history_context,
    run_agno_chat
)
from public_app.src.utilis import calculate_price

def test_estimate_tokens():
    text = "سلام، این یک تست برای شمارش توکن‌های مدل هوش مصنوعی است."
    tokens = estimate_tokens(text, model="gpt-4o-mini")
    assert isinstance(tokens, int)
    assert tokens > 0

def test_format_history_context():
    history = [
        {"question": "سلام", "answer": "درود! چطور می‌تونم کمکتون کنم؟"},
        {"question": "قیمت بیت‌کوین چنده؟", "answer": "در حال حاضر داده‌های بازار را بررسی می‌کنم."}
    ]
    formatted = format_history_context(history)
    assert "--- Conversation History ---" in formatted
    assert "User: سلام" in formatted
    assert "Assistant: درود!" in formatted

def test_calculate_price():
    # Test pricing for supported models using (input_token, output_token, model)
    price_mini = calculate_price(1000, 500, model="gpt-4o-mini")
    assert price_mini > 0

    price_o3 = calculate_price(1000, 500, model="o3-mini")
    assert price_o3 > 0

    price_gpt45 = calculate_price(1000, 500, model="gpt-4.5-preview")
    assert price_gpt45 > 0

def test_run_agno_chat_fallback(monkeypatch):
    class MockMetrics:
        input_tokens = 100
        output_tokens = 50

    class MockRunOutput:
        content = "تحلیل تکنیکال با موفقیت انجام شد."
        metrics = MockMetrics()

    def mock_run(self, prompt):
        return MockRunOutput()

    from agno.agent import Agent
    monkeypatch.setattr(Agent, "run", mock_run)

    sample_ta = {
        "pair": "BTCUSDT",
        "market": "crypto:spot",
        "charts": [{"ohlcv": [], "indicators": []}]
    }

    res = run_agno_chat(
        user_input="تحلیل تکنیکال BTC رو بده",
        analysis=sample_ta,
        model="gpt-4o-mini"
    )

    assert "answer" in res
    assert res["answer"] == "تحلیل تکنیکال با موفقیت انجام شد."
    assert "price" in res
    assert res["price"] > 0

def test_auto_enrich_payloads_greeting():
    from public_app.src.market_data_service import auto_enrich_payloads
    ta, fa = auto_enrich_payloads("hi")
    assert ta == {}
    assert fa == {}

