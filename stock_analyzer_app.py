import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import os  # Import the os module for file operations
from ta.trend import sma_indicator, macd, macd_signal
from ta.volatility import bollinger_hband, bollinger_lband
from ta.momentum import rsi
from ta.volatility import average_true_range
import io  # Import io for handling file-like objects


def analyze_stocks_complex_with_scoring_consolidated(tickers, period="1y"):
    """
    Performs complex stock analysis with a scoring system, weighted indicators, and
    market condition adaptation, iterating over multiple stock tickers and
    returning a consolidated table and plots.  The plots are now created
    using subplots within a single figure for each stock.
    """
    all_data = pd.DataFrame()  # Initialize an empty DataFrame to store all stock data
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

            # Technical Indicators
            history['SMA_20'] = sma_indicator(close=history['Close'], window=20)
            history['SMA_50'] = sma_indicator(close=history['Close'], window=50)
            history['RSI'] = rsi(close=history['Close'], window=14)
            history['MACD'] = macd(close=history['Close'])
            history['MACD_signal'] = macd_signal(close=history['Close'])
            history['BB_upper'] = bollinger_hband(close=history['Close'])
            history['BB_lower'] = bollinger_lband(close=history['Close'])
            history['ATR'] = average_true_range(
                high=history['High'], low=history['Low'], close=history['Close']
            )

            # Market Condition Adaptation (Volatility)
            atr_threshold = history['ATR'].mean() * 1.5  # Adjust threshold as needed
            high_volatility = history['ATR'].iloc[-1] > atr_threshold

            # Indicator Weights (Adjust as needed)
            weights = {
                'SMA_20_above_SMA_50': 0.3,
                'RSI_below_70': 0.25,
                'MACD_above_signal': 0.3,
                'Close_above_BB_lower': 0.15,
            }

            # Adjust weights based on volatility
            if high_volatility:
                weights['RSI_below_70'] *= 1.2  # Increase weight of RSI in high volatility
                weights['Close_above_BB_lower'] *= (
                    0.8  # Decrease weight of bollinger bands in high volatility.
                )
                st.write("\nHigh Volatility Detected: Adjusting indicator weights.")

            # Scoring System
            score = 0
            conditions = {
                'SMA_20_above_SMA_50': history['SMA_20'].iloc[-1]
                                       > history['SMA_50'].iloc[-1],
                'RSI_below_70': history['RSI'].iloc[-1] < 70,
                'MACD_above_signal': history['MACD'].iloc[-1]
                                     > history['MACD_signal'].iloc[-1],
                'Close_above_BB_lower': history['Close'].iloc[-1]
                                        > history['BB_lower'].iloc[-1],
            }
            condition_explanations = {
                'SMA_20_above_SMA_50': "Met"
                if conditions['SMA_20_above_SMA_50']
                else "Not Met",
                'RSI_below_70': "Met" if conditions['RSI_below_70'] else "Not Met",
                'MACD_above_signal': "Met"
                if conditions['MACD_above_signal']
                else "Not Met",
                'Close_above_BB_lower': "Met"
                if conditions['Close_above_BB_lower']
                else "Not Met",
            }

            for condition, value in conditions.items():
                if value:
                    score += weights[condition]

            # Flexible Buy Signal (Adjust threshold as needed)
            buy_threshold = 0.7  # 70% weighted score for buy signal

            # Adjust buy threshold based on volatility
            if high_volatility:
                buy_threshold *= 1.1  # increase buy threshold in high volatility
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

            # Data Table
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
                    'SMA_20_above_SMA_50_Explanation': condition_explanations[
                        'SMA_20_above_SMA_50'
                    ],
                    'RSI_below_70_Explanation': condition_explanations['RSI_below_70'],
                    'MACD_above_signal_Explanation': condition_explanations[
                        'MACD_above_signal'
                    ],
                    'Close_above_BB_lower_Explanation': condition_explanations[
                        'Close_above_BB_lower'
                    ],
                    "High Volatility Don't Buy": "Yes"
                    if high_volatility and signal == "Don't Buy"
                    else "No",
                },
                index=[ticker],
            )

            all_data = pd.concat([all_data, data_table])  # concat each stocks data to the all_data table

            # Plotting (Consolidated Plots) - Create subplots in one figure
            fig, axes = plt.subplots(3, 1, figsize=(16, 12))  # Create 3 subplots

            # Plot Price, Moving Averages, and Bollinger Bands
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

            # Plot RSI
            axes[1].plot(history['RSI'], label='RSI')
            axes[1].set_title(f"{info.get('longName', ticker)} ({ticker}): Relative Strength Index (RSI)\n"
                              f"RSI: Measures the speed and change of price movements. Values above 70 indicate overbought conditions, below 30 indicate oversold.")
            axes[1].set_title(f"{info.get('longName', ticker)} ({ticker}): Relative Strength Index (RSI)")
            axes[1].axhline(70, color='red', linestyle='--', label='Overbought (70)')
            axes[1].axhline(30, color='green', linestyle='--', label='Oversold (30)')
            axes[1].set_ylabel('RSI')
            axes[1].set_xlabel('Date')
            axes[1].legend()

            # Plot MACD
            axes[2].plot(history['MACD'], label='MACD')
            axes[2].plot(history['MACD_signal'], label='MACD Signal')
            axes[2].set_title(
                f"{info.get('longName', ticker)} ({ticker}): Moving Average Convergence Divergence (MACD)\n"
                f"MACD: Shows changes in strength, direction, momentum, and duration of a trend. A bullish crossover occurs when MACD crosses above the signal line.")
            axes[2].set_ylabel('MACD')
            axes[2].set_xlabel('Date')
            axes[2].legend()

            plt.tight_layout()  # Adjust layout to prevent overlapping
            plots[ticker] = fig  # Store the figure in the dictionary

        except Exception as e:
            st.error(f"An error occurred for {ticker}: {e}")

    return all_data, plots  # Return the dictionary of plots


