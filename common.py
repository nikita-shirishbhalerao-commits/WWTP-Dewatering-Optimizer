"""
Shared engine for the Hubgrade WWTP Process Analyzer Suite.
Every process page (Dewatering & Thickening, Coagulant Addition, Disinfection, ...)
imports from this module so the look, feel, and core detection/analysis logic stay
consistent without duplicating code across pages.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fuzzywuzzy import fuzz
import os

# ============================================================
# COLOR PALETTE (Veolia brand colors, from the public 2024 graphic charter)
# ============================================================
VEOLIA = {
    'red': '#FF0000',
    'marine': '#002D62',
    'turquoise': '#05C3DD',
    'sky_blue': '#8DACCD',
    'pale_blue': '#99E1EF',
    'green': '#78BE21',
    'forest_green': '#438D42',
    'apricot': '#FFAC00',
    'orange': '#FF6900',
    'purple': '#772583',
    'yellow': '#FFD616',
    'pale_green': '#C1DB8A',
    'apple_green': '#C7D64F',
    'pale_yellow': '#FFED99',
    'lavender': '#B092BD',
    'white': '#FFFFFF',
    'ink_light': '#5A6B7A',
}


def inject_theme():
    """Injects the shared Veolia-palette CSS. Call once near the top of every page script
    (Streamlit re-runs CSS injection per page in a multi-page app, so this must be called
    on each page, not just once globally)."""
    st.markdown(f"""
    <style>
        .stApp {{
            background-color: #F6F9FA;
        }}
        h1, h2, h3 {{
            color: {VEOLIA['marine']} !important;
            font-weight: 700 !important;
        }}
        h3 {{
            border-bottom: 2px solid {VEOLIA['pale_blue']};
            padding-bottom: 6px;
        }}
        p, div, span, label {{
            color: {VEOLIA['marine']};
        }}

        /* --- Header banner --- */
        .hub-header {{
            background: linear-gradient(90deg, {VEOLIA['marine']} 0%, #003D7A 100%);
            border-radius: 10px;
            padding: 22px 28px;
            margin-bottom: 22px;
            display: flex;
            align-items: center;
            gap: 22px;
            box-shadow: 0 2px 10px rgba(0,45,98,0.25);
        }}
        .hub-wordmark {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding-right: 22px;
            border-right: 1px solid rgba(255,255,255,0.25);
        }}
        .hub-wordmark-dot {{
            width: 14px; height: 14px; border-radius: 50%;
            background: {VEOLIA['turquoise']};
            box-shadow: 0 0 0 4px rgba(5,195,221,0.25);
        }}
        .hub-wordmark-text {{
            font-family: 'Trebuchet MS', 'Segoe UI', sans-serif;
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 2px;
            color: {VEOLIA['white']};
        }}
        .hub-title-text {{
            color: {VEOLIA['white']} !important;
            font-size: 24px;
            font-weight: 700;
            margin: 0 0 4px 0;
            line-height: 1.3;
            font-family: 'Trebuchet MS', 'Segoe UI', sans-serif;
        }}
        .hub-subtitle-text {{
            color: {VEOLIA['pale_blue']} !important;
            margin: 0;
            font-size: 14px;
        }}
        .hub-title-text-light {{
            color: {VEOLIA['marine']} !important;
            font-size: 24px;
            font-weight: 700;
            margin: 0 0 4px 0;
            line-height: 1.3;
            font-family: 'Trebuchet MS', 'Segoe UI', sans-serif;
        }}

        /* --- Metrics (KPI cards) --- */
        [data-testid="stMetric"] {{
            background: {VEOLIA['white']};
            border: 1px solid #E1E9EE;
            border-left: 4px solid {VEOLIA['turquoise']};
            border-radius: 8px;
            padding: 12px 14px 10px 14px;
            box-shadow: 0 1px 3px rgba(0,45,98,0.06);
            min-height: 92px;
        }}
        [data-testid="stMetricLabel"] {{
            color: {VEOLIA['ink_light']} !important;
            font-size: 11.5px !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
            line-height: 1.3 !important;
        }}
        [data-testid="stMetricLabel"] p {{
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
            line-height: 1.3 !important;
        }}
        [data-testid="stMetricValue"] {{
            color: {VEOLIA['marine']} !important;
            font-weight: 700 !important;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
            font-size: 1.5rem !important;
            line-height: 1.25 !important;
        }}

        /* --- Tabs --- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            border-bottom: 2px solid #E1E9EE;
        }}
        .stTabs [data-baseweb="tab"] {{
            color: {VEOLIA['ink_light']};
            font-weight: 600;
            padding: 8px 16px;
        }}
        .stTabs [aria-selected="true"] {{
            color: {VEOLIA['marine']} !important;
            border-bottom: 3px solid {VEOLIA['turquoise']} !important;
        }}

        /* --- Buttons --- */
        .stButton>button, .stDownloadButton>button {{
            background-color: {VEOLIA['marine']} !important;
            border: none !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
        }}
        .stButton>button, .stButton>button *,
        .stDownloadButton>button, .stDownloadButton>button * {{
            color: {VEOLIA['white']} !important;
        }}
        .stButton>button:hover, .stDownloadButton>button:hover,
        .stButton>button:hover *, .stDownloadButton>button:hover * {{
            background-color: {VEOLIA['turquoise']} !important;
            color: {VEOLIA['marine']} !important;
        }}

        /* --- Expanders --- */
        [data-testid="stExpander"] {{
            border: 1px solid #E1E9EE !important;
            border-radius: 8px !important;
            background: {VEOLIA['white']};
        }}

        /* --- Sidebar --- */
        section[data-testid="stSidebar"] {{
            background-color: {VEOLIA['marine']};
        }}
        section[data-testid="stSidebar"] * {{
            color: {VEOLIA['white']} !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stExpander"] {{
            background: rgba(255,255,255,0.06);
            border-color: rgba(255,255,255,0.15) !important;
        }}
        section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] textarea {{
            color: {VEOLIA['marine']} !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stFileUploaderFile"],
        section[data-testid="stSidebar"] [data-testid="stFileUploaderFileName"] {{
            background: rgba(255,255,255,0.14) !important;
            border-radius: 6px;
            padding: 4px 8px;
        }}
        section[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] * {{
            color: {VEOLIA['white']} !important;
            overflow: visible !important;
            text-overflow: unset !important;
            white-space: normal !important;
            word-break: break-word !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] svg {{
            fill: {VEOLIA['white']} !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
            background: {VEOLIA['white']} !important;
            border: 2px dashed rgba(255,255,255,0.4);
            border-radius: 8px;
        }}
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{
            color: {VEOLIA['marine']} !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {{
            background: {VEOLIA['turquoise']} !important;
            color: {VEOLIA['marine']} !important;
            border: none !important;
            font-weight: 600 !important;
        }}

        /* --- Dataframes --- */
        [data-testid="stDataFrame"] {{
            border: 1px solid #E1E9EE;
            border-radius: 6px;
        }}

        /* --- Dividers --- */
        hr {{
            border-top: 1px solid #E1E9EE !important;
        }}

        /* --- Status chips --- */
        .status-chip {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12.5px;
            font-weight: 700;
        }}
    </style>
    """, unsafe_allow_html=True)


def render_header(subtitle, logo_filename="hubgrade_logo.png"):
    """Renders the Hubgrade banner + page title. `subtitle` should be the process module's
    own title, e.g. 'Coagulant Addition Performance Analyzer'."""
    this_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else '.'
    logo_path = os.path.join(this_dir, logo_filename)

    with st.container():
        if os.path.exists(logo_path):
            hcol1, hcol2 = st.columns([1, 5])
            with hcol1:
                st.image(logo_path, width=140)
            with hcol2:
                st.markdown(f"""
                <div style="padding-top:8px;">
                    <div class="hub-title-text-light">{subtitle}</div>
                    <p style="color:{VEOLIA['ink_light']}; margin:0;">Fuzzy Parameter Detection | Confirm-Before-You-Analyze | Period A/B Benchmark | AI Recommendations</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="hub-header">
                <div class="hub-wordmark">
                    <div class="hub-wordmark-dot"></div>
                    <div class="hub-wordmark-text">HUBGRADE</div>
                </div>
                <div>
                    <div class="hub-title-text">{subtitle}</div>
                    <div class="hub-subtitle-text">Fuzzy Parameter Detection · Confirm-Before-You-Analyze · Period A/B Benchmark · AI Recommendations</div>
                </div>
            </div>
            """, unsafe_allow_html=True)


def status_chip(status_text):
    """Render a KPI/recommendation status string as a colored chip matching the Veolia palette,
    without changing the underlying text that calling code string-matches on."""
    if not status_text:
        return ""
    if 'On Target' in status_text or '✅' in status_text:
        bg, fg = '#EAF4DD', VEOLIA['forest_green']
    elif 'Below Target' in status_text or '🔴' in status_text:
        bg, fg = '#FFE3E3', VEOLIA['red']
    elif 'Above Target' in status_text or '🟠' in status_text:
        bg, fg = '#FFEFD9', VEOLIA['orange']
    elif 'Informational' in status_text or 'ℹ️' in status_text:
        bg, fg = '#E7F2F8', VEOLIA['marine']
    else:
        bg, fg = '#EEF3F6', VEOLIA['ink_light']
    label = status_text.replace('✅', '').replace('🔴', '').replace('🟠', '').replace('ℹ️', '').strip()
    return f'<span class="status-chip" style="background:{bg}; color:{fg};">{label}</span>'


def priority_chip(priority_text):
    """Render a recommendation priority (CRITICAL/HIGH/MEDIUM/OPTIMAL) as a colored chip."""
    if 'CRITICAL' in priority_text:
        bg, fg = '#FFE3E3', VEOLIA['red']
    elif 'HIGH' in priority_text:
        bg, fg = '#FFEFD9', VEOLIA['orange']
    elif 'MEDIUM' in priority_text:
        bg, fg = '#FFF7DB', '#9A7B00'
    elif 'OPTIMAL' in priority_text:
        bg, fg = '#EAF4DD', VEOLIA['forest_green']
    else:
        bg, fg = '#EEF3F6', VEOLIA['ink_light']
    label = priority_text.replace('🔴', '').replace('🟠', '').replace('🟡', '').replace('✅', '').strip()
    return f'<span class="status-chip" style="background:{bg}; color:{fg};">{label}</span>'


# ============================================================
# THRESHOLD FOOTNOTES
# ============================================================
def format_threshold_footnote(thresholds_dict, metric_key, unit=""):
    if metric_key not in thresholds_dict:
        return None
    thresholds = thresholds_dict[metric_key]
    order = ['excellent', 'good', 'moderate', 'poor']
    icons = {'excellent': '🟢', 'good': '🟡', 'moderate': '🟠', 'poor': '🔴'}
    parts = []
    for level in order:
        lo, hi = thresholds[level]
        if lo == 0:
            text = f"<{hi:g}{unit}"
        elif hi == float('inf'):
            text = f"≥{lo:g}{unit}"
        else:
            text = f"{lo:g}–{hi:g}{unit}"
        parts.append(f"{icons[level]} **{level.title()}**: {text}")
    return " &nbsp;|&nbsp; ".join(parts)


def render_footnote(thresholds_dict, metric_key, unit="", fallback=None):
    txt = format_threshold_footnote(thresholds_dict, metric_key, unit)
    if txt:
        st.caption(f"📊 Performance benchmark — {txt}")
    elif fallback:
        st.caption(fallback)


# ============================================================
# PLOTLY CHART DOWNLOAD HELPER
# ============================================================
PLOTLY_CONFIG = {
    'displaylogo': False,
    'toImageButtonOptions': {'format': 'png', 'scale': 2, 'filename': 'chart'},
    'modeBarButtonsToAdd': ['toImage'],
}


def render_chart_with_download(fig, key):
    """Render a Plotly chart, plus an explicit download button under its bottom-right corner.
    Tries a PNG export first (needs 'kaleido'; kaleido>=1.0 also needs a separately-installed
    Chrome browser - pin kaleido==0.2.1 in requirements.txt to avoid that). Falls back to an
    interactive HTML download instead of breaking the app, and shows the real error so the
    cause is diagnosable."""
    st.plotly_chart(fig, use_container_width=True, key=key, config=PLOTLY_CONFIG)
    spacer, dl_col = st.columns([6, 1])
    with dl_col:
        try:
            img_bytes = fig.to_image(format="png", scale=2)
            st.download_button("⬇️ Download Chart", data=img_bytes, file_name=f"{key}.png", mime="image/png",
                                key=f"dl_{key}", use_container_width=True, help="Download this chart as a PNG image.")
        except Exception as e:
            html_bytes = fig.to_html(full_html=True, include_plotlyjs='cdn').encode('utf-8')
            st.download_button("⬇️ Download Chart", data=html_bytes, file_name=f"{key}.html", mime="text/html",
                                key=f"dl_{key}", use_container_width=True,
                                help=f"PNG export failed, downloading an interactive HTML chart instead. Reason: {e}")
            with st.expander("Why HTML instead of PNG?", expanded=False):
                st.caption(f"PNG export error: `{e}`")
                st.caption("Most common cause: kaleido>=1.0 dropped its bundled Chromium and now needs a separate "
                           "browser install. Fix: pin `kaleido==0.2.1` in requirements.txt (last version with a "
                           "bundled headless browser, no extra install step needed) and redeploy/reboot the app.")


# ============================================================
# FUZZY PARAMETER DETECTOR (generic - works for any process's keyword system)
# ============================================================
class FuzzyParameterDetector:
    """Detects process parameters in uploaded column headers using fuzzy matching, with hard
    require/exclude token gates (checked before fuzzy scoring) and a unit-family penalty."""

    def __init__(self, columns):
        self.columns = list(columns)
        self.clean_columns = [self._clean(c) for c in self.columns]
        self.detected_params = {}

    @staticmethod
    def _clean(s):
        s = str(s).lower()
        for ch in ['_', '-', '/', '(', ')', '%', '#']:
            s = s.replace(ch, ' ')
        return ' '.join(s.split())

    def find_parameters(self, keyword_groups, threshold=55, expected_units=None, required_token_groups=None, exclude_tokens=None):
        expected_units = expected_units or {}
        required_token_groups = required_token_groups or {}
        exclude_tokens = exclude_tokens or {}
        results = {}
        for param_name, keywords in keyword_groups.items():
            allowed_units = expected_units.get(param_name)
            req_groups = [[self._clean(t) for t in group] for group in required_token_groups.get(param_name, [])]
            excl_tokens = [self._clean(t) for t in exclude_tokens.get(param_name, [])]
            kw_cleans = [self._clean(kw) for kw in keywords]
            best_col, best_score = None, 0
            for col, col_clean in zip(self.columns, self.clean_columns):
                padded_col = f' {col_clean} '

                def _token_hits(token):
                    if ' ' not in token and len(token) <= 3:
                        return f' {token} ' in padded_col
                    return token in col_clean

                if req_groups and not all(any(_token_hits(t) for t in group) for group in req_groups):
                    continue
                if excl_tokens and any(_token_hits(t) for t in excl_tokens):
                    continue

                col_best, best_kw_len = 0, 1
                for kw, kw_clean in zip(keywords, kw_cleans):
                    score = max(
                        fuzz.token_set_ratio(kw_clean, col_clean),
                        fuzz.partial_ratio(kw_clean, col_clean),
                    )
                    if score > col_best:
                        col_best = score
                        best_kw_len = max(1, len(kw_clean.split()))

                col_len = max(1, len(col_clean.split()))
                coverage = min(1.0, (best_kw_len + 1) / col_len)
                adjusted = col_best * coverage

                if allowed_units:
                    if self._detect_unit(col) not in allowed_units:
                        adjusted = adjusted * 0.55

                if adjusted > best_score:
                    best_score = adjusted
                    best_col = col
            if best_col and best_score >= threshold:
                results[param_name] = {'column': best_col, 'score': round(best_score), 'unit': self._detect_unit(best_col)}
            else:
                results[param_name] = {'column': None, 'score': round(best_score), 'unit': 'Unknown'}
        self.detected_params = results
        return results

    @staticmethod
    def _detect_unit(column_name):
        col_lower = column_name.lower()
        words = col_lower.replace('/', ' ').replace('-', ' ').split()
        if any(x in col_lower for x in ['ntu']):
            return 'NTU'
        if 'ph' in words:
            return 'pH'
        if 'kwh' in col_lower:
            return 'kWh'
        if 'temp' in col_lower or 'temperature' in col_lower:
            return 'Temp'
        # "lbs/MG" or "gal/MG" (dose per million gallons treated) vs "mg/L" (milligrams per liter,
        # a concentration) look confusingly similar once lowercased ("mg" vs "MG" collide) - the
        # reliable signal is which side of the slash "mg" falls on: numerator = milligrams (mg/L),
        # denominator with lbs/gal before it = million gallons (lbs/MG, gal/MG).
        if any(p in col_lower for p in ['lbs/mg', 'lb/mg', 'lbs per mg']):
            return 'lbs/MG'
        if any(p in col_lower for p in ['gal/mg', 'gallons/mg', 'gal per mg']):
            return 'gal/MG'
        ratio_markers = ['lbs/ton', 'lb/ton', 'lbs per ton', 'lb per ton', '/ton', '/dt', 'per ton', 'per dt']
        if any(m in col_lower for m in ratio_markers):
            return 'lbs/ton'
        if 'gpd' in col_lower and ('poly' in col_lower or 'coag' in col_lower or 'chem' in col_lower):
            return 'GPD'
        if any(x in col_lower for x in ['%', 'percent', 'solids', 'cake', 'ts', 'tss', 'moisture']):
            return '%'
        if 'scfm' in col_lower:
            return 'SCFM'
        if any(x in col_lower for x in ['flow', 'gpm', 'mgd', 'gpd', 'rate']):
            if 'mgd' in col_lower:
                return 'MGD'
            if 'gpm' in col_lower:
                return 'GPM'
            if 'gpd' in col_lower:
                return 'GPD'
            return 'MGD'
        if any(x in col_lower for x in ['ton', 'dry', 'wet', 'weight', 'mass']):
            if 'dry' in col_lower:
                return 'Dry Tons'
            if 'wet' in col_lower:
                return 'Wet Tons'
            return 'Tons'
        if any(x in col_lower for x in ['truck', 'count', 'number', 'qty']):
            return 'Count'
        if any(x in col_lower for x in ['hour', 'runtime', 'time', 'hrs']):
            return 'Hours'
        if 'mg/l' in col_lower or 'ppm' in col_lower:
            return 'mg/L'
        if any(x in col_lower for x in ['concentration', 'conc']):
            return 'mg/L'
        if any(x in col_lower for x in ['rpm', 'speed', 'bowl']):
            return 'RPM'
        if any(x in col_lower for x in ['torque', 'nm', 'ft-lb']):
            return 'Nm'
        if any(x in col_lower for x in ['cost', 'price', '$', 'dollar']):
            return '$'
        if any(x in col_lower for x in ['pressure', 'psi', 'bar']):
            return 'PSI'
        if 'log' in col_lower:
            return 'log'
        if 'cfu' in col_lower or 'mpn' in col_lower:
            return 'CFU or MPN/100mL'
        return 'Unknown'


# ============================================================
# CSV LOADING (generic)
# ============================================================
def load_process_csv(uploaded_file):
    """Read a CSV, detect/parse a date column (or synthesize one).
    Returns (df, date_col, used_synthetic_dates) - always check the third value and surface it
    to the user (see render_date_column_selector) rather than silently trusting the date range,
    since a failed date-parse produces a fake sequential calendar that looks plausible at a glance
    but will scramble any year-based filtering or trend analysis downstream."""
    df = pd.read_csv(uploaded_file)
    df = df.reset_index(drop=True)
    date_col = None
    best_frac = 0
    best_converted = None
    for col in df.columns:
        if any(x in col.lower() for x in ['date', 'time', 'day', 'month', 'year']):
            try:
                converted = pd.to_datetime(df[col], errors='coerce')
            except Exception:
                continue
            valid_frac = converted.notna().sum() / max(len(df), 1)
            if valid_frac > 0.5 and valid_frac > best_frac:
                best_frac = valid_frac
                date_col = col
                best_converted = converted
    if date_col:
        df[date_col] = best_converted
        df = df.sort_values(date_col).reset_index(drop=True)
        return df, date_col, False
    else:
        df['Date'] = pd.date_range(start='2023-01-01', periods=len(df), freq='D')
        return df, 'Date', True


def render_date_column_selector(df, date_col, used_synthetic, key_prefix):
    """Shows the detected date column/range plainly, warns loudly if synthetic dates were used,
    and always lets the user manually pick the real date column instead - auto-detection can't
    cover every naming convention (e.g. 'Month Year' style columns, non-English headers, etc).
    Returns the (possibly corrected) df and date_col."""
    if used_synthetic:
        st.warning(
            "⚠️ **No date column could be confidently auto-detected** — using a placeholder sequential "
            "daily calendar starting 2023-01-01. Year filtering and trend analysis will be meaningless "
            "until you pick your real date column below."
        )
    else:
        st.caption(f"📅 Date column detected: **{date_col}** ({df[date_col].min().date()} to {df[date_col].max().date()})")

    all_cols = list(df.columns)
    options = ["Keep as detected"] + [c for c in all_cols if c != date_col]
    choice = st.selectbox(
        "Not right? Pick your actual date column",
        options, index=0, key=f"{key_prefix}_date_col_override",
        help="Select the column that actually contains your date/period (e.g. 'Month Year', 'Date', 'Period')."
    )
    if choice != "Keep as detected":
        converted = pd.to_datetime(df[choice], errors='coerce')
        valid_frac = converted.notna().sum() / max(len(df), 1)
        if valid_frac < 0.5:
            st.error(f"'{choice}' couldn't be parsed as dates for most rows ({valid_frac:.0%} valid) - keeping the previous date column.")
            return df, date_col
        new_df = df.copy()
        if used_synthetic and date_col in new_df.columns:
            new_df = new_df.drop(columns=[date_col])
        new_df[choice] = converted
        new_df = new_df.sort_values(choice).reset_index(drop=True)
        st.success(f"✅ Using **{choice}** as the date column ({new_df[choice].min().date()} to {new_df[choice].max().date()}, {new_df[choice].notna().sum()}/{len(new_df)} rows parsed).")
        return new_df, choice
    return df, date_col


def detect_parameters(df, keyword_dict, expected_units, required_token_groups, exclude_tokens, threshold=55, exclude_columns=None):
    """exclude_columns should always include your date column - otherwise the date column can get
    fuzzy-matched as an unrelated parameter (e.g. 'Contact Time'), and any numeric calculation on it
    produces a nonsense astronomical number (a date's nanoseconds-since-1970 representation)."""
    exclude_columns = set(exclude_columns or [])
    candidate_cols = [c for c in df.columns if c not in exclude_columns]
    detector = FuzzyParameterDetector(candidate_cols)
    return detector.find_parameters(keyword_dict, threshold=threshold, expected_units=expected_units,
                                     required_token_groups=required_token_groups, exclude_tokens=exclude_tokens)


def render_mapping_editor(detected_params, df_columns, key_prefix, categorize_fn):
    """Interactive, editable table so the user can confirm or correct every fuzzy-matched column
    before it's used anywhere else. `categorize_fn` groups parameter keys for display (e.g. by
    sub-process) - pass any callable(key) -> str."""
    all_columns = ["— None detected —"] + list(df_columns)
    rows = []
    for key, info in sorted(detected_params.items(), key=lambda kv: (categorize_fn(kv[0]), kv[0])):
        rows.append({
            'Category': categorize_fn(key),
            'Parameter': key,
            'Column Used': info['column'] if info['column'] else "— None detected —",
            'Match %': int(info['score']),
            'Unit': info['unit'],
        })
    mapping_df = pd.DataFrame(rows)

    edited = st.data_editor(
        mapping_df,
        column_config={
            'Category': st.column_config.TextColumn(disabled=True),
            'Parameter': st.column_config.TextColumn(disabled=True),
            'Column Used': st.column_config.SelectboxColumn(options=all_columns, required=True, width="large"),
            'Match %': st.column_config.NumberColumn(disabled=True, format="%d%%"),
            'Unit': st.column_config.TextColumn(disabled=False, help="Edit this if the auto-detected unit is wrong."),
        },
        hide_index=True,
        use_container_width=True,
        key=f"{key_prefix}_mapping_editor",
    )

    updated = {}
    for _, row in edited.iterrows():
        key = row['Parameter']
        col = row['Column Used']
        unit_override = str(row['Unit']).strip() if pd.notna(row['Unit']) and str(row['Unit']).strip() else None
        if col == "— None detected —" or pd.isna(col):
            updated[key] = {'column': None, 'score': 0, 'unit': 'Unknown'}
        else:
            updated[key] = {'column': col, 'score': row['Match %'], 'unit': unit_override or FuzzyParameterDetector._detect_unit(col)}
    return updated


# ============================================================
# CORRELATION ANALYZER (generic)
# ============================================================
class CorrelationAnalyzer:
    def __init__(self, df, detected_params):
        self.df = df
        self.detected_params = detected_params

    def get_numeric_data(self):
        numeric_data = {}
        for param_info in self.detected_params.values():
            if param_info['column']:
                col_data = pd.to_numeric(self.df[param_info['column']], errors='coerce')
                if col_data.dropna().shape[0] > 0:
                    numeric_data[param_info['column']] = col_data
        return pd.DataFrame(numeric_data)

    def calculate_correlations(self):
        df_numeric = self.get_numeric_data()
        if len(df_numeric.columns) < 2:
            return None
        return df_numeric.corr()

    def find_strong_correlations(self, threshold=0.7):
        corr_matrix = self.calculate_correlations()
        if corr_matrix is None:
            return []
        strong = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                val = corr_matrix.iloc[i, j]
                if pd.notna(val) and abs(val) >= threshold:
                    strong.append({
                        'Variable 1': corr_matrix.columns[i],
                        'Variable 2': corr_matrix.columns[j],
                        'Correlation': val,
                        'Strength': 'Strong Positive' if val > 0 else 'Strong Negative',
                        'Interpretation': self._interpret(corr_matrix.columns[i], corr_matrix.columns[j], val),
                    })
        return sorted(strong, key=lambda x: abs(x['Correlation']), reverse=True)

    @staticmethod
    def _interpret(var1, var2, corr_val):
        if corr_val > 0.7:
            return "Strong positive relationship - variables move together"
        if corr_val < -0.7:
            return "Strong negative relationship - variables move in opposite directions"
        return "Moderate relationship - investigate further"

    def create_correlation_heatmap(self):
        corr_matrix = self.calculate_correlations()
        if corr_matrix is None:
            return None
        veolia_diverging = [
            [0.0, VEOLIA['red']], [0.25, '#FFB3B3'], [0.5, '#FFFFFF'],
            [0.75, VEOLIA['sky_blue']], [1.0, VEOLIA['marine']],
        ]
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values, x=corr_matrix.columns, y=corr_matrix.columns,
            colorscale=veolia_diverging, zmid=0, zmin=-1, zmax=1, text=np.round(corr_matrix.values, 2),
            texttemplate='%{text:.2f}', textfont={"size": 10, "color": VEOLIA['marine']}, colorbar=dict(title="Correlation"),
        ))
        fig.update_layout(
            title=dict(text="Correlation Matrix - Confirmed Parameters", font=dict(color=VEOLIA['marine'])),
            height=600, xaxis_title="Parameters", yaxis_title="Parameters",
            plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF', font=dict(color=VEOLIA['marine']),
        )
        return fig

    def create_scatter_plot(self, var1_col, var2_col):
        var1_data = pd.to_numeric(self.df[var1_col], errors='coerce').dropna()
        var2_data = pd.to_numeric(self.df[var2_col], errors='coerce')
        var2_data = var2_data[var1_data.index]
        corr = var1_data.corr(var2_data)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=var1_data, y=var2_data, mode='markers', marker=dict(size=8, color=VEOLIA['turquoise'], opacity=0.7), name='Data Points'))
        if len(var1_data) > 1:
            z = np.polyfit(var1_data, var2_data, 1)
            p = np.poly1d(z)
            x_trend = np.linspace(var1_data.min(), var1_data.max(), 100)
            fig.add_trace(go.Scatter(x=x_trend, y=p(x_trend), mode='lines', name='Trend Line', line=dict(color=VEOLIA['apricot'], width=2)))
        fig.update_layout(
            title=dict(text=f"{var1_col} vs {var2_col}<br>Correlation: {corr:.3f}", font=dict(color=VEOLIA['marine'])),
            xaxis_title=var1_col, yaxis_title=var2_col, height=500, hovermode='closest',
            plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF', font=dict(color=VEOLIA['marine']),
            xaxis=dict(gridcolor='#E9EEF1'), yaxis=dict(gridcolor='#E9EEF1'),
        )
        return fig


