import streamlit as st
import pandas as pd
from html import escape

from nutrition_targets import calculate_targets, MIN_MEAL_KCAL, MAX_MEAL_KCAL
from user_profile import create_user_profile, DEFAULT_MAX_DISHES, DEFAULT_HISTORY_DAYS
from meal_recommendation import generate_meal_plan
from history_store import (
    normalize_profile_id,
    list_profiles,
    load_profile_settings,
    save_profile_settings,
    save_meal_plan,
    update_meal_plan,
    get_recent_plans,
    get_recent_meals,
    get_recent_food_names,
    count_plans,
    clear_history,
)
from meal_planner import (
    MEAL_NAMES,
    calculate_daily_summary,
    compare_with_targets,
    coverage_percent,
    get_meal_foods,
    replace_meal_detailed,
)
from food_labels import readable_food_name, food_meaning, portion_basis, household_measure


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="NutriGuide AI",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# HTML HELPER
# =========================================================

def render_html(block):
    cleaned = "\n".join(
        line.strip()
        for line in block.splitlines()
        if line.strip()
    )

    st.markdown(
        cleaned,
        unsafe_allow_html=True
    )


# =========================================================
# PREMIUM THEME
# =========================================================

render_html(
    """
    <style>

    :root {
        --ink: #10241a;
        --muted: #6a7a71;
        --line: #e7e5da;
        --paper: #f5f4ee;
        --card: #ffffff;
        --deep: #0a2419;
        --deep-2: #12402d;
        --emerald: #1f9d6b;
        --mint: #7be0ae;
        --gold: #d4b062;
        --gold-deep: #b98a2c;
    }

    /* ---------- GLOBAL ---------- */

    .stApp,
    .stApp p,
    .stApp label,
    .stApp input,
    .stApp textarea,
    .stApp button,
    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    [data-testid="stMarkdownContainer"] {
        font-family: "Segoe UI", "Inter", Arial, sans-serif;
    }

    .stApp {
        background:
            radial-gradient(
                1000px 500px at 100% -10%,
                rgba(212,176,98,0.10),
                transparent 60%
            ),
            radial-gradient(
                900px 500px at -10% 0%,
                rgba(31,157,107,0.08),
                transparent 55%
            ),
            var(--paper);
        color: var(--ink);
    }

    .block-container {
        max-width: 1400px;
        padding-top: 1.6rem;
        padding-bottom: 3rem;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    #MainMenu,
    footer {
        visibility: hidden;
    }

    /* ---------- SIDEBAR ---------- */

    [data-testid="stSidebar"] {
        background:
            linear-gradient(
                180deg,
                #071a12 0%,
                #0b2419 45%,
                #0f3324 100%
            );
        border-right: 1px solid rgba(212,176,98,0.18);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.2rem;
    }

    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] label p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #d5eadf !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        letter-spacing: 0.2px;
    }

    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: #8fb3a1 !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.10) !important;
    }

    /* ---------- SIDEBAR INPUTS ---------- */

    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] [data-baseweb="base-input"],
    [data-testid="stSidebar"] [data-baseweb="textarea"],
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: #ffffff !important;
        background-color: #ffffff !important;
        border: 1.5px solid #9fc1b0 !important;
        border-radius: 12px !important;
    }

    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea {
        background: transparent !important;
        background-color: transparent !important;
        color: #0b1f15 !important;
        -webkit-text-fill-color: #0b1f15 !important;
        caret-color: #0b1f15 !important;
        font-weight: 600 !important;
        font-size: 15px !important;
    }

    [data-testid="stSidebar"] input::placeholder,
    [data-testid="stSidebar"] textarea::placeholder {
        color: #7d8f85 !important;
        -webkit-text-fill-color: #7d8f85 !important;
        font-weight: 400 !important;
    }

    [data-testid="stSidebar"] [data-baseweb="input"]:focus-within,
    [data-testid="stSidebar"] [data-baseweb="textarea"]:focus-within,
    [data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {
        border-color: var(--gold) !important;
        box-shadow: 0 0 0 2px rgba(212,176,98,0.55) !important;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #10241a !important;
        -webkit-text-fill-color: #10241a !important;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] svg {
        fill: #35584a !important;
    }

    /* ---------- SIDEBAR INPUTS: newer Streamlit wrappers (always light) ---------- */

    [data-testid="stSidebar"] [data-testid="stNumberInputContainer"],
    [data-testid="stSidebar"] [data-testid="stTextInputRootElement"],
    [data-testid="stSidebar"] [data-testid="stTextAreaRootElement"],
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] [data-baseweb="base-input"] > div,
    [data-testid="stSidebar"] [data-baseweb="textarea"] > div {
        background: #ffffff !important;
        background-color: #ffffff !important;
        color: #0b1f15 !important;
    }

    [data-testid="stSidebar"] [data-testid="stNumberInputContainer"],
    [data-testid="stSidebar"] [data-testid="stTextInputRootElement"],
    [data-testid="stSidebar"] [data-testid="stTextAreaRootElement"] {
        border: 1.5px solid #9fc1b0 !important;
        border-radius: 12px !important;
    }

    [data-testid="stSidebar"] [data-testid="stNumberInputContainer"] input,
    [data-testid="stSidebar"] [data-testid="stTextInputRootElement"] input,
    [data-testid="stSidebar"] [data-testid="stTextAreaRootElement"] textarea {
        color: #0b1f15 !important;
        -webkit-text-fill-color: #0b1f15 !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label p,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label p {
        color: #e6f4ec !important;
    }

    /* ---------- MULTISELECT ---------- */

    [data-testid="stSidebar"]
    [data-baseweb="select"]
    [data-baseweb="tag"] {
        background: var(--emerald) !important;
        background-color: var(--emerald) !important;
        border-radius: 8px !important;
    }

    [data-testid="stSidebar"]
    [data-baseweb="select"]
    [data-baseweb="tag"] span,
    [data-testid="stSidebar"]
    [data-baseweb="select"]
    [data-baseweb="tag"] div {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    [data-testid="stSidebar"]
    [data-baseweb="select"]
    [data-baseweb="tag"] svg {
        fill: #ffffff !important;
    }

    /* ---------- NUMBER INPUT ---------- */

    [data-testid="stSidebar"]
    [data-testid="stNumberInput"] button {
        background: #e3ede7 !important;
        border: none !important;
    }

    [data-testid="stSidebar"]
    [data-testid="stNumberInput"] button svg {
        fill: #10241a !important;
    }

    [data-testid="stSidebar"]
    [data-testid="stTooltipIcon"] svg {
        stroke: #8fb3a1 !important;
    }

    /* ---------- DROPDOWN ---------- */

    [data-baseweb="popover"] [data-baseweb="menu"],
    [data-baseweb="popover"] ul {
        background: #ffffff !important;
    }

    [data-baseweb="popover"] li,
    [data-baseweb="popover"] [role="option"],
    [data-baseweb="popover"] li * {
        color: #10241a !important;
        -webkit-text-fill-color: #10241a !important;
    }

    [data-baseweb="popover"] li:hover,
    [data-baseweb="popover"] [aria-selected="true"] {
        background: #e4f3ea !important;
    }

    /* ---------- SIDEBAR BRAND ---------- */

    .side-brand {
        display: flex;
        align-items: center;
        gap: 13px;
        padding: 4px;
    }

    .side-logo {
        width: 48px;
        height: 48px;
        border-radius: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 25px;
        background: linear-gradient(
            135deg,
            #e6c574,
            #b98a2c
        );
        box-shadow:
            0 8px 22px rgba(212,176,98,0.35);
    }

    .side-title {
        font-size: 21px;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.3px;
        line-height: 1.1;
    }

    .side-subtitle {
        font-size: 12px;
        color: #9cc0ad;
        margin-top: 3px;
    }

    .side-heading {
        display: flex;
        align-items: center;
        gap: 9px;
        margin: 22px 0 6px 0;
        font-size: 11.5px;
        font-weight: 800;
        letter-spacing: 1.6px;
        text-transform: uppercase;
        color: var(--gold);
    }

    .side-heading::after {
        content: "";
        flex: 1;
        height: 1px;
        background:
            linear-gradient(
                90deg,
                rgba(212,176,98,0.45),
                transparent
            );
    }

    /* ---------- BUTTON ---------- */

    .stButton > button {
        border-radius: 14px;
        font-weight: 800;
        min-height: 50px;
        border: none;
        background:
            linear-gradient(
                135deg,
                #e6c574 0%,
                #c9992f 100%
            );
        box-shadow:
            0 10px 24px rgba(201,153,47,0.32);
        transition: all 0.18s ease;
    }

    .stButton > button p {
        color: #1d1606 !important;
        font-weight: 800 !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow:
            0 14px 30px rgba(201,153,47,0.45);
        filter: brightness(1.05);
    }

    /* ---------- HERO ---------- */

    .hero {
        position: relative;
        overflow: hidden;
        background:
            radial-gradient(
                600px 300px at 90% 0%,
                rgba(212,176,98,0.28),
                transparent 60%
            ),
            radial-gradient(
                500px 300px at 0% 100%,
                rgba(123,224,174,0.18),
                transparent 60%
            ),
            linear-gradient(
                135deg,
                #071a12 0%,
                #0f3a28 55%,
                #167050 100%
            );
        padding: 42px 46px;
        border-radius: 28px;
        margin-bottom: 30px;
        color: white;
        box-shadow:
            0 24px 50px rgba(8,36,25,0.22);
        border: 1px solid rgba(212,176,98,0.22);
    }

    .hero-badge {
        display: inline-block;
        color: var(--gold);
        border: 1px solid rgba(212,176,98,0.55);
        background: rgba(212,176,98,0.10);
        padding: 7px 15px;
        border-radius: 30px;
        font-size: 11.5px;
        font-weight: 700;
        letter-spacing: 1.6px;
        margin-bottom: 18px;
    }

    .hero-title {
        font-size: 42px;
        font-weight: 800;
        letter-spacing: -1.4px;
        line-height: 1.12;
        margin-bottom: 12px;
        color: #ffffff;
    }

    .hero-title span {
        color: #f0d48a;
    }

    .hero-subtitle {
        font-size: 16px;
        color: #cfe6da;
        max-width: 720px;
        line-height: 1.7;
    }

    .hero-pills {
        margin-top: 24px;
    }

    .hero-pill {
        display: inline-block;
        background: rgba(255,255,255,0.09);
        border: 1px solid rgba(255,255,255,0.16);
        color: #e8f3ec;
        padding: 8px 14px;
        border-radius: 12px;
        font-size: 12.5px;
        font-weight: 600;
        margin: 0 8px 8px 0;
    }

    /* ---------- SECTIONS ---------- */

    .section-title {
        font-size: 23px;
        font-weight: 800;
        color: var(--ink);
        letter-spacing: -0.4px;
        margin-top: 34px;
        margin-bottom: 4px;
    }

    .section-title::after {
        content: "";
        display: block;
        width: 46px;
        height: 3px;
        border-radius: 3px;
        margin-top: 8px;
        background:
            linear-gradient(
                90deg,
                var(--gold),
                transparent
            );
    }

    .section-subtitle {
        color: var(--muted);
        font-size: 14px;
        margin-top: 8px;
        margin-bottom: 16px;
    }

    /* ---------- METRIC CARDS ---------- */

    .metric-card {
        position: relative;
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 20px 22px;
        min-height: 128px;
        box-shadow:
            0 8px 24px rgba(16,36,26,0.05);
        transition: all 0.2s ease;
    }

    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow:
            0 16px 34px rgba(16,36,26,0.10);
    }

    .metric-card::before {
        content: "";
        position: absolute;
        left: 0;
        top: 22px;
        bottom: 22px;
        width: 4px;
        border-radius: 0 4px 4px 0;
        background: var(--accent, #1f9d6b);
    }

    .metric-card.featured {
        background:
            linear-gradient(
                145deg,
                #0a2419,
                #14503a
            );
        border-color: rgba(212,176,98,0.35);
    }

    .metric-card.featured .metric-label {
        color: #a9cdb9;
    }

    .metric-card.featured .metric-value {
        color: #f0d48a;
    }

    .metric-card.featured .metric-small {
        color: #9cc0ad;
    }

    .metric-label {
        font-size: 12px;
        color: var(--muted);
        font-weight: 700;
        letter-spacing: 0.9px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .metric-value {
        font-size: 30px;
        font-weight: 800;
        color: var(--ink);
        letter-spacing: -0.8px;
    }

    .metric-small {
        font-size: 12.5px;
        color: #8a978f;
        margin-top: 6px;
    }

    /* ---------- SUMMARY ---------- */

    .summary-box {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 22px 24px;
        box-shadow:
            0 8px 24px rgba(16,36,26,0.05);
        color: #33463b;
        line-height: 1.7;
    }

    .summary-box h3 {
        margin: 0 0 8px 0;
        color: var(--ink);
    }

    .food-chip {
        display: inline-block;
        background: #eaf6ef;
        color: #17643f;
        border: 1px solid #cfe8d8;
        padding: 7px 14px;
        margin: 8px 8px 0 0;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
    }

    /* ---------- MEAL CARDS ---------- */

    .meal-card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 24px;
        min-height: 320px;
        box-shadow:
            0 10px 30px rgba(16,36,26,0.06);
        transition: all 0.2s ease;
    }

    .meal-card:hover {
        transform: translateY(-3px);
        box-shadow:
            0 18px 40px rgba(16,36,26,0.11);
    }

    .meal-head {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 18px;
    }

    .meal-icon {
        width: 48px;
        height: 48px;
        border-radius: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        background:
            linear-gradient(
                135deg,
                #0f3a28,
                #167050
            );
    }

    .meal-title {
        font-size: 20px;
        font-weight: 800;
        color: var(--ink);
        letter-spacing: -0.3px;
    }

    .meal-subtitle {
        font-size: 12.5px;
        color: var(--muted);
        margin-top: 2px;
    }

    .food-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        background: #f8f8f3;
        border: 1px solid #eeede4;
        border-radius: 14px;
        padding: 12px 14px;
        margin: 9px 0;
    }

    .food-name {
        font-weight: 700;
        color: var(--ink);
        font-size: 14.5px;
    }

    .food-detail {
        font-size: 12px;
        color: #86948b;
        margin-top: 2px;
    }

    .food-quantity {
        white-space: nowrap;
        background:
            linear-gradient(
                135deg,
                #0f3a28,
                #167050
            );
        color: #ffffff;
        font-weight: 800;
        font-size: 13px;
        padding: 6px 12px;
        border-radius: 10px;
    }

    .meal-foot {
        margin-top: 18px;
        padding-top: 16px;
        border-top: 1px dashed #dcdacb;
    }

    .meal-kcal {
        display: flex;
        justify-content: space-between;
        font-size: 13px;
        color: #4d5f54;
        margin-bottom: 8px;
    }

    .meal-kcal b {
        color: var(--ink);
        font-size: 15px;
    }

    .bar {
        height: 7px;
        border-radius: 8px;
        background: #ecebe1;
        overflow: hidden;
    }

    .bar-fill {
        height: 100%;
        border-radius: 8px;
        background:
            linear-gradient(
                90deg,
                #1f9d6b,
                #7be0ae
            );
    }

    .macro-row {
        margin-top: 12px;
    }

    .macro-chip {
        display: inline-block;
        font-size: 11.5px;
        font-weight: 700;
        padding: 5px 10px;
        border-radius: 9px;
        margin: 0 6px 6px 0;
        background: #f1f0e7;
        color: #4d5f54;
    }

    .empty-note {
        color: var(--muted);
        font-size: 14px;
        padding: 20px 0;
    }

    /* ---------- TARGET VS PLANNED ---------- */

    .nut-panel {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 10px 26px;
        box-shadow:
            0 10px 30px rgba(16,36,26,0.06);
    }

    .nut-row {
        padding: 18px 0;
        border-bottom: 1px solid #efeee5;
    }

    .nut-row:last-child {
        border-bottom: none;
    }

    .nut-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .nut-name {
        font-weight: 800;
        color: var(--ink);
        font-size: 15px;
    }

    .nut-values {
        color: #4d5f54;
        font-size: 13.5px;
    }

    .nut-values b {
        color: var(--ink);
    }

    .pill {
        display: inline-block;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.5px;
        padding: 4px 11px;
        border-radius: 20px;
        margin-left: 10px;
    }

    .pill-ok {
        background: #e2f5ea;
        color: #147a4a;
    }

    .pill-low {
        background: #fdf0d5;
        color: #9a6a0a;
    }

    .pill-high {
        background: #e6eefc;
        color: #2c58a6;
    }

    .nut-bar {
        height: 10px;
        border-radius: 10px;
        background: #ecebe1;
        overflow: hidden;
    }

    .nut-fill-ok {
        background:
            linear-gradient(
                90deg,
                #1f9d6b,
                #7be0ae
            );
        height: 100%;
    }

    .nut-fill-low {
        background:
            linear-gradient(
                90deg,
                #d4a02c,
                #f0d48a
            );
        height: 100%;
    }

    .nut-fill-high {
        background:
            linear-gradient(
                90deg,
                #3b6fd0,
                #8fb3f0
            );
        height: 100%;
    }

    .nut-note {
        margin-top: 8px;
        font-size: 12.5px;
        color: #8a6a1d;
    }

    /* ---------- INFO CARDS ---------- */

    .info-card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 22px;
        min-height: 150px;
        box-shadow:
            0 8px 24px rgba(16,36,26,0.05);
        transition: all 0.2s ease;
    }

    .info-card:hover {
        transform: translateY(-3px);
        border-color: rgba(212,176,98,0.6);
    }

    .info-icon {
        width: 42px;
        height: 42px;
        border-radius: 13px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 21px;
        margin-bottom: 14px;
        background:
            linear-gradient(
                135deg,
                #f6ecd0,
                #ecd9a3
            );
    }

    .info-title {
        color: var(--ink);
        font-weight: 800;
        font-size: 15.5px;
        margin-bottom: 7px;
    }

    .info-text {
        color: #63756a;
        font-size: 13.5px;
        line-height: 1.6;
    }

    /* ---------- EXPANDER / ALERTS ---------- */

    [data-testid="stExpander"] {
        border-radius: 18px !important;
        border: 1px solid var(--line) !important;
        background: var(--card);
    }

    [data-testid="stAlert"] {
        border-radius: 16px;
    }

    hr {
        border-color: #e5e3d8 !important;
    }

    </style>
    """
)



