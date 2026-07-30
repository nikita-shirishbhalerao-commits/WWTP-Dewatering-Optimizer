import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fuzzywuzzy import fuzz, process
from scipy import stats
from io import BytesIO
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

st.title("🌊 Complete WWTP Dewatering & Thickening Performance Analyzer")
st.markdown("**AI-Powered Analysis with Fuzzy Parameter Detection & Unit Tracking**")

# ============================================================
# FUZZY PARAMETER DETECTOR CLASS
# ============================================================
class FuzzyParameterDetector:
    """Intelligently detects WWTP parameters using fuzzy matching"""
    
    def __init__(self, columns):
        self.columns = columns
        self.column_lower = [col.lower() for col in columns]
        self.detected_params = {}
    
    def find_parameters(self, keyword_groups, threshold=65):
        """Find parameters with fuzzy matching and unit detection"""
        results = {}
        
        for param_name, keywords in keyword_groups.items():
            search_string = ' '.join(keywords).lower()
            matches = process.extract(
                search_string,
                self.column_lower,
                limit=5,
                scorer=fuzz.token_set_ratio
            )
            
            best_match = None
            best_score = 0
            
            for match, score in matches:
                if score >= threshold:
                    idx = self.column_lower.index(match)
                    if score > best_score:
                        best_score = score
                        best_match = self.columns[idx]
            
            if best_match:
                results[param_name] = {
                    'column': best_match,
                    'score': best_score,
                    'unit': self._detect_unit(best_match)
                }
            else:
                results[param_name] = {
                    'column': None,
                    'score': 0,
                    'unit': 'Unknown'
                }
        
        self.detected_params = results
        return results
    
    def _detect_unit(self, column_name):
        """Detect unit from column name"""
        col_lower = column_name.lower()
        
        # Polymer units
        if any(x in col_lower for x in ['lbs/ton', 'lbs per ton', 'lb/ton', 'polymer', 'poly']):
            if 'gal' in col_lower or 'gpd' in col_lower:
                return 'GPD'
            return 'lbs/ton'
        
        # Percentage units
        if any(x in col_lower for x in ['%', 'percent', 'solids', 'cake', 'ts', 'tss', 'moisture']):
            return '%'
        
        # Flow units
        if any(x in col_lower for x in ['flow', 'gpm', 'mgd', 'gpd', 'rate']):
            if 'mgd' in col_lower:
                return 'MGD'
            elif 'gpm' in col_lower:
                return 'GPM'
            elif 'gpd' in col_lower:
                return 'GPD'
            return 'MGD'
        
        # Weight units
        if any(x in col_lower for x in ['ton', 'dry', 'wet', 'weight', 'mass']):
            if 'dry' in col_lower:
                return 'Dry Tons'
            elif 'wet' in col_lower:
                return 'Wet Tons'
            return 'Tons'
        
        # Count units
        if any(x in col_lower for x in ['truck', 'count', 'number', 'qty']):
            return 'Count'
        
        # Hours/Time units
        if any(x in col_lower for x in ['hour', 'runtime', 'time', 'hrs']):
            return 'Hours'
        
        # Concentration units
        if any(x in col_lower for x in ['mg/l', 'mg/l', 'concentration', 'conc']):
            return 'mg/L'
        
        # RPM units
        if any(x in col_lower for x in ['rpm', 'speed', 'bowl']):
            return 'RPM'
        
        # Torque units
        if any(x in col_lower for x in ['torque', 'nm', 'ft-lb']):
            return 'Nm'
        
        # Cost units
        if any(x in col_lower for x in ['cost', 'price', '$', 'dollar']):
            return '$'
        
        # Pressure units
        if any(x in col_lower for x in ['pressure', 'psi', 'bar']):
            return 'PSI'
        
        return 'Unknown'
    
    def get_detected_params(self):
        """Return all detected parameters"""
        return self.detected_params

