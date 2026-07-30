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
        
        patterns = {
            'Date': ['date', 'time', 'day', 'month', 'year'],
            'Dewatering - Polymer': [
                'polymer', 'poly', 'active poly', 'lbs per ton', 'lbs/ton',
                'polymer dose', 'polymer usage', 'polymer efficiency',
                'centrifuge polymer', 'dewatering polymer'
            ],
            'Dewatering - Cake Quality': [
                'cake', 'solids', 'cake avg', 'cake %', 'cake quality',
                'centrifuge cake', 'dewatering cake', 'moisture', 'dry solids'
            ],
            'Dewatering - Equipment': [
                'centrifuge', 'run hours', 'runtime', 'bowl speed', 'rpm',
                'feed rate', 'gpm', 'scroll speed', 'differential'
            ],
            'Dewatering - Sludge': [
                'dry tons', 'wet tons', 'dry', 'wet', 'tons', 'sludge',
                'trucks', 'hauling', 'cake hauled'
            ],
            'Thickening - Feed': [
                'thickener feed', 'thickener inlet', 'feed rate',
                'thickener gpm', 'thickener flow'
            ],
            'Thickening - Underflow': [
                'thickener underflow', 'underflow ts', 'underflow solids',
                'thickener solids', 'thickener concentration', 'underflow %'
            ],
            'Thickening - Overflow': [
                'thickener overflow', 'overflow tss', 'overflow clarity',
                'overflow solids', 'overflow suspended'
            ],
            'Thickening - Equipment': [
                'thickener', 'rake', 'torque', 'depth', 'area',
                'thickener runtime', 'thickener hours'
            ],
            'Flow - Influent': [
                'influent', 'inflow', 'inlet', 'incoming', 'mgd',
                'flow in', 'wastewater flow'
            ],
            'Flow - Effluent': [
                'effluent', 'outflow', 'outlet', 'dval', 'flow out',
                'treated flow', 'discharge'
            ],
            'Flow - Other': [
                'recycle', 'return', 'bypass', 'flow', 'gpm', 'mgd'
            ],
            'Cost': [
                'cost', 'price', 'expense', 'dollar', '$', 'rate'
            ]
        }
        
        for col in self.columns:
            col_lower = col.lower()
            categorized = False
            
            for category, keywords in patterns.items():
                for keyword in keywords:
                    if fuzz.ratio(keyword, col_lower) > 75 or keyword in col_lower:
                        self.categories[category].append(col)
                        categorized = True
                        break
                if categorized:
                    break
            
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
        self.assumptions = self._get_assumptions()
    
    def _get_assumptions(self):
        """Define analysis assumptions"""
        return {
            'Dewatering - Polymer Efficiency': {
                'Excellent': '< 12 lbs/ton',
                'Good': '12-15 lbs/ton',
                'Poor': '> 15 lbs/ton',
                'Rationale': 'Lower polymer use = better efficiency and cost savings. Based on industry best practices for centrifuge dewatering.',
                'Data Source': 'Active Polymer per Dry Ton metric'
            },
            'Dewatering - Cake Quality': {
                'Excellent': '> 25% solids',
                'Good': '20-25% solids',
                'Poor': '< 20% solids',
                'Rationale': 'Higher solids = better dewatering, fewer trucks needed. Typical municipal WWTP targets 22-28%.',
                'Data Source': 'Centrifuge Cake Average % metric'
            },
            'Thickening - Underflow Concentration': {
                'Excellent': '> 5% TS',
                'Good': '3-5% TS',
                'Poor': '< 3% TS',
                'Rationale': 'Higher concentration reduces downstream processing load. Typical range 4-6% for gravity thickeners.',
                'Data Source': 'Thickener Underflow TS metric'
            },
            'Thickening - Overflow Clarity': {
                'Excellent': '< 500 mg/L TSS',
                'Good': '500-1000 mg/L TSS',
                'Poor': '> 1000 mg/L TSS',
                'Rationale': 'Lower TSS in overflow indicates better separation. Typical target < 300 mg/L.',
                'Data Source': 'Thickener Overflow TSS metric'
            },
            'Equipment Utilization': {
                'Optimal': '40-70%',
                'Underutilized': '< 40%',
                'Overutilized': '> 70%',
                'Rationale': 'Balanced utilization prevents equipment wear, maintains capacity, and allows for maintenance.',
                'Data Source': 'Average of Centrifuge Run Hours'
            },
            'Dry/Wet Ratio': {
                'Excellent': '> 0.25',
                'Good': '0.20-0.25',
                'Poor': '< 0.20',
                'Rationale': 'Higher ratio indicates better sludge dewatering efficiency. Typical range 0.22-0.30.',
                'Data Source': 'Dry Tons / Wet Tons calculation'
            },
            'Flow Balance': {
                'Normal': '< 15% difference',
                'Investigate': '15-25% difference',
                'Critical': '> 25% difference',
                'Rationale': 'Large differences may indicate treatment delays or measurement errors. Typical evaporation 5-10%.',
                'Data Source': '(Influent - Effluent) / Influent × 100'
            }
        }
    
    def generate_detailed_recommendations(self):
        """Generate comprehensive recommendations"""
        recommendations = []
        
        # Dewatering Polymer Analysis
        poly_cols = self.categorizer.get_all_columns_in_category('Dewatering - Polymer')
        if poly_cols:
            poly_col = poly_cols[0]
            poly_data = pd.to_numeric(self.df[poly_col], errors='coerce').dropna()
            if len(poly_data) > 0:
                poly_avg = poly_data.mean()
                poly_current = poly_data.iloc[-1]
                
                if poly_avg > 18:
                    savings = (poly_avg - 12) * 50 * 365
                    recommendations.append({
                        'priority': '🔴 CRITICAL',
                        'category': 'Dewatering - Polymer Efficiency',
                        'metric': poly_col,
                        'current': f'{poly_avg:.2f}',
                        'target': '12',
                        'unit': 'lbs/ton',
                        'issue': 'Extremely high polymer consumption',
                        'root_causes': [
                            'Centrifuge bowl speed too low',
                            'Feed rate too high',
                            'Poor polymer quality or degradation',
                            'Sludge characteristics changed',
                            'Equipment wear or malfunction'
                        ],
                        'actions': [
                            'Increase centrifuge bowl speed by 5-10%',
                            'Reduce feed rate by 10-15%',
                            'Test polymer quality and shelf life',
                            'Inspect centrifuge for wear',
                            'Analyze incoming sludge characteristics'
                        ],
                        'savings': f'${savings:,.0f}/year',
                        'timeline': '1-2 weeks',
                        'risk': 'High - May affect cake quality initially'
                    })
                elif poly_avg > 15:
                    savings = (poly_avg - 12) * 50 * 365
                    recommendations.append({
                        'priority': '🟠 HIGH',
                        'category': 'Dewatering - Polymer Efficiency',
                        'metric': poly_col,
                        'current': f'{poly_avg:.2f}',
                        'target': '12',
                        'unit': 'lbs/ton',
                        'issue': 'High polymer consumption',
                        'root_causes': [
                            'Suboptimal centrifuge parameters',
                            'Polymer dose not optimized',
                            'Feed rate inconsistency'
                        ],
                        'actions': [
                            'Conduct polymer dose optimization study',
                            'Adjust centrifuge speed incrementally',
                            'Stabilize feed rate'
                        ],
                        'savings': f'${savings:,.0f}/year',
                        'timeline': '2-4 weeks',
                        'risk': 'Medium - Monitor cake quality'
                    })
                
                if poly_current > poly_avg * 1.3:
                    recommendations.append({
                        'priority': '🟡 MEDIUM',
                        'category': 'Dewatering - Polymer Efficiency',
                        'metric': poly_col,
                        'current': f'{poly_current:.2f}',
                        'target': f'{poly_avg:.2f}',
                        'unit': 'lbs/ton',
                        'issue': 'Recent significant spike in polymer usage',
                        'root_causes': [
                            'Sudden change in sludge characteristics',
                            'Equipment malfunction',
                            'Polymer supply issue',
                            'Operational error'
                        ],
                        'actions': [
                            'Investigate sludge quality changes',
                            'Check centrifuge performance',
                            'Verify polymer supply and storage',
                            'Review operator logs'
                        ],
                        'savings': 'Prevent future spikes',
                        'timeline': 'Immediate',
                        'risk': 'Low - Investigation only'
                    })
        
        # Cake Quality Analysis
        cake_cols = self.categorizer.get_all_columns_in_category('Dewatering - Cake Quality')
        if cake_cols:
            cake_col = cake_cols[0]
            cake_data = pd.to_numeric(self.df[cake_col], errors='coerce').dropna()
            if len(cake_data) > 0:
                cake_avg = cake_data.mean()
                
                if cake_avg < 18:
                    truck_savings = 50 * 365 * 500
                    recommendations.append({
                        'priority': '🔴 CRITICAL',
                        'category': 'Dewatering - Cake Quality',
                        'metric': cake_col,
                        'current': f'{cake_avg:.2f}',
                        'target': '25',
                        'unit': '%',
                        'issue': 'Poor cake quality - very wet sludge',
                        'root_causes': [
                            'Insufficient polymer dose',
                            'Centrifuge bowl speed too high',
                            'Sludge feed rate too high',
                            'Polymer type not suitable',
                            'Equipment wear or damage'
                        ],
                        'actions': [
                            'Increase polymer dose by 15-20%',
                            'Reduce centrifuge bowl speed',
                            'Reduce feed rate',
                            'Consider polymer type change',
                            'Inspect centrifuge bowl and scroll'
                        ],
                        'savings': f'${truck_savings:,.0f}/year (truck reduction)',
                        'timeline': '1-2 weeks',
                        'risk': 'Low - Improves operation'
                    })
                elif cake_avg < 22:
                    recommendations.append({
                        'priority': '🟠 HIGH',
                        'category': 'Dewatering - Cake Quality',
                        'metric': cake_col,
                        'current': f'{cake_avg:.2f}',
                        'target': '25',
                        'unit': '%',
                        'issue': 'Below-optimal cake quality',
                        'root_causes': [
                            'Polymer dose could be optimized',
                            'Centrifuge parameters not ideal',
                            'Sludge characteristics variable'
                        ],
                        'actions': [
                            'Fine-tune polymer dose',
                            'Optimize centrifuge speed',
                            'Stabilize feed rate'
                        ],
                        'savings': 'Reduce truck hauling costs',
                        'timeline': '2-4 weeks',
                        'risk': 'Low'
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
                        'issue': 'Low thickener underflow solids concentration',
                        'root_causes': [
                            'Insufficient retention time',
                            'High feed rate',
                            'Poor polymer conditioning',
                            'Rake mechanism issues'
                        ],
                        'actions': [
                            'Reduce feed rate to thickener',
                            'Increase retention time',
                            'Optimize polymer dose',
                            'Check rake mechanism operation'
                        ],
                        'savings': 'Reduce downstream processing load',
                        'timeline': '1-2 weeks',
                        'risk': 'Low'
                    })
        
        return recommendations if recommendations else [{
            'priority': '✅ OPTIMAL',
            'category': 'Overall Performance',
            'metric': 'N/A',
            'current': 'N/A',
            'target': 'N/A',
            'unit': 'N/A',
            'issue': 'Plant operating well',
            'root_causes': [],
            'actions': ['Continue monitoring', 'Maintain preventive maintenance'],
            'savings': 'Maintain current efficiency',
            'timeline': 'Ongoing',
            'risk': 'Low'
        }]
    
    def generate_charts(self):
        """Generate charts based on available data"""
        charts = []
        
        # 1. Dewatering Polymer Chart
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
        
        # 2. Cake Quality Chart
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
        
        # 3. Equipment Hours - Centrifuge 1
        equip_cols = self.categorizer.get_all_columns_in_category('Dewatering - Equipment')
        hour_cols = [col for col in equip_cols if 'hour' in col.lower() or 'runtime' in col.lower()]
        if len(hour_cols) >= 1:
            charts.append({
                'name': 'Centrifuge 1 Run Hours',
                'column': hour_cols[0],
                'type': 'bar_with_ma',
                'unit': 'hrs'
            })
        
        # 4. Equipment Hours - Centrifuge 2
        if len(hour_cols) >= 2:
            charts.append({
                'name': 'Centrifuge 2 Run Hours',
                'column': hour_cols[1],
                'type': 'bar_with_ma',
                'unit': 'hrs'
            })
        
        # 5. Equipment Hours - Centrifuge 3
        if len(hour_cols) >= 3:
            charts.append({
                'name': 'Centrifuge 3 Run Hours',
                'column': hour_cols[2],
                'type': 'bar_with_ma',
                'unit': 'hrs'
            })
        
        # 6. Thickener Underflow Chart
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
        
        # 7. Thickener Overflow Chart
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
        
        # 8. Flow Balance Chart
        inf_cols = self.categorizer.get_all_columns_in_category('Flow - Influent')
        eff_cols = self.categorizer.get_all_columns_in_category('Flow - Effluent')
        if inf_cols and eff_cols:
            charts.append({
                'name': 'Flow Balance (Influent vs Effluent)',
                'column1': inf_cols[0],
                'column2': eff_cols[0],
                'type': 'dual_line',
                'unit': 'MGD'
            })
        
        # 9. Sludge Production Chart
        sludge_cols = self.categorizer.get_all_columns_in_category('Dewatering - Sludge')
        dry_cols = [col for col in sludge_cols if 'dry' in col.lower() and 'ton' in col.lower()]
        if dry_cols:
            charts.append({
                'name': 'Daily Sludge Production (Dry Tons)',
                'column': dry_cols[0],
                'type': 'bar_with_ma',
                'unit': 'tons'
            })
        
        # 10. Truck Hauling Chart
        truck_cols = [col for col in sludge_cols if 'truck' in col.lower()]
        if truck_cols:
            charts.append({
                'name': 'Daily Sludge Trucks',
                'column': truck_cols[0],
                'type': 'bar_with_ma',
                'unit': 'trucks'
            })
        
        # 11. Wet Tons Chart
        wet_cols = [col for col in sludge_cols if 'wet' in col.lower() and 'ton' in col.lower()]
        if wet_cols:
            charts.append({
                'name': 'Total Centrifuge Sludge (Wet Tons)',
                'column': wet_cols[0],
                'type': 'bar_with_ma',
                'unit': 'tons'
            })
        
        # 12. Dry/Wet Ratio Chart
        if dry_cols and wet_cols:
            charts.append({
                'name': 'Dewatering Efficiency (Dry/Wet Ratio)',
                'column1': dry_cols[0],
                'column2': wet_cols[0],
                'type': 'ratio_chart',
                'unit': 'ratio'
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
    3. **Generate 10+ charts** based on available data
    4. **Provide detailed recommendations** tailored to your data
    5. **Analyze correlations** between metrics
    6. **Display assumptions** used in analysis
    
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
            if 'date' in col.lower() or 'time' in col.lower() or 'month' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    if df[col].notna().sum() > len(df) * 0.5:  # At least 50% valid dates
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
            st.sidebar.warning("⚠️ No date column detected - using index")
        
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()
    
    # Categorize columns
    categorizer = ColumnCategorizer(df.columns)
    categories = categorizer.categorize_all_columns()
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📋 Column Detection",
        "📈 Dashboard",
        "📊 Charts",
        "🔗 Correlation Analysis",
        "💡 Recommendations",
        "📋 Assumptions",
        "📉 Statistics",
        "🔍 Data Quality",
        "📥 Raw Data"
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
            if columns:
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
        
        st.divider()
        
        # Sludge Metrics
        st.subheader("📦 Sludge Metrics")
        col_sludge1, col_sludge2, col_sludge3 = st.columns(3)
        
        dry_cols = [col for col in sludge_cols if 'dry' in col.lower() and 'ton' in col.lower()]
        if dry_cols:
            dry_data = pd.to_numeric(df[dry_cols[0]], errors='coerce').dropna()
            if len(dry_data) > 0:
                with col_sludge1:
                    st.metric(
                        "Avg Dry Tons/Day",
                        f"{dry_data.mean():.2f}",
                        "tons"
                    )
        
        wet_cols = [col for col in sludge_cols if 'wet' in col.lower() and 'ton' in col.lower()]
        if wet_cols:
            wet_data = pd.to_numeric(df[wet_cols[0]], errors='coerce').dropna()
            if len(wet_data) > 0:
                with col_sludge2:
                    st.metric(
                        "Avg Wet Tons/Day",
                        f"{wet_data.mean():.2f}",
                        "tons"
                    )
        
        if dry_cols and wet_cols:
            dry_data = pd.to_numeric(df[dry_cols[0]], errors='coerce').dropna()
            wet_data = pd.to_numeric(df[wet_cols[0]], errors='coerce').dropna()
            common_idx = dry_data.index.intersection(wet_data.index)
            if len(common_idx) > 0:
                ratio = (dry_data[common_idx] / wet_data[common_idx]).mean()
                with col_sludge3:
                    st.metric(
                        "Dry/Wet Ratio",
                        f"{ratio:.3f}",
                        "ratio"
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
            st.write(f"*Displaying {len(charts)} charts based on your data*")
            st.divider()
            
            for i, chart_config in enumerate(charts):
                st.subheader(f"{i+1}. {chart_config['name']}")
                
                try:
                    if chart_config['type'] == 'line_with_ma':
                        col_data = pd.to_numeric(df[chart_config['column']], errors='coerce')
                        col_ma = col_data.rolling(window=3).mean()
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=range(len(col_data)), y=col_data, mode='markers', name='Daily',
                                                marker=dict(size=6, color='#1f4788', opacity=0.6)))
                        fig.add_trace(go.Scatter(x=range(len(col_ma)), y=col_ma, mode='lines', name='3-Month MA',
                                                line=dict(color='#003d99', width=3)))
                        
                        if 'threshold_excellent' in chart_config:
                            fig.add_hline(y=chart_config['threshold_excellent'], line_dash="dash", 
                                         line_color="green", annotation_text="Excellent")
                        if 'threshold_good' in chart_config:
                            fig.add_hline(y=chart_config['threshold_good'], line_dash="dash", 
                                         line_color="orange", annotation_text="Good")
                        
                        fig.update_layout(title=f"{chart_config['name']} ({chart_config['unit']})", 
                                         height=400, hovermode='x unified',
                                         xaxis_title="Month", yaxis_title=chart_config['unit'])
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_config['type'] == 'line_with_ma_inverse':
                        col_data = pd.to_numeric(df[chart_config['column']], errors='coerce')
                        col_ma = col_data.rolling(window=3).mean()
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=range(len(col_data)), y=col_data, mode='markers', name='Daily',
                                                marker=dict(size=6, color='#8B0000', opacity=0.6)))
                        fig.add_trace(go.Scatter(x=range(len(col_ma)), y=col_ma, mode='lines', name='3-Month MA',
                                                line=dict(color='#DC143C', width=3)))
                        
                        if 'threshold_excellent' in chart_config:
                            fig.add_hline(y=chart_config['threshold_excellent'], line_dash="dash", 
                                         line_color="green", annotation_text="Excellent")
                        if 'threshold_good' in chart_config:
                            fig.add_hline(y=chart_config['threshold_good'], line_dash="dash", 
                                         line_color="orange", annotation_text="Good")
                        
                        fig.update_layout(title=f"{chart_config['name']} ({chart_config['unit']}) - Lower is Better", 
                                         height=400, hovermode='x unified',
                                         xaxis_title="Month", yaxis_title=chart_config['unit'])
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_config['type'] == 'bar_with_ma':
                        col_data = pd.to_numeric(df[chart_config['column']], errors='coerce')
                        col_ma = col_data.rolling(window=3).mean()
                        
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=range(len(col_data)), y=col_data, name='Monthly',
                                            marker=dict(color='#4169E1', opacity=0.7)))
                        fig.add_trace(go.Scatter(x=range(len(col_ma)), y=col_ma, mode='lines', name='3-Month MA',
                                                line=dict(color='#00008B', width=3)))
                        
                        fig.update_layout(title=f"{chart_config['name']} ({chart_config['unit']})", 
                                         height=400, hovermode='x unified',
                                         xaxis_title="Month", yaxis_title=chart_config['unit'])
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_config['type'] == 'dual_line':
                        col1_data = pd.to_numeric(df[chart_config['column1']], errors='coerce')
                        col2_data = pd.to_numeric(df[chart_config['column2']], errors='coerce')
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=range(len(col1_data)), y=col1_data, mode='lines', name='Influent',
                                                line=dict(color='#8B0000', width=3)))
                        fig.add_trace(go.Scatter(x=range(len(col2_data)), y=col2_data, mode='lines', name='Effluent',
                                                line=dict(color='#228B22', width=3)))
                        
                        fig.update_layout(title=f"{chart_config['name']} ({chart_config['unit']})", 
                                         height=400, hovermode='x unified',
                                         xaxis_title="Month", yaxis_title=chart_config['unit'])
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_config['type'] == 'ratio_chart':
                        col1_data = pd.to_numeric(df[chart_config['column1']], errors='coerce')
                        col2_data = pd.to_numeric(df[chart_config['column2']], errors='coerce')
                        ratio_data = (col1_data / col2_data).replace([np.inf, -np.inf], np.nan)
                        
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=range(len(ratio_data)), y=ratio_data, name='Ratio',
                                            marker=dict(color='#17becf', opacity=0.7)))
                        fig.add_hline(y=0.25, line_dash="dash", line_color="green", annotation_text="Excellent (>0.25)")
                        fig.add_hline(y=0.20, line_dash="dash", line_color="orange", annotation_text="Good (>0.20)")
                        
                        fig.update_layout(title=f"{chart_config['name']} ({chart_config['unit']})", 
                                         height=400, hovermode='x unified',
                                         xaxis_title="Month", yaxis_title=chart_config['unit'])
                        st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.warning(f"Could not create chart: {str(e)}")
                
                st.divider()
    
    # ============================================================
    # TAB 4: CORRELATION ANALYSIS
    # ============================================================
    with tab4:
        st.header("🔗 Correlation Analysis")
        st.write("*Relationships between key metrics*")
        
        # Select numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        
        if len(numeric_df.columns) > 1:
            # Correlation matrix
            corr_matrix = numeric_df.corr()
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                colorscale='RdBu',
                zmid=0,
                text=np.round(corr_matrix.values, 2),
                texttemplate='%{text}',
                textfont={"size": 8}
            ))
            fig.update_layout(title="Correlation Matrix", height=600, width=800)
            st.plotly_chart(fig, use_container_width=True)
            
            # Key correlations
            st.subheader("Key Correlations")
            
            # Flatten correlation matrix and find strong correlations
            corr_pairs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    corr_val = corr_matrix.iloc[i, j]
                    if abs(corr_val) > 0.7:  # Strong correlation
                        corr_pairs.append({
                            'Variable 1': corr_matrix.columns[i],
                            'Variable 2': corr_matrix.columns[j],
                            'Correlation': corr_val
                        })
            
            if corr_pairs:
                corr_df = pd.DataFrame(corr_pairs).sort_values('Correlation', key=abs, ascending=False)
                st.dataframe(corr_df, use_container_width=True)
            else:
                st.info("No strong correlations (>0.7) found between variables")
        else:
            st.warning("Not enough numeric columns for correlation analysis")
    
    # ============================================================
    # TAB 5: RECOMMENDATIONS
    # ============================================================
    with tab5:
        st.header("💡 AI Recommendations")
        
        analyzer = PerformanceAnalyzer(df, categorizer)
        recommendations = analyzer.generate_detailed_recommendations()
        
        for i, rec in enumerate(recommendations, 1):
            with st.container():
                col_header1, col_header2 = st.columns([3, 1])
                with col_header1:
                    st.markdown(f"### {rec['priority']} {rec['category']}")
                with col_header2:
                    st.write(f"**Risk:** {rec['risk']}")
                
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
                    
                    if rec['root_causes']:
                        st.write("**Root Causes:**")
                        for cause in rec['root_causes']:
                            st.write(f"• {cause}")
                    
                    st.markdown("---")
                    
                    st.write("**Recommended Actions:**")
                    for j, action in enumerate(rec['actions'], 1):
                        st.write(f"{j}. {action}")
                
                with col_main2:
                    st.metric("Expected Savings", rec['savings'])
                    st.metric("Timeline", rec['timeline'])
                
                st.markdown("")
    
    # ============================================================
    # TAB 6: ASSUMPTIONS
    # ============================================================
    with tab6:
        st.header("📋 Analysis Assumptions & Thresholds")
        st.write("*These are the industry standards used to evaluate your plant*")
        
        analyzer = PerformanceAnalyzer(df, categorizer)
        
        for metric, details in analyzer.assumptions.items():
            with st.expander(f"**{metric}**", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Performance Levels:**")
                    for level, threshold in details.items():
                        if level not in ['Rationale', 'Data Source']:
                            st.write(f"• **{level}:** {threshold}")
                
                with col2:
                    st.write("**Details:**")
                    st.write(f"**Rationale:** {details['Rationale']}")
                    st.write(f"**Data Source:** {details['Data Source']}")
    
    # ============================================================
    # TAB 7: STATISTICS
    # ============================================================
    with tab7:
        st.header("📉 Statistical Summary")
        st.write("*Detailed statistics for all numeric columns*")
        
        numeric_df = df.select_dtypes(include=[np.number])
        
        # Create statistics table
        stats_data = {
            'Column': [],
            'Count': [],
            'Mean': [],
            'Std Dev': [],
            'Min': [],
            'Q1': [],
            'Median': [],
            'Q3': [],
            'Max': []
        }
        
        for col in numeric_df.columns:
            data = numeric_df[col].dropna()
            if len(data) > 0:
                stats_data['Column'].append(col)
                stats_data['Count'].append(len(data))
                stats_data['Mean'].append(f"{data.mean():.2f}")
                stats_data['Std Dev'].append(f"{data.std():.2f}")
                stats_data['Min'].append(f"{data.min():.2f}")
                stats_data['Q1'].append(f"{data.quantile(0.25):.2f}")
                stats_data['Median'].append(f"{data.median():.2f}")
                stats_data['Q3'].append(f"{data.quantile(0.75):.2f}")
                stats_data['Max'].append(f"{data.max():.2f}")
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True)
        
        # Download statistics
        csv = stats_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Statistics",
            data=csv,
            file_name="WWTP_Statistics.csv",
            mime="text/csv"
        )
    
    # ============================================================
    # TAB 8: DATA QUALITY
    # ============================================================
    with tab8:
        st.header("🔍 Data Quality Analysis")
        
        quality_checker = DataQualityChecker(df)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        quality_report = quality_checker.generate_report(numeric_cols)
        
        st.subheader("📊 Overall Summary")
        col_dq1, col_dq2, col_dq3 = st.columns(3)
        
        with col_dq1:
            st.metric("Total Records", quality_report['total_records'])
        with col_dq2:
            st.metric("Columns Analyzed", len(quality_report['column_analysis']))
        with col_dq3:
            total_missing = sum([v['missing']['count'] for v in quality_report['column_analysis'].values()])
            st.metric("Total Missing Values", total_missing)
        
        st.divider()
        
        st.subheader("📋 Column-by-Column Analysis")
        
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
                    st.write("**Outliers (IQR):**")
                    st.write(f"Count: {col_analysis['outliers_iqr']['count']}")
                    st.write(f"Percentage: {col_analysis['outliers_iqr']['percentage']:.2f}%")
    
    # ============================================================
    # TAB 9: RAW DATA
    # ============================================================
    with tab9:
        st.header("📥 Raw Data")
        st.dataframe(df, use_container_width=True)
        
        # Download options
        col_download1, col_download2 = st.columns(2)
        
        with col_download1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="WWTP_Data_Analysis.csv",
                mime="text/csv"
            )
        
        with col_download2:
            # Excel export
            from io import BytesIO
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
            buffer.seek(0)
            st.download_button(
                label="📥 Download as Excel",
                data=buffer.getvalue(),
                file_name="WWTP_Data_Analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

print("\n✅ Analysis Complete!")
