import json
from typing import Dict, Any, List

class FundamentalToolKit:
    def __init__(self, fundamental_data: Dict[str, Any]):
        self.fundamental_data = fundamental_data or {}
        self.asset = self.fundamental_data.get("asset", {})
        self.chain = self.fundamental_data.get("chain", {})
        self.market = self.fundamental_data.get("market", "")
        self.strategy = self.fundamental_data.get("strategy", "")
        self.start_date = self.fundamental_data.get("startDate", "")
        self.end_date = self.fundamental_data.get("endDate", "")
        self.data_dict = self.fundamental_data.get("data", {})

    def get_fundamental_summary(self) -> str:
        """
        Returns high-level metadata about the fundamental analysis payload:
        Asset name/symbol, chain, market, date range, strategy name, and metric count.
        """
        asset_name = self.asset.get("name", "Unknown")
        asset_symbol = self.asset.get("symbol", "")
        chain_name = self.chain.get("name", "Unknown")

        metrics_available = list(self.data_dict.keys()) if isinstance(self.data_dict, dict) else []

        return (
            f"Asset: {asset_name} ({asset_symbol})\n"
            f"Chain: {chain_name}\n"
            f"Market: {self.market}\n"
            f"Strategy: {self.strategy}\n"
            f"Date Range: {self.start_date} to {self.end_date}\n"
            f"Available Metrics: {', '.join(metrics_available) if metrics_available else 'None'}"
        )

    def list_fundamental_metrics(self) -> str:
        """
        Lists all available fundamental/on-chain metric keys in the data dictionary.
        """
        if not isinstance(self.data_dict, dict) or not self.data_dict:
            return "No fundamental metric data available."
        
        summaries = []
        for metric, values in self.data_dict.items():
            count = len(values) if isinstance(values, list) else 1
            summaries.append(f"- '{metric}': {count} data point(s)")
        return "\n".join(summaries)

    def get_metric_data(self, metric_name: str, recent_count: int = 10) -> str:
        """
        Retrieves the data points for a specific fundamental/on-chain metric (e.g. 'averageBalance', 'exchangeFlow', 'largeHoldersNetflow').
        Returns the last `recent_count` entries.
        """
        if not isinstance(self.data_dict, dict):
            return "No metric data available."

        target = metric_name.strip()
        found_key = None
        for k in self.data_dict.keys():
            if k.lower() == target.lower():
                found_key = k
                break

        if not found_key:
            return f"Metric '{metric_name}' not found. Available metrics: {list(self.data_dict.keys())}"

        data_val = self.data_dict[found_key]
        if isinstance(data_val, list):
            sliced = data_val[-recent_count:]
            formatted = []
            for item in sliced:
                formatted.append(json.dumps(item, ensure_ascii=False))
            return f"--- Metric: {found_key} (showing last {len(sliced)} entries) ---\n" + "\n".join(formatted)
        else:
            return f"--- Metric: {found_key} ---\n{json.dumps(data_val, ensure_ascii=False)}"

    def get_metric_summary(self, metric_name: str) -> str:
        """
        Calculates key statistical indicators (start value, latest value, min, max, trend) for a numeric metric series.
        """
        if not isinstance(self.data_dict, dict):
            return "No metric data available."

        target = metric_name.strip()
        found_key = None
        for k in self.data_dict.keys():
            if k.lower() == target.lower():
                found_key = k
                break

        if not found_key:
            return f"Metric '{metric_name}' not found."

        data_val = self.data_dict[found_key]
        if not isinstance(data_val, list) or len(data_val) == 0:
            return f"Metric '{found_key}' has no time-series array data."

        first_entry = data_val[0]
        latest_entry = data_val[-1]

        return (
            f"--- Summary for Metric: {found_key} ---\n"
            f"Total Samples: {len(data_val)}\n"
            f"First Point: {json.dumps(first_entry)}\n"
            f"Latest Point: {json.dumps(latest_entry)}"
        )

    def create_tools(self) -> List[Any]:
        """
        Returns functions ready to be used as tools by an Agno agent.
        """
        def get_fundamental_summary() -> str:
            """Get high-level metadata (asset, chain, market, strategy, date range, available metrics)."""
            return self.get_fundamental_summary()

        def list_fundamental_metrics() -> str:
            """List all fundamental/on-chain metric keys available in the dataset."""
            return self.list_fundamental_metrics()

        def get_metric_data(metric_name: str, recent_count: int = 10) -> str:
            """Get data points for a specific metric (e.g. 'exchangeFlow', 'largeHoldersNetflow', 'bullsAndBears', 'averageBalance')."""
            return self.get_metric_data(metric_name=metric_name, recent_count=recent_count)

        def get_metric_summary(metric_name: str) -> str:
            """Get summary overview (first point, latest point, sample count) for a specific metric."""
            return self.get_metric_summary(metric_name=metric_name)

        return [
            get_fundamental_summary,
            list_fundamental_metrics,
            get_metric_data,
            get_metric_summary,
        ]