# ============================================================
# COMPREHENSIVE CHART GENERATOR
# ============================================================
class ComprehensiveChartGenerator:
    """Generates 25+ charts for complete WWTP analysis"""
    
    def __init__(self, df, detected_params):
        self.df = df
        self.detected_params = detected_params
        self.charts = []
        self.chart_counter = 0
    
    def _get_unique_id(self):
        """Generate unique chart ID"""
        self.chart_counter += 1
        return self.chart_counter
    
    def generate_all_charts(self):
        """Generate all available charts based on detected parameters"""
        
        # DEWATERING CHARTS
        self._add_polymer_efficiency_chart()
        self._add_polymer_trend_chart()
        self._add_cake_quality_chart()
        self._add_cake_trend_chart()
        self._add_centrifuge_hours_chart()
        self._add_equipment_utilization_chart()
        self._add_dry_tons_chart()
        self._add_wet_tons_chart()
        self._add_dry_wet_ratio_chart()
        self._add_truck_hauling_chart()
        self._add_polymer_vs_cake_chart()
        self._add_polymer_vs_trucks_chart()
        self._add_cake_vs_trucks_chart()
        
        # THICKENING CHARTS
        self._add_thickener_feed_chart()
        self._add_thickener_underflow_chart()
        self._add_thickener_overflow_chart()
        self._add_thickener_concentration_chart()
        self._add_thickener_torque_chart()
        
        # GBT (GRAVITY BELT THICKENER) CHARTS
        self._add_gbt_feed_chart()
        self._add_gbt_underflow_chart()
        self._add_gbt_overflow_chart()
        self._add_gbt_belt_speed_chart()
        self._add_gbt_polymer_chart()
        
        # FLOW CHARTS
        self._add_influent_flow_chart()
        self._add_effluent_flow_chart()
        self._add_flow_balance_chart()
        self._add_flow_difference_chart()
        
        # EQUIPMENT CHARTS
        self._add_bowl_speed_chart()
        self._add_equipment_performance_chart()
        
        # COST ANALYSIS
        self._add_cost_per_dry_ton_chart()
        self._add_cost_per_truck_chart()
        
        return self.charts
    
    # DEWATERING CHARTS
    def _add_polymer_efficiency_chart(self):
        if self.detected_params.get('polymer', {}).get('column'):
            col = self.detected_params['polymer']['column']
            unit = self.detected_params['polymer']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Polymer Efficiency ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'Dewatering',
                    'description': 'Daily polymer usage with 7-day moving average',
                    'threshold_excellent': 12 if unit == 'lbs/ton' else None,
                    'threshold_good': 15 if unit == 'lbs/ton' else None
                })
    
    def _add_polymer_trend_chart(self):
        if self.detected_params.get('polymer', {}).get('column'):
            col = self.detected_params['polymer']['column']
            unit = self.detected_params['polymer']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 30:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Polymer Trend Analysis ({unit})',
                    'type': 'trend_analysis',
                    'column': col,
                    'unit': unit,
                    'category': 'Dewatering',
                    'description': 'Polymer usage trend with linear regression'
                })
    
    def _add_cake_quality_chart(self):
        if self.detected_params.get('cake_quality', {}).get('column'):
            col = self.detected_params['cake_quality']['column']
            unit = self.detected_params['cake_quality']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Cake Quality ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'Dewatering',
                    'description': 'Cake solids percentage with 7-day moving average',
                    'threshold_excellent': 25,
                    'threshold_good': 20
                })
    
    def _add_cake_trend_chart(self):
        if self.detected_params.get('cake_quality', {}).get('column'):
            col = self.detected_params['cake_quality']['column']
            unit = self.detected_params['cake_quality']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 30:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Cake Quality Trend ({unit})',
                    'type': 'trend_analysis',
                    'column': col,
                    'unit': unit,
                    'category': 'Dewatering',
                    'description': 'Cake quality trend with linear regression'
                })
    
    def _add_centrifuge_hours_chart(self):
        hours_cols = []
        for i in range(1, 6):
            key = f'centrifuge_{i}_hours'
            if self.detected_params.get(key, {}).get('column'):
                hours_cols.append({
                    'column': self.detected_params[key]['column'],
                    'label': f'Centrifuge {i}',
                    'unit': self.detected_params[key]['unit']
                })
        
        if hours_cols:
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Centrifuge Run Hours',
                'type': 'multi_bar',
                'columns': hours_cols,
                'category': 'Dewatering',
                'description': 'Daily run hours for each centrifuge'
            })
    
    def _add_equipment_utilization_chart(self):
        hours_cols = []
        for i in range(1, 4):
            key = f'centrifuge_{i}_hours'
            if self.detected_params.get(key, {}).get('column'):
                hours_cols.append(self.detected_params[key]['column'])
        
        if len(hours_cols) >= 2:
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Equipment Utilization %',
                'type': 'utilization',
                'columns': hours_cols,
                'category': 'Dewatering',
                'description': 'Percentage utilization (hours/24) for each centrifuge'
            })
    
    def _add_dry_tons_chart(self):
        if self.detected_params.get('dry_tons', {}).get('column'):
            col = self.detected_params['dry_tons']['column']
            unit = self.detected_params['dry_tons']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Dry Tons Production ({unit})',
                    'type': 'bar_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'Dewatering',
                    'description': 'Daily dry solids production'
                })
    
    def _add_wet_tons_chart(self):
        if self.detected_params.get('wet_tons', {}).get('column'):
            col = self.detected_params['wet_tons']['column']
            unit = self.detected_params['wet_tons']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Wet Tons Production ({unit})',
                    'type': 'bar_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'Dewatering',
                    'description': 'Daily wet solids production'
                })
    
    def _add_dry_wet_ratio_chart(self):
        if (self.detected_params.get('dry_tons', {}).get('column') and 
            self.detected_params.get('wet_tons', {}).get('column')):
            
            dry_col = self.detected_params['dry_tons']['column']
            wet_col = self.detected_params['wet_tons']['column']
            
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Dewatering Efficiency (Dry/Wet Ratio)',
                'type': 'ratio',
                'column1': dry_col,
                'column2': wet_col,
                'unit': 'Ratio',
                'category': 'Dewatering',
                'description': 'Dry tons / Wet tons - Higher is better',
                'threshold_excellent': 0.25,
                'threshold_good': 0.20
            })
    
    def _add_truck_hauling_chart(self):
        if self.detected_params.get('trucks', {}).get('column'):
            col = self.detected_params['trucks']['column']
            unit = self.detected_params['trucks']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Sludge Truck Hauling ({unit})',
                    'type': 'bar_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'Dewatering',
                    'description': 'Daily sludge trucks hauled'
                })
    
    def _add_polymer_vs_cake_chart(self):
        if (self.detected_params.get('polymer', {}).get('column') and 
            self.detected_params.get('cake_quality', {}).get('column')):
            
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Polymer vs Cake Quality',
                'type': 'scatter_with_trend',
                'column1': self.detected_params['polymer']['column'],
                'column2': self.detected_params['cake_quality']['column'],
                'label1': f"Polymer ({self.detected_params['polymer']['unit']})",
                'label2': f"Cake Quality ({self.detected_params['cake_quality']['unit']})",
                'category': 'Dewatering',
                'description': 'Relationship between polymer dose and cake quality'
            })
    
    def _add_polymer_vs_trucks_chart(self):
        if (self.detected_params.get('polymer', {}).get('column') and 
            self.detected_params.get('trucks', {}).get('column')):
            
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Polymer vs Truck Hauling',
                'type': 'scatter_with_trend',
                'column1': self.detected_params['polymer']['column'],
                'column2': self.detected_params['trucks']['column'],
                'label1': f"Polymer ({self.detected_params['polymer']['unit']})",
                'label2': f"Trucks ({self.detected_params['trucks']['unit']})",
                'category': 'Dewatering',
                'description': 'Relationship between polymer dose and truck requirements'
            })
    
    def _add_cake_vs_trucks_chart(self):
        if (self.detected_params.get('cake_quality', {}).get('column') and 
            self.detected_params.get('trucks', {}).get('column')):
            
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Cake Quality vs Truck Hauling',
                'type': 'scatter_with_trend',
                'column1': self.detected_params['cake_quality']['column'],
                'column2': self.detected_params['trucks']['column'],
                'label1': f"Cake Quality ({self.detected_params['cake_quality']['unit']})",
                'label2': f"Trucks ({self.detected_params['trucks']['unit']})",
                'category': 'Dewatering',
                'description': 'Relationship between cake quality and truck requirements'
            })
    
    # THICKENING CHARTS
    def _add_thickener_feed_chart(self):
        if self.detected_params.get('thickener_feed', {}).get('column'):
            col = self.detected_params['thickener_feed']['column']
            unit = self.detected_params['thickener_feed']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Thickener Feed Rate ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'Thickening',
                    'description': 'Feed rate to gravity thickener'
                })
    
    def _add_thickener_underflow_chart(self):
        if self.detected_params.get('thickener_underflow', {}).get('column'):
            col = self.detected_params['thickener_underflow']['column']
            unit = self.detected_params['thickener_underflow']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Thickener Underflow Concentration ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'Thickening',
                    'description': 'Underflow solids concentration',
                    'threshold_excellent': 5,
                    'threshold_good': 3
                })
    
    def _add_thickener_overflow_chart(self):
        if self.detected_params.get('thickener_overflow', {}).get('column'):
            col = self.detected_params['thickener_overflow']['column']
            unit = self.detected_params['thickener_overflow']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Thickener Overflow Clarity ({unit})',
                    'type': 'line_with_ma_inverse',
                    'column': col,
                    'unit': unit,
                    'category': 'Thickening',
                    'description': 'Overflow TSS - Lower is better',
                    'threshold_excellent': 500,
                    'threshold_good': 1000
                })
    
    def _add_thickener_concentration_chart(self):
        if (self.detected_params.get('thickener_feed', {}).get('column') and 
            self.detected_params.get('thickener_underflow', {}).get('column')):
            
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Thickener Concentration Ratio',
                'type': 'ratio',
                'column1': self.detected_params['thickener_underflow']['column'],
                'column2': self.detected_params['thickener_feed']['column'],
                'unit': 'Ratio',
                'category': 'Thickening',
                'description': 'Underflow / Feed concentration ratio'
            })
    
    def _add_thickener_torque_chart(self):
        if self.detected_params.get('thickener_torque', {}).get('column'):
            col = self.detected_params['thickener_torque']['column']
            unit = self.detected_params['thickener_torque']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Thickener Rake Torque ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'Thickening',
                    'description': 'Rake mechanism torque - indicates sludge density'
                })
    
    # GBT (GRAVITY BELT THICKENER) CHARTS
    def _add_gbt_feed_chart(self):
        if self.detected_params.get('gbt_feed', {}).get('column'):
            col = self.detected_params['gbt_feed']['column']
            unit = self.detected_params['gbt_feed']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'GBT Feed Rate ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'GBT (Gravity Belt Thickener)',
                    'description': 'Feed rate to gravity belt thickener'
                })
    
    def _add_gbt_underflow_chart(self):
        if self.detected_params.get('gbt_underflow', {}).get('column'):
            col = self.detected_params['gbt_underflow']['column']
            unit = self.detected_params['gbt_underflow']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'GBT Underflow Concentration ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'GBT (Gravity Belt Thickener)',
                    'description': 'GBT underflow solids concentration',
                    'threshold_excellent': 8,
                    'threshold_good': 5
                })
    
    def _add_gbt_overflow_chart(self):
        if self.detected_params.get('gbt_overflow', {}).get('column'):
            col = self.detected_params['gbt_overflow']['column']
            unit = self.detected_params['gbt_overflow']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'GBT Overflow Clarity ({unit})',
                    'type': 'line_with_ma_inverse',
                    'column': col,
                    'unit': unit,
                    'category': 'GBT (Gravity Belt Thickener)',
                    'description': 'GBT overflow TSS - Lower is better',
                    'threshold_excellent': 300,
                    'threshold_good': 500
                })
    
    def _add_gbt_belt_speed_chart(self):
        if self.detected_params.get('gbt_belt_speed', {}).get('column'):
            col = self.detected_params['gbt_belt_speed']['column']
            unit = self.detected_params['gbt_belt_speed']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'GBT Belt Speed ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'GBT (Gravity Belt Thickener)',
                    'description': 'Gravity belt thickener belt speed'
                })
    
    def _add_gbt_polymer_chart(self):
        if self.detected_params.get('gbt_polymer', {}).get('column'):
            col = self.detected_params['gbt_polymer']['column']
            unit = self.detected_params['gbt_polymer']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'GBT Polymer Dose ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'GBT (Gravity Belt Thickener)',
                    'description': 'Polymer dose for gravity belt thickener'
                })
    
    # FLOW CHARTS
    def _add_influent_flow_chart(self):
        if self.detected_params.get('influent_flow', {}).get('column'):
            col = self.detected_params['influent_flow']['column']
            unit = self.detected_params['influent_flow']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Influent Flow ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'Flow',
                    'description': 'Wastewater flow into treatment plant'
                })
    
    def _add_effluent_flow_chart(self):
        if self.detected_params.get('effluent_flow', {}).get('column'):
            col = self.detected_params['effluent_flow']['column']
            unit = self.detected_params['effluent_flow']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Effluent Flow ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'Flow',
                    'description': 'Treated water discharge'
                })
    
    def _add_flow_balance_chart(self):
        if (self.detected_params.get('influent_flow', {}).get('column') and 
            self.detected_params.get('effluent_flow', {}).get('column')):
            
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Flow Balance (Influent vs Effluent)',
                'type': 'dual_line',
                'column1': self.detected_params['influent_flow']['column'],
                'column2': self.detected_params['effluent_flow']['column'],
                'label1': f"Influent ({self.detected_params['influent_flow']['unit']})",
                'label2': f"Effluent ({self.detected_params['effluent_flow']['unit']})",
                'category': 'Flow',
                'description': 'Comparison of influent and effluent flows'
            })
    
    def _add_flow_difference_chart(self):
        if (self.detected_params.get('influent_flow', {}).get('column') and 
            self.detected_params.get('effluent_flow', {}).get('column')):
            
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Flow Difference %',
                'type': 'flow_difference',
                'column1': self.detected_params['influent_flow']['column'],
                'column2': self.detected_params['effluent_flow']['column'],
                'unit': '%',
                'category': 'Flow',
                'description': '(Influent - Effluent) / Influent × 100'
            })
    
    # EQUIPMENT CHARTS
    def _add_bowl_speed_chart(self):
        if self.detected_params.get('bowl_speed', {}).get('column'):
            col = self.detected_params['bowl_speed']['column']
            unit = self.detected_params['bowl_speed']['unit']
            data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            
            if len(data) > 0:
                self.charts.append({
                    'id': self._get_unique_id(),
                    'name': f'Centrifuge Bowl Speed ({unit})',
                    'type': 'line_with_ma',
                    'column': col,
                    'unit': unit,
                    'category': 'Equipment',
                    'description': 'Centrifuge bowl rotation speed'
                })
    
    def _add_equipment_performance_chart(self):
        hours_cols = []
        for i in range(1, 4):
            key = f'centrifuge_{i}_hours'
            if self.detected_params.get(key, {}).get('column'):
                hours_cols.append(self.detected_params[key]['column'])
        
        if len(hours_cols) >= 2:
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Equipment Performance Comparison',
                'type': 'box_plot',
                'columns': hours_cols,
                'category': 'Equipment',
                'description': 'Distribution of run hours across centrifuges'
            })
    
    # COST ANALYSIS
    def _add_cost_per_dry_ton_chart(self):
        if (self.detected_params.get('polymer_cost', {}).get('column') and 
            self.detected_params.get('dry_tons', {}).get('column')):
            
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Polymer Cost per Dry Ton',
                'type': 'cost_analysis',
                'cost_column': self.detected_params['polymer_cost']['column'],
                'tons_column': self.detected_params['dry_tons']['column'],
                'unit': '$/Ton',
                'category': 'Cost',
                'description': 'Polymer cost efficiency'
            })
    
    def _add_cost_per_truck_chart(self):
        if (self.detected_params.get('hauling_cost', {}).get('column') and 
            self.detected_params.get('trucks', {}).get('column')):
            
            self.charts.append({
                'id': self._get_unique_id(),
                'name': 'Cost per Truck',
                'type': 'cost_analysis',
                'cost_column': self.detected_params['hauling_cost']['column'],
                'tons_column': self.detected_params['trucks']['column'],
                'unit': '$/Truck',
                'category': 'Cost',
                'description': 'Hauling cost per truck'
            })

