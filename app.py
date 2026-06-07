from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils.pdf_export import generate_pdf_report
from utils.pricing_engine import run_pricing_engine


st.set_page_config(
    page_title="Group Pricing Tool",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background-color: #F8F9FB; }
    .app-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #2563a8 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
    }
    .app-header h1 { font-size: 1.8rem; font-weight: 700; margin: 0; color: white; }
    .app-header p { font-size: 0.9rem; opacity: 0.82; margin: 0.3rem 0 0; color: white; }
    .step-card {
        background: white;
        border-radius: 12px;
        padding: 1.6rem 2rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        margin-bottom: 1.5rem;
    }
    .step-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #2563a8;
        margin-bottom: 0.3rem;
    }
    .step-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a3a5c;
        margin-bottom: 1.2rem;
    }
    .result-card {
        border-radius: 10px;
        padding: 1.4rem;
        text-align: center;
        border: 1px solid transparent;
        min-height: 145px;
    }
    .result-min { background: #F0FDF4; border-color: #86EFAC; }
    .result-rec { background: #EFF6FF; border-color: #93C5FD; }
    .result-str { background: #FFF7ED; border-color: #FDB562; }
    .result-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.3rem;
    }
    .result-rate { font-size: 2rem; font-weight: 700; margin: 0.2rem 0; }
    .result-desc { font-size: 0.78rem; color: #64748B; }
    .result-min .result-label, .result-min .result-rate { color: #15803D; }
    .result-rec .result-label, .result-rec .result-rate { color: #1D4ED8; }
    .result-str .result-label, .result-str .result-rate { color: #EA580C; }
    .metric-strip {
        background: white;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        border: 1px solid #E2E8F0;
        text-align: center;
    }
    .metric-strip .m-label {
        font-size: 0.72rem;
        color: #94A3B8;
        font-weight: 500;
        text-transform: uppercase;
    }
    .metric-strip .m-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1a3a5c;
    }
    .disp-warn {
        background: #FFF1F2;
        border: 1px solid #FECDD3;
        border-left: 4px solid #E11D48;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-top: 1rem;
    }
    .disp-med {
        background: #FFFBEB;
        border: 1px solid #FDE68A;
        border-left: 4px solid #D97706;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-top: 1rem;
    }
    .disp-ok {
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-left: 4px solid #16A34A;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-top: 1rem;
    }
    .calc-box {
        background: #F8F9FB;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #2563a8;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    .calc-step-num {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #2563a8;
        margin-bottom: 0.2rem;
    }
    .calc-step-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #1a3a5c;
        margin-bottom: 0.6rem;
    }
    .calc-formula {
        background: #1a3a5c;
        color: #E2E8F0;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        font-family: 'Courier New', monospace;
        font-size: 0.82rem;
        margin: 0.5rem 0;
    }
    .calc-result {
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-size: 0.88rem;
        font-weight: 600;
        color: #1D4ED8;
        margin-top: 0.4rem;
    }
    .calc-note { font-size: 0.78rem; color: #64748B; margin-top: 0.4rem; }
    hr { border: none; border-top: 1px solid #E2E8F0; margin: 1.5rem 0; }
    #MainMenu, footer { visibility: hidden; }
    label { font-size: 0.85rem !important; font-weight: 500 !important; color: #374151 !important; }
</style>
""", unsafe_allow_html=True)


def stay_dates(arrival: date, departure: date) -> list[date]:
    nights = (departure - arrival).days
    return [arrival + timedelta(days=idx) for idx in range(nights)]


def format_date(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%m/%d/%Y")
    return str(value)


def daily_results_df(results: dict) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Stay Date": format_date(row["stay_date"]),
            "Group Rooms": row["group_rooms"],
            "Forecasted Transient Rooms": row["forecasted_transient_rooms"],
            "Total Demand After Group": row["total_demand_after_group"],
            "Hotel Capacity": row["hotel_capacity"],
            "Displaced Rooms": row["displaced_rooms"],
            "Projected Transient ADR": f"${row['projected_transient_adr']:,.0f}",
            "Group Revenue": f"${row['group_revenue']:,.0f}",
            "Displaced Revenue": f"${row['displaced_revenue']:,.0f}",
            "Net Revenue Position": f"${row['net_revenue_position']:+,.0f}",
        }
        for row in results["daily_results"]
    ])


if "step" not in st.session_state:
    st.session_state.step = 1
if "sales_data" not in st.session_state:
    st.session_state.sales_data = {}
if "market_data" not in st.session_state:
    st.session_state.market_data = {}
if "results" not in st.session_state:
    st.session_state.results = None

st.markdown("""
<div class="app-header">
    <h1>🏨 Group Pricing Intelligence Tool</h1>
    <p>Evaluate each stay night separately, then summarize group displacement and revenue impact.</p>
</div>
""", unsafe_allow_html=True)

col_p1, col_p2, col_p3 = st.columns(3)
for num, label, col in [
    ("1", "Sales Request", col_p1),
    ("2", "Daily Data", col_p2),
    ("3", "Rate Analysis", col_p3),
]:
    active = st.session_state.step == int(num)
    done = st.session_state.step > int(num)
    icon = "✓" if done else num
    bg = "#2563a8" if active else ("#16A34A" if done else "#CBD5E1")
    with col:
        st.markdown(f"""
        <div style="text-align:center; padding:0.5rem;">
            <div style="width:32px;height:32px;border-radius:50%;background:{bg};
                        color:white;font-weight:700;font-size:0.9rem;
                        display:inline-flex;align-items:center;justify-content:center;">
                {icon}
            </div>
            <div style="font-size:0.78rem;font-weight:{'600' if active else '400'};
                        color:{'#2563a8' if active else '#64748B'};margin-top:0.3rem;">
                {label}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

if st.session_state.step == 1:
    st.markdown("""
    <div class="step-card">
        <div class="step-label">Step 1 of 3 · Sales Team</div>
        <div class="step-title">Group Inquiry Details</div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        group_name = st.text_input("Group / Company Name", placeholder="e.g. Salesforce Annual Retreat")
        arrival_date = st.date_input("Arrival Date", value=date.today() + timedelta(days=7), min_value=date.today())
    with c2:
        contact_name = st.text_input("Sales Contact Name", placeholder="e.g. Jane Smith")
        departure_date = st.date_input(
            "Departure Date (checkout)",
            value=date.today() + timedelta(days=10),
            min_value=date.today() + timedelta(days=1),
        )

    c3, c4 = st.columns(2)
    with c3:
        meal_plan = st.selectbox("Meal Plan Included?", ["No", "Breakfast Only", "Full Board"])
    with c4:
        st.caption("Room requirements are entered by stay date in Step 2.")

    special_notes = st.text_area(
        "Special Notes / Concessions Requested",
        placeholder="e.g. Complimentary suite, meeting room, AV equipment...",
        height=80,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    dates = stay_dates(arrival_date, departure_date)
    if not dates:
        st.error("Departure date must be after arrival date.")
    else:
        st.info(
            f"📅 **{len(dates)} night{'s' if len(dates) > 1 else ''}** | "
            f"Stay dates: **{', '.join(format_date(day) for day in dates)}**"
        )
        if st.button("Continue to Daily Market Data →", type="primary", use_container_width=True):
            if not group_name.strip():
                st.error("Please enter a group name.")
            else:
                st.session_state.sales_data = {
                    "group_name": group_name,
                    "contact_name": contact_name,
                    "arrival_date": arrival_date,
                    "departure_date": departure_date,
                    "nights": len(dates),
                    "stay_dates": dates,
                    "meal_plan": meal_plan,
                    "special_notes": special_notes,
                }
                st.session_state.step = 2
                st.rerun()

elif st.session_state.step == 2:
    sd = st.session_state.sales_data
    dates = sd["stay_dates"]

    st.info(
        f"📋 **{sd['group_name']}** | "
        f"{sd['arrival_date'].strftime('%b %d')} - {sd['departure_date'].strftime('%b %d, %Y')} | "
        f"{len(dates)} stay night{'s' if len(dates) > 1 else ''}"
    )

    yr = date.today().year
    years = [yr - 3, yr - 2, yr - 1]

    st.markdown("""
    <div class="step-card">
        <div class="step-label">Step 2 of 3 · Revenue Manager</div>
        <div class="step-title">Daily Stay-Date Inputs</div>
    """, unsafe_allow_html=True)

    c_rooms, c_mode = st.columns([1, 2])
    with c_rooms:
        total_rooms = st.number_input("Hotel Total Rooms", min_value=1, max_value=5000, value=433, step=1)
    with c_mode:
        forecast_input_method = st.radio(
            "Forecast input method",
            ["Forecasted Occupancy %", "Forecasted Transient Rooms"],
            horizontal=True,
        )

    default_daily_df = pd.DataFrame([
        {
            "Stay Date": day,
            "Group Rooms": 30,
            f"{years[0]} Occupancy %": 72.0,
            f"{years[0]} ADR": 165.0,
            f"{years[1]} Occupancy %": 72.0,
            f"{years[1]} ADR": 170.0,
            f"{years[2]} Occupancy %": 72.0,
            f"{years[2]} ADR": 176.0,
            "Forecasted Occupancy %": 68.0,
            "Forecasted Transient Rooms": round(0.68 * total_rooms),
            "Current ADR on Books": 178.0,
        }
        for day in dates
    ])

    edited_daily_df = st.data_editor(
        default_daily_df,
        hide_index=True,
        use_container_width=True,
        disabled=["Stay Date"],
        column_config={
            "Stay Date": st.column_config.DateColumn("Stay Date", format="MM/DD/YYYY"),
            "Group Rooms": st.column_config.NumberColumn("Group Rooms", min_value=0, step=1),
            "Forecasted Occupancy %": st.column_config.NumberColumn("Forecasted Occupancy %", min_value=0.0, max_value=100.0, step=0.1),
            "Forecasted Transient Rooms": st.column_config.NumberColumn("Forecasted Transient Rooms", min_value=0, step=1),
            "Current ADR on Books": st.column_config.NumberColumn("Current ADR on Books", min_value=0.0, step=1.0),
        },
        key=f"daily_inputs_{sd['arrival_date']}_{sd['departure_date']}_{total_rooms}",
    )

    if forecast_input_method == "Forecasted Occupancy %":
        st.caption("Forecasted transient rooms will be calculated as round(forecasted occupancy % × hotel rooms).")
    else:
        st.caption("Forecasted transient rooms will use the room counts entered in the table.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="step-card">
        <div class="step-label">Market Signals + Manager Inputs</div>
        <div class="step-title">Pace, STR, Growth, and Proposed Rate</div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        str_mpi = st.number_input("MPI - same period, last year (STR)", min_value=0.0, max_value=300.0, value=102.0, step=0.1)
    with c2:
        str_ari = st.number_input("ARI - same period, last year (STR)", min_value=0.0, max_value=300.0, value=98.0, step=0.1)
    with c3:
        str_comp_occ = st.number_input("Comp Set Occupancy % (STR)", min_value=0.0, max_value=100.0, value=70.0, step=0.1)

    c4, c5 = st.columns(2)
    with c4:
        pace_otb = st.number_input("Rooms on Books today (pace)", min_value=0, max_value=50000, value=210, step=1)
    with c5:
        pace_stly = st.number_input("Rooms on Books STLY", min_value=0, max_value=50000, value=195, step=1)

    c6, c7 = st.columns(2)
    with c6:
        proposed_rate = st.number_input("Your Proposed Group Rate ($/night)", min_value=0.0, max_value=5000.0, value=160.0, step=5.0)
    with c7:
        adr_growth_pct = st.slider("Expected ADR Growth % vs Last Year", min_value=-10.0, max_value=20.0, value=4.0, step=0.5)

    st.markdown("</div>", unsafe_allow_html=True)

    col_back, col_next = st.columns([1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col_next:
        if st.button("Evaluate Daily Displacement →", type="primary", use_container_width=True):
            daily_inputs = []
            for _, row in edited_daily_df.iterrows():
                if forecast_input_method == "Forecasted Occupancy %":
                    forecast_rooms = int(round((float(row["Forecasted Occupancy %"]) / 100) * total_rooms))
                else:
                    forecast_rooms = int(round(row["Forecasted Transient Rooms"]))
                daily_inputs.append({
                    "stay_date": row["Stay Date"],
                    "group_rooms": int(round(row["Group Rooms"])),
                    "hist_occ": [
                        float(row[f"{years[0]} Occupancy %"]),
                        float(row[f"{years[1]} Occupancy %"]),
                        float(row[f"{years[2]} Occupancy %"]),
                    ],
                    "hist_adr": [
                        float(row[f"{years[0]} ADR"]),
                        float(row[f"{years[1]} ADR"]),
                        float(row[f"{years[2]} ADR"]),
                    ],
                    "forecast_occ": float(row["Forecasted Occupancy %"]),
                    "forecasted_transient_rooms": forecast_rooms,
                    "curr_adr": float(row["Current ADR on Books"]),
                })

            market_data = {
                "daily_inputs": daily_inputs,
                "years": years,
                "total_rooms": total_rooms,
                "str_mpi": str_mpi,
                "str_ari": str_ari,
                "str_comp_occ": str_comp_occ,
                "pace_otb": pace_otb,
                "pace_stly": pace_stly,
                "adr_growth_pct": adr_growth_pct,
                "proposed_rate": proposed_rate,
                "forecast_input_method": forecast_input_method,
            }
            st.session_state.results = run_pricing_engine(sd, market_data)
            st.session_state.market_data = market_data
            st.session_state.step = 3
            st.rerun()

elif st.session_state.step == 3:
    r = st.session_state.results
    sd = st.session_state.sales_data
    md = st.session_state.market_data

    st.markdown(f"""
    <div class="step-card">
        <div class="step-label">Step 3 of 3 · Daily Rate Analysis</div>
        <div class="step-title">Daily Displacement Evaluation — {sd['group_name']}</div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="result-card result-min">
            <div class="result-label">Proposed Group Rate</div>
            <div class="result-rate">${r['proposed_rate']:,.0f}</div>
            <div class="result-desc">Applied to each group room night.</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="result-card result-rec">
            <div class="result-label">Weighted Transient ADR</div>
            <div class="result-rate">${r['proj_transient_adr']:,.0f}</div>
            <div class="result-desc">Weighted by daily group rooms.</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        net_css = "result-min" if r["net_revenue_position"] >= 0 else "result-str"
        st.markdown(f"""
        <div class="result-card {net_css}">
            <div class="result-label">Net Revenue Position</div>
            <div class="result-rate">${r['net_revenue_position']:,.0f}</div>
            <div class="result-desc">Group revenue minus displaced transient revenue.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### Summary")
    m1, m2, m3, m4, m5 = st.columns(5)
    metrics = [
        ("Total Group Room-Nights", f"{r['total_room_nights']:,}"),
        ("Group Revenue", f"${r['group_rev_proposed']:,.0f}"),
        ("Displaced Room-Nights", f"{r['displaced_room_nights']:,}"),
        ("Displaced Revenue", f"${r['displaced_revenue']:,.0f}"),
        ("Pace vs STLY", f"{r['pace_variance']:+.0f} rooms"),
    ]
    for col, (label, val) in zip([m1, m2, m3, m4, m5], metrics):
        with col:
            st.markdown(f"""
            <div class="metric-strip">
                <div class="m-label">{label}</div>
                <div class="m-value">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    risk = r["displacement_risk"]
    if risk == "HIGH":
        alert_class = "disp-warn"
        title = "High Displacement Risk"
    elif risk == "MEDIUM":
        alert_class = "disp-med"
        title = "Medium Displacement Risk"
    else:
        alert_class = "disp-ok"
        title = "Low Displacement Risk"
    st.markdown(f"""
    <div class="{alert_class}">
        <strong>{title}</strong><br>
        Daily inventory math shows <strong>{r['displaced_room_nights']:,} displaced room-nights</strong>
        worth <strong>${r['displaced_revenue']:,.0f}</strong> in transient revenue opportunity cost.
        Group revenue at the proposed rate is <strong>${r['group_rev_proposed']:,.0f}</strong>.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### Daily Displacement Table")
    st.dataframe(daily_results_df(r), use_container_width=True, hide_index=True)

    st.markdown("#### Revenue Summary")
    st.dataframe(pd.DataFrame({
        "Metric": [
            "Total Group Revenue",
            "Total Displaced Transient Revenue",
            "Net Revenue Position",
            "Proposed Rate vs Weighted Transient ADR",
        ],
        "Value": [
            f"${r['group_rev_proposed']:,.0f}",
            f"-${r['displaced_revenue']:,.0f}",
            f"${r['net_revenue_position']:+,.0f}",
            f"{r['rate_vs_transient_pct']:.1f}% (${r['rate_vs_transient_gap']:+,.0f})",
        ],
    }), use_container_width=True, hide_index=True)

    with st.expander("🧮 See Daily Calculation Logic", expanded=False):
        years = md["years"]
        growth = md["adr_growth_pct"]
        proposed_rate = r["proposed_rate"]

        for idx, row in enumerate(r["daily_results"], start=1):
            hist_adr = row["hist_adr"]
            hist_occ = row["hist_occ"]
            st.markdown(f"""
            <div class="calc-box">
                <div class="calc-step-num">Stay Date {idx}</div>
                <div class="calc-step-title">{format_date(row['stay_date'])}</div>
                <div class="calc-formula">
                    Historical ADR baseline:<br>
                    (${hist_adr[0]:,.2f} + ${hist_adr[1]:,.2f} + ${hist_adr[2]:,.2f}) ÷ 3 = ${row['avg_hist_adr']:,.2f}<br><br>
                    Historical occupancy baseline:<br>
                    ({hist_occ[0]:.1f}% + {hist_occ[1]:.1f}% + {hist_occ[2]:.1f}%) ÷ 3 = {row['avg_hist_occ']:.1f}%<br><br>
                    YoY ADR trend:<br>
                    {years[0]} to {years[1]}: (${hist_adr[1]:,.2f} - ${hist_adr[0]:,.2f}) ÷ ${hist_adr[0]:,.2f} = {row['yoy_1']:+.2f}%<br>
                    {years[1]} to {years[2]}: (${hist_adr[2]:,.2f} - ${hist_adr[1]:,.2f}) ÷ ${hist_adr[1]:,.2f} = {row['yoy_2']:+.2f}%<br>
                    Average YoY trend: ({row['yoy_1']:+.2f}% + {row['yoy_2']:+.2f}%) ÷ 2 = {row['yoy_trend']:+.2f}%<br><br>
                    Projected transient ADR:<br>
                    ${row['avg_hist_adr']:,.2f} × (1 + {row['yoy_trend']:+.2f}% ÷ 100) = ${row['after_yoy_trend_adr']:,.2f}<br>
                    ${row['after_yoy_trend_adr']:,.2f} × (1 + {growth:+.1f}% ÷ 100) = ${row['projected_transient_adr']:,.2f}<br><br>
                    Group revenue:<br>
                    {row['group_rooms']} rooms × ${proposed_rate:,.2f} = ${row['group_revenue']:,.2f}<br><br>
                    Displaced rooms:<br>
                    max(({row['forecasted_transient_rooms']} forecasted transient rooms + {row['group_rooms']} group rooms) - {row['hotel_capacity']} hotel capacity, 0)
                    = {row['displaced_rooms']} rooms<br><br>
                    Displaced revenue:<br>
                    {row['displaced_rooms']} displaced rooms × ${row['projected_transient_adr']:,.2f} = ${row['displaced_revenue']:,.2f}<br><br>
                    Net revenue position:<br>
                    ${row['group_revenue']:,.2f} - ${row['displaced_revenue']:,.2f} = ${row['net_revenue_position']:+,.2f}
                </div>
                <div class="calc-result">
                    {format_date(row['stay_date'])}: demand after group = {row['total_demand_after_group']} rooms,
                    displaced rooms = {row['displaced_rooms']}, net = ${row['net_revenue_position']:+,.0f}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="calc-box">
            <div class="calc-step-num">Totals</div>
            <div class="calc-step-title">Summed Daily Results</div>
            <div class="calc-formula">
                Total group room-nights = {' + '.join(str(row['group_rooms']) for row in r['daily_results'])} = {r['total_room_nights']}<br>
                Total group revenue = {' + '.join(f"${row['group_revenue']:,.0f}" for row in r['daily_results'])} = ${r['group_rev_proposed']:,.0f}<br>
                Total displaced room-nights = {' + '.join(str(row['displaced_rooms']) for row in r['daily_results'])} = {r['displaced_room_nights']}<br>
                Total displaced revenue = {' + '.join(f"${row['displaced_revenue']:,.0f}" for row in r['daily_results'])} = ${r['displaced_revenue']:,.0f}<br>
                Net revenue position = ${r['group_rev_proposed']:,.0f} - ${r['displaced_revenue']:,.0f} = ${r['net_revenue_position']:+,.0f}
            </div>
            <div class="calc-note">Displacement is based only on hotel capacity, forecasted transient rooms, and daily group rooms.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_back, col_new, col_pdf = st.columns(3)
    with col_back:
        if st.button("← Edit Daily Data", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col_new:
        if st.button("🔄 New Group Inquiry", use_container_width=True):
            st.session_state.step = 1
            st.session_state.sales_data = {}
            st.session_state.market_data = {}
            st.session_state.results = None
            st.rerun()
    with col_pdf:
        pdf_bytes = generate_pdf_report(sd, md, r)
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"GroupPricing_{sd['group_name'].replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
