import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fuzzywuzzy import fuzz
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

try:
    import openpyxl
except ImportError:
    pass

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="WWTP Dewatering & Thickening Analyzer",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌊 AI-Powered WWTP Dewatering & Thickening Performance Analyzer")
st.markdown("**Fuzzy Parameter Detection | Benchmark/YOY Analysis | AI Recommendations | Unit Tracking**")

# ============================================================
# PERFORMANCE THRESHOLDS (used for chart footnotes + ratings)
# These map to the charted metrics in the Dewatering / Thickening tabs
# ============================================================
PERFORMANCE_THRESHOLDS = {
    'polymer': {'excellent': (0, 12), 'good': (12, 15), 'moderate': (15, 18), 'poor': (18, float('inf'))},
    'cake_quality': {'excellent': (25, float('inf')), 'good': (20, 25), 'moderate': (15, 20), 'poor': (0, 15)},
    'dry_wet_ratio': {'excellent': (0.25, float('inf')), 'good': (0.20, 0.25), 'moderate': (0.15, 0.20), 'poor': (0, 0.15)},
    'thickener_underflow': {'excellent': (5, float('inf')), 'good': (3, 5), 'moderate': (2, 3), 'poor': (0, 2)},
    'thickener_overflow': {'excellent': (0, 500), 'good': (500, 1000), 'moderate': (1000, 1500), 'poor': (1500, float('inf'))},
    'gbt_underflow': {'excellent': (8, float('inf')), 'good': (5, 8), 'moderate': (3, 5), 'poor': (0, 3)},
    'gbt_overflow': {'excellent': (0, 300), 'good': (300, 500), 'moderate': (500, 800), 'poor': (800, float('inf'))},
}


def format_threshold_footnote(metric_key, unit=""):
    """Build a human-readable Excellent/Good/Moderate/Poor legend for a chart footnote."""
    if metric_key not in PERFORMANCE_THRESHOLDS:
        return None
    thresholds = PERFORMANCE_THRESHOLDS[metric_key]
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


def render_footnote(metric_key, unit="", fallback=None):
    txt = format_threshold_footnote(metric_key, unit)
    if txt:
        st.caption(f"📊 Performance benchmark — {txt}")
    elif fallback:
        st.caption(fallback)


# ============================================================
# KPI DEFINITIONS (used to render the Dashboard + drive Recommendations)
# ============================================================
DEWATERING_KPI_DEFINITIONS = {
    'cake_solids': {'name': 'Cake Solids Content (%)', 'description': 'Dry solids percentage in dewatered biosolids. Target varies by equipment: 18-25% belt press, 20-30% centrifuge.'},
    'polymer_consumption': {'name': 'Polymer Consumption (lbs/ton DS)', 'description': 'Conditioning chemical usage per ton of dry solids processed.'},
    'dewatering_throughput': {'name': 'Dewatering Throughput (lbs DS/day)', 'description': 'Daily dry solids processing capacity.'},
    'filtrate_turbidity': {'name': 'Filtrate Turbidity (NTU)', 'description': 'Clarity of return liquor/centrate. Lower = better solids capture.'},
    'solids_recovery': {'name': 'Solids Recovery Rate (%)', 'description': 'Percentage of incoming solids captured in cake vs. lost to recycle stream.'},
    'cake_production_rate': {'name': 'Cake Production Rate (lbs/hour)', 'description': 'Dewatered biosolids output rate.'},
    'filtrate_flow_rate': {'name': 'Filtrate Flow Rate (gpm)', 'description': 'Return liquor flow rate from dewatering.'},
    'polymer_cost_per_lb': {'name': 'Polymer Cost per Pound of Solids ($/lb DS)', 'description': 'Economic indicator of chemical efficiency.'},
    'cake_moisture': {'name': 'Cake Moisture Content (%)', 'description': 'Inverse of cake solids content.'},
    'equipment_availability': {'name': 'Dewatering Equipment Availability (%)', 'description': 'Uptime percentage of dewatering equipment.'},
}

THICKENING_KPI_DEFINITIONS = {
    'thickened_solids': {'name': 'Thickened Solids Concentration (%)', 'description': 'Dry solids percentage achieved. Target 4-8% gravity, 6-12% DAF.'},
    'underflow_lbs_gal': {'name': 'Underflow Solids Concentration (lbs DS/gal)', 'description': 'Underflow solids expressed as mass per gallon; higher = less downstream load.'},
    'overflow_turbidity': {'name': 'Overflow Turbidity/TSS', 'description': 'Clarified supernatant quality. Lower = better solids separation.'},
    'thickening_throughput': {'name': 'Thickening Throughput (lbs DS/day)', 'description': 'Estimated daily solids processing capacity.'},
    'solids_capture_efficiency': {'name': 'Solids Capture Efficiency (%)', 'description': 'Percentage of incoming solids retained in thickened sludge.'},
    'underflow_production_rate': {'name': 'Underflow Production Rate (lbs/hour)', 'description': 'Thickened sludge output rate.'},
    'overflow_flow_rate': {'name': 'Overflow Flow Rate (gpm)', 'description': 'Return liquor flow rate from thickening.'},
    'solids_loading_rate': {'name': 'Solids Loading Rate (lbs DS/day/sq ft)', 'description': 'Thickener surface-area efficiency.'},
    'air_polymer_consumption': {'name': 'Air/Polymer Consumption (lbs/ton DS)', 'description': 'Thickening chemical (or DAF air) usage per ton dry solids.'},
    'thickening_equipment_availability': {'name': 'Thickening Equipment Availability (%)', 'description': 'Uptime percentage of thickening equipment.'},
}