# Extra CSS for the new parts (profile dashboard, notes, gap line)
render_html(
    """
    <style>
    .gap-line {
        font-size: 0.86rem;
        margin-top: 6px;
        color: #5b6b63;
    }
    .gap-line b.ok   { color: #1f9d6b; }
    .gap-line b.low  { color: #c2410c; }
    .gap-line b.high { color: #b45309; }
    .mode-pill {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 700;
        margin-right: 8px;
    }
    .mode-on  { background: #e3f4ec; color: #146c4a; }
    .mode-off { background: #f1efe4; color: #6b6a5e; }
    .nt-wrap { overflow-x: auto; margin: 6px 0 14px 0; }
    .nt-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
    .nt-table th { text-align: left; background: #f4f1e6; padding: 8px 10px;
                   border-bottom: 2px solid #e1dccb; white-space: nowrap; }
    .nt-table td { padding: 7px 10px; border-bottom: 1px solid #ece8d9; }
    .nt-table tr:last-child td { font-weight: 600; }
    .split-block { margin: 6px 0 14px 0; }
    .split-title { font-weight: 700; font-size: 0.9rem; margin-bottom: 4px; }
    .split-bar { display: flex; width: 100%; height: 16px; border-radius: 8px;
                 overflow: hidden; background: #e8e4d4; }
    .split-legend { font-size: 0.82rem; margin-top: 4px; color: #4b5b53; }
    .verified-note {
        font-size: 0.78rem;
        color: #6b7a72;
        margin-top: 6px;
    }
    </style>
    """
)


