import time
from typing import List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ingestion.binance_ws import get_or_create_ingestor
from storage.db import resample_ticks_to_bars
from analytics.pairs import (
    compute_spread_and_zscore,
    compute_rolling_corr,
    run_adf_test,
)


AVAILABLE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]


def load_bars(symbols: List[str], timeframe: str) -> pd.DataFrame:
    return resample_ticks_to_bars(symbols, timeframe=timeframe, minutes_back=120)


def main():
    st.set_page_config(
        page_title="Binance Pairs Analytics",
        layout="wide",
    )

    st.title("Binance Pairs Analytics Dashboard")

    with st.sidebar:
        st.header("Controls")
        sym1 = st.selectbox("Symbol 1", AVAILABLE_SYMBOLS, index=0)
        sym2 = st.selectbox("Symbol 2", AVAILABLE_SYMBOLS, index=1)
        timeframe = st.radio("Timeframe", ["1s", "1m", "5m"], index=1)
        window = st.slider("Rolling window", min_value=20, max_value=300, value=100, step=10)
        z_alert_thresh = st.number_input("Z-score alert threshold", value=2.0, step=0.1)
        st.write("Tip: use the browser refresh or Streamlit 'Always rerun' for live updates.")

        st.markdown("### Data feed")
        if st.button("Start WebSocket feed"):
            get_or_create_ingestor(AVAILABLE_SYMBOLS)
            st.success("WebSocket ingestion running in background.")

    # Ensure ingestion initialised
    get_or_create_ingestor(AVAILABLE_SYMBOLS)

    # Load data once per run
    bars = load_bars([sym1, sym2], timeframe=timeframe)

    if bars.empty:
        st.warning("No data yet. Wait a few seconds for ticks to arrive, then refresh the page.")
        return

    pivot = bars.pivot_table(
        index="ts", columns="symbol", values="close"
    ).sort_index()

    px1 = pivot.get(sym1)
    px2 = pivot.get(sym2)

    # Price chart
    st.subheader("Price chart")
    fig_price = go.Figure()
    fig_price.add_trace(
        go.Scatter(x=pivot.index, y=px1, mode="lines", name=sym1)
    )
    fig_price.add_trace(
        go.Scatter(x=pivot.index, y=px2, mode="lines", name=sym2)
    )
    fig_price.update_layout(height=300, xaxis_title="Time", yaxis_title="Price")
    st.plotly_chart(fig_price, use_container_width=True, key="price_chart_main")

    # Analytics
    spread, z = compute_spread_and_zscore(px1, px2, window=window)
    corr = compute_rolling_corr(px1, px2, window=window)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Spread")
        fig_spread = go.Figure()
        fig_spread.add_trace(
            go.Scatter(
                x=spread.index,
                y=spread.values,
                mode="lines",
                name="Spread",
            )
        )
        fig_spread.update_layout(
            height=250, xaxis_title="Time", yaxis_title="Spread"
        )
        st.plotly_chart(fig_spread, use_container_width=True, key="spread_chart_main")

    with col2:
        st.subheader("Z-score")
        fig_z = go.Figure()
        fig_z.add_trace(
            go.Scatter(x=z.index, y=z.values, mode="lines", name="Z-score")
        )
        fig_z.add_hline(y=2.0, line_dash="dash", line_color="red")
        fig_z.add_hline(y=-2.0, line_dash="dash", line_color="red")
        fig_z.update_layout(
            height=250, xaxis_title="Time", yaxis_title="Z-score"
        )
        st.plotly_chart(fig_z, use_container_width=True, key="zscore_chart_main")

    st.subheader("Rolling correlation")
    fig_corr = go.Figure()
    fig_corr.add_trace(
        go.Scatter(x=corr.index, y=corr.values, mode="lines", name="Rolling corr")
    )
    fig_corr.update_layout(
        height=250, xaxis_title="Time", yaxis_title="Corr"
    )
    st.plotly_chart(fig_corr, use_container_width=True, key="corr_chart_main")

    # Stats + ADF
    latest_z = z.dropna().iloc[-1] if not z.dropna().empty else np.nan
    latest_corr = corr.dropna().iloc[-1] if not corr.dropna().empty else np.nan
    adf_stat, adf_p = run_adf_test(spread)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Latest z-score",
        f"{latest_z:.2f}" if not np.isnan(latest_z) else "N/A",
    )
    c2.metric(
        "Latest corr",
        f"{latest_corr:.2f}" if not np.isnan(latest_corr) else "N/A",
    )
    c3.metric(
        "ADF stat",
        f"{adf_stat:.2f}" if adf_stat is not None else "N/A",
    )
    c4.metric(
        "ADF p-value",
        f"{adf_p:.3f}" if adf_p is not None else "N/A",
    )

    # Alerts
    if not np.isnan(latest_z) and abs(latest_z) >= z_alert_thresh:
        st.error(
            f"Alert: |z-score| >= {z_alert_thresh:.2f} (z = {latest_z:.2f})"
        )

    # Downloads
    st.subheader("Download data")
    bars_csv = bars.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download bars CSV",
        data=bars_csv,
        file_name=f"bars_{sym1}_{sym2}_{timeframe}.csv",
        mime="text/csv",
    )

    analytics_df = pd.DataFrame(
        {
            "ts": spread.index,
            "spread": spread.values,
            "zscore": z.values,
            "rolling_corr": corr.reindex(spread.index).values,
        }
    )
    analytics_csv = analytics_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download analytics CSV",
        data=analytics_csv,
        file_name=f"analytics_{sym1}_{sym2}_{timeframe}.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
