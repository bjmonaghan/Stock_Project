import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import io
from ta.trend import sma_indicator, macd, macd_signal, adx
from ta.volatility import bollinger_hband, bollinger_lband, average_true_range
from ta.momentum import rsi, stoch
from ta.volume import OnBalanceVolumeIndicator
from ta.utils import dropna

def analyze_stocks_complex_with_scoring_consolidated(tickers, period="1y"):
    all_data = pd.DataFrame()
    plots = {}

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period=period)

            if history.empty:
                st.warning(f"No historical data found for {ticker}.")
                continue

            info = stock.info
            current_price = info.get('currentPrice')
            long_name = info.get('longName', ticker)
            sector = info.get('sector')
            pe_ratio = info.get('trailingPE')
            dividend_yield = info.get('dividendYield')

            history['SMA_20'] = sma_indicator(close=history['Close'], window=20)
            history['SMA_50'] = sma_indicator(close=history['Close'], window=50)
            history['RSI'] = rsi(close=history['Close'], window=14)
            history['MACD'] = macd(close=history['Close'])
            history['MACD_signal'] = macd_signal(close=history['Close'])
            history['BB_upper'] = bollinger_hband(close=history['Close'])
            history['BB_lower'] = bollinger_lband(close=history['Close'])
            history['ATR'] = average_true_range(
                high=history['High'], low=history['Low'], close=history['Close'])
            history['ADX'] = adx(high=history['High'], low=history['Low'], close=history['Close'])
            stoch_indicator = stoch(high=history['High'], low=history['Low'], close=history['Close'])
            history['Stoch_K'] = stoch_indicator.iloc[:, 0]
            history['Stoch_D'] = stoch_indicator.iloc[:, 1]
            obv_indicator = OnBalanceVolumeIndicator(close=history['Close'], volume=history['Volume'])
            history['OBV'] = obv_indicator.on_balance_volume()

            history = dropna(history)

            atr_threshold = history['ATR'].mean() * 1.5
            high_volatility = history['ATR'].iloc[-1] > atr_threshold

            weights = {
                'SMA_20_above_SMA_50': 0.3,
                'RSI_below_70': 0.25,
                'MACD_above_signal': 0.3,
                'Close_above_BB_lower': 0.15,
                'RSI_above_70': -0.2,
                'MACD_below_signal': -0.2,
                'ADX_above_25': 0.2,
                'Stoch_K_above_D': 0.15,
                'OBV_increasing': 0.1,
            }

            if high_volatility:
                for key in ['RSI_below_70', 'RSI_above_70', 'MACD_below_signal']:
                    if key in weights: weights[key] *= 1.2
                if 'Close_above_BB_lower' in weights: weights['Close_above_BB_lower'] *= 0.8

            score = 0
            conditions = {
                'SMA_20_above_SMA_50': history['SMA_20'].iloc[-1] > history['SMA_50'].iloc[-1],
                'RSI_below_70': history['RSI'].iloc[-1] < 70,
                'MACD_above_signal': history['MACD'].iloc[-1] > history['MACD_signal'].iloc[-1],
                'Close_above_BB_lower': history['Close'].iloc[-1] > history['BB_lower'].iloc[-1],
                'RSI_above_70': history['RSI'].iloc[-1] > 70,
                'MACD_below_signal': history['MACD'].iloc[-1] < history['MACD_signal'].iloc[-1],
                'ADX_above_25': history['ADX'].iloc[-1] > 25,
                'Stoch_K_above_D': history['Stoch_K'].iloc[-1] > history['Stoch_D'].iloc[-1],
                'OBV_increasing': history['OBV'].iloc[-1] > history['OBV'].iloc[-2] if len(history) > 1 else False,
            }
            condition_explanations = {k: "Met" if v else "Not Met" for k, v in conditions.items()}

            for condition, value in conditions.items():
                if value:
                    score += weights[condition]

            buy_threshold = 0.7
            sell_threshold = 0.3

            if high_volatility:
                buy_threshold *= 1.1
                sell_threshold *= 0.9

            signal = "Buy" if score >= buy_threshold else "Sell" if score <= sell_threshold else "Hold" if 0.6 <= score < buy_threshold else "Don't Buy"

            last_data = history.tail(1)
            data_table = pd.DataFrame(
                {
                    'Company Name': long_name,
                    'Sector': sector,
                    'P/E Ratio': pe_ratio,
                    'Dividend Yield': dividend_yield,
                    'Buy Score': score,
                    'Buy/Don\'t Buy/Hold/Sell': signal,
                    'Current Price': current_price,
                    'Close': last_data['Close'].values,
                    'SMA_20': last_data['SMA_20'].values,
                    'SMA_50': last_data['SMA_50'].values,
                    'RSI': last_data['RSI'].values,
                    'MACD': last_data['MACD'].values,
                    'MACD_signal': last_data['MACD_signal'].values,
                    'BB_upper': last_data['BB_upper'].values,
                    'BB_lower': last_data['BB_lower'].values,
                    'ATR': last_data['ATR'].values,
                    'ADX': last_data['ADX'].values,
                    'Stoch_K': last_data['Stoch_K'].values,
                    'Stoch_D': last_data['Stoch_D'].values,
                    'OBV': last_data['OBV'].values,
                    'SMA_20_above_SMA_50_Explanation': condition_explanations['SMA_20_above_SMA_50'],
                    'RSI_below_70_Explanation': condition_explanations['RSI_below_70'],
                    'MACD_above_signal_Explanation': condition_explanations['MACD_above_signal'],
                    'Close_above_BB_lower_Explanation': condition_explanations['Close_above_BB_lower'],
                    'RSI_above_70_Explanation': condition_explanations['RSI_above_70'],
                    'MACD_below_signal_Explanation': condition_explanations['MACD_below_signal'],
                    "ADX_above_25_Explanation": condition_explanations['ADX_above_25'],
                    'Stoch_K_above_D_Explanation': condition_explanations['Stoch_K_above_D'],
                    'OBV_increasing_Explanation': condition_explanations['OBV_increasing'],
                    "High Volatility Don't Buy": "Yes" if high_volatility and signal == "Don't Buy" else "No",
                    "High Volatility Sell": "Yes" if high_volatility and signal == "Sell" else "No",
                },
                index=[ticker],
            )
            data_table.index.name = "Stock Symbol"
            cols = data_table.columns.tolist()
            data_table = data_table[[cols[0]] + cols[1:4] + ['Buy Score'] + cols[4:]]
            all_data = pd.concat([all_data, data_table])

            fig, axes = plt.subplots(4, 1, figsize=(16, 16))
            axes[0].plot(history['Close'], label='Close Price')
            axes[0].plot(history['SMA_20'], label='20-day SMA')
            axes[0].plot(history['SMA_50'], label='50-day SMA')
            axes[0].plot(history['BB_upper'], label='Bollinger Upper Band')
            axes[0].plot(history['BB_lower'], label='Bollinger Lower Band')
            axes[0].set_title(f"{long_name} ({ticker}): Price, MAs, BBands")
            axes[0].legend()

            axes[1].plot(history['RSI'], label='RSI')
            axes[1].axhline(70, color='red', linestyle='--', label='Overbought (70)')
            axes[1].axhline(30, color='green', linestyle='--', label='Oversold (30)')
            axes[1].set_title(f"{long_name} ({ticker}): RSI")
            axes[1].legend()

            axes[2].plot(history['MACD'], label='MACD')
            axes[2].plot(history['MACD_signal'], label='MACD Signal')
            axes[2].set_title(f"{long_name} ({ticker}): MACD")
            axes[2].legend()

            axes[3].plot(history['ADX'], label='ADX')
            axes[3].plot(history['Stoch_K'], label='Stoch K')
            axes[3].plot(history['Stoch_D'], label='Stoch D')
            axes[3].plot(history['OBV'], label='OBV')
            axes[3].set_title(f"{long_name} ({ticker}): ADX, Stoch, OBV")
            axes[3].legend()

            plt.tight_layout()
            plots[ticker] = fig

        except Exception as e:
            st.error(f"An error occurred for {ticker}: {e}")

    return all_data, plots

# ... (rest of the streamlit code remains the same)