# ============================================================
# RECOMMENDATION TEMPLATES + PRIORITY MAP
# ============================================================
RECOMMENDATION_TEMPLATES = {
    'cake_solids': {
        'issue': 'Cake solids content is outside the target range, affecting hauling costs and disposal efficiency.',
        'root_causes': ['Insufficient or excessive polymer dose', 'Equipment speed not optimized for current sludge characteristics', 'Feed rate too high for equipment capacity', 'Polymer type not suited to sludge', 'Equipment wear (bowl, belt, scroll, bearings)'],
        'actions': ['Run a jar test to re-optimize polymer type and dose', 'Adjust equipment speed in small increments and monitor cake solids', 'Review and adjust feed/throughput rate', 'Inspect equipment for wear or mechanical issues'],
        'additional_data': ['Feed sludge %TS and VS%', 'Equipment speed/torque logs', 'Polymer type and dilution ratio'],
        'timeline': '1-2 weeks', 'risk': 'Low - improves operation',
    },
    'polymer_consumption': {
        'issue': 'Polymer usage is above the efficient operating range, increasing chemical costs.',
        'root_causes': ['Bowl/belt speed suboptimal', 'Feed rate too high', 'Polymer type/concentration mismatch with sludge', 'Equipment wear', 'Sludge characteristics changed (higher solids, harder to dewater)'],
        'actions': ['Conduct a polymer jar test to re-optimize dose and product', 'Adjust equipment speed incrementally', 'Reduce feed rate 10-15% and monitor cake quality', 'Inspect equipment for wear'],
        'additional_data': ['Sludge %TS and VS%', 'Equipment RPM/belt speed', 'Polymer type and active content'],
        'timeline': '1-2 weeks', 'risk': 'Medium - monitor cake quality while adjusting',
    },
    'filtrate_turbidity': {
        'issue': 'Filtrate/centrate turbidity is elevated, indicating solids are escaping to the recycle stream.',
        'root_causes': ['Polymer underdosed', 'Feed rate too high for equipment', 'Screen/bowl wear allowing solids bypass', 'Polymer not fully mixed before dewatering'],
        'actions': ['Increase polymer dose incrementally and monitor turbidity response', 'Check polymer mixing/injection point', 'Inspect screens, bowl, or belt for wear', 'Reduce feed rate if turbidity persists'],
        'additional_data': ['Polymer mixing energy/injection point details', 'Screen/bowl inspection records'],
        'timeline': '1-2 weeks', 'risk': 'Low',
    },
    'solids_recovery': {
        'issue': 'A larger share of incoming solids is being lost to the recycle stream instead of being captured in cake.',
        'root_causes': ['Polymer dose insufficient', 'Feed rate exceeds equipment capacity', 'Equipment wear', 'Poor polymer-sludge mixing'],
        'actions': ['Increase polymer dose incrementally', 'Reduce feed/throughput rate', 'Inspect equipment for wear', 'Optimize polymer mixing energy'],
        'additional_data': ['Feed solids loading data', 'Recycle stream solids concentration'],
        'timeline': '2-3 weeks', 'risk': 'Low',
    },
    'cake_production_rate': {
        'issue': 'Cake production rate is outside the typical operating range for this equipment class.',
        'root_causes': ['Feed rate mismatched to equipment design capacity', 'Equipment running below/above rated throughput'],
        'actions': ['Review feed rate against equipment design specs', 'Evaluate whether an additional train needs to be brought online'],
        'additional_data': ['Equipment design capacity/rated throughput'],
        'timeline': 'Ongoing', 'risk': 'Low',
    },
    'equipment_availability': {
        'issue': 'Dewatering equipment uptime is below target, risking capacity shortfalls.',
        'root_causes': ['Unplanned downtime/maintenance', 'Equipment reliability issues', 'Insufficient redundancy/backup units'],
        'actions': ['Review maintenance logs for recurring failure modes', 'Evaluate preventive maintenance schedule', 'Assess need for backup equipment or spare parts inventory'],
        'additional_data': ['Maintenance work order history', 'Downtime cause codes'],
        'timeline': '4-8 weeks', 'risk': 'Medium - reliability risk',
    },
    'cake_moisture': {
        'issue': 'Cake moisture content is outside the optimal range, affecting handling and disposal costs.',
        'root_causes': ['Same drivers as Cake Solids (inverse relationship): polymer dose, equipment speed, feed rate'],
        'actions': ['See the Cake Solids recommendation above - moisture is the inverse of cake solids'],
        'additional_data': ['See Cake Solids KPI'],
        'timeline': '1-2 weeks', 'risk': 'Low',
    },
    'polymer_cost_per_lb': {
        'issue': 'Polymer cost per pound of dry solids processed is above the typical benchmark range.',
        'root_causes': ['Polymer dose too high for sludge characteristics', 'Polymer unit price above market average', 'Inefficient mixing requiring higher dose'],
        'actions': ['Re-run polymer jar tests with competing vendors/products', 'Negotiate polymer pricing/contract terms', 'Improve polymer mixing efficiency to lower required dose'],
        'additional_data': ['Polymer contract pricing', 'Vendor jar test results'],
        'timeline': '4-6 weeks', 'risk': 'Low',
    },
    'thickened_solids': {
        'issue': 'Thickened solids concentration is below target, increasing downstream dewatering load.',
        'root_causes': ['Insufficient retention time', 'Feed rate too high', 'Poor polymer conditioning ahead of thickening', 'Rake/belt mechanism issues', 'Sludge is inherently difficult to thicken'],
        'actions': ['Reduce feed rate to the thickener', 'Increase retention time if possible', 'Optimize polymer dose for thickening', 'Inspect rake/belt mechanism'],
        'additional_data': ['Thickener feed rate and retention time', 'Polymer dose used ahead of thickening'],
        'timeline': '1-2 weeks', 'risk': 'Low',
    },
    'overflow_turbidity': {
        'issue': 'Thickener/GBT overflow quality is degraded, indicating solids loss to the return stream.',
        'root_causes': ['Feed rate too high', 'Polymer underdosed', 'Screen/mesh wear (GBT)', 'Rake speed too high (gravity thickener)'],
        'actions': ['Reduce feed rate', 'Increase polymer dose incrementally', 'Inspect belt/screen for wear', 'Adjust rake speed'],
        'additional_data': ['Overflow flow rate', 'Polymer dose ahead of thickening'],
        'timeline': '1-2 weeks', 'risk': 'Low',
    },
    'underflow_production_rate': {
        'issue': 'Underflow production rate is outside the typical operating range.',
        'root_causes': ['Feed rate mismatched to equipment capacity', 'Underflow concentration lower/higher than expected'],
        'actions': ['Review feed rate against thickener design capacity', 'Re-evaluate underflow concentration targets'],
        'additional_data': ['Thickener design capacity'],
        'timeline': 'Ongoing', 'risk': 'Low',
    },
    'solids_loading_rate': {
        'issue': 'Solids loading rate on the thickener surface area is outside the recommended range.',
        'root_causes': ['Feed rate too high relative to available surface area', 'Underflow concentration lower than expected, increasing load'],
        'actions': ['Reduce feed rate or distribute flow across additional units if available', 'Investigate ways to increase underflow concentration'],
        'additional_data': ['Confirm thickener surface area entered in Plant Information'],
        'timeline': '2-4 weeks', 'risk': 'Low',
    },
    'air_polymer_consumption': {
        'issue': 'Thickening polymer (or air, for DAF) consumption is above the typical benchmark range.',
        'root_causes': ['Polymer dose not optimized for current sludge characteristics', 'Poor mixing efficiency', 'Feed rate too high'],
        'actions': ['Run a polymer jar test to re-optimize dose', 'Improve polymer mixing/injection point', 'Review feed rate'],
        'additional_data': ['Sludge characteristics ahead of thickening'],
        'timeline': '1-2 weeks', 'risk': 'Low',
    },
    'thickening_equipment_availability': {
        'issue': 'Thickening equipment uptime is below target, risking capacity shortfalls upstream of dewatering.',
        'root_causes': ['Unplanned downtime/maintenance', 'Equipment reliability issues'],
        'actions': ['Review maintenance logs for recurring failure modes', 'Evaluate preventive maintenance schedule'],
        'additional_data': ['Maintenance work order history'],
        'timeline': '4-8 weeks', 'risk': 'Medium - reliability risk',
    },
}

PRIORITY_MAP = {
    'cake_solids': '🔴 CRITICAL', 'polymer_consumption': '🟠 HIGH', 'filtrate_turbidity': '🟡 MEDIUM',
    'solids_recovery': '🟠 HIGH', 'cake_production_rate': '🟡 MEDIUM', 'equipment_availability': '🟠 HIGH',
    'cake_moisture': '🟡 MEDIUM', 'polymer_cost_per_lb': '🟡 MEDIUM', 'thickened_solids': '🟠 HIGH',
    'overflow_turbidity': '🟡 MEDIUM', 'underflow_production_rate': '🟡 MEDIUM', 'solids_loading_rate': '🟡 MEDIUM',
    'air_polymer_consumption': '🟡 MEDIUM', 'thickening_equipment_availability': '🟠 HIGH',
}

# ============================================================
# FUZZY PARAMETER DETECTOR
# ============================================================
class FuzzyParameterDetector:
    """Detects WWTP parameters in uploaded column headers using fuzzy matching."""

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

    def find_parameters(self, keyword_groups, threshold=55):
        results = {}
        for param_name, keywords in keyword_groups.items():
            best_col, best_score = None, 0
            for col, col_clean in zip(self.columns, self.clean_columns):
                col_best = 0
                for kw in keywords:
                    kw_clean = self._clean(kw)
                    score = max(
                        fuzz.token_set_ratio(kw_clean, col_clean),
                        fuzz.partial_ratio(kw_clean, col_clean),
                    )
                    if score > col_best:
                        col_best = score
                if col_best > best_score:
                    best_score = col_best
                    best_col = col
            if best_col and best_score >= threshold:
                results[param_name] = {'column': best_col, 'score': best_score, 'unit': self._detect_unit(best_col)}
            else:
                results[param_name] = {'column': None, 'score': best_score, 'unit': 'Unknown'}
        self.detected_params = results
        return results

    @staticmethod
    def _detect_unit(column_name):
        col_lower = column_name.lower()
        if any(x in col_lower for x in ['lbs/ton', 'lbs per ton', 'lb/ton', 'polymer', 'poly']):
            if 'gal' in col_lower or 'gpd' in col_lower:
                return 'GPD'
            return 'lbs/ton'
        if any(x in col_lower for x in ['%', 'percent', 'solids', 'cake', 'ts', 'tss', 'moisture']):
            return '%'
        if any(x in col_lower for x in ['ntu', 'turbidity']):
            return 'NTU'
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
        if any(x in col_lower for x in ['mg/l', 'concentration', 'conc']):
            return 'mg/L'
        if any(x in col_lower for x in ['rpm', 'speed', 'bowl']):
            return 'RPM'
        if any(x in col_lower for x in ['torque', 'nm', 'ft-lb']):
            return 'Nm'
        if any(x in col_lower for x in ['cost', 'price', '$', 'dollar']):
            return '$'
        if any(x in col_lower for x in ['pressure', 'psi', 'bar']):
            return 'PSI'
        return 'Unknown'


