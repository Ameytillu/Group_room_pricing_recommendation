# 🏨 Group Pricing Intelligence Tool

A Streamlit app that gives your revenue team structured, data-driven group rate recommendations — replacing manual displacement analysis with a consistent, auditable workflow.

---

## How It Works

The app has **3 steps**:

1. **Sales Team** enters group details and stay dates
2. **Revenue Manager** enters daily room block, history, forecast, STR, pace, and proposed rate
3. **App evaluates** the proposed rate with daily displacement analysis + downloadable PDF

### Pricing Logic

```
For each stay date:
3-yr avg ADR
  × (1 + historical YoY ADR trend %)
  × (1 + manager's growth assumption %)
= Daily Projected Transient ADR  ← rate anchor

Manager enters proposed group rate
  compared against weighted projected transient ADR for context

Displacement math:
  Daily displaced rooms = max((forecasted transient rooms + daily group rooms) - hotel capacity, 0)
  Daily displaced revenue = daily displaced rooms × daily projected transient ADR
  Totals are summed across stay dates
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
| PMS / history | Daily occupancy % + ADR for each stay date in prior 3 years |
| Current forecast | Daily forecasted occupancy % or transient rooms + ADR on books |
| STR Report | MPI, ARI, comp set occupancy % |
| Pace report | Rooms on books now vs. same time last year |
| Manager judgment | Expected ADR growth %, proposed group rate |

---

## Output

- **Proposed rate analysis**: group rate vs. projected transient ADR
- **Daily displacement table**: stay date, group rooms, forecast, demand, capacity, displaced rooms, ADR, revenue, and net position
- **Displacement analysis**: total displaced room-nights, displaced revenue, and net impact
- **PDF report**: downloadable daily displacement report for proposals / sales communication

---

## Notes

- No live PMS or STR integration — all inputs are manual (by design for flexibility)
- Pricing recommendations are decision-support, not a replacement for managerial judgment
- Final rate decisions always rest with the Revenue Manager
