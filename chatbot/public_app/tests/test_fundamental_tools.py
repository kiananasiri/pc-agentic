import pytest
from public_app.src.agno_agents.tools.fundamental_tools import FundamentalToolKit

@pytest.fixture
def sample_fundamental_data():
    return {
        "market": "crypto",
        "asset": {"id": 1, "name": "Bitcoin", "symbol": "BTC"},
        "chain": {"id": 1, "name": "Bitcoin", "symbol": "BTC"},
        "startDate": "2024-03-01T00:00:00Z",
        "endDate": "2024-03-02T00:00:00Z",
        "strategy": "Smart Money Flow",
        "data": {
            "exchangeFlow": [
                {"timestamp": 1709251200000, "inflowVolume": 1500000, "outflowVolume": 1200000, "netflowVolume": 300000},
                {"timestamp": 1709337600000, "inflowVolume": 1550000, "outflowVolume": 1250000, "netflowVolume": 300000}
            ],
            "largeHoldersNetflow": [
                {"timestamp": 1709251200000, "netflow": 2500000.5},
                {"timestamp": 1709337600000, "netflow": 2600000.75}
            ]
        }
    }

def test_fundamental_summary(sample_fundamental_data):
    toolkit = FundamentalToolKit(sample_fundamental_data)
    summary = toolkit.get_fundamental_summary()
    assert "Asset: Bitcoin (BTC)" in summary
    assert "Chain: Bitcoin" in summary
    assert "Strategy: Smart Money Flow" in summary
    assert "exchangeFlow" in summary

def test_list_fundamental_metrics(sample_fundamental_data):
    toolkit = FundamentalToolKit(sample_fundamental_data)
    metrics_list = toolkit.list_fundamental_metrics()
    assert "exchangeFlow" in metrics_list
    assert "largeHoldersNetflow" in metrics_list

def test_get_metric_data(sample_fundamental_data):
    toolkit = FundamentalToolKit(sample_fundamental_data)
    flow_data = toolkit.get_metric_data("exchangeFlow", recent_count=2)
    assert "exchangeFlow" in flow_data
    assert "1500000" in flow_data

def test_get_metric_summary(sample_fundamental_data):
    toolkit = FundamentalToolKit(sample_fundamental_data)
    summary = toolkit.get_metric_summary("largeHoldersNetflow")
    assert "Total Samples: 2" in summary
    assert "First Point" in summary

def test_empty_fundamental_data():
    toolkit = FundamentalToolKit({})
    assert "Asset: Unknown" in toolkit.get_fundamental_summary()
    assert toolkit.list_fundamental_metrics() == "No fundamental metric data available."
    assert "not found" in toolkit.get_metric_data("non_existent")
