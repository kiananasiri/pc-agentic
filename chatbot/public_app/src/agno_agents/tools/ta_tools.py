import json
from typing import Dict, Any, List, Optional

class TAToolKit:
    def __init__(self, analysis_data: Dict[str, Any]):
        self.analysis_data = analysis_data or {}
        self.pair = self.analysis_data.get("pair", "Unknown")
        self.market = self.analysis_data.get("market", "")
        self.charts = self.analysis_data.get("charts", [])
        self.primary_chart = self.charts[0] if self.charts else {}
        self.ohlcv = self.primary_chart.get("ohlcv", [])
        self.indicators = self.primary_chart.get("indicators", [])

    def get_chart_summary(self) -> str:
        """
        Returns a high-level summary of the trading pair, market type, time range,
        total candle count, and available technical indicators.
        """
        start_date = self.primary_chart.get("startDate", "")
        end_date = self.primary_chart.get("endDate", "")
        resolution = self.primary_chart.get("resolution", "")
        indicator_names = [ind.get("fullName") or ind.get("symbol") for ind in self.indicators if isinstance(ind, dict)]

        return (
            f"Trading Pair: {self.pair}\n"
            f"Market Type: {self.market}\n"
            f"Candle Resolution: {resolution}\n"
            f"Start Date: {start_date}, End Date: {end_date}\n"
            f"Total Candles: {len(self.ohlcv)}\n"
            f"Available Indicators: {', '.join(indicator_names) if indicator_names else 'None'}"
        )

    def get_recent_candles(self, limit: int = 20) -> str:
        """
        Returns the last `limit` OHLCV (Open, High, Low, Close, Volume) candles.
        Useful for inspecting recent price action and momentum.
        """
        if not self.ohlcv:
            return "No OHLCV candle data available."
        recent = self.ohlcv[-limit:]
        formatted = []
        for i, c in enumerate(recent, start=1):
            formatted.append(
                f"Candle #{i} (Time: {c.get('timestamp')}): Open={c.get('open')}, "
                f"High={c.get('high')}, Low={c.get('low')}, Close={c.get('close')}, Volume={c.get('volume')}"
            )
        return "\n".join(formatted)

    def get_price_statistics(self) -> str:
        """
        Returns overall price statistics including highest high, lowest low,
        first open, latest close, and total volume across all candles.
        """
        if not self.ohlcv:
            return "No candle data available."
        highs = [c.get("high", 0) for c in self.ohlcv if "high" in c]
        lows = [c.get("low", 0) for c in self.ohlcv if "low" in c]
        volumes = [c.get("volume", 0) for c in self.ohlcv if "volume" in c]
        first_open = self.ohlcv[0].get("open")
        latest_close = self.ohlcv[-1].get("close")

        max_h = max(highs) if highs else 0
        min_l = min(lows) if lows else 0
        total_vol = sum(volumes)
        price_change = latest_close - first_open if (latest_close and first_open) else 0
        pct_change = (price_change / first_open * 100) if first_open else 0

        return (
            f"Price Range: Low={min_l} to High={max_h}\n"
            f"First Open: {first_open}, Latest Close: {latest_close}\n"
            f"Net Change: {price_change:.4f} ({pct_change:.2f}%)\n"
            f"Total Volume: {total_vol:.2f}"
        )

    def get_indicator_list(self) -> str:
        """
        Returns a list of all technical indicators present in the chart data along with their symbols and full names.
        """
        if not self.indicators:
            return "No technical indicators provided."
        res = []
        for ind in self.indicators:
            sym = ind.get("symbol", "unknown")
            full_name = ind.get("fullName", sym)
            options = ind.get("options", {})
            res.append(f"Symbol: '{sym}' | Full Name: '{full_name}' | Options: {options}")
        return "\n".join(res)

    def get_indicator_data(self, indicator_symbol: str, recent_count: int = 15) -> str:
        """
        Retrieves the outputs/values of a specific indicator by its symbol (e.g. 'aroon', 'cci', 'kvo', 'rsi', 'macd').
        Returns the last `recent_count` data points for that indicator.
        """
        target = indicator_symbol.lower().strip()
        found = None
        for ind in self.indicators:
            s = str(ind.get("symbol", "")).lower()
            fn = str(ind.get("fullName", "")).lower()
            if target in s or target in fn:
                found = ind
                break

        if not found:
            return f"Indicator '{indicator_symbol}' not found. Available: {[ind.get('symbol') for ind in self.indicators]}"

        full_name = found.get("fullName", indicator_symbol)
        outputs = found.get("outputs", {})
        res_lines = [f"--- Indicator: {full_name} ({indicator_symbol}) ---"]
        for key, val_list in outputs.items():
            if isinstance(val_list, list):
                slice_vals = val_list[-recent_count:]
                formatted_vals = [f"[Timestamp: {item[0]}, Value: {item[1]}]" for item in slice_vals if isinstance(item, list) and len(item)>=2]
                res_lines.append(f"Output '{key}' (Last {len(formatted_vals)} points):\n" + "\n".join(formatted_vals))
            else:
                res_lines.append(f"Output '{key}': {val_list}")

        return "\n".join(res_lines)

    def create_tools(self) -> List[Any]:
        """
        Returns functions ready to be used as tools by an Agno agent.
        """
        def get_chart_summary() -> str:
            """Get high-level summary of the trading pair, timeframe, candle count, and available indicators."""
            return self.get_chart_summary()

        def get_recent_candles(limit: int = 20) -> str:
            """Get recent OHLCV price candles (Open, High, Low, Close, Volume)."""
            return self.get_recent_candles(limit=limit)

        def get_price_statistics() -> str:
            """Get overall price statistics (highest high, lowest low, net price change %, total volume)."""
            return self.get_price_statistics()

        def get_indicator_list() -> str:
            """Get a list of all technical indicators present in the chart data."""
            return self.get_indicator_list()

        def get_indicator_data(indicator_symbol: str, recent_count: int = 15) -> str:
            """Get recent output values for a specific technical indicator by name or symbol (e.g. 'aroon', 'cci', 'kvo', 'rsi')."""
            return self.get_indicator_data(indicator_symbol=indicator_symbol, recent_count=recent_count)

        return [
            get_chart_summary,
            get_recent_candles,
            get_price_statistics,
            get_indicator_list,
            get_indicator_data,
        ]
