import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fuzzywuzzy import fuzz, process
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="WWTP Optimizer",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# TITLE AND HEADER
# ============================================================
st.title("🌊 WWTP Dewatering Optimizer")
st.markdown("**AI-Powered Analysis with Fuzzy Logic Column Detection**")
st.markdown("Upload your WWTP CSV file and get instant optimization recommendations")

# ============================================================
# FUZZY COLUMN MATCHER CLASS
# ============================================================
class FuzzyColumnMatcher:
    \"\"\"Automatically detects columns using fuzzy string matching\"\"\"
    
    def __init__(self, columns):
        self.columns = columns
        self.column_lower = [col.lower() for col in columns]
    
    def find_column(self, keywords, threshold=70):
        \"\"\"Find a column that matches keywords\"\"\"
        # Try to find best match
        search_string = ' '.join(keywords).lower()
        matches = process.extract(
            search_string, 
            self.column_lower, 
            limit=1, 
            scorer=fuzz.token_set_ratio
        )
        
        if matches and matches[0][1] >= threshold:
            matched_idx = self.column_lower.index(matches[0][0])
            return self.columns[matched_idx]
        
        # Try individual keyword matching
        for keyword in keywords:
            for col in self.column_lower:
                if fuzz.ratio(keyword.lower(), col) >= threshold:
                    idx = self.column_lower.index(col)
                    return self.columns[idx]
        
        return None
    
    def find_all_columns(self, keyword_groups):
        \"\"\"Find multiple columns from keyword groups\"\"\"
        results = {}
        for key, keywords in keyword_groups.items():
            results[key] = self.find_column(keywords)
        return results

# ============================================================
# SIDEBAR - FILE UPLOAD
# ============================================================
st.sidebar.header("📊 Upload Your Data")
uploaded_file = st.sidebar.file_uploader(
    "Choose your WWTP CSV file",
    type=['csv'],
    help="Upload a CSV file with your WWTP daily or monthly data"
)

# ============================================================
# MAIN APP LOGIC
# ============================================================
if uploaded_file is None:
    # Show welcome message if no file uploaded
    st.info("👈 **Please upload a CSV file to get started**")
    
    st.markdown("""
    ### 📋 Expected Data Format:
    
    Your CSV should contain columns like:
    - **Date** - Any date format
    - **Influent Flow** (MGD) - Water flowing in
    - **Effluent Flow** (MGD) - Water flowing out
    - **Active Poly** (lbs/ton) - Polymer efficiency
    - **Cake Quality** (%) - Dewatering performance
    - **Centrifuge Run Hours** - Equipment utilization
    - **Dry/Wet Tons** - Sludge reduction
    - **Daily Trucks** - Hauling costs
    
    ### ✨ What the AI Does:
    - 🔍 **Auto-detects** your columns (even with different names!)
    - 📊 **Analyzes** performance metrics
    - 💡 **Recommends** optimizations
    - 💰 **Calculates** potential savings
    - 📈 **Visualizes** trends
    
    ### 🚀 Ready? Upload your file!
    """)