def html_table(frame):
    """Plain HTML table (no pyarrow / Arrow dependency)."""
    if frame is None or len(frame) == 0:
        return ""
    head = "".join(f"<th>{escape(str(col))}</th>" for col in frame.columns)
    body = ""
    for _, row in frame.iterrows():
        cells = "".join(f"<td>{escape(str(value))}</td>" for value in row)
        body += f"<tr>{cells}</tr>"
    return f'<div class="nt-wrap"><table class="nt-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


# =========================================================
# SETTINGS (one dictionary = one profile's saved inputs)
# =========================================================

NEW_PROFILE = "➕ Create new profile"

GENDERS = ["Male", "Female"]
ACTIVITIES = ["Sedentary", "Light", "Moderate", "Active", "Very Active"]
GOALS = ["Maintenance", "Weight Loss", "Weight Gain"]
DIETS = ["No Restriction", "Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"]
ALLERGY_OPTIONS = ["Peanut", "Nuts", "Dairy", "Egg", "Fish", "Shellfish", "Alcohol"]
RESTRICTION_OPTIONS = ["No Nuts", "Nut Free", "Dairy Free", "Egg Free", "Gluten Free"]
HISTORY_CHOICES = [10, 15]
DISH_CHOICES = [1, 2, 3, 4]

CAL_AUTO = "Auto (from my profile)"
CAL_DAILY = "Custom daily calories"
CAL_MEAL = "Custom calories per meal"
CAL_MODES = [CAL_AUTO, CAL_DAILY, CAL_MEAL]

ACTIVITY_MAP = {
    "Sedentary": "sedentary",
    "Light": "light",
    "Moderate": "moderate",
    "Active": "active",
    "Very Active": "very_active",
}
GOAL_MAP = {
    "Maintenance": "maintenance",
    "Weight Loss": "weight_loss",
    "Weight Gain": "weight_gain",
}

DEFAULT_SETTINGS = {
    "age": 21,
    "gender": "Male",
    "height": 170.0,
    "weight": 55.0,
    "activity": "Moderate",
    "goal": "Maintenance",
    "diet": "No Restriction",
    "allergies": [],
    "restrictions": [],
    "likes": "",
    "dislikes": "",
    "available": "",
    "avail_only": True,
    "max_dishes": DEFAULT_MAX_DISHES,
    "history_days": DEFAULT_HISTORY_DAYS,
    "cal_mode": CAL_AUTO,
    "cal_daily": 2000,
    "cal_b": 500,
    "cal_l": 800,
    "cal_d": 700,
}

RESULT_KEYS = [
    "generated", "result", "targets", "bmi", "available_foods",
    "availability_mode", "user_profile", "plan_row_id", "flash",
]


