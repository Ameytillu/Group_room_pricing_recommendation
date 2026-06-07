import streamlit as st
from datetime import date, timedelta
import pandas as pd
from utils.pricing_engine import run_pricing_engine
from utils.pdf_export import generate_pdf_report

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Group Pricing Tool",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main { background-color: #F8F9FB; }

    /* Header */
    .app-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #2563a8 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
    }
    .app-header h1 { font-size: 1.8rem; font-weight: 700; margin: 0; color: white; }
    .app-header p  { font-size: 0.9rem; opacity: 0.8; margin: 0.3rem 0 0; color: white; }

    /* Step cards */
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

    /* Result cards */
    .result-card {
        border-radius: 10px;
        padding: 1.4rem;
        text-align: center;
        border: 1px solid transparent;
    }
    .result-min  { background: #F0FDF4; border-color: #86EFAC; }
    .result-rec  { background: #EFF6FF; border-color: #93C5FD; }
    .result-str  { background: #FFF7ED; border-color: #FDB562; }
    .result-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.3rem; }
    .result-rate  { font-size: 2rem; font-weight: 700; margin: 0.2rem 0; }
    .result-desc  { font-size: 0.78rem; color: #64748B; }
    .result-min  .result-label { color: #16A34A; }
    .result-rec  .result-label { color: #2563A8; }
    .result-str  .result-label { color: #C2410C; }
    .result-min  .result-rate  { color: #15803D; }
    .result-rec  .result-rate  { color: #1D4ED8; }
    .result-str  .result-rate  { color: #EA580C; }

    /* Metric strip */
    .metric-strip {
        background: white;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        border: 1px solid #E2E8F0;
        text-align: center;
    }
    .metric-strip .m-label { font-size: 0.72rem; color: #94A3B8; font-weight: 500; text-transform: uppercase; }
    .metric-strip .m-value { font-size: 1.3rem; font-weight: 700; color: #1a3a5c; }

    /* Displacement alert */
    .disp-warn {
        background: #FFF1F2;
        border: 1px solid #FECDD3;
        border-left: 4px solid #E11D48;
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

    /* Divider */
    hr { border: none; border-top: 1px solid #E2E8F0; margin: 1.5rem 0; }

    /* Hide streamlit branding */
    #MainMenu, footer { visibility: hidden; }

    /* Input labels */
    label { font-size: 0.85rem !important; font-weight: 500 !important; color: #374151 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = 1
if "sales_data" not in st.session_state:
    st.session_state.sales_data = {}
if "results" not in st.session_state:
    st.session_state.results = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>🏨 Group Pricing Intelligence Tool</h1>
    <p>Structured group rate recommendations powered by historical data, market signals & displacement logic</p>
</div>
""", unsafe_allow_html=True)

# ── Progress indicator ────────────────────────────────────────────────────────
col_p1, col_p2, col_p3 = st.columns(3)
steps = [
    ("1", "Sales Request", col_p1),
    ("2", "Market Data", col_p2),
    ("3", "Pricing Output", col_p3),
]
for num, label, col in steps:
    active = (st.session_state.step == int(num))
    done   = (st.session_state.step > int(num))
    icon   = "✓" if done else num
    bg     = "#2563a8" if active else ("#16A34A" if done else "#CBD5E1")
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


# ════════════════════════════════════════════════════════════════════════════
# STEP 1 — Sales Request
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.step == 1:
    st.markdown("""
    <div class="step-card">
        <div class="step-label">Step 1 of 3 · Sales Team</div>
        <div class="step-title">Group Inquiry Details</div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        group_name    = st.text_input("Group / Company Name", placeholder="e.g. Salesforce Annual Retreat")
        arrival_date  = st.date_input("Arrival Date", value=date.today() + timedelta(days=7), min_value=date.today())
    with c2:
        contact_name  = st.text_input("Sales Contact Name", placeholder="e.g. Jane Smith")
        departure_date = st.date_input("Departure Date", value=date.today() + timedelta(days=10), min_value=date.today() + timedelta(days=1))

    c3, c4 = st.columns(2)
    with c3:
        room_block    = st.number_input("Room Block (rooms/night)", min_value=1, max_value=433, value=30, step=1)
    with c4:
        meal_plan     = st.selectbox("Meal Plan Included?", ["No", "Breakfast Only", "Full Board"])

    special_notes = st.text_area("Special Notes / Concessions Requested", placeholder="e.g. Complimentary suite, meeting room, AV equipment...", height=80)

    st.markdown("</div>", unsafe_allow_html=True)

    nights = (departure_date - arrival_date).days
    if nights <= 0:
        st.error("Departure date must be after arrival date.")
    else:
        st.info(f"📅  **{nights} night{'s' if nights > 1 else ''}**  |  **{room_block} rooms/night**  |  Total room-nights: **{nights * room_block}**")

        if st.button("Continue to Market Data →", type="primary", use_container_width=True):
            if not group_name.strip():
                st.error("Please enter a group name.")
            else:
                st.session_state.sales_data = {
                    "group_name":    group_name,
                    "contact_name":  contact_name,
                    "arrival_date":  arrival_date,
                    "departure_date": departure_date,
                    "nights":        nights,
                    "room_block":    room_block,
                    "meal_plan":     meal_plan,
                    "special_notes": special_notes,
                }
                st.session_state.step = 2
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# STEP 2 — Manager Market Data
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 2:
    sd = st.session_state.sales_data
    st.info(f"📋  **{sd['group_name']}**  |  {sd['arrival_date'].strftime('%b %d')} – {sd['departure_date'].strftime('%b %d, %Y')}  |  {sd['room_block']} rooms  |  {sd['nights']} nights")

    # ── Historical Data ──────────────────────────────────────────────────
    st.markdown("""
    <div class="step-card">
        <div class="step-label">Step 2 of 3 · Revenue Manager · Historical Performance</div>
        <div class="step-title">Same-Period Data — Prior 3 Years</div>
    """, unsafe_allow_html=True)

    yr = date.today().year
    years = [yr - 3, yr - 2, yr - 1]

    hist_occ, hist_adr = [], []
    cols = st.columns(3)
    for i, year in enumerate(years):
        with cols[i]:
            st.markdown(f"**{year}**")
            occ = st.number_input(f"Occupancy % ({year})", min_value=0.0, max_value=100.0,
                                  value=72.0, step=0.1, key=f"occ_{year}",
                                  help="Same dates, that year")
            adr = st.number_input(f"ADR $ ({year})", min_value=0.0, max_value=2000.0,
                                  value=165.0, step=1.0, key=f"adr_{year}")
            hist_occ.append(occ)
            hist_adr.append(adr)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Current Forecast ─────────────────────────────────────────────────
    st.markdown("""
    <div class="step-card">
        <div class="step-label">Current Forecast (on the books for group dates)</div>
        <div class="step-title">Current Performance Snapshot</div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        curr_occ = st.number_input("Forecasted Occupancy %", min_value=0.0, max_value=100.0,
                                   value=68.0, step=0.1)
    with c2:
        curr_adr = st.number_input("Current ADR on Books ($)", min_value=0.0, max_value=2000.0,
                                   value=178.0, step=1.0)
    with c3:
        total_rooms = st.number_input("Hotel Total Rooms", min_value=1, max_value=5000,
                                      value=433, step=1)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── STR & Pace ───────────────────────────────────────────────────────
    st.markdown("""
    <div class="step-card">
        <div class="step-label">STR Report + Pace Data</div>
        <div class="step-title">Market & Pace Signals</div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        str_mpi = st.number_input("Market Penetration Index (MPI)", min_value=0.0, max_value=300.0,
                                  value=102.0, step=0.1,
                                  help="Your occ / comp set occ × 100. Above 100 = outperforming.")
    with c2:
        str_ari = st.number_input("Average Rate Index (ARI)", min_value=0.0, max_value=300.0,
                                  value=98.0, step=0.1,
                                  help="Your ADR / comp set ADR × 100.")
    with c3:
        str_comp_occ = st.number_input("Comp Set Occupancy % (STR)", min_value=0.0, max_value=100.0,
                                       value=70.0, step=0.1)

    c4, c5 = st.columns(2)
    with c4:
        pace_otb = st.number_input("Rooms on Books (current pace)", min_value=0, max_value=5000,
                                   value=210, step=1,
                                   help="How many rooms sold for these dates right now")
    with c5:
        pace_stly = st.number_input("Rooms on Books STLY (same time last year)", min_value=0,
                                    max_value=5000, value=195, step=1)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Manager Assumptions ──────────────────────────────────────────────
    st.markdown("""
    <div class="step-card">
        <div class="step-label">Manager Assumptions</div>
        <div class="step-title">Rate Growth & Strategy</div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        adr_growth_pct = st.slider("Expected ADR Growth % vs Last Year", min_value=-10.0,
                                   max_value=20.0, value=4.0, step=0.5,
                                   help="Your market judgment on rate trend for these dates")
    with c2:
        strategy = st.selectbox("Revenue Strategy for These Dates",
                                ["Balanced (default)", "Protect Occupancy", "Maximize Rate"],
                                help="Shifts the rate multipliers used in suggestions")

    st.markdown("</div>", unsafe_allow_html=True)

    col_back, col_next = st.columns([1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col_next:
        if st.button("Generate Pricing Recommendations →", type="primary", use_container_width=True):
            market_data = {
                "hist_occ":       hist_occ,
                "hist_adr":       hist_adr,
                "years":          years,
                "curr_occ":       curr_occ,
                "curr_adr":       curr_adr,
                "total_rooms":    total_rooms,
                "str_mpi":        str_mpi,
                "str_ari":        str_ari,
                "str_comp_occ":   str_comp_occ,
                "pace_otb":       pace_otb,
                "pace_stly":      pace_stly,
                "adr_growth_pct": adr_growth_pct,
                "strategy":       strategy,
            }
            st.session_state.results = run_pricing_engine(st.session_state.sales_data, market_data)
            st.session_state.market_data = market_data
            st.session_state.step = 3
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# STEP 3 — Results
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 3:
    r  = st.session_state.results
    sd = st.session_state.sales_data
    md = st.session_state.market_data

    st.markdown(f"""
    <div class="step-card">
        <div class="step-label">Step 3 of 3 · Pricing Output</div>
        <div class="step-title">Group Rate Recommendations — {sd['group_name']}</div>
    """, unsafe_allow_html=True)

    # Rate cards
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="result-card result-min">
            <div class="result-label">🟢 Minimum Acceptable</div>
            <div class="result-rate">${r['rate_min']:,.0f}</div>
            <div class="result-desc">Floor rate — covers variable cost & avoids displacement loss. Use only for low-risk, low-occ dates or strategic accounts.</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="result-card result-rec">
            <div class="result-label">🔵 Recommended Rate</div>
            <div class="result-rate">${r['rate_rec']:,.0f}</div>
            <div class="result-desc">Optimal balance of group competitiveness vs. transient revenue protection. Start negotiations here.</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="result-card result-str">
            <div class="result-label">🔴 Stretch Rate</div>
            <div class="result-rate">${r['rate_stretch']:,.0f}</div>
            <div class="result-desc">Push here when occupancy forecast is strong (>75%). Near transient parity — justified by high displacement risk.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Key metrics strip
    st.markdown("#### Key Metrics")
    m1, m2, m3, m4, m5 = st.columns(5)
    metrics = [
        ("Projected Transient ADR", f"${r['proj_transient_adr']:,.0f}"),
        ("3-Yr Avg Occupancy",      f"{r['avg_hist_occ']:.1f}%"),
        ("3-Yr Avg ADR",            f"${r['avg_hist_adr']:,.0f}"),
        ("Pace vs STLY",            f"{r['pace_variance']:+.0f} rooms"),
        ("Displaced Room-Nights",   f"{r['displaced_room_nights']}"),
    ]
    for col, (label, val) in zip([m1, m2, m3, m4, m5], metrics):
        with col:
            st.markdown(f"""
            <div class="metric-strip">
                <div class="m-label">{label}</div>
                <div class="m-value">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Displacement analysis
    if r["displacement_risk"] == "HIGH":
        st.markdown(f"""
        <div class="disp-warn">
            <strong>⚠️ High Displacement Risk</strong><br>
            Accepting this group at minimum rate would displace an estimated
            <strong>{r['displaced_room_nights']} transient room-nights</strong> worth
            <strong>${r['displaced_revenue']:,.0f}</strong> in transient revenue.
            Group revenue at recommended rate: <strong>${r['group_rev_rec']:,.0f}</strong>.
            {f"<br><strong>Net displacement cost at min rate: ${r['displacement_cost']:,.0f}</strong>" if r['displacement_cost'] > 0 else ""}
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="disp-ok">
            <strong>✅ Low Displacement Risk</strong><br>
            Current occupancy forecast ({md['curr_occ']:.1f}%) leaves sufficient transient capacity.
            Group revenue at recommended rate: <strong>${r['group_rev_rec']:,.0f}</strong>.
        </div>""", unsafe_allow_html=True)

    # Revenue comparison table
    st.markdown("#### Revenue Impact Summary")
    rev_df = pd.DataFrame({
        "Scenario":          ["Minimum Rate", "Recommended Rate", "Stretch Rate"],
        "Rate/Night":        [f"${r['rate_min']:,.0f}", f"${r['rate_rec']:,.0f}", f"${r['rate_stretch']:,.0f}"],
        "Total Group Rev":   [f"${r['group_rev_min']:,.0f}", f"${r['group_rev_rec']:,.0f}", f"${r['group_rev_str']:,.0f}"],
        "vs. Transient Rev": [
            f"${r['group_rev_min'] - r['displaced_revenue']:+,.0f}",
            f"${r['group_rev_rec'] - r['displaced_revenue']:+,.0f}",
            f"${r['group_rev_str'] - r['displaced_revenue']:+,.0f}",
        ]
    })
    st.dataframe(rev_df, use_container_width=True, hide_index=True)

    # ── See Calculations expander ─────────────────────────────────────────
    with st.expander("🧮 See Calculations", expanded=False):
        st.markdown("""
        <style>
        .calc-box {
            background: #F8F9FB;
            border: 1px solid #E2E8F0;
            border-left: 4px solid #2563a8;
            border-radius: 8px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            font-family: 'Inter', sans-serif;
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
        .calc-note {
            font-size: 0.78rem;
            color: #64748B;
            margin-top: 0.4rem;
        }
        .adj-tag {
            display: inline-block;
            background: #DBEAFE;
            color: #1D4ED8;
            border-radius: 4px;
            padding: 1px 7px;
            font-size: 0.75rem;
            font-weight: 600;
            margin: 2px 2px;
        }
        .adj-tag-warn { background: #FEF3C7; color: #B45309; }
        .adj-tag-ok   { background: #DCFCE7; color: #15803D; }
        </style>
        """, unsafe_allow_html=True)

        avg_y1, avg_y2, avg_y3 = md['hist_adr']
        yrs = md['years']
        avg_adr = r['avg_hist_adr']
        yoy = r['yoy_trend']
        growth = md['adr_growth_pct']
        proj = r['proj_transient_adr']

        # ── Step 1: Historical average ────────────────────────────────────
        st.markdown(f"""
        <div class="calc-box">
            <div class="calc-step-num">Step 1 of 5</div>
            <div class="calc-step-title">3-Year Historical ADR Average</div>
            <div class="calc-formula">
                ({yrs[0]} ADR ${avg_y1:,.2f} + {yrs[1]} ADR ${avg_y2:,.2f} + {yrs[2]} ADR ${avg_y3:,.2f}) ÷ 3
            </div>
            <div class="calc-result">= ${avg_adr:,.2f} &nbsp;&nbsp;← Historical ADR Baseline</div>
            <div class="calc-note">Avg occupancy same period: {r['avg_hist_occ']:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Step 2: YoY trend ─────────────────────────────────────────────
        ch1 = ((avg_y2 - avg_y1) / avg_y1 * 100) if avg_y1 else 0
        ch2 = ((avg_y3 - avg_y2) / avg_y2 * 100) if avg_y2 else 0
        st.markdown(f"""
        <div class="calc-box">
            <div class="calc-step-num">Step 2 of 5</div>
            <div class="calc-step-title">Historical Year-over-Year ADR Trend</div>
            <div class="calc-formula">
                {yrs[0]}→{yrs[1]}: (${avg_y2:,.2f} − ${avg_y1:,.2f}) ÷ ${avg_y1:,.2f} = {ch1:+.1f}%<br>
                {yrs[1]}→{yrs[2]}: (${avg_y3:,.2f} − ${avg_y2:,.2f}) ÷ ${avg_y2:,.2f} = {ch2:+.1f}%<br>
                Average trend = ({ch1:+.1f}% + {ch2:+.1f}%) ÷ 2
            </div>
            <div class="calc-result">= {yoy:+.2f}% avg YoY ADR growth</div>
            <div class="calc-note">This is the property's own rate trend — independent of your growth assumption.</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Step 3: Projected transient ADR ──────────────────────────────
        after_trend = avg_adr * (1 + yoy / 100)
        st.markdown(f"""
        <div class="calc-box">
            <div class="calc-step-num">Step 3 of 5</div>
            <div class="calc-step-title">Projected Transient ADR (Rate Anchor)</div>
            <div class="calc-formula">
                ${avg_adr:,.2f} × (1 + {yoy:+.2f}%) = ${after_trend:,.2f} &nbsp;[after historical trend]<br>
                ${after_trend:,.2f} × (1 + {growth:+.1f}%) = ${proj:,.2f} &nbsp;[after manager growth assumption]
            </div>
            <div class="calc-result">= ${proj:,.2f} &nbsp;&nbsp;← All rate tiers are anchored to this</div>
            <div class="calc-note">This is what a transient guest would likely pay on these dates — your group rate is set relative to this.</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Step 4: Multiplier adjustments ───────────────────────────────
        from utils.pricing_engine import (
            _STRATEGY_MULTIPLIERS, _occupancy_multiplier_adjustment,
            _pace_adjustment, _str_adjustment
        )
        base_min, base_rec, base_str = _STRATEGY_MULTIPLIERS[md['strategy']]
        occ_adj  = _occupancy_multiplier_adjustment(md['curr_occ'])
        pace_adj = _pace_adjustment(md['pace_otb'], md['pace_stly'])
        str_adj  = _str_adjustment(md['str_mpi'], md['str_ari'])
        total_adj = occ_adj + pace_adj + str_adj

        def adj_tag(label, val):
            css = "adj-tag-ok" if val > 0 else ("adj-tag-warn" if val < 0 else "adj-tag")
            sign = "+" if val >= 0 else ""
            return f'<span class="adj-tag {css}">{label}: {sign}{val:.3f}</span>'

        st.markdown(f"""
        <div class="calc-box">
            <div class="calc-step-num">Step 4 of 5</div>
            <div class="calc-step-title">Rate Multiplier Adjustments</div>
            <div class="calc-formula">
                Base multipliers ({md['strategy']}): Min {base_min:.0%} | Rec {base_rec:.0%} | Stretch {base_str:.0%}<br><br>
                Adjustments applied:<br>
                &nbsp;&nbsp;Occupancy signal ({md['curr_occ']:.1f}%):  {occ_adj:+.3f}<br>
                &nbsp;&nbsp;Pace vs STLY ({r['pace_variance']:+.0f} rooms):    {pace_adj:+.3f}<br>
                &nbsp;&nbsp;STR MPI/ARI ({md['str_mpi']:.1f} / {md['str_ari']:.1f}):    {str_adj:+.3f}<br>
                &nbsp;&nbsp;────────────────────────────────<br>
                &nbsp;&nbsp;Total adjustment:            {total_adj:+.3f}<br><br>
                Final multipliers: Min {r['mult_min']:.0%} | Rec {r['mult_rec']:.0%} | Stretch {r['mult_str']:.0%}
            </div>
            <div style="margin-top:0.5rem;">
                {adj_tag("Occupancy", occ_adj)}
                {adj_tag("Pace", pace_adj)}
                {adj_tag("STR", str_adj)}
            </div>
            <div class="calc-note" style="margin-top:0.5rem;">Multipliers represent group rate as a % of transient ADR — groups get a discount because they remove OTA commission risk (~15–18%).</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Step 5: Final rates & displacement ───────────────────────────
        total_rooms   = md['total_rooms']
        nights        = sd['nights']
        room_block    = sd['room_block']
        fill_thresh   = round(0.95 * total_rooms) * nights
        otb_rn        = round((md['curr_occ'] / 100) * total_rooms) * nights
        headroom      = max(fill_thresh - otb_rn, 0)
        displaced_rn  = r['displaced_room_nights']

        st.markdown(f"""
        <div class="calc-box">
            <div class="calc-step-num">Step 5 of 5</div>
            <div class="calc-step-title">Final Rates & Displacement Math</div>
            <div class="calc-formula">
                — Rate Calculation —<br>
                Min:     ${proj:,.2f} × {r['mult_min']:.0%} = <b>${r['rate_min']:,.0f}</b><br>
                Rec:     ${proj:,.2f} × {r['mult_rec']:.0%} = <b>${r['rate_rec']:,.0f}</b><br>
                Stretch: ${proj:,.2f} × {r['mult_str']:.0%} = <b>${r['rate_stretch']:,.0f}</b><br>
                (rates rounded to nearest $10)<br><br>
                — Displacement Calculation —<br>
                Fill threshold (95% occ): {round(0.95 * total_rooms)} rooms × {nights} nights = {fill_thresh} room-nights<br>
                Currently on books:       {round((md['curr_occ']/100) * total_rooms)} rooms × {nights} nights = {otb_rn} room-nights<br>
                Headroom remaining:       {fill_thresh} − {otb_rn} = {headroom} room-nights<br>
                Group block:              {room_block} rooms × {nights} nights = {room_block * nights} room-nights<br>
                Displaced room-nights:    max({room_block * nights} − {headroom}, 0) = {displaced_rn}<br>
                Displaced revenue:        {displaced_rn} × ${proj:,.2f} = ${r['displaced_revenue']:,.0f}
            </div>
            <div class="calc-result">
                Group rev @ Rec rate: {room_block * nights} × ${r['rate_rec']:,.0f} = ${r['group_rev_rec']:,.0f}
                &nbsp;&nbsp;|&nbsp;&nbsp;
                Displacement risk: {r['displacement_risk']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_back, col_new, col_pdf = st.columns(3)
    with col_back:
        if st.button("← Edit Market Data", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col_new:
        if st.button("🔄 New Group Inquiry", use_container_width=True):
            st.session_state.step = 1
            st.session_state.sales_data = {}
            st.session_state.results = None
            st.rerun()
    with col_pdf:
        pdf_bytes = generate_pdf_report(sd, md, r)
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"GroupPricing_{sd['group_name'].replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