def main():
    st.title("Stock Analysis App")

    tickers_input = st.text_input(
        "Enter stock tickers (comma-separated):", "PG,HD,IBM,CSCO,KO,JNJ,AMGN,MRK,CVX,VZ"
    )
    period = st.selectbox("Select period:", ["1y", "6mo", "3mo", "1mo"])
    export_option = st.selectbox("Export Results:", ["None", "CSV", "All (CSV and Plots)"])

    if st.button("Analyze Stocks"):
        tickers = [ticker.strip().upper() for ticker in tickers_input.split(",")]
        all_data, plots = analyze_stocks_complex_with_scoring_consolidated(tickers, period=period)

        st.header("Consolidated Analysis:")
        st.dataframe(all_data)

        # Exporting
        if export_option != "None":
            if export_option in ["CSV", "All (CSV and Plots)"]:
                csv_file = all_data.to_csv().encode('utf-8')
                st.download_button(
                    label="Download Consolidated Data (CSV)",
                    data=csv_file,
                    file_name="consolidated_stock_analysis.csv",
                    mime="text/csv",
                )

            if export_option == "All (CSV and Plots)":
                for ticker, plot in plots.items():
                    # Save each plot to a BytesIO object (in memory)
                    buf = io.BytesIO()
                    plot.savefig(buf, format='png')  # Save the plot to the buffer
                    buf.seek(0)  # Go back to the beginning of the buffer

                    st.download_button(
                        label=f"Download {ticker} Analysis Plot (PNG)",
                        data=buf,  # Use the buffer's content
                        file_name=f"{ticker}_analysis_plot.png",
                        mime="image/png",
                    )
                    plt.close(plot)  # Close the plot to free memory

        # Display Plots
        st.header("Individual Stock Plots:")
        for ticker, plot in plots.items():
            st.pyplot(plot)
            plt.close(plot)  # Close the plot.


if __name__ == "__main__":
    main()