# ============================================================
# CHART RENDERER
# ============================================================
class ChartRenderer:
    """Renders all chart types"""
    
    def __init__(self, df):
        self.df = df
    
    def render_chart(self, chart_config):
        """Render a single chart based on configuration"""
        
        try:
            if chart_config['type'] == 'line_with_ma':
                return self._render_line_with_ma(chart_config)
            elif chart_config['type'] == 'line_with_ma_inverse':
                return self._render_line_with_ma_inverse(chart_config)
            elif chart_config['type'] == 'bar_with_ma':
                return self._render_bar_with_ma(chart_config)
            elif chart_config['type'] == 'trend_analysis':
                return self._render_trend_analysis(chart_config)
            elif chart_config['type'] == 'multi_bar':
                return self._render_multi_bar(chart_config)
            elif chart_config['type'] == 'utilization':
                return self._render_utilization(chart_config)
            elif chart_config['type'] == 'ratio':
                return self._render_ratio(chart_config)
            elif chart_config['type'] == 'scatter_with_trend':
                return self._render_scatter_with_trend(chart_config)
            elif chart_config['type'] == 'dual_line':
                return self._render_dual_line(chart_config)
            elif chart_config['type'] == 'flow_difference':
                return self._render_flow_difference(chart_config)
            elif chart_config['type'] == 'box_plot':
                return self._render_box_plot(chart_config)
            elif chart_config['type'] == 'cost_analysis':
                return self._render_cost_analysis(chart_config)
        except Exception as e:
            st.error(f"Error rendering chart: {str(e)}")
            return None
    
    def _render_line_with_ma(self, config):
        col_data = pd.to_numeric(self.df[config['column']], errors='coerce')
        col_ma = col_data.rolling(window=7).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.df.index, y=col_data, mode='markers', name='Daily',
            marker=dict(size=4, color='lightblue', opacity=0.6)
        ))
        fig.add_trace(go.Scatter(
            x=self.df.index, y=col_ma, mode='lines', name='7-day MA',
            line=dict(color='darkblue', width=2)
        ))
        
        if 'threshold_excellent' in config and config['threshold_excellent']:
            fig.add_hline(y=config['threshold_excellent'], line_dash="dash",
                         line_color="green", annotation_text="Excellent")
        if 'threshold_good' in config and config['threshold_good']:
            fig.add_hline(y=config['threshold_good'], line_dash="dash",
                         line_color="orange", annotation_text="Good")
        
        fig.update_layout(
            title=f"{config['name']} ({config['unit']})",
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title=config['unit']
        )
        return fig
    
    def _render_line_with_ma_inverse(self, config):
        col_data = pd.to_numeric(self.df[config['column']], errors='coerce')
        col_ma = col_data.rolling(window=7).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.df.index, y=col_data, mode='markers', name='Daily',
            marker=dict(size=4, color='#FF6B6B', opacity=0.6)
        ))
        fig.add_trace(go.Scatter(
            x=self.df.index, y=col_ma, mode='lines', name='7-day MA',
            line=dict(color='darkred', width=2)
        ))
        
        if 'threshold_excellent' in config and config['threshold_excellent']:
            fig.add_hline(y=config['threshold_excellent'], line_dash="dash",
                         line_color="green", annotation_text="Excellent (Lower)")
        if 'threshold_good' in config and config['threshold_good']:
            fig.add_hline(y=config['threshold_good'], line_dash="dash",
                         line_color="orange", annotation_text="Good (Lower)")
        
        fig.update_layout(
            title=f"{config['name']} ({config['unit']}) - Lower is Better",
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title=config['unit']
        )
        return fig
    
    def _render_bar_with_ma(self, config):
        col_data = pd.to_numeric(self.df[config['column']], errors='coerce')
        col_ma = col_data.rolling(window=7).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=self.df.index, y=col_data, name='Daily',
            marker=dict(color='#4169E1', opacity=0.7)
        ))
        fig.add_trace(go.Scatter(
            x=self.df.index, y=col_ma, mode='lines', name='7-day MA',
            line=dict(color='darkblue', width=2)
        ))
        
        fig.update_layout(
            title=f"{config['name']} ({config['unit']})",
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title=config['unit']
        )
        return fig
    
    def _render_trend_analysis(self, config):
        col_data = pd.to_numeric(self.df[config['column']], errors='coerce').dropna()
        
        if len(col_data) < 2:
            return None
        
        x = np.arange(len(col_data))
        z = np.polyfit(x, col_data.values, 1)
        p = np.poly1d(z)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.df.index[:len(col_data)], y=col_data, mode='markers', name='Data',
            marker=dict(size=6, color='blue', opacity=0.6)
        ))
        fig.add_trace(go.Scatter(
            x=self.df.index[:len(col_data)], y=p(x), mode='lines', name='Trend',
            line=dict(color='red', width=2)
        ))
        
        slope = z[0]
        trend_text = "Increasing" if slope > 0 else "Decreasing"
        
        fig.update_layout(
            title=f"{config['name']} ({config['unit']}) - {trend_text} Trend",
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title=config['unit']
        )
        return fig
    
    def _render_multi_bar(self, config):
        fig = go.Figure()
        
        for col_info in config['columns']:
            col_data = pd.to_numeric(self.df[col_info['column']], errors='coerce')
            fig.add_trace(go.Bar(
                x=self.df.index, y=col_data, name=col_info['label']
            ))
        
        fig.update_layout(
            title=config['name'],
            height=400,
            barmode='group',
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title=config['columns'][0]['unit']
        )
        return fig
    
    def _render_utilization(self, config):
        fig = go.Figure()
        
        for i, col in enumerate(config['columns']):
            col_data = pd.to_numeric(self.df[col], errors='coerce')
            utilization = (col_data / 24) * 100
            fig.add_trace(go.Scatter(
                x=self.df.index, y=utilization, mode='lines', name=f'Centrifuge {i+1}',
                line=dict(width=2)
            ))
        
        fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overutilized (>70%)")
        fig.add_hline(y=40, line_dash="dash", line_color="green", annotation_text="Optimal (40-70%)")
        
        fig.update_layout(
            title=config['name'],
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title="Utilization %"
        )
        return fig
    
    def _render_ratio(self, config):
        col1_data = pd.to_numeric(self.df[config['column1']], errors='coerce')
        col2_data = pd.to_numeric(self.df[config['column2']], errors='coerce')
        ratio_data = (col1_data / col2_data).replace([np.inf, -np.inf], np.nan)
        ratio_ma = ratio_data.rolling(window=7).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.df.index, y=ratio_data, mode='markers', name='Daily',
            marker=dict(size=4, color='teal', opacity=0.6)
        ))
        fig.add_trace(go.Scatter(
            x=self.df.index, y=ratio_ma, mode='lines', name='7-day MA',
            line=dict(color='darkslategray', width=2)
        ))
        
        if 'threshold_excellent' in config and config['threshold_excellent']:
            fig.add_hline(y=config['threshold_excellent'], line_dash="dash",
                         line_color="green", annotation_text="Excellent")
        if 'threshold_good' in config and config['threshold_good']:
            fig.add_hline(y=config['threshold_good'], line_dash="dash",
                         line_color="orange", annotation_text="Good")
        
        fig.update_layout(
            title=f"{config['name']} ({config['unit']})",
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title=config['unit']
        )
        return fig
    
    def _render_scatter_with_trend(self, config):
        col1_data = pd.to_numeric(self.df[config['column1']], errors='coerce').dropna()
        col2_data = pd.to_numeric(self.df[config['column2']], errors='coerce')
        col2_data = col2_data[col1_data.index]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=col1_data, y=col2_data, mode='markers',
            marker=dict(size=8, color='blue', opacity=0.6)
        ))
        
        if len(col1_data) > 1:
            z = np.polyfit(col1_data, col2_data, 1)
            p = np.poly1d(z)
            x_trend = np.linspace(col1_data.min(), col1_data.max(), 100)
            fig.add_trace(go.Scatter(
                x=x_trend, y=p(x_trend), mode='lines', name='Trend',
                line=dict(color='red', width=2)
            ))
            
            corr = col1_data.corr(col2_data)
            fig.update_layout(
                title=f"{config['name']} (Correlation: {corr:.2f})",
            )
        
        fig.update_layout(
            height=400,
            hovermode='closest',
            xaxis_title=config['label1'],
            yaxis_title=config['label2']
        )
        return fig
    
    def _render_dual_line(self, config):
        col1_data = pd.to_numeric(self.df[config['column1']], errors='coerce')
        col2_data = pd.to_numeric(self.df[config['column2']], errors='coerce')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.df.index, y=col1_data, mode='lines', name=config['label1'],
            line=dict(color='red', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=self.df.index, y=col2_data, mode='lines', name=config['label2'],
            line=dict(color='green', width=2)
        ))
        
        fig.update_layout(
            title=config['name'],
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title="Flow"
        )
        return fig
    
    def _render_flow_difference(self, config):
        col1_data = pd.to_numeric(self.df[config['column1']], errors='coerce')
        col2_data = pd.to_numeric(self.df[config['column2']], errors='coerce')
        diff = ((col1_data - col2_data) / col1_data * 100).replace([np.inf, -np.inf], np.nan)
        diff_ma = diff.rolling(window=7).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=self.df.index, y=diff, name='Daily',
            marker=dict(color='purple', opacity=0.7)
        ))
        fig.add_trace(go.Scatter(
            x=self.df.index, y=diff_ma, mode='lines', name='7-day MA',
            line=dict(color='darkviolet', width=2)
        ))
        
        fig.add_hline(y=15, line_dash="dash", line_color="orange", annotation_text="Investigate (15%)")
        fig.add_hline(y=25, line_dash="dash", line_color="red", annotation_text="Critical (25%)")
        
        fig.update_layout(
            title=config['name'],
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title=config['unit']
        )
        return fig
    
    def _render_box_plot(self, config):
        fig = go.Figure()
        
        for i, col in enumerate(config['columns']):
            col_data = pd.to_numeric(self.df[col], errors='coerce').dropna()
            fig.add_trace(go.Box(y=col_data, name=f'Centrifuge {i+1}'))
        
        fig.update_layout(
            title=config['name'],
            height=400,
            yaxis_title="Hours"
        )
        return fig
    
    def _render_cost_analysis(self, config):
        cost_data = pd.to_numeric(self.df[config['cost_column']], errors='coerce')
        tons_data = pd.to_numeric(self.df[config['tons_column']], errors='coerce')
        cost_per_unit = (cost_data / tons_data).replace([np.inf, -np.inf], np.nan)
        cost_ma = cost_per_unit.rolling(window=7).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.df.index, y=cost_per_unit, mode='markers', name='Daily',
            marker=dict(size=6, color='purple', opacity=0.6)
        ))
        fig.add_trace(go.Scatter(
            x=self.df.index, y=cost_ma, mode='lines', name='7-day MA',
            line=dict(color='darkviolet', width=2)
        ))
        
        fig.update_layout(
            title=f"{config['name']} ({config['unit']})",
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title=config['unit']
        )
        return fig

