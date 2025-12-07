import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.graph_objs as go

st.set_page_config(page_title="Crypto BB Signals", page_icon="📈", layout="wide")

st.title("📈 5m Bollinger Band Signals – Crypto")
st.markdown(
    """
**Logic**

- 🔴 Red signal → 5m candle **OPEN & CLOSE above Upper Bollinger Band**  
- 🟢 Green signal → 5m candle **OPEN & CLOSE below Lower Bollinger Band**  
"""
)

# Sidebar controls
st.sidebar.header("Settings")

symbol = st.sidebar.text_input("Symbol (Yahoo format)", value="BTC-USD")
interval = st.sidebar.selectbox(
    "Timeframe", ["5m", "1m", "15m", "1h", "4h", "1d"], index=0
)
period = st.sidebar.selectbox(
    "History period", ["1d", "5d", "1mo", "3mo"], index=1
)
length = st.sidebar.number_input("BB Length", min_value=5, max_value=100, value=20)
mult = st.sidebar.number_input("BB Deviation (multiplier)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)

run_button = st.sidebar.button("🚀 Run Scan")

def download_data(symbol: str, interval: str, period: str) -> pd.DataFrame:
    data = yf.download(tickers=symbol, interval=interval, period=period)
    if data.empty:
        return data
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data.columns = [c.lower() for c in data.columns]
    return data

def compute_signals(df: pd.DataFrame, length: int, mult: float) -> pd.DataFrame:
    df = df.copy()
    df["basis"] = df["close"].rolling(length).mean()
    df["std"] = df["close"].rolling(length).std()
    df["upper"] = df["basis"] + mult * df["std"]
    df["lower"] = df["basis"] - mult * df["std"]
    df["red_signal"] = (df["open"] > df["upper"]) & (df["close"] > df["upper"])
    df["green_signal"] = (df["open"] < df["lower"]) & (df["close"] < df["lower"])
    return df

if run_button:
    with st.spinner("Fetching data & computing signals..."):
        data = download_data(symbol, interval, period)
        if data.empty:
            st.error("No data found. Check symbol/period/interval.")
        else:
            data = compute_signals(data, length, mult)
            signals = data[(data["red_signal"]) | (data["green_signal"])].copy()

            col1, col2, col3 = st.columns(3)
            col1.metric("Total candles", len(data))
            col2.metric("🔴 Red signals", int(signals["red_signal"].sum()))
            col3.metric("🟢 Green signals", int(signals["green_signal"].sum()))

            st.markdown("---")
            st.subheader("📋 Recent Signals")

            if signals.empty:
                st.info("No signals found in this period.")
            else:
                signals["signal_type"] = signals.apply(
                    lambda r: "RED" if r["red_signal"] else "GREEN", axis=1
                )
                st.dataframe(
                    signals[
                        ["signal_type", "open", "high", "low", "close", "upper", "lower"]
                    ].tail(50)
                )

            st.subheader("📊 Price, Bands & Signals")

            plot_df = data[["close", "upper", "lower", "red_signal", "green_signal"]].dropna()
            if not plot_df.empty:
                fig = go.Figure()

                fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["close"], mode="lines", name="Close"))
                fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["upper"], mode="lines", name="Upper BB"))
                fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["lower"], mode="lines", name="Lower BB"))

                red_pts = plot_df[plot_df["red_signal"]]
                fig.add_trace(
                    go.Scatter(
                        x=red_pts.index,
                        y=red_pts["close"],
                        mode="markers",
                        name="Red Signal",
                        marker=dict(symbol="triangle-down", size=10),
                    )
                )

                green_pts = plot_df[plot_df["green_signal"]]
                fig.add_trace(
                    go.Scatter(
                        x=green_pts.index,
                        y=green_pts["close"],
                        mode="markers",
                        name="Green Signal",
                        marker=dict(symbol="triangle-up", size=10),
                    )
                )

                fig.update_layout(height=500, xaxis_title="Time", yaxis_title="Price")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough data yet to compute Bollinger Bands.")
else:
    st.info("👈 Choose settings & click **Run Scan** in the sidebar.")