# ============================================================
# CHART RENDERER (generic)
# ============================================================
class ChartRenderer:
    def __init__(self, df):
        self.df = df

    @staticmethod
    def _base_layout(fig, title, unit):
        fig.update_layout(
            title=dict(text=title, font=dict(color=VEOLIA['marine'], size=16)),
            height=400, hovermode='x unified', xaxis_title="Days", yaxis_title=unit,
            plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF',
            font=dict(color=VEOLIA['marine']),
            legend=dict(bgcolor='rgba(255,255,255,0.8)'),
            xaxis=dict(gridcolor='#E9EEF1'), yaxis=dict(gridcolor='#E9EEF1'),
        )
        return fig

    def render_line_with_ma(self, column, unit, title, threshold_excellent=None, threshold_good=None):
        col_data = pd.to_numeric(self.df[column], errors='coerce')
        col_ma = col_data.rolling(window=7).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self.df.index, y=col_data, mode='markers', name='Daily', marker=dict(size=4, color=VEOLIA['sky_blue'], opacity=0.7)))
        fig.add_trace(go.Scatter(x=self.df.index, y=col_ma, mode='lines', name='7-day MA', line=dict(color=VEOLIA['marine'], width=2)))
        if threshold_excellent is not None:
            fig.add_hline(y=threshold_excellent, line_dash="dash", line_color=VEOLIA['forest_green'], annotation_text="Excellent", annotation_font_color=VEOLIA['forest_green'])
        if threshold_good is not None:
            fig.add_hline(y=threshold_good, line_dash="dash", line_color=VEOLIA['apricot'], annotation_text="Good", annotation_font_color=VEOLIA['apricot'])
        return self._base_layout(fig, f"{title} ({unit})", unit)

    def render_bar_with_ma(self, column, unit, title):
        col_data = pd.to_numeric(self.df[column], errors='coerce')
        col_ma = col_data.rolling(window=7).mean()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=self.df.index, y=col_data, name='Daily', marker=dict(color=VEOLIA['turquoise'], opacity=0.75)))
        fig.add_trace(go.Scatter(x=self.df.index, y=col_ma, mode='lines', name='7-day MA', line=dict(color=VEOLIA['marine'], width=2)))
        return self._base_layout(fig, f"{title} ({unit})", unit)

    def render_ratio(self, column1, column2, unit, title, threshold_excellent=None, threshold_good=None):
        col1_data = pd.to_numeric(self.df[column1], errors='coerce')
        col2_data = pd.to_numeric(self.df[column2], errors='coerce')
        ratio_data = (col1_data / col2_data).replace([np.inf, -np.inf], np.nan)
        ratio_ma = ratio_data.rolling(window=7).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self.df.index, y=ratio_data, mode='markers', name='Daily', marker=dict(size=4, color=VEOLIA['sky_blue'], opacity=0.7)))
        fig.add_trace(go.Scatter(x=self.df.index, y=ratio_ma, mode='lines', name='7-day MA', line=dict(color=VEOLIA['marine'], width=2)))
        if threshold_excellent is not None:
            fig.add_hline(y=threshold_excellent, line_dash="dash", line_color=VEOLIA['forest_green'], annotation_text="Excellent", annotation_font_color=VEOLIA['forest_green'])
        if threshold_good is not None:
            fig.add_hline(y=threshold_good, line_dash="dash", line_color=VEOLIA['apricot'], annotation_text="Good", annotation_font_color=VEOLIA['apricot'])
        return self._base_layout(fig, f"{title} ({unit})", unit)