def clean_settings(raw):
    """Merge saved settings with defaults and drop values that are no longer valid."""
    settings = dict(DEFAULT_SETTINGS)
    settings.update(raw or {})

    def pick(key, options):
        if settings[key] not in options:
            settings[key] = DEFAULT_SETTINGS[key]

    pick("gender", GENDERS)
    pick("activity", ACTIVITIES)
    pick("goal", GOALS)
    pick("diet", DIETS)
    pick("max_dishes", DISH_CHOICES)
    pick("history_days", HISTORY_CHOICES)
    pick("cal_mode", CAL_MODES)

    settings["allergies"] = [a for a in settings["allergies"] if a in ALLERGY_OPTIONS]
    settings["restrictions"] = [r for r in settings["restrictions"] if r in RESTRICTION_OPTIONS]

    try:
        settings["age"] = int(min(100, max(10, settings["age"])))
        settings["height"] = float(min(230.0, max(100.0, settings["height"])))
        settings["weight"] = float(min(250.0, max(25.0, settings["weight"])))
        settings["cal_daily"] = int(min(6000, max(800, settings["cal_daily"])))
        for key in ("cal_b", "cal_l", "cal_d"):
            settings[key] = int(min(MAX_MEAL_KCAL, max(MIN_MEAL_KCAL, settings[key])))
    except (TypeError, ValueError):
        return dict(DEFAULT_SETTINGS)

    settings["avail_only"] = bool(settings["avail_only"])
    return settings


def auto_targets(settings):
    return calculate_targets(
        age=settings["age"],
        gender=settings["gender"].lower(),
        weight_kg=settings["weight"],
        height_cm=settings["height"],
        activity_level=ACTIVITY_MAP[settings["activity"]],
        goal=GOAL_MAP[settings["goal"]],
    )


def load_settings_into_widgets(raw):
    """Fill every sidebar widget key from a settings dictionary."""
    settings = clean_settings(raw)

    # fresh profile: start the custom-calorie boxes at the auto values
    if not raw or "cal_l" not in raw:
        meal_kcal = auto_targets(settings)["meal_calories"]
        settings["cal_b"] = int(round(meal_kcal["Breakfast"]))
        settings["cal_l"] = int(round(meal_kcal["Lunch"]))
        settings["cal_d"] = int(round(meal_kcal["Dinner"]))
        settings["cal_daily"] = int(round(auto_targets(settings)["calorie_target"]))

    for key, value in settings.items():
        st.session_state[f"w_{key}"] = value


def parse_items(text):
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def calculate_bmi(weight, height):
    height_m = height / 100
    if height_m <= 0:
        return 0
    return weight / (height_m ** 2)


def bmi_status(bmi):
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal range"
    if bmi < 30:
        return "Overweight"
    return "Obesity range"


# =========================================================
# DISPLAY HELPERS
# =========================================================

NUTRIENT_LABELS = {
    "calories": ("Calories", "kcal"),
    "protein_g": ("Protein", "g"),
    "carbs_g": ("Carbohydrates", "g"),
    "fat_g": ("Fat", "g"),
    "fiber_g": ("Fiber", "g"),
}

STATUS_STYLE = {
    "on target": ("ok", "ON TARGET"),
    "below target": ("low", "BELOW TARGET"),
    "above target": ("high", "ABOVE TARGET"),
}


def render_metric(label, value, subtitle="", accent="#1f9d6b", featured=False):
    css_class = "metric-card featured" if featured else "metric-card"
    render_html(
        f"""
        <div class="{css_class}" style="--accent:{accent};">
            <div class="metric-label">{escape(str(label))}</div>
            <div class="metric-value">{escape(str(value))}</div>
            <div class="metric-small">{escape(str(subtitle))}</div>
        </div>
        """
    )


def render_info_card(icon, title, text):
    render_html(
        f"""
        <div class="info-card">
            <div class="info-icon">{icon}</div>
            <div class="info-title">{title}</div>
            <div class="info-text">{text}</div>
        </div>
        """
    )


def side_heading(text):
    render_html(f'<div class="side-heading">{text}</div>')


def dish_label(item):
    return readable_food_name(
        item.get("food_name"),
        None if item.get("user_food") == item.get("food_name") else item.get("user_food"),
    )


def gap_html(planned, target):
    """Remaining / excess calories, always from the real numbers."""
    difference = planned - target
    if abs(difference) <= 0.03 * target:
        style, text = "ok", f"Within 3% of target ({difference:+.0f} kcal)"
    elif difference < 0:
        style, text = "low", f"{-difference:.0f} kcal remaining to reach the target"
    else:
        style, text = "high", f"{difference:.0f} kcal above the target"
    return f'<div class="gap-line"><b class="{style}">{text}</b></div>'


def meal_card_html(meal_name, icon, entry):
    items = entry.get("foods", []) if isinstance(entry, dict) else []
    target = entry.get("target", {}) if isinstance(entry, dict) else {}
    target_kcal = float(target.get("calories", 0) or 0)

    if items:
        rows = ""
        for item in items:
            name = item.get("food_name") or item.get("user_food")
            meaning = food_meaning(name)
            basis = portion_basis(name)
            extra = f"{escape(meaning)} " if meaning else ""
            measure = household_measure(name, item.get("quantity_g", 0))
            measure_html = f'<div class="food-detail">{escape(measure)} (approx.)</div>' if measure else ""
            rows += f"""
            <div class="food-row">
                <div>
                    <div class="food-name">{escape(dish_label(item))}</div>
                    <div class="food-detail">{item.get('calories', 0):.0f} kcal &bull; protein {item.get('protein_g', 0):.1f} g</div>
                    {measure_html}
                    <div class="food-detail">{extra}(grams = {basis})</div>
                </div>
                <div class="food-quantity">{item.get('quantity_g', 0):.0f} g</div>
            </div>
            """

        planned = sum(i.get("calories", 0) for i in items)
        protein = sum(i.get("protein_g", 0) for i in items)
        carbs = sum(i.get("carbs_g", 0) for i in items)
        fat = sum(i.get("fat_g", 0) for i in items)
        fiber = sum(i.get("fiber_g", 0) for i in items)
        percent = coverage_percent(planned, target_kcal)
        bar_width = max(0.0, min(100.0, percent))

        body = f"""
        {rows}
        <div class="meal-foot">
            <div class="meal-kcal">
                <span><b>{planned:.0f} kcal</b> planned</span>
                <span>{percent:.1f}% of {target_kcal:.0f} kcal target</span>
            </div>
            <div class="bar"><div class="bar-fill" style="width:{bar_width:.0f}%;"></div></div>
            {gap_html(planned, target_kcal)}
            <div class="macro-row">
                <span class="macro-chip">P {protein:.1f} g</span>
                <span class="macro-chip">C {carbs:.1f} g</span>
                <span class="macro-chip">F {fat:.1f} g</span>
                <span class="macro-chip">Fiber {fiber:.1f} g</span>
            </div>
            <div class="verified-note">{len(items)} dish(es) &bull; limit {entry.get('max_dishes', '-')}</div>
        </div>
        """
    else:
        body = '<div class="empty-note">No suitable combination found.</div>'

    return f"""
    <div class="meal-card">
        <div class="meal-head">
            <div class="meal-icon">{icon}</div>
            <div>
                <div class="meal-title">{meal_name}</div>
                <div class="meal-subtitle">Target: {target_kcal:.0f} kcal</div>
            </div>
        </div>
        {body}
    </div>
    """