# ============================================================
# CORRELATION ANALYZER
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
        v1, v2 = var1.lower(), var2.lower()
        if ('polymer' in v1 or 'poly' in v1) and ('cake' in v2 or 'solids' in v2):
            if corr_val < -0.5:
                return "✅ Expected: More polymer → Better cake quality"
            if corr_val > 0.5:
                return "⚠️ Unexpected: More polymer → Worse cake quality (investigate)"
        if ('cake' in v1 or 'solids' in v1) and 'truck' in v2:
            if corr_val < -0.5:
                return "✅ Expected: Better cake → Fewer trucks needed"
            if corr_val > 0.5:
                return "⚠️ Unexpected: Better cake → More trucks (investigate)"
        if ('polymer' in v1 or 'poly' in v1) and 'truck' in v2:
            if corr_val > 0.5:
                return "✅ Expected: More polymer → Better dewatering → Fewer trucks"
            if corr_val < -0.5:
                return "⚠️ Unexpected: More polymer → More trucks (investigate)"
        if 'underflow' in v1 and 'overflow' in v2:
            if corr_val < -0.5:
                return "✅ Expected: Better underflow → Better overflow clarity"
            if corr_val > 0.5:
                return "⚠️ Unexpected: Better underflow → Worse overflow (investigate)"
        if 'feed' in v1 and 'underflow' in v2:
            if corr_val < -0.5:
                return "✅ Expected: Higher feed → Lower underflow concentration"
            if corr_val > 0.5:
                return "⚠️ Unexpected: Higher feed → Higher underflow (investigate)"
        if corr_val > 0.7:
            return "Strong positive relationship - variables move together"
        if corr_val < -0.7:
            return "Strong negative relationship - variables move in opposite directions"
        return "Moderate relationship - investigate further"

    def create_correlation_heatmap(self):
        corr_matrix = self.calculate_correlations()
        if corr_matrix is None:
            return None
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values, x=corr_matrix.columns, y=corr_matrix.columns,
            colorscale='RdBu', zmid=0, text=np.round(corr_matrix.values, 2),
            texttemplate='%{text:.2f}', textfont={"size": 10}, colorbar=dict(title="Correlation"),
        ))
        fig.update_layout(title="Correlation Matrix - All Detected Parameters", height=600, xaxis_title="Parameters", yaxis_title="Parameters")
        return fig

    def create_scatter_plot(self, var1_col, var2_col):
        var1_data = pd.to_numeric(self.df[var1_col], errors='coerce').dropna()
        var2_data = pd.to_numeric(self.df[var2_col], errors='coerce')
        var2_data = var2_data[var1_data.index]
        corr = var1_data.corr(var2_data)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=var1_data, y=var2_data, mode='markers', marker=dict(size=8, color='blue', opacity=0.6), name='Data Points'))
        if len(var1_data) > 1:
            z = np.polyfit(var1_data, var2_data, 1)
            p = np.poly1d(z)
            x_trend = np.linspace(var1_data.min(), var1_data.max(), 100)
            fig.add_trace(go.Scatter(x=x_trend, y=p(x_trend), mode='lines', name='Trend Line', line=dict(color='red', width=2)))
        fig.update_layout(title=f"{var1_col} vs {var2_col}<br>Correlation: {corr:.3f}", xaxis_title=var1_col, yaxis_title=var2_col, height=500, hovermode='closest')
        return fig


