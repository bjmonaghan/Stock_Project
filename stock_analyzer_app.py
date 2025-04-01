import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import io
from ta.trend import sma_indicator, macd, macd_signal
from ta.volatility import bollinger_hband, bollinger_lband
from ta.momentum import rsi
from ta.volatility import average_true_range


def get_all_tickers():
    """Retrieves a list of all available stock tickers and their company names."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        sp500_table = tables[0]
        tickers = sp500_table['Symbol'].tolist()

        ticker_info = {}
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                if 'longName' in info:
                    ticker_info[ticker] = info['longName']
            except Exception as e:
                print(f"Error getting info for {ticker}: {e}")
                pass
        return ticker_info
    except Exception as e:
        print(f"Error getting tickers: {e}")
        return {}


def analyze_stocks_complex_with_scoring_consolidated(tickers, period="1y"):
    """
    Performs complex stock analysis with a scoring system, weighted indicators, and
    market condition adaptation, iterating over multiple stock tickers and
    returning a consolidated table and plots. The plots are now created
    using subplots within a single figure for each stock.
    """
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
            st.write(f"Analyzing {info.get('longName', ticker)} ({ticker}):")
            st.write(f"Current Price: {current_price}")

            history['SMA_20'] = sma_indicator(close=history['Close'], window=20)
            history['SMA_50'] = sma_indicator(close=history['Close'], window=50)
            history['RSI'] = rsi(close=history['Close'], window=14)
            history['MACD'] = macd(close=history['Close'])
            history['MACD_signal'] = macd_signal(close=history['Close'])
            history['BB_upper'] = bollinger_hband(close=history['Close'])
            history['BB_lower'] = bollinger_lband(close=history['Close'])
            history['ATR'] = average_true_range(
                high=history['High'], low=history['Low'], close=history['Close'])

            atr_threshold = history['ATR'].mean() * 1.5
            high_volatility = history['ATR'].iloc[-1] > atr_threshold

            weights = {
                'SMA_20_above_SMA_50': 0.3,
                'RSI_below_70': 0.25,
                'MACD_above_signal': 0.3,
                'Close_above_BB_lower': 0.15,
            }

            if high_volatility:
                weights['RSI_below_70'] *= 1.2
                weights['Close_above_BB_lower'] *= 0.8
                st.write("\nHigh Volatility Detected: Adjusting indicator weights.")

            score = 0
            conditions = {
                'SMA_20_above_SMA_50': history['SMA_20'].iloc[-1] > history['SMA_50'].iloc[-1],
                'RSI_below_70': history['RSI'].iloc[-1] < 70,
                'MACD_above_signal': history['MACD'].iloc[-1] > history['MACD_signal'].iloc[-1],
                'Close_above_BB_lower': history['Close'].iloc[-1] > history['BB_lower'].iloc[-1],
            }
            condition_explanations = {
                'SMA_20_above_SMA_50': "Met" if conditions['SMA_20_above_SMA_50'] else "Not Met",
                'RSI_below_70': "Met" if conditions['RSI_below_70'] else "Not Met",
                'MACD_above_signal': "Met" if conditions['MACD_above_signal'] else "Not Met",
                'Close_above_BB_lower': "Met" if conditions['Close_above_BB_lower'] else "Not Met",
            }

            for condition, value in conditions.items():
                if value:
                    score += weights[condition]

            buy_threshold = 0.7

            if high_volatility:
                buy_threshold *= 1.1
                st.write("High Volatility Detected: Adjusting buy threshold.")

            if 0.6 <= score < buy_threshold:
                signal = "Hold"
            elif score >= buy_threshold:
                signal = "Buy"
            else:
                signal = "Don't Buy"

            st.write(f"\nBuy/Don't Buy/Hold Signal: {signal}")
            st.write(f"Score: {score}")

            if signal == "Buy":
                st.write("\nBuy Signal Explanation:")
                for condition, value in conditions.items():
                    if value:
                        st.write(f"- {condition}: Met")
                    else:
                        st.write(f"- {condition}: Not Met")

            elif signal == "Don't Buy":
                st.write("\nDon't Buy Signal Explanation:")
                for condition, value in conditions.items():
                    if not value:
                        st.write(f"- {condition}: Not Met")
            elif signal == "Hold":
                st.write("\nHold Signal Explanation:")
                for condition, value in conditions.items():
                    st.write(f"- {condition}: {'Met' if value else 'Not Met'}")

            last_data = history.tail(1)
            data_table = pd.DataFrame(
                {
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
                    'Buy Score': score,
                    'Buy/Don\'t Buy/Hold': signal,
                    'SMA_20_above_SMA_50_Explanation': condition_explanations['SMA_20_above_SMA_50'],
                    'RSI_below_70_Explanation': condition_explanations['RSI_below_70'],
                    'MACD_above_signal_Explanation': condition_explanations['MACD_above_signal'],
                    'Close_above_BB_lower_Explanation': condition_explanations['Close_above_BB_lower'],
                    "High Volatility Don't Buy": "Yes" if high_volatility and signal == "Don't Buy" else "No",
                },
                index=[ticker],
            )

            all_data = pd.concat([all_data, data_table])

            fig, axes = plt.subplots(3, 1, figsize=(16, 12))

            axes[0].plot(history['Close'], label='Close Price')
            axes[0].plot(history['SMA_20'], label='20-day SMA')
            axes[0].plot(history['SMA_50'], label='50-day SMA')
            axes[0].plot(history['BB_upper'], label='Bollinger Upper Band')
            axes[0].plot(history['BB_lower'], label='Bollinger Lower Band')
            axes[0].set_title(
                f"{info.get('longName', ticker)} ({ticker}): Price, Moving Averages, and Bollinger Bands\n"
                f"Bollinger Bands: Measure volatility. Prices near upper band may be overbought, near lower band may be oversold."
            )
            axes[0].set_ylabel('Price')
            axes[0].set_xlabel('Date')
            axes[0].legend()

            axes[1].plot(history['RSI'], label='RSI')
            axes[1].set_title(
                f"{info.get('longName', ticker)} ({ticker}): Relative Strength Index (RSI)\n"
                f"RSI: Measures the speed and change of price movements. Values above 70 indicate overbought conditions, below 30 indicate oversold."
            )
            axes[1].axhline(70, color='red', linestyle='--', label='Overbought (70)')
            axes[1].axhline(30, color='green', linestyle='--', label='Oversold (30)')
            axes[1].set_ylabel('RSI')
            axes[1].set_xlabel('Date')
            axes[1].legend()

            axes[2].plot(history['MACD'], label='MACD')
            axes[2].plot(history['MACD_signal'], label='MACD Signal')
            axes[2].set_title(
                f"{info.get('longName', ticker)} ({ticker}): Moving Average Convergence Divergence (MACD)\n"
                f"MACD: Shows changes in strength, direction, momentum, and duration of a trend. A bullish crossover occurs when MACD crosses above the signal line."
            )
            axes[2].set_ylabel('MACD')
            axes[2].set_xlabel('Date')
            axes[2].legend()

            plt.tight_layout()
            plots[ticker] = fig

        except Exception as e:
            st.error(f"An error occurred for {ticker}: {e}")

    return all_data, plots


def main():
    st.title("Stock Analysis App")

    ticker_info = get_all_tickers()
    ticker_options = [f"{name} ({ticker})" for ticker, name in ticker_info.items()]

    selected_options = st.multiselect("Select stocks:", ticker_options)
    selected_tickers = [option.split("(")[-1][:-1] for option in selected_options]

    period = st.selectbox("Select period:", ["1y", "6mo", "3mo", "1mo"])
    export_option = st.selectbox("Export Results:", ["None", "CSV", "All (CSV and Plots)"])

    if st.button("Analyze Stocks"):
        if not selected_tickers:
            st.warning("Please select at least one stock.")
            return

        all_data, plots = analyze_stocks_complex_with_scoring_consolidated(
            selected_tickers, period=period)

        st.header("Consolidated Analysis:")
        st.dataframe(all_data)

        if export_option != "None":
            if export_option in ["CSV", "All (CSV and Plots)"]:
                csv_file = all_data.to_csv().encode('utf-8')
                st.download_button(label="Download Consolidated Data (CSV)",
                                    data=csv_file,
                                    file_name="consolidated_stock_analysis.csv",
                                    mime="text/csv")

            if export_option == "All (CSV and Plots)":
                for ticker, plot in plots.items():
                    buf = io.BytesIO()
                    plot.savefig(buf, format='png')
                    buf.seek(0)
                    st.download_button(label=f"Download {ticker} Analysis Plot (PNG)",
                                        data=buf,
                                        file_name=f"{ticker}_analysis_plot.png",
                                        mime="image/png")
                    plt.close(plot)

        st.header("Individual Stock Plots:")
        for ticker, plot in plots.items():
            st.pyplot(plot)
            plt.close(plot)


if __name__ == "__main__":
    main()
