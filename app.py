import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fuzzywuzzy import fuzz, process
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Universal WWTP Analyzer",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌊 Universal WWTP Performance Analyzer")
st.markdown("**Works with ANY WWTP data format - Dewatering, Thickening, Flow Analysis**")

# ============================================================
# COLUMN CATEGORIZER CLASS
# ============================================================
class ColumnCategorizer:
    """Intelligently categorizes all columns by process type"""
    
    def __init__(self, columns):
        self.columns = columns
        self.column_lower = [col.lower() for col in columns]
        self.categories = {
            'Date': [],
            'Dewatering - Polymer': [],
            'Dewatering - Cake Quality': [],
            'Dewatering - Equipment': [],
            'Dewatering - Sludge': [],
            'Thickening - Feed': [],
            'Thickening - Underflow': [],
            'Thickening - Overflow': [],
            'Thickening - Equipment': [],
            'Flow - Influent': [],
            'Flow - Effluent': [],
            'Flow - Other': [],
            'Cost': [],
            'Other': []
        }
    
    def categorize_all_columns(self):
        """Categorize every column in the dataset"""
        
        # Define keyword patterns for each category
        patterns = {
            'Date': ['date', 'time', 'day', 'month', 'year'],
            
            # Dewatering - Polymer
            'Dewatering - Polymer': [
                'polymer', 'poly', 'active poly', 'lbs per ton', 'lbs/ton',
                'polymer dose', 'polymer usage', 'polymer efficiency',
                'centrifuge polymer', 'dewatering polymer'
            ],
            
            # Dewatering - Cake Quality
            'Dewatering - Cake Quality': [
                'cake', 'solids', 'cake avg', 'cake %', 'cake quality',
                'centrifuge cake', 'dewatering cake', 'moisture', 'dry solids'
            ],
            
            # Dewatering - Equipment
            'Dewatering - Equipment': [
                'centrifuge', 'run hours', 'runtime', 'bowl speed', 'rpm',
                'feed rate', 'gpm', 'scroll speed', 'differential'
            ],
            
            # Dewatering - Sludge
            'Dewatering - Sludge': [
                'dry tons', 'wet tons', 'dry', 'wet', 'tons', 'sludge',
                'trucks', 'hauling', 'cake hauled'
            ],
            
            # Thickening - Feed
            'Thickening - Feed': [
                'thickener feed', 'thickener inlet', 'feed rate',
                'thickener gpm', 'thickener flow'
            ],
            
            # Thickening - Underflow
            'Thickening - Underflow': [
                'thickener underflow', 'underflow ts', 'underflow solids',
                'thickener solids', 'thickener concentration', 'underflow %'
            ],
            
            # Thickening - Overflow
            'Thickening - Overflow': [
                'thickener overflow', 'overflow tss', 'overflow clarity',
                'overflow solids', 'overflow suspended'
            ],
            
            # Thickening - Equipment
            'Thickening - Equipment': [
                'thickener', 'rake', 'torque', 'depth', 'area',
                'thickener runtime', 'thickener hours'
            ],
            
            # Flow - Influent
            'Flow - Influent': [
                'influent', 'inflow', 'inlet', 'incoming', 'mgd',
                'flow in', 'wastewater flow'
            ],
            
            # Flow - Effluent
            'Flow - Effluent': [
                'effluent', 'outflow', 'outlet', 'dval', 'flow out',
                'treated flow', 'discharge'
            ],
            
            # Flow - Other
            'Flow - Other': [
                'recycle', 'return', 'bypass', 'flow', 'gpm', 'mgd'
            ],
            
            # Cost
            'Cost': [
                'cost', 'price', 'expense', 'dollar', '$', 'rate'
            ]
        }
        
        # Categorize each column
        for col in self.columns:
            col_lower = col.lower()
            categorized = False
            
            # Check each pattern
            for category, keywords in patterns.items():
                for keyword in keywords:
                    if fuzz.ratio(keyword, col_lower) > 75 or keyword in col_lower:
                        self.categories[category].append(col)
                        categorized = True
                        break
                if categorized:
                    break
            
            # If not categorized, put in Other
            if not categorized:
                self.categories['Other'].append(col)
        
        return self.categories
    
    def get_best_column(self, category):
        """Get the best column from a category"""
        if category in self.categories and len(self.categories[category]) > 0:
            return self.categories[category][0]
        return None
    
    def get_all_columns_in_category(self, category):
        """Get all columns in a category"""
        if category in self.categories:
            return self.categories[category]
        return []