# ============================================================
# KPI CALCULATOR
# ============================================================
class KPICalculator:
    """Computes meaningful KPIs from whatever parameters were detected in the data."""

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

    def calculate_dewatering_kpis(self):
        k = {}
        dew_equip = [e.lower() for e in self.plant_info.get('dewatering_equipment', [])]
        is_centrifuge = any('centrifuge' in e for e in dew_equip)
        is_belt = any('belt' in e for e in dew_equip)

        cake = self._col('cake_quality')
        if cake is not None:
            v = cake.mean()
            if is_centrifuge and not is_belt:
                lo, hi = 20, 30
            elif is_belt and not is_centrifuge:
                lo, hi = 18, 25
            else:
                lo, hi = 18, 30
            k['cake_solids'] = {'value': v, 'unit': '%', 'target': f'{lo}-{hi}%', 'status': self._status_range(v, lo, hi)}
            moisture = 100 - v
            k['cake_moisture'] = {'value': moisture, 'unit': '%', 'target': '75-82%', 'status': self._status_range(moisture, 75, 82)}
        else:
            k['cake_solids'] = self._insufficient(['Cake solids / cake quality (%) column'])
            k['cake_moisture'] = self._insufficient(['Cake solids / cake quality (%) column'])

        poly = self._col('polymer')
        dry = self._col('dry_tons')
        if poly is not None:
            v = poly.mean()
            k['polymer_consumption'] = {'value': v, 'unit': 'lbs/ton', 'target': '5-15 lbs/ton DS', 'status': self._status_range(v, 5, 15)}
        else:
            k['polymer_consumption'] = self._insufficient(['Polymer dose (lbs/ton) column'])

        if dry is not None:
            throughput = dry.mean() * 2000
            k['dewatering_throughput'] = {'value': throughput, 'unit': 'lbs DS/day', 'target': 'Varies by equipment', 'status': 'ℹ️ Informational'}
            cake_rate = throughput / 24
            k['cake_production_rate'] = {'value': cake_rate, 'unit': 'lbs/hour', 'target': '500-2,000 lbs/hour', 'status': self._status_range(cake_rate, 500, 2000)}
        else:
            k['dewatering_throughput'] = self._insufficient(['Dry tons / dry solids column'])
            k['cake_production_rate'] = self._insufficient(['Dry tons / dry solids column'])

        filt_turb = self._col('filtrate_turbidity')
        if filt_turb is not None:
            v = filt_turb.mean()
            k['filtrate_turbidity'] = {'value': v, 'unit': 'NTU', 'target': '<10 NTU', 'status': self._status_upper(v, 10)}
        else:
            k['filtrate_turbidity'] = self._insufficient(['Filtrate/centrate turbidity (NTU) column'])

        feed_solids = self._col('feed_solids')
        if dry is not None and feed_solids is not None and feed_solids.mean() > 0:
            recovery = min((dry.mean() / feed_solids.mean()) * 100, 100)
            k['solids_recovery'] = {'value': recovery, 'unit': '%', 'target': '>95%', 'status': self._status_lower(recovery, 95)}
        else:
            k['solids_recovery'] = self._insufficient(['Influent/feed solids loading (tons or lbs DS) column - not detected in your data'])

        filt_flow = self._col('filtrate_flow')
        if filt_flow is not None:
            v = filt_flow.mean()
            k['filtrate_flow_rate'] = {'value': v, 'unit': 'gpm', 'target': 'Varies by equipment', 'status': 'ℹ️ Informational'}
        else:
            k['filtrate_flow_rate'] = self._insufficient(['Filtrate/centrate flow rate (gpm) column'])

        cost_col = self.dp.get('polymer_cost', {}).get('column')
        dry_col = self.dp.get('dry_tons', {}).get('column')
        if cost_col and dry_col:
            cost_series = pd.to_numeric(self.df[cost_col], errors='coerce')
            dry_series = pd.to_numeric(self.df[dry_col], errors='coerce')
            ratio = (cost_series / (dry_series * 2000)).replace([np.inf, -np.inf], np.nan).dropna()
            if len(ratio) > 0:
                v = ratio.mean()
                k['polymer_cost_per_lb'] = {'value': v, 'unit': '$/lb DS', 'target': '$0.05-$0.15/lb DS', 'status': self._status_range(v, 0.05, 0.15)}
            else:
                k['polymer_cost_per_lb'] = self._insufficient(['Polymer cost ($) and dry tons columns (valid paired data)'])
        else:
            k['polymer_cost_per_lb'] = self._insufficient(['Polymer cost ($) column'])

        hrs_keys = ['centrifuge_1_hours', 'centrifuge_2_hours', 'centrifuge_3_hours', 'bfp_hours', 'rotary_press_hours', 'dewatering_run_hours']
        vals = []
        for hkey in hrs_keys:
            d = self._col(hkey)
            if d is not None:
                vals.append((d / 24 * 100).clip(upper=100).mean())
        if vals:
            v = float(np.mean(vals))
            k['equipment_availability'] = {'value': v, 'unit': '%', 'target': '>90%', 'status': self._status_lower(v, 90)}
        else:
            k['equipment_availability'] = self._insufficient(['Equipment run-hours column(s), e.g. daily centrifuge/BFP run hours'])

        return k

    def calculate_thickening_kpis(self):
        k = {}
        thick_equip = [e.lower() for e in self.plant_info.get('thickening_equipment', [])]
        is_daf = any('daf' in e or 'flotation' in e for e in thick_equip)

        uf = self._col('thickener_underflow')
        gbt_uf = self._col('gbt_underflow')
        primary_uf = uf if uf is not None else gbt_uf
        if primary_uf is not None:
            v = primary_uf.mean()
            lo, hi = (6, 12) if is_daf else (4, 8)
            k['thickened_solids'] = {'value': v, 'unit': '%', 'target': f'{lo}-{hi}%', 'status': self._status_range(v, lo, hi)}
            lbs_gal = v * 8.34 / 100
            k['underflow_lbs_gal'] = {'value': lbs_gal, 'unit': 'lbs DS/gal', 'target': 'Higher = less downstream load', 'status': 'ℹ️ Informational'}
        else:
            k['thickened_solids'] = self._insufficient(['Thickener/GBT underflow solids (%) column'])
            k['underflow_lbs_gal'] = self._insufficient(['Thickener/GBT underflow solids (%) column'])

        of = self._col('thickener_overflow')
        gbt_of = self._col('gbt_overflow')
        primary_of = of if of is not None else gbt_of
        if primary_of is not None:
            v = primary_of.mean()
            k['overflow_turbidity'] = {'value': v, 'unit': 'mg/L TSS', 'target': '<500 mg/L TSS', 'status': self._status_upper(v, 500)}
        else:
            k['overflow_turbidity'] = self._insufficient(['Thickener/GBT overflow TSS or turbidity column'])

        feed = self._col('thickener_feed')
        if feed is None:
            feed = self._col('gbt_feed')

        if feed is not None and primary_uf is not None:
            throughput = feed.mean() * 1440 * 8.34 * (primary_uf.mean() / 100)
            k['thickening_throughput'] = {'value': throughput, 'unit': 'lbs DS/day', 'target': 'Varies by equipment', 'status': 'ℹ️ Informational (estimated)'}
            underflow_rate = throughput / 24
            k['underflow_production_rate'] = {'value': underflow_rate, 'unit': 'lbs/hour', 'target': '200-1,000 lbs/hour', 'status': self._status_range(underflow_rate, 200, 1000)}
        else:
            k['thickening_throughput'] = self._insufficient(['Thickener/GBT feed flow (gpm) column together with underflow % column'])
            k['underflow_production_rate'] = self._insufficient(['Thickener/GBT feed flow (gpm) column together with underflow % column'])

        k['solids_capture_efficiency'] = self._insufficient(['Full mass-balance data: feed solids concentration (%), feed flow, and overflow TSS'])
        k['overflow_flow_rate'] = self._insufficient(['Overflow flow rate (gpm) column - not currently tracked in your data'])

        area = self.plant_info.get('thickener_area')
        if area and feed is not None and primary_uf is not None:
            throughput = feed.mean() * 1440 * 8.34 * (primary_uf.mean() / 100)
            loading = throughput / area
            k['solids_loading_rate'] = {'value': loading, 'unit': 'lbs DS/day/sq ft', 'target': '0.5-2.0 lbs/day/sq ft', 'status': self._status_range(loading, 0.5, 2.0)}
        else:
            k['solids_loading_rate'] = self._insufficient(['Thickener surface area (enter in Plant Information) plus feed flow & underflow % data'])

        poly2 = self._col('gbt_polymer')
        if poly2 is not None:
            v = poly2.mean()
            k['air_polymer_consumption'] = {'value': v, 'unit': 'lbs/ton DS', 'target': '3-8 lbs/ton DS', 'status': self._status_range(v, 3, 8)}
        else:
            k['air_polymer_consumption'] = self._insufficient(['Thickening polymer/air dose (lbs/ton) column'])

        th_hrs = self._col('thickening_run_hours')
        if th_hrs is not None:
            v = (th_hrs / 24 * 100).clip(upper=100).mean()
            k['thickening_equipment_availability'] = {'value': v, 'unit': '%', 'target': '>92%', 'status': self._status_lower(v, 92)}
        else:
            k['thickening_equipment_availability'] = self._insufficient(['Thickening equipment run-hours column'])

        return k


# ============================================================
# PERFORMANCE ANALYZER (AI RECOMMENDATIONS)
# ============================================================
class PerformanceAnalyzer:
    def __init__(self, df, detected_params, plant_info=None):
        self.df = df
        self.detected_params = detected_params
        self.plant_info = plant_info or {}

    @staticmethod
    def _estimate_savings(key, val):
        value = val['value']
        if key == 'polymer_consumption':
            annual_cost = value * 50 * 365
            target_cost = 12 * 50 * 365
            savings = max(annual_cost - target_cost, 0)
            return (f"${savings:,.0f}/year*",
                    f"*Estimated at an assumed $50/lb polymer price (replace with your actual pricing). "
                    f"Reducing dose from {value:.1f} to 12 lbs/ton DS saves roughly ${savings:,.0f}/year.")
        if key == 'cake_solids':
            if value < 20:
                current_trucks, target_trucks = 100, 60
                savings = (current_trucks - target_trucks) * 500 * 365
                return (f"${savings:,.0f}/year*",
                        f"*Illustrative estimate assuming ~{current_trucks} trucks/day at current cake quality vs "
                        f"~{target_trucks} trucks/day at 25% cake solids, at $500/haul. Replace with your actual "
                        f"hauling contract rates and truck counts for an accurate figure.")
            return ("Reduced hauling costs", "Improving cake solids further reduces cake volume and hauling frequency.")
        return ("Improves process efficiency", "Specific dollar savings require site-specific cost data (hauling rates, energy costs, chemical pricing) not available from the uploaded dataset.")

    def generate_recommendations(self, dew_kpis, thick_kpis):
        combined = [(k, v, DEWATERING_KPI_DEFINITIONS.get(k, {})) for k, v in dew_kpis.items()]
        combined += [(k, v, THICKENING_KPI_DEFINITIONS.get(k, {})) for k, v in thick_kpis.items()]

        recs = []
        good_items = []

        for key, val, defn in combined:
            if val.get('insufficient'):
                continue
            status = val.get('status', '')
            if 'On Target' in status or 'Informational' in status:
                good_items.append((key, defn.get('name', key), val))
                continue

            template = RECOMMENDATION_TEMPLATES.get(key, {})
            priority = PRIORITY_MAP.get(key, '🟡 MEDIUM')
            savings, savings_note = self._estimate_savings(key, val)

            recs.append({
                'priority': priority,
                'category': defn.get('name', key.replace('_', ' ').title()),
                'metric': defn.get('name', key),
                'current_value': f"{val['value']:.2f} {val['unit']}",
                'target_value': val.get('target', 'N/A'),
                'issue': template.get('issue', f"{defn.get('name', key)} is outside the target range."),
                'root_causes': template.get('root_causes', ['Process or equipment parameters may need adjustment', 'Sludge/feed characteristics may have changed']),
                'actions': template.get('actions', ['Review recent operational data', 'Consult a process engineer for optimization']),
                'potential_savings': savings,
                'savings_explanation': savings_note,
                'additional_data_needed': template.get('additional_data', ['Continue routine monitoring']),
                'timeline': template.get('timeline', '2-4 weeks'),
                'risk': template.get('risk', 'Low - monitor closely'),
            })

        if not recs:
            recs.append({
                'priority': '✅ OPTIMAL', 'category': 'Overall Performance', 'metric': 'N/A',
                'current_value': 'N/A', 'target_value': 'N/A',
                'issue': 'All computable KPIs are at or near target - plant is operating at optimal performance levels.',
                'root_causes': [], 'actions': ['Continue current operations', 'Maintain preventive maintenance schedule'],
                'potential_savings': 'Maintain current efficiency',
                'savings_explanation': 'Plant is performing well across all KPIs that could be computed from your data.',
                'additional_data_needed': ['Continue routine monitoring'], 'timeline': 'Ongoing', 'risk': 'Low',
            })

        return recs, good_items


# ============================================================
# CHART RENDERER
# ============================================================
class ChartRenderer:
    def __init__(self, df):
        self.df = df

    def render_line_with_ma(self, column, unit, title, threshold_excellent=None, threshold_good=None):
        col_data = pd.to_numeric(self.df[column], errors='coerce')
        col_ma = col_data.rolling(window=7).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self.df.index, y=col_data, mode='markers', name='Daily', marker=dict(size=4, color='lightblue', opacity=0.6)))
        fig.add_trace(go.Scatter(x=self.df.index, y=col_ma, mode='lines', name='7-day MA', line=dict(color='darkblue', width=2)))
        if threshold_excellent is not None:
            fig.add_hline(y=threshold_excellent, line_dash="dash", line_color="green", annotation_text="Excellent")
        if threshold_good is not None:
            fig.add_hline(y=threshold_good, line_dash="dash", line_color="orange", annotation_text="Good")
        fig.update_layout(title=f"{title} ({unit})", height=400, hovermode='x unified', xaxis_title="Days", yaxis_title=unit)
        return fig

    def render_bar_with_ma(self, column, unit, title):
        col_data = pd.to_numeric(self.df[column], errors='coerce')
        col_ma = col_data.rolling(window=7).mean()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=self.df.index, y=col_data, name='Daily', marker=dict(color='#4169E1', opacity=0.7)))
        fig.add_trace(go.Scatter(x=self.df.index, y=col_ma, mode='lines', name='7-day MA', line=dict(color='darkblue', width=2)))
        fig.update_layout(title=f"{title} ({unit})", height=400, hovermode='x unified', xaxis_title="Days", yaxis_title=unit)
        return fig

    def render_ratio(self, column1, column2, unit, title, threshold_excellent=None, threshold_good=None):
        col1_data = pd.to_numeric(self.df[column1], errors='coerce')
        col2_data = pd.to_numeric(self.df[column2], errors='coerce')
        ratio_data = (col1_data / col2_data).replace([np.inf, -np.inf], np.nan)
        ratio_ma = ratio_data.rolling(window=7).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self.df.index, y=ratio_data, mode='markers', name='Daily', marker=dict(size=4, color='teal', opacity=0.6)))
        fig.add_trace(go.Scatter(x=self.df.index, y=ratio_ma, mode='lines', name='7-day MA', line=dict(color='darkslategray', width=2)))
        if threshold_excellent is not None:
            fig.add_hline(y=threshold_excellent, line_dash="dash", line_color="green", annotation_text="Excellent")
        if threshold_good is not None:
            fig.add_hline(y=threshold_good, line_dash="dash", line_color="orange", annotation_text="Good")
        fig.update_layout(title=f"{title} ({unit})", height=400, hovermode='x unified', xaxis_title="Days", yaxis_title=unit)
        return fig


def render_kpi_grid(kpis, definitions, per_row=5):
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
                    st.write(val.get('status', ''))


# ============================================================
# SIDEBAR - FILE UPLOAD
# ============================================================
st.sidebar.header("📊 Upload Your Data")
uploaded_file = st.sidebar.file_uploader("Choose your WWTP CSV file", type=['csv'], help="Upload a CSV file with your WWTP data")

# ============================================================
# MAIN APP LOGIC
# ============================================================
if uploaded_file is None:
    st.info("👈 **Please upload a CSV file to get started**")
    st.markdown("""
    ### 📋 Expected Data Format

    Your CSV should contain columns like:

    **Dewatering:** Centrifuge / BFP / Rotary Press, Active Polymer (lbs/ton), Cake Solids (%), Equipment Run Hours,
    Dry Tons, Wet Tons, Daily Trucks, Filtrate Turbidity/Flow, Polymer Cost

    **Thickening:** Gravity Thickener / GBT / DAF, Feed Rate (GPM), Underflow TS (%), Overflow TSS/Turbidity,
    Thickening Polymer, Equipment Run Hours

    **Flow:** Influent Flow (MGD), Effluent Flow (MGD)

    ### ✨ Features
    - 🔍 Fuzzy Logic auto-detects your columns
    - 📊 AI-derived KPI dashboard (only shows what can be computed from your data)
    - 💡 AI recommendations with root causes, actions, and savings estimates
    - 📈 Trend, custom-period, and side-by-side benchmark comparison
    - 🔗 Correlation analysis between parameters
    - 🔎 Data quality / outlier detection

    ### 🚀 Ready? Upload your file!
    """)
