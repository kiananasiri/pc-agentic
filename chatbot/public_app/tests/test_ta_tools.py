import pytest
from public_app.src.agno_agents.tools.ta_tools import TAToolKit

@pytest.fixture
def sample_ta_data():
    return {
        "pair": "BTCUSDT",
        "market": "crypto:spot",
        "charts": [{
            "startDate": "2025-05-01T05:40:53.254Z",
            "endDate": "2025-05-03T07:40:53.254Z",
            "resolution": "1m",
            "ohlcv": [
                {"low": 102887.9, "high": 102902.7, "open": 102902.6, "close": 102898.4, "volume": 18.642, "timestamp": 1746841800000},
                {"low": 102866.0, "high": 102901.6, "open": 102898.4, "close": 102899.9, "volume": 82.579, "timestamp": 1746841860000},
                {"low": 102900.0, "high": 102915.5, "open": 102900.0, "close": 102915.4, "volume": 31.620, "timestamp": 1746841920000}
            ],
            "indicators": [
                {
                    "symbol": "aroon",
                    "fullName": "Aroon Indicator",
                    "outputs": {
                        "aroon_up": [[1746841920000, 85.7]],
                        "aroon_down": [[1746841920000, 14.2]]
                    }
                },
                {
                    "symbol": "rsi",
                    "fullName": "Relative Strength Index",
                    "outputs": {
                        "rsi": [[1746841920000, 62.4]]
                    }
                }
            ]
        }]
    }

def test_chart_summary(sample_ta_data):
    toolkit = TAToolKit(sample_ta_data)
    summary = toolkit.get_chart_summary()
    assert "Trading Pair: BTCUSDT" in summary
    assert "Market Type: crypto:spot" in summary
    assert "Total Candles: 3" in summary
    assert "Aroon Indicator" in summary

def test_recent_candles(sample_ta_data):
    toolkit = TAToolKit(sample_ta_data)
    recent = toolkit.get_recent_candles(limit=2)
    assert "Candle #1" in recent
    assert "Candle #2" in recent
    assert "102915.4" in recent

def test_price_statistics(sample_ta_data):
    toolkit = TAToolKit(sample_ta_data)
    stats = toolkit.get_price_statistics()
    assert "High=102915.5" in stats
    assert "Low=102866.0" in stats
    assert "First Open: 102902.6" in stats
    assert "Latest Close: 102915.4" in stats

def test_indicator_data(sample_ta_data):
    toolkit = TAToolKit(sample_ta_data)
    aroon_info = toolkit.get_indicator_data("aroon")
    assert "Aroon Indicator" in aroon_info
    assert "aroon_up" in aroon_info

def test_empty_ta_data():
    toolkit = TAToolKit({})
    summary = toolkit.get_chart_summary()
    assert "Total Candles: 0" in summary
    assert toolkit.get_recent_candles() == "No OHLCV candle data available."
    assert toolkit.get_price_statistics() == "No candle data available."