# ============================================================
# DATA QUALITY CHECKER CLASS
# ============================================================
class DataQualityChecker:
    """Comprehensive data quality analysis"""
    
    def __init__(self, df):
        self.df = df
    
    def detect_outliers(self, column, method='iqr'):
        """Detect outliers using IQR or Z-score"""
        data = pd.to_numeric(self.df[column], errors='coerce').dropna()
        
        if len(data) < 4:
            return {'count': 0, 'percentage': 0, 'values': []}
        
        if method == 'iqr':
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outliers = data[(data < lower_bound) | (data > upper_bound)]
        else:
            z_scores = np.abs(stats.zscore(data))
            outliers = data[z_scores > 3]
        
        return {
            'count': len(outliers),
            'percentage': (len(outliers) / len(data) * 100) if len(data) > 0 else 0,
            'values': outliers.values if len(outliers) > 0 else []
        }
    
    def check_missing_values(self, column):
        """Check for missing values"""
        missing = self.df[column].isna().sum()
        total = len(self.df)
        return {
            'count': missing,
            'percentage': (missing / total * 100) if total > 0 else 0
        }
    
    def check_data_range(self, column):
        """Check if data is in expected range"""
        data = pd.to_numeric(self.df[column], errors='coerce').dropna()
        if len(data) == 0:
            return {'min': 0, 'max': 0, 'mean': 0, 'std': 0}
        return {
            'min': data.min(),
            'max': data.max(),
            'mean': data.mean(),
            'std': data.std()
        }
    
    def generate_report(self, columns_to_check):
        """Generate comprehensive quality report"""
        report = {
            'total_records': len(self.df),
            'column_analysis': {}
        }
        
        for col in columns_to_check:
            if col in self.df.columns:
                report['column_analysis'][col] = {
                    'missing': self.check_missing_values(col),
                    'range': self.check_data_range(col),
                    'outliers_iqr': self.detect_outliers(col, 'iqr')
                }
        
        return report