def nutrient_panel_html(rows):
    if isinstance(rows, dict):
        rows = list(rows.values())

    body = ""
    for row in rows:
        if not isinstance(row, dict):
            continue
        nutrient = row.get("nutrient")
        if nutrient not in NUTRIENT_LABELS:
            continue

        label, unit = NUTRIENT_LABELS[nutrient]
        style, pill_text = STATUS_STYLE.get(row.get("status"), ("ok", "ON TARGET"))
        target = float(row.get("target", 0) or 0)
        planned = float(row.get("planned", 0) or 0)
        difference = float(row.get("difference", 0) or 0)
        coverage = float(row.get("coverage_percent", 0) or 0)
        bar_width = max(0.0, min(100.0, coverage))

        body += f"""
        <div class="nut-row">
            <div class="nut-top">
                <div class="nut-name">{label}
                    <span class="pill pill-{style}">{pill_text}</span>
                </div>
                <div class="nut-values">
                    <b>{planned:.1f}</b> / {target:.1f} {unit}
                    &nbsp;({coverage:.1f}% coverage, {difference:+.1f} {unit})
                </div>
            </div>
            <div class="nut-bar"><div class="nut-fill-{style}" style="width:{bar_width:.0f}%;"></div></div>
        </div>
        """

    return f'<div class="nut-panel">{body}</div>'


def meal_table(meal_plan, targets):
    """Per-meal Target vs Planned table (planned from the foods shown)."""
    rows = []
    totals = {"target": 0.0, "planned": 0.0, "p": 0.0, "c": 0.0, "f": 0.0, "fi": 0.0}

    for meal_name in MEAL_NAMES:
        items = get_meal_foods(meal_plan, meal_name)
        target = meal_plan[meal_name]["target"]["calories"]
        planned = sum(i["calories"] for i in items)
        p = sum(i["protein_g"] for i in items)
        c = sum(i["carbs_g"] for i in items)
        f = sum(i["fat_g"] for i in items)
        fi = sum(i["fiber_g"] for i in items)

        rows.append(_table_row(meal_name, len(items), target, planned, p, c, f, fi))
        for key, value in zip(totals, (target, planned, p, c, f, fi)):
            totals[key] += value

    rows.append(_table_row(
        "Whole day",
        sum(len(get_meal_foods(meal_plan, m)) for m in MEAL_NAMES),
        totals["target"], totals["planned"], totals["p"], totals["c"], totals["f"], totals["fi"],
    ))
    return pd.DataFrame(rows)


def _table_row(name, dishes, target, planned, p, c, f, fi):
    return {
        "Meal": name,
        "Dishes": dishes,
        "Target kcal": f"{target:.0f}",
        "Planned kcal": f"{planned:.0f}",
        "Difference": f"{planned - target:+.0f}",
        "Coverage": f"{coverage_percent(planned, target):.1f}%",
        "Protein g": f"{p:.1f}",
        "Carbs g": f"{c:.1f}",
        "Fat g": f"{f:.1f}",
        "Fiber g": f"{fi:.1f}",
    }


def calorie_split(items_by_meal):
    """% of calories from protein / carbs / fat (4-4-9 rule)."""
    protein = sum(i["protein_g"] for items in items_by_meal for i in items)
    carbs = sum(i["carbs_g"] for items in items_by_meal for i in items)
    fat = sum(i["fat_g"] for items in items_by_meal for i in items)
    parts = {"Protein": protein * 4, "Carbs": carbs * 4, "Fat": fat * 9}
    total = sum(parts.values())
    if total <= 0:
        return {name: 0.0 for name in parts}
    return {name: value / total * 100 for name, value in parts.items()}


def split_bar_html(title, split):
    colors = {"Protein": "#e07a5f", "Carbs": "#d4b062", "Fat": "#3b6fd0"}
    segments = "".join(
        f'<div style="width:{value:.1f}%;background:{colors[name]};height:100%;"></div>'
        for name, value in split.items()
    )
    legend = " &nbsp; ".join(
        f'<span style="color:{colors[name]};font-weight:700;">&#9632;</span> {name} {value:.0f}%'
        for name, value in split.items()
    )
    return (
        f'<div class="split-block"><div class="split-title">{escape(title)}</div>'
        f'<div class="split-bar">{segments}</div><div class="split-legend">{legend}</div></div>'
    )


def plan_csv(meal_plan, targets):
    """Plain CSV of the plan (one row per dish + one per meal total)."""
    rows = []
    for meal_name in MEAL_NAMES:
        entry = meal_plan[meal_name]
        items = get_meal_foods(meal_plan, meal_name)
        for item in items:
            rows.append({
                "Meal": meal_name, "Dish": dish_label(item), "Grams": item["quantity_g"],
                "kcal": round(item["calories"], 1), "Protein g": round(item["protein_g"], 1),
                "Carbs g": round(item["carbs_g"], 1), "Fat g": round(item["fat_g"], 1),
                "Fiber g": round(item["fiber_g"], 1),
            })
        planned = sum(i["calories"] for i in items)
        rows.append({
            "Meal": meal_name, "Dish": f"TOTAL (target {entry['target']['calories']:.0f} kcal, "
                                       f"coverage {coverage_percent(planned, entry['target']['calories']):.1f}%)",
            "Grams": sum(i["quantity_g"] for i in items), "kcal": round(planned, 1),
            "Protein g": round(sum(i["protein_g"] for i in items), 1),
            "Carbs g": round(sum(i["carbs_g"] for i in items), 1),
            "Fat g": round(sum(i["fat_g"] for i in items), 1),
            "Fiber g": round(sum(i["fiber_g"] for i in items), 1),
        })
    return pd.DataFrame(rows).to_csv(index=False)


# =========================================================
# SESSION STATE (initialised once, safely)
# =========================================================

for _key in RESULT_KEYS:
    st.session_state.setdefault(_key, None)
