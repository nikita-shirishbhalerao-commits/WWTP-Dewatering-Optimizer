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

st.title("🌊 WWTP Dewatering Optimizer")
st.markdown("**AI-Powered Analysis with Fuzzy Logic Column Detection**")
st.markdown("Upload your WWTP CSV file and get instant optimization recommendations")

# ============================================================
# FUZZY COLUMN MATCHER CLASS
# ============================================================
class FuzzyColumnMatcher:
    """Automatically detects columns using fuzzy string matching"""
    
    def __init__(self, columns):
        self.columns = columns
        self.column_lower = [col.lower() for col in columns]
    
    def find_column(self, keywords, threshold=70):
        """Find a column that matches keywords"""
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
        
        for keyword in keywords:
            for col in self.column_lower:
                if fuzz.ratio(keyword.lower(), col) >= threshold:
                    idx = self.column_lower.index(col)
                    return self.columns[idx]
        
        return None
    
    def find_all_columns(self, keyword_groups):
        """Find multiple columns from keyword groups"""
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
    try:
        df = pd.read_csv(uploaded_file)
        df['Date'] = pd.to_datetime(df.iloc[:, 0], errors='coerce')
        df = df.sort_values('Date')
        
        st.sidebar.success(f"✅ Loaded {len(df)} records")
        st.sidebar.write(f"📅 {df['Date'].min().date()} to {df['Date'].max().date()}")
        
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()
    
    # Initialize matcher
    matcher = FuzzyColumnMatcher(df.columns)
    
    column_patterns = {
        'polymer': ['active poly', 'polymer', 'lbs per ton', 'poly efficiency'],
        'cake': ['cake', 'solids', 'cake avg', '%'],
        'c1_hours': ['centrifuge 1', 'run hours', 'c1'],
        'c2_hours': ['centrifuge 2', 'run hours', 'c2'],
        'c3_hours': ['centrifuge 3', 'run hours', 'c3'],
        'influent': ['influent', 'flow', 'mgd'],
        'effluent': ['effluent', 'flow', 'dval'],
        'dry_tons': ['dry tons', 'dry', 'tons'],
        'wet_tons': ['wet tons', 'wet', 'tons'],
        'trucks': ['trucks', 'sludge', 'count'],
        'cost': ['cost', 'polymer cost', '$'],
    }
    
    found_columns = matcher.find_all_columns(column_patterns)
    
    st.sidebar.subheader("🔍 Detected Columns")
    detected_count = 0
    for key, col in found_columns.items():
        if col:
            st.sidebar.write(f"✅ {key}: {col}")
            detected_count += 1
        else:
            st.sidebar.write(f"❌ {key}: Not found")
    
    st.sidebar.write(f"\n**Found: {detected_count}/{len(found_columns)} columns**")
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Dashboard",
        "📊 Detailed Analysis",
        "💡 Recommendations",
        "📋 Statistics",
        "📥 Data"
    ])
    
    # ============================================================
    # TAB 1: DASHBOARD
    # ============================================================
    with tab1:
        st.header("Real-Time Performance Dashboard")
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        if found_columns['polymer'] and found_columns['polymer'] in df.columns:
            poly_data = pd.to_numeric(df[found_columns['polymer']], errors='coerce').dropna()
            if len(poly_data) > 0:
                current_poly = poly_data.iloc[-1]
                avg_poly = poly_data.mean()
                delta = current_poly - avg_poly
                
                with col1:
                    st.metric("Polymer Efficiency", f"{avg_poly:.2f} lbs/ton", f"{delta:+.2f}", delta_color="inverse")
                    if avg_poly < 12:
                        st.success("✅ Excellent")
                    elif avg_poly < 15:
                        st.warning("⚠️ Good")
                    else:
                        st.error("❌ Needs Work")
        
        if found_columns['cake'] and found_columns['cake'] in df.columns:
            cake_data = pd.to_numeric(df[found_columns['cake']], errors='coerce').dropna()
            if len(cake_data) > 0:
                current_cake = cake_data.iloc[-1]
                avg_cake = cake_data.mean()
                delta = current_cake - avg_cake
                
                with col2:
                    st.metric("Cake Quality", f"{avg_cake:.2f}%", f"{delta:+.2f}%")
                    if avg_cake > 25:
                        st.success("✅ Excellent")
                    elif avg_cake > 20:
                        st.warning("⚠️ Good")
                    else:
                        st.error("❌ Needs Work")
        
        if all(found_columns[k] and found_columns[k] in df.columns for k in ['c1_hours', 'c2_hours', 'c3_hours']):
            c1 = pd.to_numeric(df[found_columns['c1_hours']], errors='coerce').mean()
            c2 = pd.to_numeric(df[found_columns['c2_hours']], errors='coerce').mean()
            c3 = pd.to_numeric(df[found_columns['c3_hours']], errors='coerce').mean()
            avg_util = ((c1 + c2 + c3) / 3 / 24) * 100
            
            with col3:
                st.metric("Equipment Util.", f"{avg_util:.1f}%")
                if 30 < avg_util < 80:
                    st.success("✅ Optimal")
                else:
                    st.warning("⚠️ Adjust")
        
        if found_columns['dry_tons'] and found_columns['wet_tons']:
            if found_columns['dry_tons'] in df.columns and found_columns['wet_tons'] in df.columns:
                dry = pd.to_numeric(df[found_columns['dry_tons']], errors='coerce')
                wet = pd.to_numeric(df[found_columns['wet_tons']], errors='coerce')
                ratio = (dry / wet).mean()
                
                with col4:
                    st.metric("Dry/Wet Ratio", f"{ratio:.3f}")
                    if ratio > 0.25:
                        st.success("✅ Excellent")
                    else:
                        st.warning("⚠️ Good")
        
        if found_columns['trucks'] and found_columns['trucks'] in df.columns:
            trucks = pd.to_numeric(df[found_columns['trucks']], errors='coerce').dropna()
            if len(trucks) > 0:
                with col5:
                    st.metric("Avg Trucks/Day", f"{trucks.mean():.1f}")
                    cost = trucks.mean() * 500 * 30
                    st.write(f"Est. Monthly: ${cost:,.0f}")
        
        if found_columns['influent'] and found_columns['effluent']:
            if found_columns['influent'] in df.columns and found_columns['effluent'] in df.columns:
                inf = pd.to_numeric(df[found_columns['influent']], errors='coerce').mean()
                eff = pd.to_numeric(df[found_columns['effluent']], errors='coerce').mean()
                diff = ((inf - eff) / inf * 100) if inf > 0 else 0
                
                with col6:
                    st.metric("Flow Diff", f"{diff:.1f}%")
                    st.write("Evaporation")
        
        st.divider()
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            if found_columns['polymer'] and found_columns['polymer'] in df.columns:
                poly_data = pd.to_numeric(df[found_columns['polymer']], errors='coerce')
                poly_ma = poly_data.rolling(window=7).mean()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['Date'], y=poly_data, mode='markers', name='Daily',
                                        marker=dict(size=3, color='lightblue', opacity=0.5)))
                fig.add_trace(go.Scatter(x=df['Date'], y=poly_ma, mode='lines', name='7-day MA',
                                        line=dict(color='darkblue', width=2)))
                fig.add_hline(y=12, line_dash="dash", line_color="green", annotation_text="Excellent")
                fig.add_hline(y=15, line_dash="dash", line_color="orange", annotation_text="Good")
                fig.update_layout(title="Polymer Efficiency Trend", height=400, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
        
        with col_chart2:
            if found_columns['cake'] and found_columns['cake'] in df.columns:
                cake_data = pd.to_numeric(df[found_columns['cake']], errors='coerce')
                cake_ma = cake_data.rolling(window=7).mean()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['Date'], y=cake_data, mode='markers', name='Daily',
                                        marker=dict(size=3, color='plum', opacity=0.5)))
                fig.add_trace(go.Scatter(x=df['Date'], y=cake_ma, mode='lines', name='7-day MA',
                                        line=dict(color='purple', width=2)))
                fig.add_hline(y=25, line_dash="dash", line_color="green", annotation_text="Excellent")
                fig.add_hline(y=20, line_dash="dash", line_color="orange", annotation_text="Good")
                fig.update_layout(title="Cake Quality Trend", height=400, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
    
    # ============================================================
    # TAB 2: DETAILED ANALYSIS
    # ============================================================
    with tab2:
        st.header("Detailed Performance Analysis")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("📊 Polymer Efficiency Analysis")
            if found_columns['polymer'] and found_columns['polymer'] in df.columns:
                poly_data = pd.to_numeric(df[found_columns['polymer']], errors='coerce').dropna()
                
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    st.metric("Average", f"{poly_data.mean():.2f} lbs/ton")
                    st.metric("Median", f"{poly_data.median():.2f} lbs/ton")
                with col_a2:
                    st.metric("Min (Best)", f"{poly_data.min():.2f} lbs/ton")
                    st.metric("Max (Worst)", f"{poly_data.max():.2f} lbs/ton")
                
                st.metric("Std Dev", f"{poly_data.std():.2f}")
                
                if len(poly_data) > 60:
                    first_30 = poly_data.iloc[:30].mean()
                    last_30 = poly_data.iloc[-30:].mean()
                    change = ((last_30 - first_30) / first_30 * 100)
                    
                    st.write(f"**Trend:** {change:+.1f}%")
                    if change < -5:
                        st.success("📈 Improving - Getting more efficient!")
                    elif change > 5:
                        st.error("📉 Declining - Efficiency getting worse")
                    else:
                        st.info("➡️ Stable - Consistent performance")
        
        with col_b:
            st.subheader("🎂 Cake Quality Analysis")
            if found_columns['cake'] and found_columns['cake'] in df.columns:
                cake_data = pd.to_numeric(df[found_columns['cake']], errors='coerce').dropna()
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.metric("Average", f"{cake_data.mean():.2f}%")
                    st.metric("Median", f"{cake_data.median():.2f}%")
                with col_b2:
                    st.metric("Min", f"{cake_data.min():.2f}%")
                    st.metric("Max", f"{cake_data.max():.2f}%")
                
                st.metric("Std Dev", f"{cake_data.std():.2f}%")
                
                if cake_data.mean() > 25:
                    st.success("✅ Excellent dewatering performance")
                elif cake_data.mean() > 20:
                    st.warning("⚠️ Good dewatering, room for improvement")
                else:
                    st.error("❌ Poor dewatering, needs attention")
    
    # ============================================================
    # TAB 3: RECOMMENDATIONS
    # ============================================================
    with tab3:
        st.header("🎯 AI-Generated Recommendations")
        
        recommendations = []
        
        if found_columns['polymer'] and found_columns['polymer'] in df.columns:
            poly_data = pd.to_numeric(df[found_columns['polymer']], errors='coerce').dropna()
            poly_avg = poly_data.mean()
            poly_current = poly_data.iloc[-1]
            
            if poly_avg > 15:
                savings = (poly_avg - 12) * 50 * 30
                recommendations.append({
                    'priority': '🔴 HIGH',
                    'category': 'Polymer Efficiency',
                    'issue': 'High polymer consumption',
                    'action': 'Reduce polymer dose by 10-15%. Adjust centrifuge speed or feed rate.',
                    'savings': f'${savings:,.0f}/month'
                })
            
            if poly_current > poly_avg * 1.2:
                recommendations.append({
                    'priority': '🟡 MEDIUM',
                    'category': 'Polymer Efficiency',
                    'issue': 'Recent spike in polymer usage',
                    'action': 'Investigate operational changes. Check polymer quality and centrifuge parameters.',
                    'savings': 'Prevent future spikes'
                })
        
        if found_columns['cake'] and found_columns['cake'] in df.columns:
            cake_data = pd.to_numeric(df[found_columns['cake']], errors='coerce').dropna()
            cake_avg = cake_data.mean()
            
            if cake_avg < 20:
                recommendations.append({
                    'priority': '🔴 HIGH',
                    'category': 'Cake Quality',
                    'issue': 'Poor cake quality',
                    'action': 'Increase polymer dose or adjust centrifuge bowl speed. Check for equipment wear.',
                    'savings': 'Reduce truck hauling costs'
                })
        
        if all(found_columns[k] and found_columns[k] in df.columns for k in ['c1_hours', 'c2_hours', 'c3_hours']):
            c1 = pd.to_numeric(df[found_columns['c1_hours']], errors='coerce').mean()
            c2 = pd.to_numeric(df[found_columns['c2_hours']], errors='coerce').mean()
            c3 = pd.to_numeric(df[found_columns['c3_hours']], errors='coerce').mean()
            avg_util = ((c1 + c2 + c3) / 3 / 24) * 100
            
            if avg_util < 30:
                recommendations.append({
                    'priority': '🟢 LOW',
                    'category': 'Equipment Utilization',
                    'issue': 'Underutilized equipment',
                    'action': 'Consider reducing number of centrifuges or consolidating operations.',
                    'savings': 'Reduce maintenance costs'
                })
            elif avg_util > 80:
                recommendations.append({
                    'priority': '🔴 HIGH',
                    'category': 'Equipment Utilization',
                    'issue': 'Overutilized equipment',
                    'action': 'Add additional centrifuge capacity to prevent equipment failure.',
                    'savings': 'Prevent downtime'
                })
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                st.markdown(f"### {rec['priority']} {rec['category']}")
                st.write(f"**Issue:** {rec['issue']}")
                st.write(f"**Action:** {rec['action']}")
                st.write(f"**Potential Savings:** {rec['savings']}")
                st.divider()
        else:
            st.success("✅ No critical issues detected. Plant is well-optimized!")
    
    # ============================================================
    # TAB 4: STATISTICS
    # ============================================================
    with tab4:
        st.header("📊 Statistical Summary")
        
        summary_data = []
        
        metrics = {
            'Polymer Efficiency (lbs/ton)': found_columns['polymer'],
            'Cake Quality (%)': found_columns['cake'],
            'Daily Trucks': found_columns['trucks'],
        }
        
        for metric_name, col_name in metrics.items():
            if col_name and col_name in df.columns:
                data = pd.to_numeric(df[col_name], errors='coerce').dropna()
                summary_data.append({
                    'Metric': metric_name,
                    'Count': len(data),
                    'Mean': f"{data.mean():.2f}",
                    'Median': f"{data.median():.2f}",
                    'Std Dev': f"{data.std():.2f}",
                    'Min': f"{data.min():.2f}",
                    'Max': f"{data.max():.2f}"
                })
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
        
        csv = summary_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Summary",
            data=csv,
            file_name="wwtp_summary.csv",
            mime="text/csv"
        )
    
    # ============================================================
    # TAB 5: RAW DATA
    # ============================================================
    with tab5:
        st.header("📋 Raw Data")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Data",
            data=csv,
            file_name="wwtp_data.csv",
            mime="text/csv"
        )