# ============================================================
# PERFORMANCE ANALYZER CLASS
# ============================================================
class PerformanceAnalyzer:
    """Comprehensive WWTP performance analysis"""
    
    def __init__(self, df, categorizer):
        self.df = df
        self.categorizer = categorizer
    
    def generate_recommendations(self):
        """Generate recommendations based on available data"""
        recommendations = []
        
        # Dewatering Polymer Analysis
        poly_cols = self.categorizer.get_all_columns_in_category('Dewatering - Polymer')
        if poly_cols:
            poly_col = poly_cols[0]
            poly_data = pd.to_numeric(self.df[poly_col], errors='coerce').dropna()
            if len(poly_data) > 0:
                poly_avg = poly_data.mean()
                
                if poly_avg > 15:
                    recommendations.append({
                        'priority': '🔴 HIGH',
                        'category': 'Dewatering - Polymer Efficiency',
                        'metric': poly_col,
                        'current': f'{poly_avg:.2f}',
                        'target': '12',
                        'unit': 'lbs/ton',
                        'issue': 'High polymer consumption',
                        'actions': [
                            'Reduce polymer dose by 10-15%',
                            'Optimize centrifuge speed',
                            'Stabilize feed rate',
                            'Check polymer quality'
                        ],
                        'savings': f'${(poly_avg - 12) * 50 * 365:,.0f}/year'
                    })
        
        # Cake Quality Analysis
        cake_cols = self.categorizer.get_all_columns_in_category('Dewatering - Cake Quality')
        if cake_cols:
            cake_col = cake_cols[0]
            cake_data = pd.to_numeric(self.df[cake_col], errors='coerce').dropna()
            if len(cake_data) > 0:
                cake_avg = cake_data.mean()
                
                if cake_avg < 20:
                    recommendations.append({
                        'priority': '🔴 HIGH',
                        'category': 'Dewatering - Cake Quality',
                        'metric': cake_col,
                        'current': f'{cake_avg:.2f}',
                        'target': '25',
                        'unit': '%',
                        'issue': 'Poor cake quality - wet sludge',
                        'actions': [
                            'Increase polymer dose',
                            'Reduce centrifuge bowl speed',
                            'Reduce feed rate',
                            'Inspect equipment for wear'
                        ],
                        'savings': 'Reduce truck hauling costs'
                    })
        
        # Thickener Analysis
        thick_uf_cols = self.categorizer.get_all_columns_in_category('Thickening - Underflow')
        if thick_uf_cols:
            thick_col = thick_uf_cols[0]
            thick_data = pd.to_numeric(self.df[thick_col], errors='coerce').dropna()
            if len(thick_data) > 0:
                thick_avg = thick_data.mean()
                
                if thick_avg < 3:
                    recommendations.append({
                        'priority': '🟡 MEDIUM',
                        'category': 'Thickening - Underflow Concentration',
                        'metric': thick_col,
                        'current': f'{thick_avg:.2f}',
                        'target': '5',
                        'unit': '% TS',
                        'issue': 'Low thickener underflow solids',
                        'actions': [
                            'Reduce feed rate',
                            'Increase retention time',
                            'Optimize polymer dose',
                            'Check rake mechanism'
                        ],
                        'savings': 'Reduce downstream processing load'
                    })
        
        return recommendations if recommendations else [{
            'priority': '✅ OPTIMAL',
            'category': 'Overall Performance',
            'metric': 'N/A',
            'current': 'N/A',
            'target': 'N/A',
            'unit': 'N/A',
            'issue': 'Plant operating well',
            'actions': ['Continue monitoring', 'Maintain preventive maintenance'],
            'savings': 'Maintain current efficiency'
        }]
    
    def generate_charts(self):
        """Generate charts based on available data"""
        charts = []
        
        # Dewatering Polymer Chart
        poly_cols = self.categorizer.get_all_columns_in_category('Dewatering - Polymer')
        if poly_cols:
            charts.append({
                'name': 'Dewatering Polymer Efficiency',
                'column': poly_cols[0],
                'type': 'line_with_ma',
                'unit': 'lbs/ton',
                'threshold_excellent': 12,
                'threshold_good': 15
            })
        
        # Cake Quality Chart
        cake_cols = self.categorizer.get_all_columns_in_category('Dewatering - Cake Quality')
        if cake_cols:
            charts.append({
                'name': 'Dewatering Cake Quality',
                'column': cake_cols[0],
                'type': 'line_with_ma',
                'unit': '%',
                'threshold_excellent': 25,
                'threshold_good': 20
            })
        
        # Equipment Hours Chart
        equip_cols = self.categorizer.get_all_columns_in_category('Dewatering - Equipment')
        if len(equip_cols) >= 3:
            hour_cols = [col for col in equip_cols if 'hour' in col.lower() or 'runtime' in col.lower()]
            if len(hour_cols) >= 2:
                charts.append({
                    'name': 'Equipment Run Hours',
                    'columns': hour_cols[:3],
                    'type': 'multi_line',
                    'unit': 'hrs'
                })
        
        # Thickener Underflow Chart
        thick_uf_cols = self.categorizer.get_all_columns_in_category('Thickening - Underflow')
        if thick_uf_cols:
            charts.append({
                'name': 'Thickener Underflow TS',
                'column': thick_uf_cols[0],
                'type': 'line_with_ma',
                'unit': '% TS',
                'threshold_excellent': 5,
                'threshold_good': 3
            })
        
        # Thickener Overflow Chart
        thick_of_cols = self.categorizer.get_all_columns_in_category('Thickening - Overflow')
        if thick_of_cols:
            charts.append({
                'name': 'Thickener Overflow TSS',
                'column': thick_of_cols[0],
                'type': 'line_with_ma_inverse',
                'unit': 'mg/L',
                'threshold_excellent': 500,
                'threshold_good': 1000
            })
        
        # Flow Chart
        inf_cols = self.categorizer.get_all_columns_in_category('Flow - Influent')
        eff_cols = self.categorizer.get_all_columns_in_category('Flow - Effluent')
        if inf_cols and eff_cols:
            charts.append({
                'name': 'Flow Balance',
                'column1': inf_cols[0],
                'column2': eff_cols[0],
                'type': 'dual_line',
                'unit': 'MGD'
            })
        
        # Sludge Production Chart
        sludge_cols = self.categorizer.get_all_columns_in_category('Dewatering - Sludge')
        dry_cols = [col for col in sludge_cols if 'dry' in col.lower()]
        if dry_cols:
            charts.append({
                'name': 'Daily Sludge Production',
                'column': dry_cols[0],
                'type': 'bar_with_ma',
                'unit': 'tons'
            })
        
        return charts

