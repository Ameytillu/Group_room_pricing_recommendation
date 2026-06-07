# 🏨 Group Pricing Intelligence Tool

A Streamlit app that gives your revenue team structured, data-driven group rate recommendations — replacing manual displacement analysis with a consistent, auditable workflow.

---

## How It Works

The app has **3 steps**:

1. **Sales Team** enters group details (name, dates, room block)
2. **Revenue Manager** enters market data (3-yr history, STR, pace, forecast)
3. **App evaluates** the manager's proposed rate + displacement analysis + downloadable PDF

### Pricing Logic

```
3-yr avg ADR (same dates)
  × (1 + historical YoY ADR trend %)
  × (1 + manager's growth assumption %)
= Projected Transient ADR  ← rate anchor

Manager enters proposed group rate
  compared against projected transient ADR for context

Displacement math:
  Displaced room-nights = group block that exceeds 95% occ threshold
  Displaced revenue     = displaced room-nights × projected transient ADR
  Group revenue         = block × nights × proposed rate
  Net revenue position  = group revenue − displaced transient revenue
```

---

## Project Structure

```
group_pricing_tool/
├── app.py                  # Main Streamlit app (3-step UI)
├── requirements.txt        # Python dependencies
├── README.md
└── utils/
    ├── __init__.py
    ├── pricing_engine.py   # All pricing & displacement logic
    └── pdf_export.py       # ReportLab PDF report generator
```

---

## Deploy to Streamlit Cloud

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit: Group Pricing Tool"
git remote add origin https://github.com/Ameytillu/Group_room_pricing_recommendation.git
git push -u origin main
```

### Step 2 — Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New app**
3. Connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Click **Deploy** — done!

Streamlit Cloud auto-installs everything in `requirements.txt`.

---

## Local Development

```bash
# Clone / navigate to project folder
cd group_pricing_tool

# Install dependencies
pip install -r requirements.txt

# Run app
streamlit run app.py
```

---

## Data Inputs Required (per group inquiry)

| Source | Fields |
|--------|--------|
| PMS / history | Occupancy % + ADR for same dates in prior 3 years |
| Current forecast | Forecasted occupancy % + ADR on books for group dates |
| STR Report | MPI, ARI, comp set occupancy % |
| Pace report | Rooms on books now vs. same time last year |
| Manager judgment | Expected ADR growth %, proposed group rate |

---

## Output

- **Proposed rate analysis**: group rate vs. projected transient ADR
- **Displacement analysis**: displaced room-nights, displaced revenue, net impact
- **Revenue comparison table**: group revenue vs. transient revenue at each tier
- **PDF report**: downloadable one-pager for proposals / sales communication

---

## Notes

- No live PMS or STR integration — all inputs are manual (by design for flexibility)
- Pricing recommendations are decision-support, not a replacement for managerial judgment
- Final rate decisions always rest with the Revenue Manager
