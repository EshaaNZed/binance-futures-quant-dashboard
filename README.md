Binance Futures Quant Dashboard
Real-time pairs trading analytics for Binance Futures
Live tick ingestion → OHLC bars → hedge ratios, z-scores, ADF tests → interactive dashboard

🚀 Quick Start

bash
# Clone repo
git clone https://github.com/EshaaNZed/binance-futures-quant-dashboard.git
cd binance-futures-quant-dashboard

# Install dependencies
pip install -r requirements.txt

# Run dashboard
streamlit run app.py
Open browser → http://localhost:8501 → Click "Start WebSocket feed" → Watch live analytics!

✨ Features
Live Data: Binance Futures WebSocket (fstream.binance.com/ws/{sym}@trade)

Multi-timeframe: 1s, 1m, 5m OHLCV resampling

Pairs Analytics:

Hedge ratio via OLS regression: 
PX = α + β × PY + ε
 
Spread: 
Spread = PX - β × PY

Z-score: 
Z = (Spread - μ) / σ (rolling window)

ADF test for spread stationarity

Rolling price correlation

Interactive UI: Symbol selection, zoomable Plotly charts, real-time alerts

Export: CSV downloads for bars + analytics

📊 Analytics Explained
1. Hedge Ratio (OLS)
text
PX = α + β × PY + ε
β is the optimal hedge ratio for pairs trading.

2. Spread & Z-Score
text
Spread = PX - β × PY
Z = (Spread - μ) / σ (rolling window)
Alert: |Z| > 2.0 (mean reversion signal)

3. ADF Test
Tests if spread is stationary (mean-reverting). Lower p-value = better pairs candidate.

🏗️ Architecture
text
Binance Futures WS ───┐
  {sym}@trade         │
                      ▼
ingestion/binance_ws.py ──→ storage/db.py (ticks → bars)
                              │
                              ▼
                       analytics/pairs.py
                   (OLS, z-score, ADF, corr)
                              │
                              ▼
                      app.py (Streamlit)
                ┌─────────────┴─────────────┐
                │                           │
          Plotly Charts              Alerts + CSV Export
          
Modular Design:

Loose coupling: Each module has clean interfaces

Extensible: Add Kalman filter, backtests, new data sources easily

Scalable: SQLite → Redis/Postgres, Streamlit → FastAPI+React

🛠️ Tech Stack
Component	Technology
Backend	Python 3.11, Streamlit, SQLite
Data	websocket-client, pandas
Analytics	statsmodels (OLS, ADF)
Frontend	Plotly (interactive charts)
Deployment	streamlit run app.py
📁 File Structure
text
├── app.py                 # Streamlit dashboard
├── requirements.txt       # Dependencies
├── ingestion/
│   └── binance_ws.py      # Futures WebSocket (HTML replica)
├── storage/
│   └── db.py              # SQLite ORM + OHLC resampling
├── analytics/
│   └── pairs.py           # Hedge ratio, z-score, ADF
├── data.db                # Auto-created (gitignore)
└── architecture.*         # Diagram source + PNG


🎯 Usage
Start: Click "Start WebSocket feed" (sidebar)

Configure: Select Symbol 1/2, timeframe, rolling window

Monitor: Watch price charts, z-score (±2 bands), alerts

Export: Download bars/analytics CSV

Demo Flow:

text
BTCUSDT vs ETHUSDT (1m) → Live prices → Z-score crosses +2 → ALERT → Export CSV


🔧 Design Decisions
Choice	                Why
SQLite	                Simple, file-based, no setup
One WS/symbol          	Matches HTML collector exactly
Streamlit             	Single app.py, rapid prototyping
pandas resample	        Industry standard OHLCV
statsmodels OLS/ADF   	Production-grade quant stats


🚀 Production Scaling Path

Local SQLite    → Redis + TimescaleDB
Streamlit       → FastAPI + React
Single process  → Celery workers
Local demo      → Docker + Kubernetes


📈 Gemscap Fit
Why this demonstrates quant skills:

End-to-end: Data → Analytics → Visualization

Real quant metrics: Pairs trading signals

Production patterns: Threading, error handling, modularity

Extensible: Easy to add Kalman filter, backtests