# ============================================================
# SIDEBAR - FILE UPLOAD
# ============================================================
st.sidebar.header("📊 Upload Your Data")
uploaded_file = st.sidebar.file_uploader(
    "Choose your WWTP CSV file",
    type=['csv'],
    help="Upload ANY WWTP CSV file - the AI will detect your columns"
)

# ============================================================
# MAIN APP LOGIC
# ============================================================
if uploaded_file is None:
    st.info("👈 **Upload a CSV file to get started**")
    
    st.markdown("""
    ### 📋 How This Works:
    
    This analyzer works with **ANY WWTP data format**. Simply upload your CSV file and the AI will:
    
    1. **Scan all columns** and categorize them by process type
    2. **Show you what it found** before running analysis
    3. **Generate charts** based on available data
    4. **Provide recommendations** tailored to your data
    
    ### 🔍 Supported Data Types:
    
    **Dewatering Process:**
    - Polymer efficiency (lbs/ton, GPD, etc.)
    - Cake quality (%, solids, moisture)
    - Equipment run hours
    - Sludge production (dry/wet tons)
    - Truck hauling data
    
    **Thickening Process:**
    - Feed rate (GPM, MGD)
    - Underflow concentration (% TS)
    - Overflow clarity (TSS mg/L)
    - Equipment runtime
    
    **Flow Data:**
    - Influent flow (MGD, GPM)
    - Effluent flow (MGD, GPM)
    - Recycle/return flows
    
    **Cost Data:**
    - Polymer costs
    - Equipment costs
    - Hauling costs
    
    ### 🚀 Ready? Upload your file!
    """)

else:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Try to find and parse date column
        date_col = None
        for col in df.columns:
            if 'date' in col.lower() or 'time' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    date_col = col
                    break
                except:
                    pass
        
        if date_col:
            df = df.sort_values(date_col)
            st.sidebar.success(f"✅ Loaded {len(df)} records")
            st.sidebar.write(f"📅 {df[date_col].min().date()} to {df[date_col].max().date()}")
        else:
            st.sidebar.success(f"✅ Loaded {len(df)} records")
        
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()
    
    # Categorize columns
    categorizer = ColumnCategorizer(df.columns)
    categories = categorizer.categorize_all_columns()
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Column Detection",
        "📈 Dashboard",
        "📊 Charts",
        "💡 Recommendations",
        "🔍 Data Quality",
        "📥 Data"
    ])
    
    # ============================================================
    # TAB 1: COLUMN DETECTION
    # ============================================================
    with tab1:
        st.header("📋 Column Detection & Categorization")
        st.write("*The AI has scanned your file and categorized all columns*")
        
        st.markdown("---")
        
        # Display categorized columns
        for category, columns in categories.items():
            if columns:  # Only show categories with columns
                with st.expander(f"**{category}** ({len(columns)} columns)", expanded=True):
                    for col in columns:
                        st.write(f"✅ `{col}`")
        
        st.markdown("---")
        
        # Summary
        st.subheader("📊 Summary")
        col_summary1, col_summary2, col_summary3 = st.columns(3)
        
        with col_summary1:
            total_cols = sum(len(cols) for cols in categories.values())
            st.metric("Total Columns", total_cols)
        
        with col_summary2:
            categorized = sum(len(cols) for cat, cols in categories.items() if cat != 'Other')
            st.metric("Categorized", categorized)
        
        with col_summary3:
            other = len(categories['Other'])
            st.metric("Uncategorized", other)
        
        st.info("✅ Column detection complete! Proceed to other tabs for analysis.")
    
    # ============================================================
    # TAB 2: DASHBOARD
    # ============================================================
    with tab2:
        st.header("📈 Performance Dashboard")
        
        # Dewatering Metrics
        st.subheader("🔄 Dewatering Process")
        col_dew1, col_dew2, col_dew3 = st.columns(3)
        
        poly_cols = categorizer.get_all_columns_in_category('Dewatering - Polymer')
        if poly_cols:
            poly_data = pd.to_numeric(df[poly_cols[0]], errors='coerce').dropna()
            if len(poly_data) > 0:
                with col_dew1:
                    delta_val = float(poly_data.iloc[-1] - poly_data.mean())
                    st.metric(
                        "Polymer Efficiency",
                        f"{poly_data.mean():.2f} lbs/ton",
                        delta=delta_val,
                        delta_color="inverse"
                    )
        
        cake_cols = categorizer.get_all_columns_in_category('Dewatering - Cake Quality')
        if cake_cols:
            cake_data = pd.to_numeric(df[cake_cols[0]], errors='coerce').dropna()
            if len(cake_data) > 0:
                with col_dew2:
                    delta_val = float(cake_data.iloc[-1] - cake_data.mean())
                    st.metric(
                        "Cake Quality",
                        f"{cake_data.mean():.2f}%",
                        delta=delta_val
                    )
        
        sludge_cols = categorizer.get_all_columns_in_category('Dewatering - Sludge')
        truck_cols = [col for col in sludge_cols if 'truck' in col.lower()]
        if truck_cols:
            truck_data = pd.to_numeric(df[truck_cols[0]], errors='coerce').dropna()
            if len(truck_data) > 0:
                with col_dew3:
                    st.metric(
                        "Avg Trucks/Day",
                        f"{truck_data.mean():.1f}",
                        f"Est. ${truck_data.mean() * 500 * 30:,.0f}/month"
                    )
        
        st.divider()
        
        # Thickening Metrics
        st.subheader("🌀 Thickening Process")
        col_thick1, col_thick2 = st.columns(2)
        
        thick_uf_cols = categorizer.get_all_columns_in_category('Thickening - Underflow')
        if thick_uf_cols:
            thick_data = pd.to_numeric(df[thick_uf_cols[0]], errors='coerce').dropna()
            if len(thick_data) > 0:
                with col_thick1:
                    delta_val = float(thick_data.iloc[-1] - thick_data.mean())
                    st.metric(
                        "Underflow TS",
                        f"{thick_data.mean():.2f}% TS",
                        delta=delta_val
                    )
        
        thick_of_cols = categorizer.get_all_columns_in_category('Thickening - Overflow')
        if thick_of_cols:
            thick_of_data = pd.to_numeric(df[thick_of_cols[0]], errors='coerce').dropna()
            if len(thick_of_data) > 0:
                with col_thick2:
                    delta_val = float(thick_of_data.iloc[-1] - thick_of_data.mean())
                    st.metric(
                        "Overflow TSS",
                        f"{thick_of_data.mean():.0f} mg/L",
                        delta=delta_val,
                        delta_color="inverse"
                    )
        
        st.divider()
        
        # Flow Metrics
        st.subheader("💧 Flow Data")
        col_flow1, col_flow2 = st.columns(2)
        
        inf_cols = categorizer.get_all_columns_in_category('Flow - Influent')
        if inf_cols:
            inf_data = pd.to_numeric(df[inf_cols[0]], errors='coerce').dropna()
            if len(inf_data) > 0:
                with col_flow1:
                    st.metric(
                        "Influent Flow",
                        f"{inf_data.mean():.2f} MGD"
                    )
        
        eff_cols = categorizer.get_all_columns_in_category('Flow - Effluent')
        if eff_cols:
            eff_data = pd.to_numeric(df[eff_cols[0]], errors='coerce').dropna()
            if len(eff_data) > 0:
                with col_flow2:
                    st.metric(
                        "Effluent Flow",
                        f"{eff_data.mean():.2f} MGD"
                    )
    
    # ============================================================
    # TAB 3: CHARTS
    # ============================================================
    with tab3:
        st.header("📊 Performance Charts")
        
        analyzer = PerformanceAnalyzer(df, categorizer)
        charts = analyzer.generate_charts()
        
        if not charts:
            st.warning("⚠️ No suitable data found for charts. Check your column names.")
        else:
            for i, chart_config in enumerate(charts):
                st.subheader(f"{i+1}. {chart_config['name']}")
                
                try:
                    if chart_config['type'] == 'line_with_ma':
                        col_data = pd.to_numeric(df[chart_config['column']], errors='coerce')
                        col_ma = col_data.rolling(window=7).mean()
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=df.index, y=col_data, mode='markers', name='Daily',
                                                marker=dict(size=4, color='#1f4788', opacity=0.7)))
                        fig.add_trace(go.Scatter(x=df.index, y=col_ma, mode='lines', name='7-day MA',
                                                line=dict(color='#003d99', width=3)))
                        
                        if 'threshold_excellent' in chart_config:
                            fig.add_hline(y=chart_config['threshold_excellent'], line_dash="dash", 
                                         line_color="green", annotation_text="Excellent")
                        if 'threshold_good' in chart_config:
                            fig.add_hline(y=chart_config['threshold_good'], line_dash="dash", 
                                         line_color="orange", annotation_text="Good")
                        
                        fig.update_layout(title=f"{chart_config['name']} ({chart_config['unit']})", 
                                         height=400, hovermode='x unified')
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_config['type'] == 'line_with_ma_inverse':
                        col_data = pd.to_numeric(df[chart_config['column']], errors='coerce')
                        col_ma = col_data.rolling(window=7).mean()
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=df.index, y=col_data, mode='markers', name='Daily',
                                                marker=dict(size=4, color='#8B0000', opacity=0.7)))
                        fig.add_trace(go.Scatter(x=df.index, y=col_ma, mode='lines', name='7-day MA',
                                                line=dict(color='#DC143C', width=3)))
                        
                        if 'threshold_excellent' in chart_config:
                            fig.add_hline(y=chart_config['threshold_excellent'], line_dash="dash", 
                                         line_color="green", annotation_text="Excellent")
                        if 'threshold_good' in chart_config:
                            fig.add_hline(y=chart_config['threshold_good'], line_dash="dash", 
                                         line_color="orange", annotation_text="Good")
                        
                        fig.update_layout(title=f"{chart_config['name']} ({chart_config['unit']}) - Lower is Better", 
                                         height=400, hovermode='x unified')
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_config['type'] == 'multi_line':
                        fig = go.Figure()
                        colors = ['#1f4788', '#FF8C00', '#228B22']
                        for col, color in zip(chart_config['columns'], colors):
                            col_data = pd.to_numeric(df[col], errors='coerce')
                            fig.add_trace(go.Scatter(x=df.index, y=col_data, mode='lines', name=col,
                                                    line=dict(width=3, color=color)))
                        
                        fig.update_layout(title=f"{chart_config['name']} ({chart_config['unit']})", 
                                         height=400, hovermode='x unified')
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_config['type'] == 'dual_line':
                        col1_data = pd.to_numeric(df[chart_config['column1']], errors='coerce')
                        col2_data = pd.to_numeric(df[chart_config['column2']], errors='coerce')
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=df.index, y=col1_data, mode='lines', name='Influent',
                                                line=dict(color='#8B0000', width=3)))
                        fig.add_trace(go.Scatter(x=df.index, y=col2_data, mode='lines', name='Effluent',
                                                line=dict(color='#228B22', width=3)))
                        
                        fig.update_layout(title=f"{chart_config['name']} ({chart_config['unit']})", 
                                         height=400, hovermode='x unified')
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_config['type'] == 'bar_with_ma':
                        col_data = pd.to_numeric(df[chart_config['column']], errors='coerce')
                        col_ma = col_data.rolling(window=7).mean()
                        
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=df.index, y=col_data, name='Daily', 
                                            marker=dict(color='#4169E1', opacity=0.7)))
                        fig.add_trace(go.Scatter(x=df.index, y=col_ma, mode='lines', name='7-day MA',
                                                line=dict(color='#00008B', width=3)))
                        
                        fig.update_layout(title=f"{chart_config['name']} ({chart_config['unit']})", 
                                         height=400, hovermode='x unified')
                        st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.warning(f"Could not create chart: {str(e)}")
                
                st.divider()
    
    # ============================================================
    # TAB 4: RECOMMENDATIONS
    # ============================================================
    with tab4:
        st.header("💡 AI Recommendations")
        
        analyzer = PerformanceAnalyzer(df, categorizer)
        recommendations = analyzer.generate_recommendations()
        
        for i, rec in enumerate(recommendations, 1):
            with st.container():
                col_header1, col_header2 = st.columns([3, 1])
                with col_header1:
                    st.markdown(f"### {rec['priority']} {rec['category']}")
                with col_header2:
                    st.write(f"**Metric:** {rec['metric']}")
                
                st.markdown("---")
                
                col_main1, col_main2 = st.columns([2, 1])
                
                with col_main1:
                    st.write(f"**Issue:** {rec['issue']}")
                    
                    col_cv1, col_cv2 = st.columns(2)
                    with col_cv1:
                        st.write(f"**Current:** {rec['current']} {rec['unit']}")
                    with col_cv2:
                        st.write(f"**Target:** {rec['target']} {rec['unit']}")
                    
                    st.markdown("---")
                    
                    st.write("**Recommended Actions:**")
                    for j, action in enumerate(rec['actions'], 1):
                        st.write(f"{j}. {action}")
                
                with col_main2:
                    st.metric("Expected Savings", rec['savings'])
                
                st.markdown("")
    
    # ============================================================
    # TAB 5: DATA QUALITY
    # ============================================================
    with tab5:
        st.header("🔍 Data Quality Analysis")
        
        quality_checker = DataQualityChecker(df)
        numeric_cols = [col for col in df.columns if pd.to_numeric(df[col], errors='coerce').notna().sum() > 0]
        quality_report = quality_checker.generate_report(numeric_cols)
        
        st.subheader("📊 Overall Summary")
        col_dq1, col_dq2 = st.columns(2)
        
        with col_dq1:
            st.metric("Total Records", f"{quality_report['total_records']} records")
        with col_dq2:
            st.metric("Columns Analyzed", f"{len(quality_report['column_analysis'])} columns")
        
        st.divider()
        
        st.subheader("📋 Column Analysis")
        
        for col_name, col_analysis in quality_report['column_analysis'].items():
            with st.expander(f"📊 {col_name}"):
                col_dq_a, col_dq_b, col_dq_c = st.columns(3)
                
                with col_dq_a:
                    st.write("**Missing Values:**")
                    st.write(f"Count: {col_analysis['missing']['count']}")
                    st.write(f"Percentage: {col_analysis['missing']['percentage']:.2f}%")
                
                with col_dq_b:
                    st.write("**Data Range:**")
                    st.write(f"Min: {col_analysis['range']['min']:.2f}")
                    st.write(f"Max: {col_analysis['range']['max']:.2f}")
                    st.write(f"Mean: {col_analysis['range']['mean']:.2f}")
                
                with col_dq_c:
                    st.write("**Outliers:**")
                    st.write(f"Count: {col_analysis['outliers_iqr']['count']}")
                    st.write(f"Percentage: {col_analysis['outliers_iqr']['percentage']:.2f}%")
    
    # ============================================================
    # TAB 6: RAW DATA
    # ============================================================
    with tab6:
        st.header("📋 Raw Data")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Data",
            data=csv,
            file_name="wwtp_data.csv",
            mime="text/csv"
        )