else:
    # ============================================================
    # LOAD AND PROCESS DATA
    # ============================================================
    try:
        df = pd.read_csv(uploaded_file)
        
        # Convert first column to date
        df['Date'] = pd.to_datetime(df.iloc[:, 0], errors='coerce')
        df = df.sort_values('Date')
        
        st.sidebar.success(f"✅ Loaded {len(df)} records")
        st.sidebar.write(f"📅 {df['Date'].min().date()} to {df['Date'].max().date()}")
        
    except Exception as e:
        st.error(f"❌ Error loading file: {e}")
        st.stop()
    
    # ============================================================
    # INITIALIZE FUZZY MATCHER
    # ============================================================
    matcher = FuzzyColumnMatcher(df.columns)
    
    # Define what columns to look for
    column_patterns = {
        'polymer': ['active poly', 'polymer', 'lbs per ton', 'poly efficiency', 'lbs act poly'],
        'cake': ['cake', 'solids', 'cake avg', '%', 'cake quality'],
        'c1_hours': ['centrifuge 1', 'run hours', 'c1', 'hrs'],
        'c2_hours': ['centrifuge 2', 'run hours', 'c2', 'hrs'],
        'c3_hours': ['centrifuge 3', 'run hours', 'c3', 'hrs'],
        'influent': ['influent', 'flow', 'mgd', 'inflow'],
        'effluent': ['effluent', 'flow', 'dval', 'outflow'],
        'dry_tons': ['dry tons', 'dry', 'tons', 'dry ton'],\n        'wet_tons': ['wet tons', 'wet', 'tons', 'wet ton'],\n        'trucks': ['trucks', 'sludge', 'count', 'hauling'],\n        'cost': ['cost', 'polymer cost', '$', 'price'],\n    }\n    \n    # Find columns\n    found_columns = matcher.find_all_columns(column_patterns)\n    \n    # Show detected columns in sidebar\n    st.sidebar.subheader(\"🔍 Detected Columns\")\n    detected_count = 0\n    for key, col in found_columns.items():\n        if col:\n            st.sidebar.write(f\"✅ {key}: {col}\")\n            detected_count += 1\n        else:\n            st.sidebar.write(f\"❌ {key}: Not found\")\n    \n    st.sidebar.write(f\"\\n**Found: {detected_count}/{len(found_columns)} columns**\")\n    \n    # ============================================================\n    # CREATE TABS\n    # ============================================================\n    tab1, tab2, tab3, tab4, tab5 = st.tabs([\n        \"📈 Dashboard\",\n        \"📊 Detailed Analysis\",\n        \"💡 Recommendations\",\n        \"📋 Statistics\",\n        \"📥 Data\"\n    ])\n    \n    # ============================================================\n    # TAB 1: DASHBOARD\n    # ============================================================\n    with tab1:\n        st.header(\"Real-Time Performance Dashboard\")\n        \n        # Key metrics row\n        col1, col2, col3, col4, col5, col6 = st.columns(6)\n        \n        # Metric 1: Polymer Efficiency\n        if found_columns['polymer'] and found_columns['polymer'] in df.columns:\n            poly_data = pd.to_numeric(df[found_columns['polymer']], errors='coerce').dropna()\n            if len(poly_data) > 0:\n                current_poly = poly_data.iloc[-1]\n                avg_poly = poly_data.mean()\n                delta = current_poly - avg_poly\n                \n                with col1:\n                    st.metric(\n                        \"Polymer Efficiency\",\n                        f\"{avg_poly:.2f} lbs/ton\",\n                        f\"{delta:+.2f}\",\n                        delta_color=\"inverse\"\n                    )\n                    if avg_poly < 12:\n                        st.success(\"✅ Excellent\")\n                    elif avg_poly < 15:\n                        st.warning(\"⚠️ Good\")\n                    else:\n                        st.error(\"❌ Needs Work\")\n        \n        # Metric 2: Cake Quality\n        if found_columns['cake'] and found_columns['cake'] in df.columns:\n            cake_data = pd.to_numeric(df[found_columns['cake']], errors='coerce').dropna()\n            if len(cake_data) > 0:\n                current_cake = cake_data.iloc[-1]\n                avg_cake = cake_data.mean()\n                delta = current_cake - avg_cake\n                \n                with col2:\n                    st.metric(\n                        \"Cake Quality\",\n                        f\"{avg_cake:.2f}%\",\n                        f\"{delta:+.2f}%\"\n                    )\n                    if avg_cake > 25:\n                        st.success(\"✅ Excellent\")\n                    elif avg_cake > 20:\n                        st.warning(\"⚠️ Good\")\n                    else:\n                        st.error(\"❌ Needs Work\")\n        \n        # Metric 3: Equipment Utilization\n        if all(found_columns[k] and found_columns[k] in df.columns for k in ['c1_hours', 'c2_hours', 'c3_hours']):\n            c1 = pd.to_numeric(df[found_columns['c1_hours']], errors='coerce').mean()\n            c2 = pd.to_numeric(df[found_columns['c2_hours']], errors='coerce').mean()\n            c3 = pd.to_numeric(df[found_columns['c3_hours']], errors='coerce').mean()\n            avg_util = ((c1 + c2 + c3) / 3 / 24) * 100\n            \n            with col3:\n                st.metric(\"Equipment Util.\", f\"{avg_util:.1f}%\")\n                if 30 < avg_util < 80:\n                    st.success(\"✅ Optimal\")\n                else:\n                    st.warning(\"⚠️ Adjust\")\n        \n        # Metric 4: Dry/Wet Ratio\n        if found_columns['dry_tons'] and found_columns['wet_tons']:\n            if found_columns['dry_tons'] in df.columns and found_columns['wet_tons'] in df.columns:\n                dry = pd.to_numeric(df[found_columns['dry_tons']], errors='coerce')\n                wet = pd.to_numeric(df[found_columns['wet_tons']], errors='coerce')\n                ratio = (dry / wet).mean()\n                \n                with col4:\n                    st.metric(\"Dry/Wet Ratio\", f\"{ratio:.3f}\")\n                    if ratio > 0.25:\n                        st.success(\"✅ Excellent\")\n                    else:\n                        st.warning(\"⚠️ Good\")\n        \n        # Metric 5: Daily Trucks\n        if found_columns['trucks'] and found_columns['trucks'] in df.columns:\n            trucks = pd.to_numeric(df[found_columns['trucks']], errors='coerce').dropna()\n            if len(trucks) > 0:\n                with col5:\n                    st.metric(\"Avg Trucks/Day\", f\"{trucks.mean():.1f}\")\n                    cost = trucks.mean() * 500 * 30\n                    st.write(f\"Est. Monthly: ${cost:,.0f}\")\n        \n        # Metric 6: Flow Balance\n        if found_columns['influent'] and found_columns['effluent']:\n            if found_columns['influent'] in df.columns and found_columns['effluent'] in df.columns:\n                inf = pd.to_numeric(df[found_columns['influent']], errors='coerce').mean()\n                eff = pd.to_numeric(df[found_columns['effluent']], errors='coerce').mean()\n                diff = ((inf - eff) / inf * 100) if inf > 0 else 0\n                \n                with col6:\n                    st.metric(\"Flow Diff\", f\"{diff:.1f}%\")\n                    st.write(\"Evaporation\")\n        \n        st.divider()\n        \n        # Charts\n        col_chart1, col_chart2 = st.columns(2)\n        \n        # Chart 1: Polymer Efficiency\n        with col_chart1:\n            if found_columns['polymer'] and found_columns['polymer'] in df.columns:\n                poly_data = pd.to_numeric(df[found_columns['polymer']], errors='coerce')\n                poly_ma = poly_data.rolling(window=7).mean()\n                \n                fig = go.Figure()\n                fig.add_trace(go.Scatter(\n                    x=df['Date'], y=poly_data,\n                    mode='markers', name='Daily',\n                    marker=dict(size=3, color='lightblue', opacity=0.5)\n                ))\n                fig.add_trace(go.Scatter(\n                    x=df['Date'], y=poly_ma,\n                    mode='lines', name='7-day MA',\n                    line=dict(color='darkblue', width=2)\n                ))\n                fig.add_hline(y=12, line_dash=\"dash\", line_color=\"green\", annotation_text=\"Excellent\")\n                fig.add_hline(y=15, line_dash=\"dash\", line_color=\"orange\", annotation_text=\"Good\")\n                fig.update_layout(\n                    title=\"Polymer Efficiency Trend\",\n                    height=400,\n                    hovermode='x unified',\n                    xaxis_title=\"Date\",\n                    yaxis_title=\"Lbs/Ton\"\n                )\n                st.plotly_chart(fig, use_container_width=True)\n        \n        # Chart 2: Cake Quality\n        with col_chart2:\n            if found_columns['cake'] and found_columns['cake'] in df.columns:\n                cake_data = pd.to_numeric(df[found_columns['cake']], errors='coerce')\n                cake_ma = cake_data.rolling(window=7).mean()\n                \n                fig = go.Figure()\n                fig.add_trace(go.Scatter(\n                    x=df['Date'], y=cake_data,\n                    mode='markers', name='Daily',\n                    marker=dict(size=3, color='plum', opacity=0.5)\n                ))\n                fig.add_trace(go.Scatter(\n                    x=df['Date'], y=cake_ma,\n                    mode='lines', name='7-day MA',\n                    line=dict(color='purple', width=2)\n                ))\n                fig.add_hline(y=25, line_dash=\"dash\", line_color=\"green\", annotation_text=\"Excellent\")\n                fig.add_hline(y=20, line_dash=\"dash\", line_color=\"orange\", annotation_text=\"Good\")\n                fig.update_layout(\n                    title=\"Cake Quality Trend\",\n                    height=400,\n                    hovermode='x unified',\n                    xaxis_title=\"Date\",\n                    yaxis_title=\"Solids %\"\n                )\n                st.plotly_chart(fig, use_container_width=True)\n    \n    # ============================================================\n    # TAB 2: DETAILED ANALYSIS\n    # ============================================================\n    with tab2:\n        st.header(\"Detailed Performance Analysis\")\n        \n        col_a, col_b = st.columns(2)\n        \n        with col_a:\n            st.subheader(\"📊 Polymer Efficiency Analysis\")\n            if found_columns['polymer'] and found_columns['polymer'] in df.columns:\n                poly_data = pd.to_numeric(df[found_columns['polymer']], errors='coerce').dropna()\n                \n                col_a1, col_a2 = st.columns(2)\n                with col_a1:\n                    st.metric(\"Average\", f\"{poly_data.mean():.2f} lbs/ton\")\n                    st.metric(\"Median\", f\"{poly_data.median():.2f} lbs/ton\")\n                with col_a2:\n                    st.metric(\"Min (Best)\", f\"{poly_data.min():.2f} lbs/ton\")\n                    st.metric(\"Max (Worst)\", f\"{poly_data.max():.2f} lbs/ton\")\n                \n                st.metric(\"Std Dev\", f\"{poly_data.std():.2f}\")\n                \n                # Trend\n                if len(poly_data) > 60:\n                    first_30 = poly_data.iloc[:30].mean()\n                    last_30 = poly_data.iloc[-30:].mean()\n                    change = ((last_30 - first_30) / first_30 * 100)\n                    \n                    st.write(f\"**Trend:** {change:+.1f}%\")\n                    if change < -5:\n                        st.success(\"📈 Improving - Getting more efficient!\")\n                    elif change > 5:\n                        st.error(\"📉 Declining - Efficiency getting worse\")\n                    else:\n                        st.info(\"➡️ Stable - Consistent performance\")\n        \n        with col_b:\n            st.subheader(\"🎂 Cake Quality Analysis\")\n            if found_columns['cake'] and found_columns['cake'] in df.columns:\n                cake_data = pd.to_numeric(df[found_columns['cake']], errors='coerce').dropna()\n                \n                col_b1, col_b2 = st.columns(2)\n                with col_b1:\n                    st.metric(\"Average\", f\"{cake_data.mean():.2f}%\")\n                    st.metric(\"Median\", f\"{cake_data.median():.2f}%\")\n                with col_b2:\n                    st.metric(\"Min\", f\"{cake_data.min():.2f}%\")\n                    st.metric(\"Max\", f\"{cake_data.max():.2f}%\")\n                \n                st.metric(\"Std Dev\", f\"{cake_data.std():.2f}%\")\n                \n                # Quality assessment\n                if cake_data.mean() > 25:\n                    st.success(\"✅ Excellent dewatering performance\")\n                elif cake_data.mean() > 20:\n                    st.warning(\"⚠️ Good dewatering, room for improvement\")\n                else:\n                    st.error(\"❌ Poor dewatering, needs attention\")\n    \n    # ============================================================\n    # TAB 3: RECOMMENDATIONS\n    # ============================================================\n    with tab3:\n        st.header(\"🎯 AI-Generated Recommendations\")\n        \n        recommendations = []\n        \n        # Polymer recommendations\n        if found_columns['polymer'] and found_columns['polymer'] in df.columns:\n            poly_data = pd.to_numeric(df[found_columns['polymer']], errors='coerce').dropna()\n            poly_avg = poly_data.mean()\n            poly_current = poly_data.iloc[-1]\n            \n            if poly_avg > 15:\n                savings = (poly_avg - 12) * 50 * 30\n                recommendations.append({\n                    'priority': '🔴 HIGH',\n                    'category': 'Polymer Efficiency',\n                    'issue': 'High polymer consumption',\n                    'action': 'Reduce polymer dose by 10-15%. Adjust centrifuge speed or feed rate.',\n                    'savings': f'${savings:,.0f}/month'\n                })\n            \n            if poly_current > poly_avg * 1.2:\n                recommendations.append({\n                    'priority': '🟡 MEDIUM',\n                    'category': 'Polymer Efficiency',\n                    'issue': 'Recent spike in polymer usage',\n                    'action': 'Investigate operational changes. Check polymer quality and centrifuge parameters.',\n                    'savings': 'Prevent future spikes'\n                })\n        \n        # Cake quality recommendations\n        if found_columns['cake'] and found_columns['cake'] in df.columns:\n            cake_data = pd.to_numeric(df[found_columns['cake']], errors='coerce').dropna()\n            cake_avg = cake_data.mean()\n            \n            if cake_avg < 20:\n                recommendations.append({\n                    'priority': '🔴 HIGH',\n                    'category': 'Cake Quality',\n                    'issue': 'Poor cake quality',\n                    'action': 'Increase polymer dose or adjust centrifuge bowl speed. Check for equipment wear.',\n                    'savings': 'Reduce truck hauling costs'\n                })\n        \n        # Equipment recommendations\n        if all(found_columns[k] and found_columns[k] in df.columns for k in ['c1_hours', 'c2_hours', 'c3_hours']):\n            c1 = pd.to_numeric(df[found_columns['c1_hours']], errors='coerce').mean()\n            c2 = pd.to_numeric(df[found_columns['c2_hours']], errors='coerce').mean()\n            c3 = pd.to_numeric(df[found_columns['c3_hours']], errors='coerce').mean()\n            avg_util = ((c1 + c2 + c3) / 3 / 24) * 100\n            \n            if avg_util < 30:\n                recommendations.append({\n                    'priority': '🟢 LOW',\n                    'category': 'Equipment Utilization',\n                    'issue': 'Underutilized equipment',\n                    'action': 'Consider reducing number of centrifuges or consolidating operations.',\n                    'savings': 'Reduce maintenance costs'\n                })\n            elif avg_util > 80:\n                recommendations.append({\n                    'priority': '🔴 HIGH',\n                    'category': 'Equipment Utilization',\n                    'issue': 'Overutilized equipment',\n                    'action': 'Add additional centrifuge capacity to prevent equipment failure.',\n                    'savings': 'Prevent downtime'\n                })\n        \n        # Display recommendations\n        if recommendations:\n            for i, rec in enumerate(recommendations, 1):\n                st.markdown(f\"### {rec['priority']} {rec['category']}\")\n                st.write(f\"**Issue:** {rec['issue']}\")\n                st.write(f\"**Action:** {rec['action']}\")\n                st.write(f\"**Potential Savings:** {rec['savings']}\")\n                st.divider()\n        else:\n            st.success(\"✅ No critical issues detected. Plant is well-optimized!\")\n    \n    # ============================================================\n    # TAB 4: STATISTICS\n    # ============================================================\n    with tab4:\n        st.header(\"📊 Statistical Summary\")\n        \n        summary_data = []\n        \n        metrics = {\n            'Polymer Efficiency (lbs/ton)': found_columns['polymer'],\n            'Cake Quality (%)': found_columns['cake'],\n            'Daily Trucks': found_columns['trucks'],\n        }\n        \n        for metric_name, col_name in metrics.items():\n            if col_name and col_name in df.columns:\n                data = pd.to_numeric(df[col_name], errors='coerce').dropna()\n                summary_data.append({\n                    'Metric': metric_name,\n                    'Count': len(data),\n                    'Mean': f\"{data.mean():.2f}\",\n                    'Median': f\"{data.median():.2f}\",\n                    'Std Dev': f\"{data.std():.2f}\",\n                    'Min': f\"{data.min():.2f}\",\n                    'Max': f\"{data.max():.2f}\"\n                })\n        \n        summary_df = pd.DataFrame(summary_data)\n        st.dataframe(summary_df, use_container_width=True)\n        \n        # Download button\n        csv = summary_df.to_csv(index=False)\n        st.download_button(\n            label=\"📥 Download Summary\",\n            data=csv,\n            file_name=\"wwtp_summary.csv\",\n            mime=\"text/csv\"\n        )\n    \n    # ============================================================\n    # TAB 5: RAW DATA\n    # ============================================================\n    with tab5:\n        st.header(\"📋 Raw Data\")\n        st.dataframe(df, use_container_width=True)\n        \n        # Download button\n        csv = df.to_csv(index=False)\n        st.download_button(\n            label=\"📥 Download Data\",\n            data=csv,\n            file_name=\"wwtp_data.csv\",\n            mime=\"text/csv\"\n        )\n```

---

## **STEP 3: Save the File**

Make sure you save it as `app.py` (not `app.py.txt`)

Your folder should now look like:
