import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fuzzywuzzy import fuzz, process
from scipy import stats
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="WWTP Performance Analyzer",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌊 WWTP Dewatering & Thickening Performance Analyzer")
st.markdown("**AI-Powered Complete Performance Analysis with Data Quality Checks**")

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
# DATA QUALITY CHECKER CLASS
# ============================================================
class DataQualityChecker:
    """Comprehensive data quality analysis"""
    
    def __init__(self, df):
        self.df = df
        self.quality_report = {}
    
    def detect_outliers(self, column, method='iqr'):
        """Detect outliers using IQR or Z-score"""
        data = pd.to_numeric(self.df[column], errors='coerce').dropna()
        
        if method == 'iqr':
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outliers = data[(data < lower_bound) | (data > upper_bound)]
        else:  # z-score
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
        return {
            'min': data.min(),
            'max': data.max(),
            'mean': data.mean(),
            'std': data.std()
        }
    
    def check_duplicates(self):
        """Check for duplicate rows"""
        duplicates = self.df.duplicated().sum()
        return {
            'count': duplicates,
            'percentage': (duplicates / len(self.df) * 100) if len(self.df) > 0 else 0
        }
    
    def generate_report(self, columns_to_check):
        """Generate comprehensive quality report"""
        report = {
            'total_records': len(self.df),
            'duplicate_rows': self.check_duplicates(),
            'column_analysis': {}
        }
        
        for col in columns_to_check:
            if col in self.df.columns:
                report['column_analysis'][col] = {
                    'missing': self.check_missing_values(col),
                    'range': self.check_data_range(col),
                    'outliers_iqr': self.detect_outliers(col, 'iqr'),
                    'outliers_zscore': self.detect_outliers(col, 'zscore')
                }
        
        return report

# ============================================================
# PERFORMANCE ANALYZER CLASS
# ============================================================
class PerformanceAnalyzer:
    """Comprehensive WWTP performance analysis"""
    
    def __init__(self, df, found_columns):
        self.df = df
        self.found_columns = found_columns
        self.assumptions = self._get_assumptions()
    
    def _get_assumptions(self):
        """Define analysis assumptions"""
        return {
            'Polymer Efficiency': {
                'Excellent': '< 12 lbs/ton',
                'Good': '12-15 lbs/ton',
                'Poor': '> 15 lbs/ton',
                'Rationale': 'Lower polymer use = better efficiency and cost savings'
            },
            'Cake Quality': {
                'Excellent': '> 25% solids',
                'Good': '20-25% solids',
                'Poor': '< 20% solids',
                'Rationale': 'Higher solids = better dewatering, fewer trucks needed'
            },
            'Equipment Utilization': {
                'Optimal': '40-70%',
                'Underutilized': '< 40%',
                'Overutilized': '> 70%',
                'Rationale': 'Balanced utilization prevents equipment wear and maintains capacity'
            },
            'Dry/Wet Ratio': {
                'Excellent': '> 0.25',
                'Good': '0.20-0.25',
                'Poor': '< 0.20',
                'Rationale': 'Higher ratio indicates better sludge dewatering'
            },
            'Flow Balance': {
                'Normal': '< 15% difference',
                'Investigate': '15-25% difference',
                'Critical': '> 25% difference',
                'Rationale': 'Large differences may indicate treatment delays or storage issues'
            },
            'Truck Hauling': {
                'Excellent': '< 50 trucks/month',
                'Good': '50-100 trucks/month',
                'Poor': '> 100 trucks/month',
                'Rationale': 'Fewer trucks = lower costs and better cake quality'
            }
        }
    
    def generate_detailed_recommendations(self):
        """Generate comprehensive recommendations"""
        recommendations = []
        
        # Polymer Analysis
        if self.found_columns['polymer'] and self.found_columns['polymer'] in self.df.columns:
            poly_data = pd.to_numeric(self.df[self.found_columns['polymer']], errors='coerce').dropna()
            poly_avg = poly_data.mean()
            poly_current = poly_data.iloc[-1]
            poly_trend = poly_data.iloc[-30:].mean() if len(poly_data) > 30 else poly_avg
            
            if poly_avg > 18:
                savings = (poly_avg - 12) * 50 * 365
                recommendations.append({
                    'priority': '🔴 CRITICAL',
                    'category': 'Polymer Efficiency',
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
                    'expected_savings': f'${savings:,.0f}/year',
                    'timeline': '1-2 weeks',
                    'risk': 'High - May affect cake quality initially'
                })
            elif poly_avg > 15:
                savings = (poly_avg - 12) * 50 * 365
                recommendations.append({
                    'priority': '🟠 HIGH',
                    'category': 'Polymer Efficiency',
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
                    'expected_savings': f'${savings:,.0f}/year',
                    'timeline': '2-4 weeks',
                    'risk': 'Medium - Monitor cake quality'
                })
            
            if poly_current > poly_avg * 1.3:
                recommendations.append({
                    'priority': '🟡 MEDIUM',
                    'category': 'Polymer Efficiency',
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
                    'expected_savings': 'Prevent future spikes',
                    'timeline': 'Immediate',
                    'risk': 'Low - Investigation only'
                })
        
        # Cake Quality Analysis
        if self.found_columns['cake'] and self.found_columns['cake'] in self.df.columns:
            cake_data = pd.to_numeric(self.df[self.found_columns['cake']], errors='coerce').dropna()
            cake_avg = cake_data.mean()
            cake_current = cake_data.iloc[-1]
            
            if cake_avg < 18:
                truck_savings = 50 * 365 * 500  # Estimated
                recommendations.append({
                    'priority': '🔴 CRITICAL',
                    'category': 'Cake Quality',
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
                    'expected_savings': f'${truck_savings:,.0f}/year (truck reduction)',
                    'timeline': '1-2 weeks',
                    'risk': 'Low - Improves operation'
                })
            elif cake_avg < 22:
                recommendations.append({
                    'priority': '🟠 HIGH',
                    'category': 'Cake Quality',
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
                    'expected_savings': 'Reduce truck hauling costs',
                    'timeline': '2-4 weeks',
                    'risk': 'Low'
                })
        
        # Equipment Utilization
        if all(self.found_columns[k] and self.found_columns[k] in self.df.columns for k in ['c1_hours', 'c2_hours', 'c3_hours']):
            c1 = pd.to_numeric(self.df[self.found_columns['c1_hours']], errors='coerce').mean()
            c2 = pd.to_numeric(self.df[self.found_columns['c2_hours']], errors='coerce').mean()
            c3 = pd.to_numeric(self.df[self.found_columns['c3_hours']], errors='coerce').mean()
            avg_util = ((c1 + c2 + c3) / 3 / 24) * 100
            
            if avg_util < 25:
                maintenance_savings = 15000 * 0.3  # 30% reduction
                recommendations.append({
                    'priority': '🟢 LOW',
                    'category': 'Equipment Utilization',
                    'issue': 'Significantly underutilized equipment',
                    'root_causes': [
                        'Oversized centrifuge capacity',
                        'Low sludge production',
                        'Operational inefficiency'
                    ],
                    'actions': [
                        'Consider consolidating to fewer centrifuges',
                        'Evaluate equipment right-sizing',
                        'Reduce maintenance schedule'
                    ],
                    'expected_savings': f'${maintenance_savings:,.0f}/year',
                    'timeline': '3-6 months',
                    'risk': 'Medium - Requires capital planning'
                })
            elif avg_util > 85:
                recommendations.append({
                    'priority': '🔴 CRITICAL',
                    'category': 'Equipment Utilization',
                    'issue': 'Severely overutilized equipment',
                    'root_causes': [
                        'Insufficient centrifuge capacity',
                        'Increased sludge production',
                        'Equipment downtime'
                    ],
                    'actions': [
                        'Add additional centrifuge capacity',
                        'Improve preventive maintenance',
                        'Optimize feed distribution',
                        'Consider equipment upgrade'
                    ],
                    'expected_savings': 'Prevent equipment failure and downtime',
                    'timeline': '2-6 months',
                    'risk': 'High - Equipment failure risk'
                })
        
        # Truck Hauling Analysis
        if self.found_columns['trucks'] and self.found_columns['trucks'] in self.df.columns:
            trucks = pd.to_numeric(self.df[self.found_columns['trucks']], errors='coerce').dropna()
            trucks_avg = trucks.mean()
            
            if trucks_avg > 200:
                truck_cost_savings = (trucks_avg - 100) * 500 * 365
                recommendations.append({
                    'priority': '🔴 CRITICAL',
                    'category': 'Sludge Hauling',
                    'issue': 'Excessive sludge truck hauling',
                    'root_causes': [
                        'Poor cake quality (wet sludge)',
                        'Inefficient dewatering',
                        'High sludge production'
                    ],
                    'actions': [
                        'Improve cake quality (see Cake Quality recommendations)',
                        'Optimize polymer dose',
                        'Increase centrifuge efficiency'
                    ],
                    'expected_savings': f'${truck_cost_savings:,.0f}/year',
                    'timeline': '1-4 weeks',
                    'risk': 'Low'
                })
        
        return recommendations if recommendations else [{
            'priority': '✅ OPTIMAL',
            'category': 'Overall Performance',
            'issue': 'Plant is operating well',
            'root_causes': [],
            'actions': ['Continue current operations', 'Monitor key metrics'],
            'expected_savings': 'Maintain current efficiency',
            'timeline': 'Ongoing',
            'risk': 'Low'
        }]
    
    def generate_ai_charts(self):
        """AI decides which charts to generate based on data"""
        charts = []
        
        # Always include these
        if self.found_columns['polymer'] and self.found_columns['polymer'] in self.df.columns:
            charts.append({
                'name': 'Polymer Efficiency Trend',
                'type': 'line_with_ma',
                'column': self.found_columns['polymer'],
                'title': 'Polymer Efficiency (lbs/ton)',
                'threshold_good': 15,
                'threshold_excellent': 12
            })
        
        if self.found_columns['cake'] and self.found_columns['cake'] in self.df.columns:
            charts.append({
                'name': 'Cake Quality Trend',
                'type': 'line_with_ma',
                'column': self.found_columns['cake'],
                'title': 'Cake Solids %',
                'threshold_good': 20,
                'threshold_excellent': 25
            })
        
        # Conditional charts based on data availability
        if all(self.found_columns[k] and self.found_columns[k] in self.df.columns for k in ['c1_hours', 'c2_hours', 'c3_hours']):
            charts.append({
                'name': 'Equipment Utilization',
                'type': 'multi_line',
                'columns': [self.found_columns['c1_hours'], self.found_columns['c2_hours'], self.found_columns['c3_hours']],
                'title': 'Centrifuge Run Hours/Day',
                'labels': ['Centrifuge 1', 'Centrifuge 2', 'Centrifuge 3']
            })
        
        if self.found_columns['influent'] and self.found_columns['effluent']:
            if self.found_columns['influent'] in self.df.columns and self.found_columns['effluent'] in self.df.columns:
                charts.append({
                    'name': 'Flow Balance',
                    'type': 'dual_line',
                    'column1': self.found_columns['influent'],
                    'column2': self.found_columns['effluent'],
                    'title': 'Influent vs Effluent Flow',
                    'label1': 'Influent',
                    'label2': 'Effluent'
                })
        
        if self.found_columns['dry_tons'] and self.found_columns['wet_tons']:
            if self.found_columns['dry_tons'] in self.df.columns and self.found_columns['wet_tons'] in self.df.columns:
                charts.append({
                    'name': 'Dewatering Efficiency',
                    'type': 'ratio',
                    'column1': self.found_columns['dry_tons'],
                    'column2': self.found_columns['wet_tons'],
                    'title': 'Dry/Wet Ton Ratio',
                    'threshold': 0.25
                })
        
        if self.found_columns['trucks'] and self.found_columns['trucks'] in self.df.columns:
            charts.append({
                'name': 'Sludge Trucks',
                'type': 'bar_with_ma',
                'column': self.found_columns['trucks'],
                'title': 'Daily Sludge Trucks'
            })
        
        if self.found_columns['cost'] and self.found_columns['dry_tons']:
            if self.found_columns['cost'] in self.df.columns and self.found_columns['dry_tons'] in self.df.columns:
                charts.append({
                    'name': 'Cost per Dry Ton',
                    'type': 'cost_analysis',
                    'cost_column': self.found_columns['cost'],
                    'tons_column': self.found_columns['dry_tons'],
                    'title': 'Polymer Cost per Dry Ton'
                })
        
        return charts

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
    - 🔍 **Auto-detects** your columns
    - 📊 **Generates AI-selected charts**
    - 💡 **Detailed recommendations** with root causes
    - 🔎 **Data quality checks** with outlier detection
    - 📋 **Lists all assumptions** used in analysis
    - 💰 **Calculates potential savings**
    - 📈 **Visualizes trends**
    
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
    
    # Initialize analyzers
    analyzer = PerformanceAnalyzer(df, found_columns)
    quality_checker = DataQualityChecker(df)
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 Dashboard",
        "📊 AI-Generated Charts",
        "💡 Detailed Recommendations",
        "🔍 Data Quality",
        "📋 Assumptions",
        "📉 Statistics",
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
        
        # Quick summary
        st.subheader("📊 Quick Summary")
        col_summary1, col_summary2 = st.columns(2)
        
        with col_summary1:
            st.write("**Key Metrics Status:**")
            if found_columns['polymer'] and found_columns['polymer'] in df.columns:
                poly_avg = pd.to_numeric(df[found_columns['polymer']], errors='coerce').mean()
                st.write(f"- Polymer: {'✅ Good' if poly_avg < 15 else '⚠️ Needs Work'}")
            if found_columns['cake'] and found_columns['cake'] in df.columns:
                cake_avg = pd.to_numeric(df[found_columns['cake']], errors='coerce').mean()
                st.write(f"- Cake Quality: {'✅ Good' if cake_avg > 20 else '⚠️ Needs Work'}")
        
        with col_summary2:
            st.write("**Data Quality:**")
            quality_report = quality_checker.generate_report(
                [col for col in found_columns.values() if col and col in df.columns]
            )
            st.write(f"- Total Records: {quality_report['total_records']}")
            st.write(f"- Duplicate Rows: {quality_report['duplicate_rows']['count']}")
    
    # ============================================================
    # TAB 2: AI-GENERATED CHARTS
    # ============================================================
    with tab2:
        st.header("📊 AI-Selected Performance Charts")
        st.write("*Charts automatically selected based on your data*")
        
        charts = analyzer.generate_ai_charts()
        
        for i, chart_config in enumerate(charts):
            st.subheader(f"{i+1}. {chart_config['name']}")
            
            if chart_config['type'] == 'line_with_ma':
                col_data = pd.to_numeric(df[chart_config['column']], errors='coerce')
                col_ma = col_data.rolling(window=7).mean()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['Date'], y=col_data, mode='markers', name='Daily',
                                        marker=dict(size=3, color='lightblue', opacity=0.5)))
                fig.add_trace(go.Scatter(x=df['Date'], y=col_ma, mode='lines', name='7-day MA',
                                        line=dict(color='darkblue', width=2)))
                
                if 'threshold_excellent' in chart_config:
                    fig.add_hline(y=chart_config['threshold_excellent'], line_dash="dash", line_color="green")
                if 'threshold_good' in chart_config:
                    fig.add_hline(y=chart_config['threshold_good'], line_dash="dash", line_color="orange")
                
                fig.update_layout(title=chart_config['title'], height=400, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
            
            elif chart_config['type'] == 'multi_line':
                fig = go.Figure()
                for col, label in zip(chart_config['columns'], chart_config['labels']):
                    col_data = pd.to_numeric(df[col], errors='coerce')
                    fig.add_trace(go.Scatter(x=df['Date'], y=col_data, mode='lines', name=label, linewidth=2))
                
                fig.update_layout(title=chart_config['title'], height=400, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
            
            elif chart_config['type'] == 'dual_line':
                col1_data = pd.to_numeric(df[chart_config['column1']], errors='coerce')
                col2_data = pd.to_numeric(df[chart_config['column2']], errors='coerce')
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['Date'], y=col1_data, mode='lines', name=chart_config['label1'],
                                        line=dict(color='red', width=2)))
                fig.add_trace(go.Scatter(x=df['Date'], y=col2_data, mode='lines', name=chart_config['label2'],
                                        line=dict(color='green', width=2)))
                
                fig.update_layout(title=chart_config['title'], height=400, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
            
            elif chart_config['type'] == 'ratio':
                col1_data = pd.to_numeric(df[chart_config['column1']], errors='coerce')
                col2_data = pd.to_numeric(df[chart_config['column2']], errors='coerce')
                ratio_data = (col1_data / col2_data).replace([np.inf, -np.inf], np.nan)
                ratio_ma = ratio_data.rolling(window=7).mean()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['Date'], y=ratio_data, mode='markers', name='Daily',
                                        marker=dict(size=3, color='teal', opacity=0.5)))
                fig.add_trace(go.Scatter(x=df['Date'], y=ratio_ma, mode='lines', name='7-day MA',
                                        line=dict(color='darkslategray', width=2)))
                fig.add_hline(y=chart_config['threshold'], line_dash="dash", line_color="green")
                
                fig.update_layout(title=chart_config['title'], height=400, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
            
            elif chart_config['type'] == 'bar_with_ma':
                col_data = pd.to_numeric(df[chart_config['column']], errors='coerce')
                col_ma = col_data.rolling(window=7).mean()
                
                fig = go.Figure()
                fig.add_trace(go.Bar(x=df['Date'], y=col_data, name='Daily', marker=dict(color='coral', opacity=0.7)))
                fig.add_trace(go.Scatter(x=df['Date'], y=col_ma, mode='lines', name='7-day MA',
                                        line=dict(color='darkred', width=2)))
                
                fig.update_layout(title=chart_config['title'], height=400, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
            
            elif chart_config['type'] == 'cost_analysis':
                cost_data = pd.to_numeric(df[chart_config['cost_column']], errors='coerce')
                tons_data = pd.to_numeric(df[chart_config['tons_column']], errors='coerce')
                cost_per_ton = (cost_data / tons_data).replace([np.inf, -np.inf], np.nan)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['Date'], y=cost_per_ton, mode='lines+markers',
                                        name='Cost/Ton', line=dict(color='purple', width=2)))
                
                fig.update_layout(title=chart_config['title'], height=400, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
    
    # ============================================================
    # TAB 3: DETAILED RECOMMENDATIONS
    # ============================================================
    with tab3:
        st.header("💡 Detailed AI Recommendations")
        
        recommendations = analyzer.generate_detailed_recommendations()
        
        for i, rec in enumerate(recommendations, 1):
            with st.container():
                st.markdown(f"### {rec['priority']} {rec['category']}")
                
                col_rec1, col_rec2 = st.columns([2, 1])
                
                with col_rec1:
                    st.write(f"**Issue:** {rec['issue']}")
                    
                    if rec['root_causes']:
                        st.write("**Root Causes:**")
                        for cause in rec['root_causes']:
                            st.write(f"- {cause}")
                    
                    st.write("**Recommended Actions:**")
                    for j, action in enumerate(rec['actions'], 1):
                        st.write(f"{j}. {action}")
                
                with col_rec2:
                    st.metric("Expected Savings", rec['expected_savings'])
                    st.metric("Timeline", rec['timeline'])
                    st.metric("Risk Level", rec['risk'])
                
                st.divider()
    
    # ============================================================
    # TAB 4: DATA QUALITY
    # ============================================================
    with tab4:
        st.header("🔍 Data Quality Analysis")
        
        # Generate quality report
        columns_to_check = [col for col in found_columns.values() if col and col in df.columns]
        quality_report = quality_checker.generate_report(columns_to_check)
        
        # Overall summary
        st.subheader("📊 Overall Data Quality Summary")
        col_dq1, col_dq2, col_dq3 = st.columns(3)
        
        with col_dq1:
            st.metric("Total Records", quality_report['total_records'])
        with col_dq2:
            st.metric("Duplicate Rows", f"{quality_report['duplicate_rows']['count']} ({quality_report['duplicate_rows']['percentage']:.1f}%)")
        with col_dq3:
            st.metric("Columns Analyzed", len(quality_report['column_analysis']))
        
        st.divider()
        
        # Column-by-column analysis
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
                    st.write(f"Std Dev: {col_analysis['range']['std']:.2f}")
                
                with col_dq_c:
                    st.write("**Outliers (IQR):**")
                    st.write(f"Count: {col_analysis['outliers_iqr']['count']}")
                    st.write(f"Percentage: {col_analysis['outliers_iqr']['percentage']:.2f}%")
                
                if col_analysis['outliers_iqr']['count'] > 0:
                    st.write("**Outlier Values:**")
                    st.write(col_analysis['outliers_iqr']['values'][:10])  # Show first 10
        
        st.divider()
        
        # Data quality score
        st.subheader("📈 Data Quality Score")
        
        total_missing = sum([col['missing']['percentage'] for col in quality_report['column_analysis'].values()])
        total_outliers = sum([col['outliers_iqr']['percentage'] for col in quality_report['column_analysis'].values()])
        
        quality_score = 100 - (total_missing / len(quality_report['column_analysis']) * 0.3) - (total_outliers / len(quality_report['column_analysis']) * 0.2)
        quality_score = max(0, min(100, quality_score))
        
        col_score1, col_score2 = st.columns(2)
        with col_score1:
            st.metric("Overall Quality Score", f"{quality_score:.1f}/100")
        with col_score2:
            if quality_score > 90:
                st.success("✅ Excellent data quality")
            elif quality_score > 75:
                st.warning("⚠️ Good data quality - minor issues")
            else:
                st.error("❌ Poor data quality - investigate issues")
    
    # ============================================================
    # TAB 5: ASSUMPTIONS
    # ============================================================
    with tab5:
        st.header("📋 Analysis Assumptions")
        st.write("*These are the assumptions used in the AI analysis*")
        
        for metric, assumptions in analyzer.assumptions.items():
            with st.expander(f"📌 {metric}"):
                for key, value in assumptions.items():
                    st.write(f"**{key}:** {value}")
    
    # ============================================================
    # TAB 6: STATISTICS
    # ============================================================
    with tab6:
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
                    'Max': f"{data.max():.2f}",
                    'Q1': f"{data.quantile(0.25):.2f}",
                    'Q3': f"{data.quantile(0.75):.2f}"
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
    # TAB 7: RAW DATA
    # ============================================================
    with tab7:
        st.header("📋 Raw Data")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Data",
            data=csv,
            file_name="wwtp_data.csv",
            mime="text/csv"
        )