# ============================================================
# DATA QUALITY CHECKER
# ============================================================
class DataQualityChecker:
    """Comprehensive data quality analysis"""
    
    def __init__(self, df):
        self.df = df
    
    def detect_outliers(self, column, method='iqr'):
        """Detect outliers"""
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
            'values': outliers.values[:5] if len(outliers) > 0 else []
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
        """Check data range"""
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
        """Generate quality report"""
        report = {
            'total_records': len(self.df),
            'column_analysis': {}
        }
        
        for col in columns_to_check:
            if col and col in self.df.columns:
                try:
                    report['column_analysis'][col] = {
                        'missing': self.check_missing_values(col),
                        'range': self.check_data_range(col),
                        'outliers': self.detect_outliers(col, 'iqr')
                    }
                except Exception as e:
                    pass
        
        return report

# ============================================================
# SIDEBAR - FILE UPLOAD
# ============================================================
st.sidebar.header("📊 Upload Your Data")
uploaded_file = st.sidebar.file_uploader(
    "Choose your WWTP CSV file",
    type=['csv'],
    help="Upload a CSV file with your WWTP dewatering and thickening data"
)

# ============================================================
# MAIN APP LOGIC
# ============================================================
if uploaded_file is None:
    st.info("👈 **Please upload a CSV file to get started**")
    st.markdown("""
    ### 📋 Expected Data Format:
    
    Your CSV should contain columns like:
    
    **Dewatering:**
    - Active Polymer (lbs/ton, GPD)
    - Cake Quality (%), Cake Solids (%), Cake % Solids
    - Centrifuge 1/2/3 Run Hours
    - Dry Tons, Wet Tons
    - Daily Trucks
    
    **Thickening (Gravity Thickener):**
    - Thickener Feed Rate (GPM, MGD)
    - Thickener Underflow TS (%)
    - Thickener Overflow TSS (mg/L)
    - Thickener Torque (Nm)
    
    **GBT (Gravity Belt Thickener):**
    - GBT Feed Rate (GPM, MGD)
    - GBT Underflow TS (%)
    - GBT Overflow TSS (mg/L)
    - GBT Belt Speed (%)
    - GBT Polymer Dose (lbs/ton)
    
    **Flow:**
    - Influent Flow (MGD, GPM)
    - Effluent Flow (MGD, GPM)
    
    **Equipment:**
    - Bowl Speed (RPM)
    
    **Cost:**
    - Polymer Cost ($)
    - Hauling Cost ($)
    
    ### ✨ Features:
    - 🔍 **Fuzzy Logic** - Auto-detects your columns
    - 📊 **30+ Charts** - Comprehensive analysis
    - 📈 **Unit Detection** - Shows units automatically
    - 💡 **Performance Metrics** - Industry benchmarks
    - 🔎 **Data Quality** - Outlier detection
    
    ### 🚀 Ready? Upload your file!
    """)

else:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Reset index for easier charting
        df = df.reset_index(drop=True)
        
        st.sidebar.success(f"✅ Loaded {len(df)} records")
        st.sidebar.write(f"📊 {len(df.columns)} columns detected")
        
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()
    
    # Initialize parameter detector
    parameter_keywords = {
        'polymer': ['active poly', 'polymer', 'lbs per ton', 'lbs/ton', 'poly dose', 'polymer dose'],
        'cake_quality': ['cake', 'solids', 'cake avg', 'cake %', 'cake quality', 'moisture', 'cake solids', '% solids'],
        'centrifuge_1_hours': ['centrifuge 1', 'c1', 'run hours 1', 'c1 hours'],
        'centrifuge_2_hours': ['centrifuge 2', 'c2', 'run hours 2', 'c2 hours'],
        'centrifuge_3_hours': ['centrifuge 3', 'c3', 'run hours 3', 'c3 hours'],
        'centrifuge_4_hours': ['centrifuge 4', 'c4', 'run hours 4', 'c4 hours'],
        'centrifuge_5_hours': ['centrifuge 5', 'c5', 'run hours 5', 'c5 hours'],
        'dry_tons': ['dry tons', 'dry', 'dry solids'],
        'wet_tons': ['wet tons', 'wet', 'wet solids'],
        'trucks': ['trucks', 'sludge trucks', 'daily trucks', 'truck count'],
        'influent_flow': ['influent', 'inflow', 'inlet flow', 'mgd in'],
        'effluent_flow': ['effluent', 'outflow', 'outlet flow', 'dval', 'mgd out'],
        'thickener_feed': ['thickener feed', 'thickener inlet', 'feed rate', 'gravity thickener feed'],
        'thickener_underflow': ['thickener underflow', 'underflow ts', 'underflow solids', 'gravity thickener underflow'],
        'thickener_overflow': ['thickener overflow', 'overflow tss', 'overflow clarity', 'gravity thickener overflow'],
        'thickener_torque': ['thickener torque', 'rake torque', 'torque'],
        'gbt_feed': ['gbt feed', 'gravity belt feed', 'belt thickener feed'],
        'gbt_underflow': ['gbt underflow', 'gravity belt underflow', 'belt thickener underflow'],
        'gbt_overflow': ['gbt overflow', 'gravity belt overflow', 'belt thickener overflow'],
        'gbt_belt_speed': ['gbt belt speed', 'gravity belt speed', 'belt speed'],
        'gbt_polymer': ['gbt polymer', 'gravity belt polymer', 'belt polymer'],
        'bowl_speed': ['bowl speed', 'rpm', 'centrifuge speed'],
        'polymer_cost': ['polymer cost', 'polymer $', 'polymer price'],
        'hauling_cost': ['hauling cost', 'hauling $', 'truck cost']
    }
    
    detector = FuzzyParameterDetector(df.columns)
    detected_params = detector.find_parameters(parameter_keywords, threshold=60)
    
    # Display detected parameters
    st.sidebar.subheader("🔍 Detected Parameters")
    detected_count = 0
    for param_name, param_info in detected_params.items():
        if param_info['column']:
            st.sidebar.write(f"✅ {param_name}: **{param_info['column']}** ({param_info['unit']})")
            detected_count += 1
    
    st.sidebar.write(f"\n**Found: {detected_count}/{len(parameter_keywords)} parameters**")
    
    # Initialize chart generator and renderer
    chart_generator = ComprehensiveChartGenerator(df, detected_params)
    charts = chart_generator.generate_all_charts()
    chart_renderer = ChartRenderer(df)
    quality_checker = DataQualityChecker(df)
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📊 Dashboard",
        "📈 All Charts",
        "🔄 Dewatering",
        "🌀 Thickening",
        "🎯 GBT",
        "💧 Flow Analysis",
        "🔍 Data Quality",
        "📋 Parameters",
        "📥 Raw Data"
    ])
    
    # ============================================================
    # TAB 1: DASHBOARD
    # ============================================================
    with tab1:
        st.header("📊 Performance Dashboard")
        
        # Dewatering Metrics
        st.subheader("🔄 Dewatering Performance")
        col1, col2, col3, col4 = st.columns(4)
        
        if detected_params.get('polymer', {}).get('column'):
            poly_col = detected_params['polymer']['column']
            poly_unit = detected_params['polymer']['unit']
            poly_data = pd.to_numeric(df[poly_col], errors='coerce').dropna()
            if len(poly_data) > 0:
                with col1:
                    st.metric(
                        f"Polymer Efficiency ({poly_unit})",
                        f"{poly_data.mean():.2f}",
                        f"{poly_data.iloc[-1] - poly_data.mean():+.2f}",
                        delta_color="inverse"
                    )
        
        if detected_params.get('cake_quality', {}).get('column'):
            cake_col = detected_params['cake_quality']['column']
            cake_unit = detected_params['cake_quality']['unit']
            cake_data = pd.to_numeric(df[cake_col], errors='coerce').dropna()
            if len(cake_data) > 0:
                with col2:
                    st.metric(
                        f"Cake Quality ({cake_unit})",
                        f"{cake_data.mean():.2f}",
                        f"{cake_data.iloc[-1] - cake_data.mean():+.2f}"
                    )
        
        if detected_params.get('dry_tons', {}).get('column') and detected_params.get('wet_tons', {}).get('column'):
            dry_col = detected_params['dry_tons']['column']
            wet_col = detected_params['wet_tons']['column']
            dry_data = pd.to_numeric(df[dry_col], errors='coerce')
            wet_data = pd.to_numeric(df[wet_col], errors='coerce')
            ratio = (dry_data / wet_data).mean()
            with col3:
                st.metric("Dry/Wet Ratio", f"{ratio:.3f}", "Higher is Better")
        
        if detected_params.get('trucks', {}).get('column'):
            truck_col = detected_params['trucks']['column']
            truck_unit = detected_params['trucks']['unit']
            truck_data = pd.to_numeric(df[truck_col], errors='coerce').dropna()
            if len(truck_data) > 0:
                with col4:
                    st.metric(
                        f"Avg Trucks/Day ({truck_unit})",
                        f"{truck_data.mean():.1f}",
                        f"Est. ${truck_data.mean() * 500 * 30:,.0f}/month"
                    )
        
        st.divider()
        
        # Thickening Metrics
        st.subheader("🌀 Thickening Performance")
        col5, col6, col7 = st.columns(3)
        
        if detected_params.get('thickener_feed', {}).get('column'):
            feed_col = detected_params['thickener_feed']['column']
            feed_unit = detected_params['thickener_feed']['unit']
            feed_data = pd.to_numeric(df[feed_col], errors='coerce').dropna()
            if len(feed_data) > 0:
                with col5:
                    st.metric(f"Thickener Feed ({feed_unit})", f"{feed_data.mean():.2f}")
        
        if detected_params.get('thickener_underflow', {}).get('column'):
            uf_col = detected_params['thickener_underflow']['column']
            uf_unit = detected_params['thickener_underflow']['unit']
            uf_data = pd.to_numeric(df[uf_col], errors='coerce').dropna()
            if len(uf_data) > 0:
                with col6:
                    st.metric(f"Underflow Conc. ({uf_unit})", f"{uf_data.mean():.2f}")
        
        if detected_params.get('thickener_overflow', {}).get('column'):
            of_col = detected_params['thickener_overflow']['column']
            of_unit = detected_params['thickener_overflow']['unit']
            of_data = pd.to_numeric(df[of_col], errors='coerce').dropna()
            if len(of_data) > 0:
                with col7:
                    st.metric(f"Overflow TSS ({of_unit})", f"{of_data.mean():.0f}", "Lower is Better")
        
        st.divider()
        
        # GBT Metrics
        st.subheader("🎯 GBT (Gravity Belt Thickener) Performance")
        col8, col9, col10 = st.columns(3)
        
        if detected_params.get('gbt_feed', {}).get('column'):
            gbt_feed_col = detected_params['gbt_feed']['column']
            gbt_feed_unit = detected_params['gbt_feed']['unit']
            gbt_feed_data = pd.to_numeric(df[gbt_feed_col], errors='coerce').dropna()
            if len(gbt_feed_data) > 0:
                with col8:
                    st.metric(f"GBT Feed ({gbt_feed_unit})", f"{gbt_feed_data.mean():.2f}")
        
        if detected_params.get('gbt_underflow', {}).get('column'):
            gbt_uf_col = detected_params['gbt_underflow']['column']
            gbt_uf_unit = detected_params['gbt_underflow']['unit']
            gbt_uf_data = pd.to_numeric(df[gbt_uf_col], errors='coerce').dropna()
            if len(gbt_uf_data) > 0:
                with col9:
                    st.metric(f"GBT Underflow ({gbt_uf_unit})", f"{gbt_uf_data.mean():.2f}")
        
        if detected_params.get('gbt_overflow', {}).get('column'):
            gbt_of_col = detected_params['gbt_overflow']['column']
            gbt_of_unit = detected_params['gbt_overflow']['unit']
            gbt_of_data = pd.to_numeric(df[gbt_of_col], errors='coerce').dropna()
            if len(gbt_of_data) > 0:
                with col10:
                    st.metric(f"GBT Overflow ({gbt_of_unit})", f"{gbt_of_data.mean():.0f}", "Lower is Better")
        
        st.divider()
        
        # Flow Metrics
        st.subheader("💧 Flow Data")
        col11, col12 = st.columns(2)
        
        if detected_params.get('influent_flow', {}).get('column'):
            inf_col = detected_params['influent_flow']['column']
            inf_unit = detected_params['influent_flow']['unit']
            inf_data = pd.to_numeric(df[inf_col], errors='coerce').dropna()
            if len(inf_data) > 0:
                with col11:
                    st.metric(f"Influent Flow ({inf_unit})", f"{inf_data.mean():.2f}")
        
        if detected_params.get('effluent_flow', {}).get('column'):
            eff_col = detected_params['effluent_flow']['column']
            eff_unit = detected_params['effluent_flow']['unit']
            eff_data = pd.to_numeric(df[eff_col], errors='coerce').dropna()
            if len(eff_data) > 0:
                with col12:
                    st.metric(f"Effluent Flow ({eff_unit})", f"{eff_data.mean():.2f}")
    
    # ============================================================
    # TAB 2: ALL CHARTS
    # ============================================================
    with tab2:
        st.header(f"📈 All Charts ({len(charts)} Total)")
        
        if not charts:
            st.warning("⚠️ No charts could be generated. Check your data format.")
        else:
            # Filter by category
            categories = list(set([c.get('category', 'Other') for c in charts]))
            selected_category = st.selectbox("Filter by Category:", ["All"] + sorted(categories))
            
            filtered_charts = charts if selected_category == "All" else [c for c in charts if c.get('category') == selected_category]
            
            st.write(f"Showing {len(filtered_charts)} charts")
            st.divider()
            
            for chart_config in filtered_charts:
                col_title, col_desc = st.columns([3, 1])
                with col_title:
                    st.subheader(chart_config['name'])
                with col_desc:
                    st.caption(f"Category: {chart_config.get('category', 'Other')}")
                
                st.caption(chart_config.get('description', ''))
                
                fig = chart_renderer.render_chart(chart_config)
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{chart_config['id']}")
                
                st.divider()
    
    # ============================================================
    # TAB 3: DEWATERING
    # ============================================================
    with tab3:
        st.header("🔄 Dewatering Analysis")
        
        dewatering_charts = [c for c in charts if c.get('category') == 'Dewatering']
        
        if not dewatering_charts:
            st.info("No dewatering data detected")
        else:
            st.write(f"Showing {len(dewatering_charts)} dewatering charts")
            
            for chart_config in dewatering_charts:
                st.subheader(chart_config['name'])
                st.caption(chart_config.get('description', ''))
                
                fig = chart_renderer.render_chart(chart_config)
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key=f"dew_chart_{chart_config['id']}")
                
                st.divider()
    
    # ============================================================
    # TAB 4: THICKENING
    # ============================================================
    with tab4:
        st.header("🌀 Thickening Analysis")
        
        thickening_charts = [c for c in charts if c.get('category') == 'Thickening']
        
        if not thickening_charts:
            st.info("No thickening data detected")
        else:
            st.write(f"Showing {len(thickening_charts)} thickening charts")
            
            for chart_config in thickening_charts:
                st.subheader(chart_config['name'])
                st.caption(chart_config.get('description', ''))
                
                fig = chart_renderer.render_chart(chart_config)
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key=f"thick_chart_{chart_config['id']}")
                
                st.divider()
    
    # ============================================================
    # TAB 5: GBT
    # ============================================================
    with tab5:
        st.header("🎯 GBT (Gravity Belt Thickener) Analysis")
        
        gbt_charts = [c for c in charts if c.get('category') == 'GBT (Gravity Belt Thickener)']
        
        if not gbt_charts:
            st.info("No GBT data detected")
        else:
            st.write(f"Showing {len(gbt_charts)} GBT charts")
            
            for chart_config in gbt_charts:
                st.subheader(chart_config['name'])
                st.caption(chart_config.get('description', ''))
                
                fig = chart_renderer.render_chart(chart_config)
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key=f"gbt_chart_{chart_config['id']}")
                
                st.divider()
    
    # ============================================================
    # TAB 6: FLOW ANALYSIS
    # ============================================================
    with tab6:
        st.header("💧 Flow Analysis")
        
        flow_charts = [c for c in charts if c.get('category') == 'Flow']
        
        if not flow_charts:
            st.info("No flow data detected")
        else:
            st.write(f"Showing {len(flow_charts)} flow charts")
            
            for chart_config in flow_charts:
                st.subheader(chart_config['name'])
                st.caption(chart_config.get('description', ''))
                
                fig = chart_renderer.render_chart(chart_config)
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key=f"flow_chart_{chart_config['id']}")
                
                st.divider()
    
    # ============================================================
    # TAB 7: DATA QUALITY
    # ============================================================
    with tab7:
        st.header("🔍 Data Quality Analysis")
        
        columns_to_check = [p['column'] for p in detected_params.values() if p['column']]
        quality_report = quality_checker.generate_report(columns_to_check)
        
        col_dq1, col_dq2, col_dq3 = st.columns(3)
        with col_dq1:
            st.metric("Total Records", quality_report['total_records'])
        with col_dq2:
            st.metric("Columns Analyzed", len(quality_report['column_analysis']))
        with col_dq3:
            total_missing = sum([v['missing']['count'] for v in quality_report['column_analysis'].values()])
            st.metric("Total Missing Values", total_missing)
        
        st.divider()
        
        for col_name, col_analysis in quality_report['column_analysis'].items():
            with st.expander(f"📊 {col_name}"):
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.write("**Missing Values:**")
                    st.write(f"Count: {col_analysis['missing']['count']}")
                    st.write(f"Percentage: {col_analysis['missing']['percentage']:.2f}%")
                
                with col_b:
                    st.write("**Data Range:**")
                    st.write(f"Min: {col_analysis['range']['min']:.2f}")
                    st.write(f"Max: {col_analysis['range']['max']:.2f}")
                    st.write(f"Mean: {col_analysis['range']['mean']:.2f}")
                
                with col_c:
                    st.write("**Outliers (IQR):**")
                    st.write(f"Count: {col_analysis['outliers']['count']}")
                    st.write(f"Percentage: {col_analysis['outliers']['percentage']:.2f}%")
    
    # ============================================================
    # TAB 8: PARAMETERS
    # ============================================================
    with tab8:
        st.header("📋 Detected Parameters & Units")
        
        param_data = []
        for param_name, param_info in detected_params.items():
            if param_info['column']:
                param_data.append({
                    'Parameter': param_name,
                    'Column': param_info['column'],
                    'Unit': param_info['unit'],
                    'Match Score': f"{param_info['score']:.0f}%"
                })
        
        if param_data:
            param_df = pd.DataFrame(param_data)
            st.dataframe(param_df, use_container_width=True)
            
            csv = param_df.to_csv(index=False)
            st.download_button("📥 Download Parameters", data=csv, file_name="parameters.csv", mime="text/csv")
        else:
            st.info("No parameters detected")
    
    # ============================================================
    # TAB 9: RAW DATA
    # ============================================================
    with tab9:
        st.header("📥 Raw Data")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Data", data=csv, file_name="wwtp_data.csv", mime="text/csv")

st.success("✅ App loaded successfully!")