st.session_state.setdefault("generated", False)
st.session_state.setdefault("loaded_profile", None)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    render_html(
        """
        <div class="side-brand">
            <div class="side-logo">🥗</div>
            <div>
                <div class="side-title">NutriGuide AI</div>
                <div class="side-subtitle">Personalized Nutrition Planner</div>
            </div>
        </div>
        """
    )

    # ---------------- PROFILE SELECTOR ----------------
    side_heading("Profile")

    known_profiles = list_profiles()
    profile_names = {pid: name for pid, name in known_profiles}
    profile_options = [NEW_PROFILE] + [pid for pid, _ in known_profiles]

    if st.session_state.get("profile_choice") not in profile_options:
        st.session_state["profile_choice"] = (
            profile_options[1] if len(profile_options) > 1 else NEW_PROFILE
        )

    choice = st.selectbox(
        "Active profile",
        profile_options,
        key="profile_choice",
        format_func=lambda pid: pid if pid == NEW_PROFILE else profile_names.get(pid, pid),
        help="A profile keeps its own settings and meal history on this computer. "
             "It is a local nickname, not a secure login.",
    )

    if choice == NEW_PROFILE:
        new_name = st.text_input(
            "New profile name",
            key="new_profile_name",
            placeholder="for example: rahul",
        ).strip()
        active_profile_id = normalize_profile_id(new_name) if new_name else None
        active_profile_name = new_name or None
    else:
        active_profile_id = choice
        active_profile_name = profile_names.get(choice, choice)

    # Switching profile loads THAT profile's settings and clears the old plan,
    # so histories and plans never mix between profiles.
    if active_profile_id and st.session_state["loaded_profile"] != active_profile_id:
        load_settings_into_widgets(load_profile_settings(active_profile_id))
        for _key in RESULT_KEYS:
            st.session_state[_key] = False if _key == "generated" else None
        st.session_state["loaded_profile"] = active_profile_id

    if active_profile_id is None:
        st.info("Type a profile name to start.")
        for _key, _value in DEFAULT_SETTINGS.items():
            st.session_state.setdefault(f"w_{_key}", _value)

    st.caption(
        f"Active: **{active_profile_name}**" if active_profile_name
        else "No active profile yet."
    )

    # ---------------- PERSONAL DETAILS ----------------
    side_heading("Personal details")

    age = st.number_input("Age", min_value=10, max_value=100, key="w_age")
    gender = st.selectbox("Gender", GENDERS, key="w_gender")
    height = st.number_input("Height (cm)", min_value=100.0, max_value=230.0, step=1.0, key="w_height")
    weight = st.number_input("Weight (kg)", min_value=25.0, max_value=250.0, step=0.5, key="w_weight")

    side_heading("Lifestyle")

    activity = st.selectbox("Activity Level", ACTIVITIES, key="w_activity")
    goal = st.selectbox("Your Goal", GOALS, key="w_goal")

    # ---------------- CALORIE TARGET ----------------
    side_heading("Calorie target")

    current = clean_settings({
        "age": age, "gender": gender, "height": height, "weight": weight,
        "activity": activity, "goal": goal,
    })
    auto = auto_targets(current)

    cal_mode = st.selectbox("How should calories be set?", CAL_MODES, key="w_cal_mode")

    custom_daily = None
    custom_meals = None

    if cal_mode == CAL_DAILY:
        custom_daily = st.number_input(
            "Daily calories (kcal)", min_value=800, max_value=6000, step=50, key="w_cal_daily"
        )
        st.caption("Split 25% Breakfast / 40% Lunch / 35% Dinner.")
    elif cal_mode == CAL_MEAL:
        cal_b = st.number_input("Breakfast (kcal)", min_value=int(MIN_MEAL_KCAL),
                                max_value=int(MAX_MEAL_KCAL), step=10, key="w_cal_b")
        cal_l = st.number_input("Lunch (kcal)", min_value=int(MIN_MEAL_KCAL),
                                max_value=int(MAX_MEAL_KCAL), step=10, key="w_cal_l")
        cal_d = st.number_input("Dinner (kcal)", min_value=int(MIN_MEAL_KCAL),
                                max_value=int(MAX_MEAL_KCAL), step=10, key="w_cal_d")
        custom_meals = {"Breakfast": cal_b, "Lunch": cal_l, "Dinner": cal_d}
        st.caption("The planner searches for foods and gram portions that come as close as possible to each number.")

    st.caption(
        "Auto target for this profile: "
        f"B {auto['meal_calories']['Breakfast']:.0f} / "
        f"L {auto['meal_calories']['Lunch']:.0f} / "
        f"D {auto['meal_calories']['Dinner']:.0f} kcal "
        f"(day {auto['calorie_target']:.0f})."
    )

    # ---------------- DIET & SAFETY ----------------
    side_heading("Diet & safety")

    diet = st.selectbox("Diet Preference", DIETS, key="w_diet")
    allergies = st.multiselect("Allergies", ALLERGY_OPTIONS, key="w_allergies")
    restrictions = st.multiselect("Dietary Restrictions", RESTRICTION_OPTIONS, key="w_restrictions")

    side_heading("Food preferences")

    likes_text = st.text_input("Foods you like", placeholder="chicken, rice, oats", key="w_likes")
    dislikes_text = st.text_input("Foods you dislike", placeholder="spinach, broccoli", key="w_dislikes")

    # ---------------- AVAILABLE FOODS ----------------
    side_heading("Foods you have")

    available_text = st.text_area(
        "Available foods",
        placeholder="rice, dal, paneer, roti",
        height=90,
        key="w_available",
        help="Separate foods with commas. Examples: rice, dal, paneer, roti, chicken, egg, "
             "oats, milk, curd, banana, potato, palak, tofu.",
    )
    avail_only = st.checkbox(
        "Use ONLY these foods (strict mode)",
        key="w_avail_only",
        help="When ON, every meal, replacement and regenerated plan uses only the foods "
             "you typed (if they pass your diet and allergy filters).",
    )

    # ---------------- MEAL SETTINGS ----------------
    side_heading("Meal settings")

    max_dishes = st.selectbox(
        "Maximum dishes per meal",
        DISH_CHOICES,
        key="w_max_dishes",
        help="A dish is one food. A bigger portion of the same food is NOT a new dish.",
    )
    history_days = st.radio(
        "Use recent history of",
        HISTORY_CHOICES,
        format_func=lambda days: f"{days} days",
        horizontal=True,
        key="w_history_days",
    )
    st.caption(
        "History only encourages variety when you press Generate again. "
        "Plans do not change automatically."
    )

    st.write("")

    generate = st.button(
        "✨ Generate My Meal Plan",
        type="primary",
        use_container_width=True,
        disabled=active_profile_id is None,
    )


# =========================================================
# HERO
# =========================================================

render_html(
    """
    <div class="hero">
        <div class="hero-badge">AI-BASED PERSONALIZED NUTRITION</div>
        <div class="hero-title">Your Nutrition, Your Foods,<br><span>Your Plan.</span></div>
        <div class="hero-subtitle">
            Get a daily meal plan whose calories come as close as possible to your target,
            using your health profile, dietary requirements and the foods you have.
        </div>
        <div class="hero-pills">
            <span class="hero-pill">🛡️ Safety-first filtering</span>
            <span class="hero-pill">🧬 USDA FoodData Central</span>
            <span class="hero-pill">🎯 Calorie-target matching</span>
            <span class="hero-pill">👤 Separate profiles</span>
        </div>
    </div>
    """
)


# =========================================================
# GENERATE PLAN
# =========================================================

if generate and active_profile_id:

    allergies_list = [item.lower() for item in allergies]
    restrictions_list = [item.lower() for item in restrictions]
    likes = parse_items(likes_text)
    dislikes = parse_items(dislikes_text)
    typed_foods = parse_items(available_text)

    availability_mode = bool(avail_only and typed_foods)
    available_foods = typed_foods if availability_mode else None

    # Profile first, THEN history: this order is what fixes the old
    # "user_profile is not defined" crash.
    user_profile = create_user_profile(
        age=age,
        gender=gender.lower(),
        height_cm=height,
        weight_kg=weight,
        activity_level=ACTIVITY_MAP[activity],
        goal=GOAL_MAP[goal],
        diet_preference=diet.lower(),
        allergies=allergies_list,
        restrictions=restrictions_list,
        likes=likes,
        dislikes=dislikes,
        profile_id=active_profile_id,
        available_foods=typed_foods,
        available_only=availability_mode,
        max_dishes=max_dishes,
        history_days=history_days,
    )
    user_profile["recent_foods"] = get_recent_food_names(active_profile_id, days=history_days)
    user_profile["recent_meals"] = get_recent_meals(active_profile_id, days=history_days)

    targets = calculate_targets(
        age=age,
        gender=gender.lower(),
        weight_kg=weight,
        height_cm=height,
        activity_level=ACTIVITY_MAP[activity],
        goal=GOAL_MAP[goal],
        custom_daily_calories=custom_daily,
        custom_meal_calories=custom_meals,
    )

    with st.spinner("Searching food combinations and portions..."):
        result = generate_meal_plan(
            user_profile=user_profile,
            targets=targets,
            available_foods=available_foods,
            max_dishes=max_dishes,
        )

    row_id = save_meal_plan(active_profile_id, result.get("meal_plan", {}))

    save_profile_settings(
        active_profile_id,
        {
            "age": age, "gender": gender, "height": height, "weight": weight,
            "activity": activity, "goal": goal, "diet": diet,
            "allergies": allergies, "restrictions": restrictions,
            "likes": likes_text, "dislikes": dislikes_text,
            "available": available_text, "avail_only": avail_only,
            "max_dishes": max_dishes, "history_days": history_days,
            "cal_mode": cal_mode,
            "cal_daily": custom_daily if custom_daily else int(round(auto["calorie_target"])),
            "cal_b": (custom_meals or auto["meal_calories"])["Breakfast"],
            "cal_l": (custom_meals or auto["meal_calories"])["Lunch"],
            "cal_d": (custom_meals or auto["meal_calories"])["Dinner"],
        },
        display_name=active_profile_name,
    )

    st.session_state["profile_id"] = active_profile_id
    st.session_state["user_profile"] = user_profile
    st.session_state["result"] = result
    st.session_state["targets"] = targets
    st.session_state["bmi"] = calculate_bmi(weight, height)
    st.session_state["available_foods"] = available_foods
    st.session_state["availability_mode"] = availability_mode
    st.session_state["plan_row_id"] = row_id
    st.session_state["flash"] = None
    st.session_state["generated"] = True

    if avail_only and not typed_foods:
        st.session_state["flash"] = (
            "info",
            "Strict mode is ON but no foods were typed, so a list of common foods was used.",
        )
    elif typed_foods and not avail_only:
        st.session_state["flash"] = (
            "info",
            "Strict mode is OFF, so your typed foods were NOT used as a limit. "
            "Tick 'Use ONLY these foods' to restrict meals to them.",
        )