def render_kpi_grid(kpis, definitions, per_row=4):
    keys = list(definitions.keys())
    for i in range(0, len(keys), per_row):
        row_keys = keys[i:i + per_row]
        cols = st.columns(len(row_keys))
        for col, key in zip(cols, row_keys):
            defn = definitions[key]
            val = kpis.get(key)
            with col:
                if not val or val.get('insufficient'):
                    st.metric(defn['name'], "—")
                    needed = (val.get('needed') if val else None) or ['Additional data']
                    st.caption(f"ℹ️ Need: {needed[0]}")
                else:
                    st.metric(defn['name'], f"{val['value']:.2f} {val['unit']}", help=defn['description'])
                    st.caption(f"Target: {val.get('target', 'N/A')}")
                    st.markdown(status_chip(val.get('status', '')), unsafe_allow_html=True)


# ============================================================
# BASE KPI CALCULATOR (generic helpers - process pages subclass this)
# ============================================================
class BaseKPICalculator:
    def __init__(self, df, detected_params, plant_info=None):
        self.df = df
        self.dp = detected_params
        self.plant_info = plant_info or {}

    def _col(self, key):
        info = self.dp.get(key, {})
        col = info.get('column')
        if not col:
            return None
        data = pd.to_numeric(self.df[col], errors='coerce').dropna()
        return data if len(data) > 0 else None

    @staticmethod
    def _status_range(value, lo, hi):
        if lo <= value <= hi:
            return '✅ On Target'
        elif value < lo:
            return '🔴 Below Target'
        else:
            return '🟠 Above Target'

    @staticmethod
    def _status_upper(value, hi):
        return '✅ On Target' if value <= hi else '🟠 Above Target'

    @staticmethod
    def _status_lower(value, lo):
        return '✅ On Target' if value >= lo else '🔴 Below Target'

    @staticmethod
    def _insufficient(needed):
        return {'insufficient': True, 'needed': needed}

    @staticmethod
    def _clarity_kpi(value, unit, ntu_target, mgl_target):
        """Only apply a numeric pass/fail rating if the unit is actually recognized as NTU/mg-L,
        otherwise report the value honestly as informational so we never invent a benchmark."""
        if unit == 'NTU':
            status = BaseKPICalculator._status_upper(value, ntu_target)
            target = f'<{ntu_target} NTU'
            display_unit = 'NTU'
        elif unit == 'mg/L':
            status = BaseKPICalculator._status_upper(value, mgl_target)
            target = f'<{mgl_target} mg/L'
            display_unit = 'mg/L'
        else:
            status = 'ℹ️ Informational — unit not confirmed as NTU/mg/L, no benchmark applied'
            target = 'Lower is generally better'
            display_unit = unit if unit not in ('Unknown', None) else 'units'
        return {'value': value, 'unit': display_unit, 'target': target, 'status': status}


