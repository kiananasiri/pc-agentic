
import yfinance as yf

def calculate_sma(data, window):
   return data.rolling(window=window).mean()

def calculate_ema(data, window):
   return data.ewm(span=window, adjust=False).mean()

def calculate_rsi(data, window):
   delta = data.diff()
   gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
   loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
   rs = gain / loss
   rsi = 100 - (100 / (1 + rs))
   return rsi

def calculate_macd(data, short_window, long_window, signal_window):
   short_ema = calculate_ema(data, short_window)
   long_ema = calculate_ema(data, long_window)
   macd = short_ema - long_ema
   signal = calculate_ema(macd, signal_window)
   return macd, signal

def generate_signals(data, short_window, long_window, signal_window):
   macd, signal = calculate_macd(data, short_window, long_window, signal_window)
   buy_signals = (macd > signal) & (macd.shift(1) <= signal.shift(1))
   sell_signals = (macd < signal) & (macd.shift(1) >= signal.shift(1))
   return buy_signals, sell_signals

def get_stock_data(ticker, start_date, end_date):
   return yf.download(ticker, start=start_date, end=end_date)['Close']

def trading_strategy(ticker, start_date, end_date, short_window, long_window, signal_window):
   data = get_stock_data(ticker, start_date, end_date)
   buy_signals, sell_signals = generate_signals(data, short_window, long_window, signal_window)
   return data, buy_signals, sell_signals