# =========================================================
# PROFILE DASHBOARD
# =========================================================

render_html(
    """
    <div class="section-title">👤 Profile Dashboard</div>
    <div class="section-subtitle">
        Each profile has its own settings and its own meal history on this computer.
        Profiles are local nicknames, not a secure login.
    </div>
    """
)

if active_profile_id:
    plans_in_window = get_recent_plans(active_profile_id, days=history_days)

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        render_metric("Active profile", active_profile_name, "Local nickname", accent="#1f9d6b")
    with d2:
        render_metric("Saved plans", count_plans(active_profile_id), "All time", accent="#d4b062")
    with d3:
        render_metric("History period", f"{history_days} days",
                      f"{len(plans_in_window)} plan(s) inside it", accent="#3b6fd0")
    with d4:
        render_metric("Max dishes", max_dishes, "Per meal", accent="#e07a5f")

    with st.expander(f"Recent plans for this profile (last {history_days} days)"):
        if not plans_in_window:
            st.write("No saved plans yet. Generate a plan to start this profile's history.")
        else:
            history_rows = []
            for plan in plans_in_window:
                for meal_name in MEAL_NAMES:
                    items = get_meal_foods(plan["meal_plan"], meal_name)
                    if items:
                        history_rows.append({
                            "Saved at": plan["created_at"].replace("T", " "),
                            "Meal": meal_name,
                            "Foods": ", ".join(readable_food_name(i.get("food_name")) for i in items),
                            "kcal": f"{sum(i.get('calories', 0) for i in items):.0f}",
                        })
            render_html(html_table(pd.DataFrame(history_rows)))

        confirm_clear = st.checkbox("I want to delete the history of THIS profile only", key="confirm_clear")
        if st.button("Clear this profile's history", disabled=not confirm_clear):
            removed = clear_history(active_profile_id)
            st.session_state["confirm_clear"] = False
            st.session_state["flash"] = ("success", f"Deleted {removed} saved plan(s) for this profile.")
            st.rerun()
else:
    st.info("Create or select a profile in the sidebar.")


# =========================================================
# RESULTS
# =========================================================