# ============================================================
# RULE-BASED RECOMMENDATION ENGINE (generic - no AI/API calls, no key needed)
# ============================================================
class BaseRecommendationEngine:
    """Generates technically-grounded recommendations purely from rule-based templates -
    no external API calls. Each process page supplies its own KPI_DEFINITIONS (list of dicts
    to merge), RECOMMENDATION_TEMPLATES, and PRIORITY_MAP."""

    def __init__(self, kpi_definitions_list, recommendation_templates, priority_map, savings_estimator=None):
        """kpi_definitions_list: list of {key: {'name':..., 'description':...}} dicts to merge
        (e.g. [DEWATERING_KPI_DEFINITIONS, THICKENING_KPI_DEFINITIONS]).
        savings_estimator(key, val) -> (savings_str, explanation_str), optional per-process override."""
        self.definitions = {}
        for d in kpi_definitions_list:
            self.definitions.update(d)
        self.templates = recommendation_templates
        self.priority_map = priority_map
        self.savings_estimator = savings_estimator or self._default_savings_estimator

    @staticmethod
    def _default_savings_estimator(key, val):
        return ("Improves process efficiency", "Specific dollar savings require site-specific cost data not available from the uploaded dataset.")

    def generate_recommendations(self, *kpi_dicts):
        """Pass one or more computed KPI dicts (e.g. dew_kpis, thick_kpis)."""
        combined = []
        for kpis in kpi_dicts:
            for k, v in kpis.items():
                combined.append((k, v, self.definitions.get(k, {})))

        recs = []
        good_items = []

        for key, val, defn in combined:
            if val.get('insufficient'):
                continue
            status = val.get('status', '')
            if 'On Target' in status or 'Informational' in status:
                good_items.append((key, defn.get('name', key), val))
                continue

            template = self.templates.get(key, {})
            priority = self.priority_map.get(key, '🟡 MEDIUM')
            savings, savings_note = self.savings_estimator(key, val)

            recs.append({
                'priority': priority,
                'category': defn.get('name', key.replace('_', ' ').title()),
                'metric': defn.get('name', key),
                'current_value': f"{val['value']:.2f} {val['unit']}",
                'target_value': val.get('target', 'N/A'),
                'issue': template.get('issue', f"{defn.get('name', key)} is outside the target range."),
                'root_causes': template.get('root_causes', ['Process or equipment parameters may need adjustment', 'Feed characteristics may have changed']),
                'actions': template.get('actions', ['Review recent operational data', 'Consult a process engineer for optimization']),
                'potential_savings': savings,
                'savings_explanation': savings_note,
                'additional_data_needed': template.get('additional_data', ['Continue routine monitoring']),
                'timeline': template.get('timeline', '2-4 weeks'),
                'risk': template.get('risk', 'Low - monitor closely'),
                'basis': val.get('basis', 'Calculation basis unavailable for this metric.'),
            })

        if not recs:
            recs.append({
                'priority': '✅ OPTIMAL', 'category': 'Overall Performance', 'metric': 'N/A',
                'current_value': 'N/A', 'target_value': 'N/A',
                'issue': 'All computable KPIs are at or near target - process is operating at optimal performance levels.',
                'root_causes': [], 'actions': ['Continue current operations', 'Maintain preventive maintenance schedule'],
                'potential_savings': 'Maintain current efficiency',
                'savings_explanation': 'Process is performing well across all KPIs that could be computed from your data.',
                'additional_data_needed': ['Continue routine monitoring'], 'timeline': 'Ongoing', 'risk': 'Low',
                'basis': 'N/A - no metric was flagged.',
            })

        return recs, good_items