else:
    try:
        df = pd.read_csv(uploaded_file)
        df = df.reset_index(drop=True)

        date_col = None
        for col in df.columns:
            if any(x in col.lower() for x in ['date', 'time', 'day', 'month', 'year']):
                try:
                    converted = pd.to_datetime(df[col], errors='coerce')
                    if converted.notna().sum() > len(df) * 0.5:
                        df[col] = converted
                        date_col = col
                        df = df.sort_values(col).reset_index(drop=True)
                        break
                except Exception:
                    pass

        if not date_col:
            df['Date'] = pd.date_range(start='2023-01-01', periods=len(df), freq='D')
            date_col = 'Date'

        st.sidebar.success(f"✅ Loaded {len(df)} records")
        st.sidebar.write(f"📅 {df[date_col].min().date()} to {df[date_col].max().date()}")

    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()

    # ------------------------------------------------------
    # PLANT INFORMATION
    # ------------------------------------------------------
    with st.sidebar.expander("🏭 Plant Information", expanded=False):
        plant_name = st.text_input("Plant Name", value="WWTP")
        plant_location = st.text_input("Location", value="")

        st.write("**Dewatering Equipment:**")
        dewatering_equipment = st.multiselect(
            "Select equipment types", ["Centrifuge", "Belt Filter Press (BFP)", "Rotary Press", "Drying Bed", "Other"],
            default=["Centrifuge"],
        )

        st.write("**Thickening Equipment:**")
        thickening_equipment = st.multiselect(
            "Select equipment types", ["Gravity Thickener", "GBT (Gravity Belt Thickener)", "Rotary Drum", "DAF (Dissolved Air Flotation)", "Membrane", "Other"],
            default=["GBT (Gravity Belt Thickener)"],
        )

        plant_capacity = st.number_input("Plant Capacity (MGD)", value=10.0, min_value=0.1)
        thickener_area_input = st.number_input(
            "Thickener Surface Area (sq ft) - optional, enables Solids Loading Rate KPI",
            value=0.0, min_value=0.0,
        )

        plant_info = {
            'name': plant_name, 'location': plant_location,
            'dewatering_equipment': dewatering_equipment, 'thickening_equipment': thickening_equipment,
            'capacity': plant_capacity, 'thickener_area': thickener_area_input if thickener_area_input > 0 else None,
        }

    # ------------------------------------------------------
    # PARAMETER DETECTION
    # ------------------------------------------------------
    parameter_keywords = {
        'polymer': ['active polymer', 'polymer dose', 'poly dose', 'lbs per ton', 'lbs/ton', 'polymer lbs', 'poly lbs', 'polymer consumption', 'dewatering polymer'],
        'cake_quality': ['cake solids', 'cake percent', 'cake quality', 'percent solids cake', 'dewatered solids', 'cake ts', 'cake dry solids', 'cake avg'],
        'centrifuge_1_hours': ['centrifuge 1 hours', 'c1 run hours', 'centrifuge 1 runtime'],
        'centrifuge_2_hours': ['centrifuge 2 hours', 'c2 run hours', 'centrifuge 2 runtime'],
        'centrifuge_3_hours': ['centrifuge 3 hours', 'c3 run hours', 'centrifuge 3 runtime'],
        'bfp_hours': ['bfp hours', 'belt filter press hours', 'belt press run hours'],
        'rotary_press_hours': ['rotary press hours', 'rotary press runtime'],
        'dry_tons': ['dry tons', 'dry ton', 'dry solids tons', 'dry solids produced', 'tons dry solids'],
        'wet_tons': ['wet tons', 'wet ton', 'wet cake tons', 'cake wet tons'],
        'trucks': ['sludge trucks', 'daily trucks', 'truck count', 'number of trucks', 'haul trucks'],
        'influent_flow': ['influent flow', 'plant influent', 'inflow mgd', 'influent mgd'],
        'effluent_flow': ['effluent flow', 'plant effluent', 'outflow mgd', 'effluent mgd'],
        'filtrate_turbidity': ['filtrate turbidity', 'centrate turbidity', 'filtrate ntu', 'centrate ntu', 'dewatering filtrate quality'],
        'filtrate_flow': ['filtrate flow', 'centrate flow', 'filtrate gpm', 'centrate gpm', 'return flow dewatering'],
        'feed_solids': ['feed solids', 'influent solids concentration', 'feed ts', 'raw sludge solids'],
        'thickener_feed': ['thickener feed', 'gravity thickener feed', 'thickener inlet flow', 'feed rate gpm'],
        'thickener_underflow': ['thickener underflow', 'gravity thickener underflow', 'underflow ts', 'underflow solids', 'thickener underflow solids'],
        'thickener_overflow': ['thickener overflow', 'gravity thickener overflow', 'overflow tss', 'overflow turbidity', 'thickener overflow tss'],
        'thickener_torque': ['thickener torque', 'rake torque', 'thickener rake torque'],
        'gbt_feed': ['gbt feed', 'gravity belt thickener feed', 'belt thickener feed rate'],
        'gbt_underflow': ['gbt underflow', 'gravity belt thickener underflow', 'belt thickener underflow solids'],
        'gbt_overflow': ['gbt overflow', 'gravity belt thickener overflow', 'belt thickener overflow tss'],
        'gbt_belt_speed': ['gbt belt speed', 'gravity belt speed', 'belt thickener speed'],
        'gbt_polymer': ['gbt polymer', 'gravity belt polymer dose', 'belt thickener polymer', 'daf polymer', 'thickening polymer'],
        'bowl_speed': ['bowl speed rpm', 'centrifuge bowl speed', 'centrifuge rpm'],
        'polymer_cost': ['polymer cost', 'polymer price', 'polymer dollar cost', 'chemical cost polymer'],
        'hauling_cost': ['hauling cost', 'truck hauling cost', 'disposal hauling cost'],
        'dewatering_run_hours': ['dewatering run hours', 'dewatering equipment hours', 'dewatering uptime hours'],
        'thickening_run_hours': ['thickening run hours', 'thickener uptime hours', 'gbt run hours'],
    }

    detector = FuzzyParameterDetector(df.columns)
    detected_params = detector.find_parameters(parameter_keywords, threshold=55)

    st.sidebar.subheader("🔍 Detected Parameters")
    detected_count = 0
    for param_name, param_info in detected_params.items():
        if param_info['column']:
            st.sidebar.write(f"✅ {param_name}: **{param_info['column']}** ({param_info['unit']})")
            detected_count += 1
    st.sidebar.write(f"\n**Found: {detected_count}/{len(parameter_keywords)} parameters**")

    analyzer = PerformanceAnalyzer(df, detected_params, plant_info)
    kpi_calculator = KPICalculator(df, detected_params, plant_info)
    correlation_analyzer = CorrelationAnalyzer(df, detected_params)
    chart_renderer = ChartRenderer(df)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📊 Dashboard", "💡 AI Recommendations", "📈 Trend / Benchmark", "🔗 Correlation Analysis",
        "🔄 Dewatering", "🌀 Thickening", "🔍 Data Quality", "📋 Parameters", "📥 Raw Data",
    ])

    # ============================================================
    # TAB 1: DASHBOARD
    # ============================================================
    with tab1:
        st.header(f"📊 Performance Dashboard - {plant_info.get('name', 'WWTP')}")
        if plant_info.get('location'):
            st.caption(f"📍 {plant_info['location']} | Capacity: {plant_info.get('capacity', 'N/A')} MGD")

        dew_kpis = kpi_calculator.calculate_dewatering_kpis()
        thick_kpis = kpi_calculator.calculate_thickening_kpis()

        st.subheader("🔄 Dewatering KPIs")
        render_kpi_grid(dew_kpis, DEWATERING_KPI_DEFINITIONS)

        st.divider()

        st.subheader("🌀 Thickening KPIs")
        render_kpi_grid(thick_kpis, THICKENING_KPI_DEFINITIONS)

        st.divider()

        st.subheader("💧 Flow Data")
        flow_col1, flow_col2 = st.columns(2)
        if detected_params.get('influent_flow', {}).get('column'):
            inf_col = detected_params['influent_flow']['column']
            inf_unit = detected_params['influent_flow']['unit']
            inf_data = pd.to_numeric(df[inf_col], errors='coerce').dropna()
            if len(inf_data) > 0:
                with flow_col1:
                    st.metric(f"Influent Flow ({inf_unit})", f"{inf_data.mean():.2f}")
        if detected_params.get('effluent_flow', {}).get('column'):
            eff_col = detected_params['effluent_flow']['column']
            eff_unit = detected_params['effluent_flow']['unit']
            eff_data = pd.to_numeric(df[eff_col], errors='coerce').dropna()
            if len(eff_data) > 0:
                with flow_col2:
                    st.metric(f"Effluent Flow ({eff_unit})", f"{eff_data.mean():.2f}")

    # ============================================================
    # TAB 2: AI RECOMMENDATIONS
    # ============================================================
    with tab2:
        st.header("💡 AI-Powered Recommendations")
        st.write("Generated from the KPIs on the Dashboard tab, using only the parameters detected in your data.")

        dew_kpis = kpi_calculator.calculate_dewatering_kpis()
        thick_kpis = kpi_calculator.calculate_thickening_kpis()
        recommendations, good_items = analyzer.generate_recommendations(dew_kpis, thick_kpis)

        for rec in recommendations:
            with st.container():
                col_h1, col_h2 = st.columns([3, 1])
                with col_h1:
                    st.markdown(f"### {rec['priority']} {rec['category']}")
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

                with st.expander("📋 Additional Data That Would Improve This Analysis"):
                    for item in rec['additional_data_needed']:
                        st.write(f"• {item}")

                st.divider()

        if good_items:
            with st.expander(f"✅ Performing Well ({len(good_items)} metric(s) at or near target)"):
                for key, name, val in good_items:
                    st.write(f"**{name}:** {val['value']:.2f} {val['unit']} — {val.get('status', '')}")

    # ============================================================
    # TAB 3: TREND / BENCHMARK ANALYSIS
    # ============================================================
    with tab3:
        st.header("📈 Trend & Benchmark Analysis")
        st.write("Analyze a single indicator over time, over a custom date range, or benchmark two periods side-by-side.")

        numeric_cols = {}
        for param_info in detected_params.values():
            if param_info['column']:
                numeric_cols[param_info['column']] = param_info['unit']

        if not numeric_cols:
            st.warning("No numeric columns detected")
        else:
            mode = st.radio("Analysis Mode", ["Full Timeline", "Custom Period", "Period Comparison (Benchmark)"], horizontal=True)

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                selected_column = st.selectbox("Select Indicator", list(numeric_cols.keys()), format_func=lambda x: f"{x} ({numeric_cols[x]})")
            with col_s2:
                aggregation = st.selectbox("Aggregation Period", ["Daily", "Weekly", "Monthly", "Quarterly"])

            freq_map = {"Daily": 'D', "Weekly": 'W', "Monthly": 'MS', "Quarterly": 'QS'}

            df_yoy = df[[date_col, selected_column]].copy()
            df_yoy[date_col] = pd.to_datetime(df_yoy[date_col])
            df_yoy[selected_column] = pd.to_numeric(df_yoy[selected_column], errors='coerce')
            df_yoy = df_yoy.dropna()

            if len(df_yoy) == 0:
                st.warning("No valid numeric data for the selected indicator")
            else:
                data_min = df_yoy[date_col].min().date()
                data_max = df_yoy[date_col].max().date()

                def plot_series(df_agg, title):
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df_agg.index, y=df_agg.values, mode='lines+markers', name=selected_column, line=dict(color='#1f77b4', width=2), marker=dict(size=6)))
                    x_numeric = np.arange(len(df_agg))
                    z = None
                    if len(x_numeric) > 1:
                        z = np.polyfit(x_numeric, df_agg.values, 1)
                        p = np.poly1d(z)
                        fig.add_trace(go.Scatter(x=df_agg.index, y=p(x_numeric), mode='lines', name='Trend', line=dict(color='red', width=2, dash='dash')))
                    fig.update_layout(title=title, xaxis_title="Date", yaxis_title=numeric_cols[selected_column], height=500, hovermode='x unified')
                    st.plotly_chart(fig, use_container_width=True)

                    stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)
                    with stat_c1:
                        st.metric("Mean", f"{df_agg.mean():.2f}")
                    with stat_c2:
                        st.metric("Median", f"{df_agg.median():.2f}")
                    with stat_c3:
                        st.metric("Min", f"{df_agg.min():.2f}")
                    with stat_c4:
                        st.metric("Max", f"{df_agg.max():.2f}")

                    if z is not None:
                        direction = "📈 Increasing" if z[0] > 0 else "📉 Decreasing"
                        st.write(f"**Trend:** {direction} (slope: {z[0]:.4f} per {aggregation.lower()[:-2] if aggregation != 'Daily' else 'day'})")

                if mode == "Full Timeline":
                    try:
                        df_agg = df_yoy.set_index(date_col)[selected_column].resample(freq_map[aggregation]).mean().dropna()
                        if len(df_agg) > 0:
                            plot_series(df_agg, f"{selected_column} - {aggregation} Aggregation (Full Timeline)")
                        else:
                            st.warning("No data available after aggregation")
                    except Exception as e:
                        st.error(f"Error processing data: {e}")

                elif mode == "Custom Period":
                    date_range = st.date_input("Select Date Range", value=(data_min, data_max), min_value=data_min, max_value=data_max)
                    if isinstance(date_range, tuple) and len(date_range) == 2:
                        start_d, end_d = date_range
                        mask = (df_yoy[date_col].dt.date >= start_d) & (df_yoy[date_col].dt.date <= end_d)
                        df_period = df_yoy[mask]
                        if len(df_period) == 0:
                            st.warning("No data in the selected range")
                        else:
                            try:
                                df_agg = df_period.set_index(date_col)[selected_column].resample(freq_map[aggregation]).mean().dropna()
                                if len(df_agg) > 0:
                                    plot_series(df_agg, f"{selected_column} - {start_d.strftime('%b %d, %Y')} to {end_d.strftime('%b %d, %Y')}")
                                else:
                                    st.warning("No data available after aggregation for this range")
                            except Exception as e:
                                st.error(f"Error processing data: {e}")
                    else:
                        st.info("👆 Select both a start and end date to continue")

                else:  # Period Comparison (Benchmark)
                    st.write("**Compare two time periods on the same chart** (e.g., Jan–Jun 2025 vs Jan–Jun 2026)")
                    pc1, pc2 = st.columns(2)
                    with pc1:
                        st.markdown("**Period A**")
                        a_range = st.date_input("Period A date range", value=(data_min, data_min), min_value=data_min, max_value=data_max, key="period_a")
                    with pc2:
                        st.markdown("**Period B**")
                        b_range = st.date_input("Period B date range", value=(data_max, data_max), min_value=data_min, max_value=data_max, key="period_b")

                    if isinstance(a_range, tuple) and len(a_range) == 2 and isinstance(b_range, tuple) and len(b_range) == 2:
                        a_start, a_end = a_range
                        b_start, b_end = b_range
                        mask_a = (df_yoy[date_col].dt.date >= a_start) & (df_yoy[date_col].dt.date <= a_end)
                        mask_b = (df_yoy[date_col].dt.date >= b_start) & (df_yoy[date_col].dt.date <= b_end)
                        df_a = df_yoy[mask_a].copy()
                        df_b = df_yoy[mask_b].copy()

                        if len(df_a) == 0 or len(df_b) == 0:
                            st.warning("One or both periods have no data. Adjust the date ranges above.")
                        else:
                            try:
                                agg_a = df_a.set_index(date_col)[selected_column].resample(freq_map[aggregation]).mean().dropna()
                                agg_b = df_b.set_index(date_col)[selected_column].resample(freq_map[aggregation]).mean().dropna()

                                label_a = f"{a_start.strftime('%b %Y')} - {a_end.strftime('%b %Y')}"
                                label_b = f"{b_start.strftime('%b %Y')} - {b_end.strftime('%b %Y')}"

                                x_a = list(range(len(agg_a)))
                                x_b = list(range(len(agg_b)))

                                fig = go.Figure()
                                fig.add_trace(go.Scatter(x=x_a, y=agg_a.values, mode='lines+markers', name=label_a, line=dict(color='#1f77b4', width=3)))
                                fig.add_trace(go.Scatter(x=x_b, y=agg_b.values, mode='lines+markers', name=label_b, line=dict(color='#ff7f0e', width=3)))
                                fig.update_layout(
                                    title=f"Benchmark Comparison: {selected_column}",
                                    xaxis_title=f"{aggregation} Period Offset (0 = start of each period)",
                                    yaxis_title=numeric_cols[selected_column], height=500, hovermode='x unified',
                                )
                                st.plotly_chart(fig, use_container_width=True)

                                st.subheader("📊 Comparison Statistics")
                                stat_df = pd.DataFrame({
                                    'Metric': ['Mean', 'Median', 'Min', 'Max', 'Std Dev'],
                                    label_a: [agg_a.mean(), agg_a.median(), agg_a.min(), agg_a.max(), agg_a.std()],
                                    label_b: [agg_b.mean(), agg_b.median(), agg_b.min(), agg_b.max(), agg_b.std()],
                                })
                                stat_df['% Change (A→B)'] = ((stat_df[label_b] - stat_df[label_a]) / stat_df[label_a] * 100)
                                st.dataframe(stat_df.round(3), use_container_width=True)

                                if agg_a.mean() != 0:
                                    pct_change_mean = (agg_b.mean() - agg_a.mean()) / agg_a.mean() * 100
                                    direction = "increased" if pct_change_mean > 0 else "decreased"
                                    st.info(f"**{selected_column}** {direction} by **{abs(pct_change_mean):.1f}%** from {label_a} to {label_b}")
                            except Exception as e:
                                st.error(f"Error processing comparison: {e}")
                    else:
                        st.info("👆 Select both a start and end date for each period to continue")

    # ============================================================
    # TAB 4: CORRELATION ANALYSIS
    # ============================================================
    with tab4:
        st.header("🔗 Correlation Analysis")
        st.write("Analyze relationships between detected WWTP parameters.")

        corr_matrix = correlation_analyzer.calculate_correlations()

        if corr_matrix is None or len(corr_matrix.columns) < 2:
            st.warning("Not enough numeric parameters detected for correlation analysis. Check the Parameters tab to see what was found.")
        else:
            st.subheader("📊 Correlation Heatmap")
            fig_heatmap = correlation_analyzer.create_correlation_heatmap()
            if fig_heatmap:
                st.plotly_chart(fig_heatmap, use_container_width=True)

            st.divider()
            st.subheader("🔍 Strong Correlations (|r| ≥ 0.7)")
            strong_corrs = correlation_analyzer.find_strong_correlations(threshold=0.7)

            if strong_corrs:
                st.dataframe(pd.DataFrame(strong_corrs), use_container_width=True)
                st.divider()
                st.subheader("📈 Scatter Plots - Strong Correlations")
                for i, corr_pair in enumerate(strong_corrs[:5]):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**{corr_pair['Variable 1']} vs {corr_pair['Variable 2']}**")
                        st.caption(f"Correlation: {corr_pair['Correlation']:.3f}")
                    with c2:
                        st.caption(corr_pair['Interpretation'])
                    fig_scatter = correlation_analyzer.create_scatter_plot(corr_pair['Variable 1'], corr_pair['Variable 2'])
                    st.plotly_chart(fig_scatter, use_container_width=True, key=f"scatter_{i}")
                    st.divider()
            else:
                st.info("No strong correlations found (threshold: |r| ≥ 0.7)")
                st.subheader("📊 Moderate Correlations (0.5 ≤ |r| < 0.7)")
                moderate_corrs = correlation_analyzer.find_strong_correlations(threshold=0.5)
                moderate_corrs = [c for c in moderate_corrs if abs(c['Correlation']) < 0.7]
                if moderate_corrs:
                    st.dataframe(pd.DataFrame(moderate_corrs), use_container_width=True)
                else:
                    st.info("No moderate correlations found")

    # ============================================================
    # TAB 5: DEWATERING
    # ============================================================
    with tab5:
        st.header("🔄 Dewatering Analysis")
        st.write(f"**Equipment:** {', '.join(plant_info.get('dewatering_equipment', ['Not specified']))}")

        if detected_params.get('polymer', {}).get('column'):
            st.subheader("Polymer Efficiency")
            poly_col = detected_params['polymer']['column']
            poly_unit = detected_params['polymer']['unit']
            fig = chart_renderer.render_line_with_ma(poly_col, poly_unit, "Polymer Efficiency", threshold_excellent=12, threshold_good=15)
            st.plotly_chart(fig, use_container_width=True, key="poly_chart")
            render_footnote('polymer', ' lbs/ton')

        if detected_params.get('cake_quality', {}).get('column'):
            st.subheader("Cake Quality")
            cake_col = detected_params['cake_quality']['column']
            cake_unit = detected_params['cake_quality']['unit']
            fig = chart_renderer.render_line_with_ma(cake_col, cake_unit, "Cake Quality", threshold_excellent=25, threshold_good=20)
            st.plotly_chart(fig, use_container_width=True, key="cake_chart")
            render_footnote('cake_quality', '%')

        if detected_params.get('dry_tons', {}).get('column') and detected_params.get('wet_tons', {}).get('column'):
            st.subheader("Dewatering Efficiency (Dry/Wet Ratio)")
            dry_col = detected_params['dry_tons']['column']
            wet_col = detected_params['wet_tons']['column']
            fig = chart_renderer.render_ratio(dry_col, wet_col, "Ratio", "Dry/Wet Ratio", threshold_excellent=0.25, threshold_good=0.20)
            st.plotly_chart(fig, use_container_width=True, key="ratio_chart")
            render_footnote('dry_wet_ratio')

        if detected_params.get('trucks', {}).get('column'):
            st.subheader("Sludge Truck Hauling")
            truck_col = detected_params['trucks']['column']
            truck_unit = detected_params['trucks']['unit']
            fig = chart_renderer.render_bar_with_ma(truck_col, truck_unit, "Daily Sludge Trucks")
            st.plotly_chart(fig, use_container_width=True, key="truck_chart")
            st.caption("ℹ️ No fixed industry benchmark for truck counts - fewer trucks generally indicates better dewatering "
                       "(higher cake solids = less volume to haul). Compare against your own historical baseline.")

    # ============================================================
    # TAB 6: THICKENING
    # ============================================================
    with tab6:
        st.header("🌀 Thickening Analysis")
        st.write(f"**Equipment:** {', '.join(plant_info.get('thickening_equipment', ['Not specified']))}")

        if detected_params.get('thickener_underflow', {}).get('column'):
            st.subheader("Gravity Thickener - Underflow Concentration")
            uf_col = detected_params['thickener_underflow']['column']
            uf_unit = detected_params['thickener_underflow']['unit']
            fig = chart_renderer.render_line_with_ma(uf_col, uf_unit, "Underflow Concentration", threshold_excellent=5, threshold_good=3)
            st.plotly_chart(fig, use_container_width=True, key="thick_uf_chart")
            render_footnote('thickener_underflow', '%')

        if detected_params.get('thickener_overflow', {}).get('column'):
            st.subheader("Gravity Thickener - Overflow Clarity")
            of_col = detected_params['thickener_overflow']['column']
            of_unit = detected_params['thickener_overflow']['unit']
            fig = chart_renderer.render_line_with_ma(of_col, of_unit, "Overflow TSS", threshold_excellent=500, threshold_good=1000)
            st.plotly_chart(fig, use_container_width=True, key="thick_of_chart")
            render_footnote('thickener_overflow', ' mg/L')

        if detected_params.get('gbt_underflow', {}).get('column'):
            st.subheader("GBT - Underflow Concentration")
            gbt_uf_col = detected_params['gbt_underflow']['column']
            gbt_uf_unit = detected_params['gbt_underflow']['unit']
            fig = chart_renderer.render_line_with_ma(gbt_uf_col, gbt_uf_unit, "GBT Underflow Concentration", threshold_excellent=8, threshold_good=5)
            st.plotly_chart(fig, use_container_width=True, key="gbt_uf_chart")
            render_footnote('gbt_underflow', '%')

        if detected_params.get('gbt_overflow', {}).get('column'):
            st.subheader("GBT - Overflow Clarity")
            gbt_of_col = detected_params['gbt_overflow']['column']
            gbt_of_unit = detected_params['gbt_overflow']['unit']
            fig = chart_renderer.render_line_with_ma(gbt_of_col, gbt_of_unit, "GBT Overflow TSS", threshold_excellent=300, threshold_good=500)
            st.plotly_chart(fig, use_container_width=True, key="gbt_of_chart")
            render_footnote('gbt_overflow', ' mg/L')

        if not any(detected_params.get(k, {}).get('column') for k in ['thickener_underflow', 'thickener_overflow', 'gbt_underflow', 'gbt_overflow']):
            st.info("No thickening indicators were detected in your data. Check the **Parameters** tab to see match "
                    "scores, or rename your thickening columns to include words like 'underflow', 'overflow', 'GBT', "
                    "or 'thickener' so they're easier to auto-detect.")

    # ============================================================
    # TAB 7: DATA QUALITY
    # ============================================================
    with tab7:
        st.header("🔍 Data Quality Analysis")
        columns_to_check = [p['column'] for p in detected_params.values() if p['column']]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Records", len(df))
        with c2:
            st.metric("Columns Analyzed", len(columns_to_check))
        with c3:
            total_missing = sum(df[col].isna().sum() for col in columns_to_check if col in df.columns)
            st.metric("Total Missing Values", int(total_missing))

        st.divider()

        for col_name in columns_to_check:
            if col_name in df.columns:
                with st.expander(f"📊 {col_name}"):
                    col_data = pd.to_numeric(df[col_name], errors='coerce')
                    a, b, c = st.columns(3)
                    with a:
                        missing = df[col_name].isna().sum()
                        st.write("**Missing Values:**")
                        st.write(f"Count: {missing}")
                        st.write(f"Percentage: {(missing / len(df) * 100):.2f}%")
                    with b:
                        st.write("**Data Range:**")
                        if col_data.notna().any():
                            st.write(f"Min: {col_data.min():.2f}")
                            st.write(f"Max: {col_data.max():.2f}")
                            st.write(f"Mean: {col_data.mean():.2f}")
                        else:
                            st.write("No numeric data")
                    with c:
                        st.write("**Outliers (IQR):**")
                        clean = col_data.dropna()
                        if len(clean) > 0:
                            Q1, Q3 = clean.quantile(0.25), clean.quantile(0.75)
                            IQR = Q3 - Q1
                            outliers = clean[(clean < Q1 - 1.5 * IQR) | (clean > Q3 + 1.5 * IQR)]
                            st.write(f"Count: {len(outliers)}")
                            st.write(f"Percentage: {(len(outliers) / len(clean) * 100):.2f}%")
                        else:
                            st.write("No numeric data")

    # ============================================================
    # TAB 8: PARAMETERS
    # ============================================================
    with tab8:
        st.header("📋 Detected Parameters & Units")
        param_data = []
        for param_name, param_info in detected_params.items():
            param_data.append({
                'Parameter': param_name,
                'Column': param_info['column'] if param_info['column'] else '— not detected —',
                'Unit': param_info['unit'],
                'Match Score': f"{param_info['score']:.0f}%",
            })
        param_df = pd.DataFrame(param_data)
        st.dataframe(param_df, use_container_width=True)
        csv = param_df.to_csv(index=False)
        st.download_button("📥 Download Parameters", data=csv, file_name="parameters.csv", mime="text/csv")

    # ============================================================
    # TAB 9: RAW DATA
    # ============================================================
    with tab9:
        st.header("📥 Raw Data")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Data", data=csv, file_name="wwtp_data.csv", mime="text/csv")

st.success("✅ App loaded successfully!")