if st.session_state.get("generated", False) and st.session_state.get("result") is not None:

    result = st.session_state["result"]
    targets = st.session_state["targets"]
    bmi = st.session_state["bmi"]
    entered_foods = st.session_state.get("available_foods")
    availability_mode = st.session_state.get("availability_mode", False)
    user_profile = st.session_state.get("user_profile") or {}
    meal_plan = result["meal_plan"]
    stats = result["stats"]
    pool = result.get("recommendations")
    max_dishes_used = result.get("max_dishes", DEFAULT_MAX_DISHES)

    flash = st.session_state.get("flash")
    if flash:
        kind, message = flash
        getattr(st, kind, st.info)(message)
        st.session_state["flash"] = None

    # ---------------- HEALTH OVERVIEW ----------------
    render_html(
        """
        <div class="section-title">📊 Health Overview</div>
        <div class="section-subtitle">Your calculated health and energy profile</div>
        """
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("BMI", f"{bmi:.1f}", bmi_status(bmi), accent="#1f9d6b")
    with c2:
        render_metric("BMR", f"{targets['bmr']:.0f} kcal", "Basal metabolic rate", accent="#d4b062")
    with c3:
        render_metric("TDEE", f"{targets['tdee']:.0f} kcal", "Estimated daily expenditure", accent="#3b6fd0")
    with c4:
        source = {
            "auto": "Based on your goal",
            "custom_daily": "Your custom daily target",
            "custom_meal": "Sum of your custom meal targets",
        }.get(targets.get("target_source"), "")
        render_metric("Daily Target", f"{targets['calorie_target']:.0f} kcal", source, featured=True)

    # ---------------- NUTRITION TARGETS ----------------
    render_html(
        """
        <div class="section-title">🎯 Your Daily Nutrition Targets</div>
        <div class="section-subtitle">Macronutrient goals calculated for you</div>
        """
    )

    n1, n2, n3, n4 = st.columns(4)
    with n1:
        render_metric("Protein", f"{targets['protein_g']:.0f} g", "Daily target", accent="#e07a5f")
    with n2:
        render_metric("Carbohydrates", f"{targets['carbs_g']:.0f} g", "Daily target", accent="#d4b062")
    with n3:
        render_metric("Fat", f"{targets['fat_g']:.0f} g", "Daily target", accent="#3b6fd0")
    with n4:
        render_metric("Fiber", f"{targets['fiber_g']:.0f} g", "Daily target", accent="#1f9d6b")

    # ---------------- FOOD SOURCE ----------------
    if availability_mode:
        render_html(
            """
            <div class="section-title">🍱 Your Available Foods</div>
            <div class="section-subtitle">Strict mode: meals use only these foods.</div>
            """
        )
        render_html(
            f"""
            <div class="summary-box">
                <span class="mode-pill mode-on">Available-food-only: ON</span>
                <span class="mode-pill mode-off">Max dishes per meal: {max_dishes_used}</span>
                <div>{''.join(f'<span class="food-chip">{escape(food.title())}</span>' for food in (entered_foods or []))}</div>
            </div>
            """
        )
        st.write("")

        if pool is not None and len(pool):
            mapping = pd.DataFrame({
                "You typed": pool["user_food"].astype(str).str.title(),
                "Shown as": [readable_food_name(n) for n in pool["food_name"]],
                "USDA entry used": pool["food_name"],
                "kcal per 100 g": pool["calories"],
            })
            with st.expander("How your foods were matched to USDA entries"):
                render_html(html_table(mapping))
                for note in sorted({n for n in pool.get("match_note", []) if isinstance(n, str) and n}):
                    st.caption("ℹ️ " + note)

        if stats.get("blocked"):
            st.warning(
                "Not used because of your diet / allergy settings: "
                + ", ".join(stats["blocked"])
            )
        if stats.get("not_found"):
            st.warning(
                "Not found in the USDA SR Legacy data (so they cannot be used): "
                + ", ".join(stats["not_found"])
            )
    else:
        render_html(
            """
            <div class="section-title">🌾 Common Foods Used</div>
            <div class="section-subtitle">
                No available-food list is active, so a short list of everyday USDA foods is used.
            </div>
            """
        )
        render_html(
            f"""
            <div class="summary-box">
                <span class="mode-pill mode-off">Available-food-only: OFF</span>
                <span class="mode-pill mode-off">Max dishes per meal: {max_dishes_used}</span>
                <br><b>{stats.get('matched_foods', 0)}</b> everyday foods remained after your
                dietary safety filters. Combinations and portions are searched among them.
            </div>
            """
        )

    # ---------------- MEAL PLAN ----------------
    render_html(
        """
        <div class="section-title">🍽️ Your Personalized Meal Plan</div>
        <div class="section-subtitle">
            Portions are solved so that each meal's calories come as close as possible to its target,
            within realistic gram limits and your dish limit. Gram weights follow the USDA entry
            (cooked weight for cooked foods).
        </div>
        """
    )

    meal_icons = {"Breakfast": "🌅", "Lunch": "☀️", "Dinner": "🌙"}
    plan_has_items = any(get_meal_foods(meal_plan, name) for name in MEAL_NAMES) if meal_plan else False

    if not plan_has_items:
        if availability_mode:
            st.warning(
                "No suitable meal combination was found from the available foods. "
                "Check the messages above, or add more foods."
            )
        else:
            st.warning(
                "No suitable meal combination was found for this profile. "
                "Try adjusting dietary preferences or restrictions."
            )
    else:
        meal_columns = st.columns(3)

        for column, meal_name in zip(meal_columns, MEAL_NAMES):
            with column:
                entry = meal_plan[meal_name]
                render_html(meal_card_html(meal_name, meal_icons[meal_name], entry))

                for note in entry.get("notes", []):
                    st.caption("ℹ️ " + note)

                if st.button(
                    f"🔄 Replace {meal_name}",
                    key=f"replace_{meal_name.lower()}",
                    use_container_width=True,
                ):
                    updated_plan, changed, message = replace_meal_detailed(
                        meal_plan,
                        meal_name,
                        pool,
                        targets,
                        max_dishes=max_dishes_used,
                        user_profile=user_profile,
                    )
                    if changed:
                        result["meal_plan"] = updated_plan
                        result["daily_summary"] = calculate_daily_summary(updated_plan)
                        st.session_state["result"] = result
                        row_id = st.session_state.get("plan_row_id")
                        if not update_meal_plan(row_id, st.session_state.get("profile_id"), updated_plan):
                            st.session_state["plan_row_id"] = save_meal_plan(
                                st.session_state.get("profile_id"), updated_plan
                            )
                        st.session_state["flash"] = ("success", message)
                    else:
                        st.session_state["flash"] = ("info", message)
                    st.rerun()

        # ---------------- TARGET VS PLANNED ----------------
        render_html(
            """
            <div class="section-title">📈 Target vs Planned</div>
            <div class="section-subtitle">
                Planned values are calculated from the foods and gram portions shown above.
                This is a meal-plan estimate, not a record of food actually eaten.
            </div>
            """
        )

        render_html(html_table(meal_table(meal_plan, targets)))

        daily_summary = calculate_daily_summary(meal_plan)
        result["daily_summary"] = daily_summary
        render_html(nutrient_panel_html(compare_with_targets(daily_summary, targets)))

        planned_split = calorie_split([get_meal_foods(meal_plan, m) for m in MEAL_NAMES])
        target_total = targets["protein_g"] * 4 + targets["carbs_g"] * 4 + targets["fat_g"] * 9
        target_split = {
            "Protein": targets["protein_g"] * 4 / target_total * 100,
            "Carbs": targets["carbs_g"] * 4 / target_total * 100,
            "Fat": targets["fat_g"] * 9 / target_total * 100,
        }
        sp1, sp2 = st.columns(2)
        with sp1:
            render_html(split_bar_html("Target calorie split", target_split))
        with sp2:
            render_html(split_bar_html("Planned calorie split", planned_split))

        st.download_button(
            "⬇️ Download this plan (CSV)",
            data=plan_csv(meal_plan, targets),
            file_name="my_meal_plan.csv",
            mime="text/csv",
        )

        if all(meal_plan[m].get("verified", True) for m in MEAL_NAMES):
            st.caption("✔ Every meal was re-calculated from the original USDA CSV and matched.")
        else:
            st.error("A calculation check failed for at least one meal. See the notes under the meal cards.")

    # ---------------- SAFETY ----------------
    render_html(
        """
        <div class="section-title">🛡️ Safety & Personalization</div>
        <div class="section-subtitle">What happens behind your plan</div>
        """
    )

    a, b, c = st.columns(3)
    with a:
        render_info_card(
            "🛡️", "Safety First",
            "Diet, supported allergies and restrictions are applied before any ranking or "
            "meal search. Available-food mode never adds a food you did not list."
        )
    with b:
        render_info_card(
            "🎯", "Whole-Meal Matching",
            "Food combinations and gram portions are evaluated as a complete meal, "
            "so the real calories approach your target."
        )
    with c:
        render_info_card(
            "🔁", "Variety From History",
            "Your recent plans (10 or 15 days) gently discourage repeats when you generate "
            "a new plan. Safety and calorie fit always come first."
        )

    st.write("")

    with st.expander("🔍 How NutriGuide AI creates your plan"):
        st.markdown(
            """
            **1. Health analytics** - age, gender, height, weight and activity give BMI, BMR and TDEE.

            **2. Targets** - daily calories and macros are calculated (or you set calories yourself,
            per day or per meal). Meal targets always add up to the daily target.

            **3. Safety filtering** - diet, allergies and restrictions remove foods first.
            In strict mode only the foods you typed (that survive the filters) are considered.

            **4. Content-based scoring** - foods are scored with cosine similarity to your
            nutrient profile, plus likes, dislikes and recent history. This score is only a
            small tie-breaker.

            **5. Combination search** - every combination of up to *N* dishes is built,
            gram portions are solved (bounded least squares, rounded to practical grams),
            and the **complete meal** is evaluated.

            **6. Ranking** - calorie closeness comes first, then protein / carbs / fat / fibre,
            realistic portions, simple meals and variety.

            **7. Verification** - each chosen meal is re-calculated from the original USDA CSV.

            **8. Replace** - changes only the chosen meal; the other two stay exactly as they are.
            If the foods cannot reach the target within the dish limit and realistic portions,
            the best valid meal is shown together with the reason.
            """
        )

    st.warning(
        "⚠️ Nutrition values and portions are estimates for educational and project "
        "demonstration purposes. USDA SR Legacy does not contain complete allergen data and "
        "the safety filter works from food categories and keywords, so it must not be treated "
        "as medical advice or a guarantee of allergen safety."
    )

    st.caption(
        "NutriGuide AI • USDA FoodData Central SR Legacy • "
        "AI-Based Personalized Nutrition Recommendation System"
    )

else:

    flash = st.session_state.get("flash")
    if flash:
        kind, message = flash
        getattr(st, kind, st.info)(message)
        st.session_state["flash"] = None

    render_html(
        """
        <div class="section-title">🚀 Build Your Personalized Plan</div>
        <div class="section-subtitle">Three simple steps</div>
        """
    )

    render_html(
        """
        <div class="summary-box">
            <h3>How it works</h3>
            Choose or create a profile, enter your details, optionally set your own calorie
            target (for example 876 kcal for lunch) and the foods you have, then generate.
            NutriGuide AI searches for foods and gram portions that come as close as possible
            to each meal's calorie target.
        </div>
        """
    )

    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_info_card("👤", "Your Profile", "Settings and history are kept separately for each profile.")
    with c2:
        render_info_card("🛡️", "Safety", "Diet, allergies and restrictions are applied before ranking.")
    with c3:
        render_info_card("🍱", "Food Choice", "Use only the foods you have, with a maximum number of dishes per meal.")
    with c4:
        render_info_card("🎯", "Calorie Match", "Meals are solved to approach your target calories, honestly reported.")

    st.write("")
    st.info("👈 Fill in your details in the sidebar and click **Generate My Meal Plan**.")