def render_recommendations_tab(recommendations, good_items):
    """Shared rendering for the AI Recommendations tab, given the output of
    BaseRecommendationEngine.generate_recommendations()."""
    for rec in recommendations:
        with st.container():
            col_h1, col_h2 = st.columns([3, 1])
            with col_h1:
                st.markdown(priority_chip(rec['priority']), unsafe_allow_html=True)
                st.markdown(f"### {rec['category']}")
            with col_h2:
                st.write(f"**Risk:** {rec['risk']}")

            st.markdown("---")

            col_m1, col_m2 = st.columns([2, 1])
            with col_m1:
                st.write(f"**Metric:** {rec['metric']}")
                st.write(f"**Current:** {rec['current_value']} | **Target:** {rec['target_value']}")
                st.write(f"**Why this matters:** {rec['issue']}")

                if rec['root_causes']:
                    st.write("**Likely Root Causes:**")
                    for cause in rec['root_causes']:
                        st.write(f"• {cause}")

                st.write("**Recommended Actions:**")
                for j, action in enumerate(rec['actions'], 1):
                    st.write(f"{j}. {action}")

            with col_m2:
                st.metric("Potential Savings", rec['potential_savings'])
                st.metric("Timeline", rec['timeline'])

            with st.expander("📊 Savings Explanation"):
                st.write(rec['savings_explanation'])

            with st.expander("🧮 How This Was Calculated", expanded=False):
                st.write(f"**Indicators/columns used:** {rec['basis']}")

            with st.expander("📋 Additional Data That Would Improve This Analysis"):
                for item in rec['additional_data_needed']:
                    st.write(f"• {item}")

            st.divider()

    if good_items:
        with st.expander(f"✅ Performing Well ({len(good_items)} metric(s) at or near target)"):
            for key, name, val in good_items:
                st.markdown(f"**{name}:** {val['value']:.2f} {val['unit']} &nbsp; {status_chip(val.get('status', ''))}", unsafe_allow_html=True)
                if val.get('basis'):
                    st.caption(val['basis'])
