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
    # ... (rest of the analyze_stocks_complex_with_scoring_consolidated function remains the same)

def main():
    st.title("Stock Analysis App")

    # Stock selector dropdown (without default tickers)
    all_tickers = ["PG", "HD", "IBM", "CSCO", "KO", "JNJ", "AMGN", "MRK", "CVX", "VZ"]  # Example tickers, you can modify or populate dynamically
    selected_tickers = st.multiselect("Select stock tickers:", all_tickers) #No default tickers

    period = st.selectbox("Select period:", ["1y", "6mo", "3mo", "1mo"])
    export_option = st.selectbox("Export Results:", ["None", "CSV", "All (CSV and Plots)"])

    if st.button("Analyze Stocks"):
        if not selected_tickers: # Check if any tickers are selected
            st.warning("Please select at least one stock ticker.")
            return

        all_data, plots = analyze_stocks_complex_with_scoring_consolidated(selected_tickers, period=period)

        st.header("Consolidated Analysis:")
        st.dataframe(all_data)

        # Exporting
        # ... (rest of the exporting logic remains the same)

        # Display Plots
        # ... (rest of the plotting logic remains the same)

if __name__ == "__main__":
    main()
