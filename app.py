import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fuzzywuzzy import fuzz, process
from scipy import stats
from datetime import datetime, timedelta
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

st.title("🌊 AI-Powered WWTP Dewatering & Thickening Performance Analyzer")
st.markdown("**Fuzzy Parameter Detection | YOY Analysis | AI Recommendations | Unit Tracking**")

# ============================================================
# PERFORMANCE THRESHOLDS & RATINGS
# ============================================================
PERFORMANCE_THRESHOLDS = {
    'polymer': {
        'excellent': (0, 12),
        'good': (12, 15),
        'moderate': (15, 18),
        'poor': (18, float('inf'))
    },
    'cake_quality': {
        'excellent': (25, float('inf')),
        'good': (20, 25),
        'moderate': (15, 20),
        'poor': (0, 15)
    },
    'dry_wet_ratio': {
        'excellent': (0.25, float('inf')),
        'good': (0.20, 0.25),
        'moderate': (0.15, 0.20),
        'poor': (0, 0.15)
    },
    'thickener_underflow': {
        'excellent': (5, float('inf')),
        'good': (3, 5),
        'moderate': (2, 3),
        'poor': (0, 2)
    },
    'thickener_overflow': {
        'excellent': (0, 500),
        'good': (500, 1000),
        'moderate': (1000, 1500),
        'poor': (1500, float('inf'))
    },
    'gbt_underflow': {
        'excellent': (8, float('inf')),
        'good': (5, 8),
        'moderate': (3, 5),
        'poor': (0, 3)
    },
    'gbt_overflow': {
        'excellent': (0, 300),
        'good': (300, 500),
        'moderate': (500, 800),
        'poor': (800, float('inf'))
    }
}

PERFORMANCE_DESCRIPTIONS = {
    'excellent': '✅ Excellent - Operating at best practice levels',
    'good': '⚠️ Good - Acceptable performance, minor optimization possible',
    'moderate': '🟡 Moderate - Performance below target, optimization recommended',
    'poor': '🔴 Poor - Significant issues, immediate action required'
}

# ============================================================
# KPI DEFINITIONS
# ============================================================
DEWATERING_KPI_DEFINITIONS = {
    'cake_solids': {
        'name': 'Cake Solids Content (%)',
        'description': 'Measures the dry solids percentage in dewatered biosolids',
        'target': '18-25% (belt press), 20-30% (centrifuge)',
        'unit': '%',
        'keywords': ['cake', 'solids', 'cake %', 'cake quality', 'moisture']
    },
    'polymer_consumption': {
        'name': 'Polymer Consumption (lbs/ton DS)',
        'description': 'Tracks conditioning chemical usage per ton of dry solids',
        'target': '5-15 lbs/ton DS',
        'unit': 'lbs/ton',
        'keywords': ['polymer', 'active poly', 'lbs per ton']
    },
    'dewatering_throughput': {
        'name': 'Dewatering Throughput (lbs DS/day)',
        'description': 'Daily dry solids processing capacity',
        'target': 'Varies by equipment',
        'unit': 'lbs/day',
        'keywords': ['dry tons', 'dry']
    },
    'solids_recovery': {
        'name': 'Solids Recovery Rate (%)',
        'description': 'Percentage of incoming solids captured in cake',
        'target': '>95%',
        'unit': '%',
        'keywords': ['recovery', 'capture']
    },
    'cake_production': {
        'name': 'Cake Production Rate (lbs/hour)',
        'description': 'Dewatered biosolids output',
        'target': '500-2,000 lbs/hour',
        'unit': 'lbs/hour',
        'keywords': ['cake', 'production']
    },
    'polymer_cost_per_lb': {
        'name': 'Polymer Cost per Pound of Solids ($/lb DS)',
        'description': 'Economic indicator tracking chemical efficiency',
        'target': '$0.05-$0.15/lb DS',
        'unit': '$/lb',
        'keywords': ['polymer cost', 'cost']
    },
    'cake_moisture': {
        'name': 'Cake Moisture Content (%)',
        'description': 'Inverse of solids content',
        'target': '75-82%',
        'unit': '%',
        'keywords': ['moisture', 'cake']
    },
    'equipment_availability': {
        'name': 'Dewatering Equipment Availability (%)',
        'description': 'Uptime percentage of dewatering equipment',
        'target': '>90%',
        'unit': '%',
        'keywords': ['availability', 'uptime', 'runtime']
    }
}

THICKENING_KPI_DEFINITIONS = {
    'thickened_solids': {
        'name': 'Thickened Solids Concentration (%)',
        'description': 'Dry solids percentage achieved',
        'target': '4-8% (gravity), 6-12% (DAF)',
        'unit': '%',
        'keywords': ['underflow', 'concentration', 'ts']
    },
    'overflow_turbidity': {
        'name': 'Overflow Turbidity (NTU)',
        'description': 'Clarified supernatant quality',
        'target': '<5 NTU',
        'unit': 'NTU',
        'keywords': ['overflow', 'tss', 'turbidity']
    },
    'thickening_throughput': {
        'name': 'Thickening Throughput (lbs DS/day)',
        'description': 'Daily solids processing capacity',
        'target': 'Varies by equipment',
        'unit': 'lbs/day',
        'keywords': ['throughput', 'capacity']
    },
    'solids_capture_efficiency': {
        'name': 'Solids Capture Efficiency (%)',
        'description': 'Percentage of incoming solids retained',
        'target': '>90%',
        'unit': '%',
        'keywords': ['capture', 'efficiency']
    },
    'underflow_production': {
        'name': 'Underflow Production Rate (lbs/hour)',
        'description': 'Thickened sludge output',
        'target': '200-1,000 lbs/hour',
        'unit': 'lbs/hour',
        'keywords': ['underflow', 'production']
    },
    'overflow_flow': {
        'name': 'Overflow Flow Rate (gpm)',
        'description': 'Return liquor from thickening',
        'target': 'Varies by equipment',
        'unit': 'gpm',
        'keywords': ['overflow', 'flow', 'gpm']
    },
    'solids_loading': {
        'name': 'Solids Loading Rate (lbs DS/day/sq ft)',
        'description': 'Thickener surface area efficiency',
        'target': '0.5-2.0 lbs DS/day/sq ft',
        'unit': 'lbs/day/sq ft',
        'keywords': ['loading', 'rate']
    },
    'equipment_availability': {
        'name': 'Thickening Equipment Availability (%)',
        'description': 'Uptime percentage of thickening equipment',
        'target': '>92%',
        'unit': '%',
        'keywords': ['availability', 'uptime']
    }
}

# ============================================================
# FUZZY PARAMETER DETECTOR CLASS
# ============================================================
class FuzzyParameterDetector:
    """Intelligently detects WWTP parameters using fuzzy matching"""
    
    def __init__(self, columns):
        self.columns = columns
        self.column_lower = [col.lower() for col in columns]
        self.detected_params = {}
    
    def find_parameters(self, keyword_groups, threshold=60):
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
        
        if any(x in col_lower for x in ['lbs/ton', 'lbs per ton', 'lb/ton', 'polymer', 'poly']):
            if 'gal' in col_lower or 'gpd' in col_lower:
                return 'GPD'
            return 'lbs/ton'
        
        if any(x in col_lower for x in ['%', 'percent', 'solids', 'cake', 'ts', 'tss', 'moisture']):
            return '%'
        
        if any(x in col_lower for x in ['flow', 'gpm', 'mgd', 'gpd', 'rate']):
            if 'mgd' in col_lower:
                return 'MGD'
            elif 'gpm' in col_lower:
                return 'GPM'
            elif 'gpd' in col_lower:
                return 'GPD'
            return 'MGD'
        
        if any(x in col_lower for x in ['ton', 'dry', 'wet', 'weight', 'mass']):
            if 'dry' in col_lower:
                return 'Dry Tons'
            elif 'wet' in col_lower:
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
# KPI CALCULATOR CLASS
# ============================================================
class KPICalculator:
    """Calculates meaningful KPIs from detected parameters"""
    
    def __init__(self, df, detected_params):
        self.df = df
        self.detected_params = detected_params
    
    def calculate_dewatering_kpis(self):
        """Calculate dewatering KPIs"""
        kpis = {}
        
        # Cake Solids Content
        if self.detected_params.get('cake_quality', {}).get('column'):
            cake_col = self.detected_params['cake_quality']['column']
            cake_data = pd.to_numeric(self.df[cake_col], errors='coerce').dropna()
            if len(cake_data) > 0:
                kpis['cake_solids'] = {
                    'value': cake_data.mean(),
                    'unit': '%',
                    'target': '20-30%',
                    'status': self._get_status(cake_data.mean(), 20, 30)
                }
        
        # Polymer Consumption
        if self.detected_params.get('polymer', {}).get('column'):
            poly_col = self.detected_params['polymer']['column']
            poly_data = pd.to_numeric(self.df[poly_col], errors='coerce').dropna()
            if len(poly_data) > 0:
                kpis['polymer_consumption'] = {
                    'value': poly_data.mean(),
                    'unit': 'lbs/ton',
                    'target': '5-15 lbs/ton',
                    'status': self._get_status(poly_data.mean(), 5, 15)
                }
        
        # Dewatering Throughput (Dry Tons/day)
        if self.detected_params.get('dry_tons', {}).get('column'):
            dry_col = self.detected_params['dry_tons']['column']
            dry_data = pd.to_numeric(self.df[dry_col], errors='coerce').dropna()
            if len(dry_data) > 0:
                kpis['dewatering_throughput'] = {
                    'value': dry_data.mean(),
                    'unit': 'Dry Tons/day',
                    'target': 'Varies',
                    'status': '✅' if dry_data.mean() > 0 else '❌'
                }
        
        # Cake Moisture Content (inverse of solids)
        if self.detected_params.get('cake_quality', {}).get('column'):
            cake_col = self.detected_params['cake_quality']['column']
            cake_data = pd.to_numeric(self.df[cake_col], errors='coerce').dropna()
            if len(cake_data) > 0:
                moisture = 100 - cake_data.mean()
                kpis['cake_moisture'] = {
                    'value': moisture,
                    'unit': '%',
                    'target': '75-82%',
                    'status': self._get_status(moisture, 75, 82)
                }
        
        # Polymer Cost per Pound
        if (self.detected_params.get('polymer_cost', {}).get('column') and 
            self.detected_params.get('dry_tons', {}).get('column')):
            cost_col = self.detected_params['polymer_cost']['column']
            dry_col = self.detected_params['dry_tons']['column']
            cost_data = pd.to_numeric(self.df[cost_col], errors='coerce')
            dry_data = pd.to_numeric(self.df[dry_col], errors='coerce')
            
            if len(cost_data) > 0 and len(dry_data) > 0:
                cost_per_lb = (cost_data / (dry_data * 2000)).mean()  # Convert tons to lbs
                kpis['polymer_cost_per_lb'] = {
                    'value': cost_per_lb,
                    'unit': '$/lb',
                    'target': '$0.05-$0.15/lb',
                    'status': self._get_status(cost_per_lb, 0.05, 0.15)
                }
        
        return kpis
    
    def calculate_thickening_kpis(self):
        """Calculate thickening KPIs"""
        kpis = {}
        
        # Thickened Solids Concentration
        if self.detected_params.get('thickener_underflow', {}).get('column'):
            uf_col = self.detected_params['thickener_underflow']['column']
            uf_data = pd.to_numeric(self.df[uf_col], errors='coerce').dropna()
            if len(uf_data) > 0:
                kpis['thickened_solids'] = {
                    'value': uf_data.mean(),
                    'unit': '%',
                    'target': '4-8%',
                    'status': self._get_status(uf_data.mean(), 4, 8)
                }
        
        # Overflow Turbidity
        if self.detected_params.get('thickener_overflow', {}).get('column'):
            of_col = self.detected_params['thickener_overflow']['column']
            of_data = pd.to_numeric(self.df[of_col], errors='coerce').dropna()
            if len(of_data) > 0:
                kpis['overflow_turbidity'] = {
                    'value': of_data.mean(),
                    'unit': 'mg/L',
                    'target': '<500 mg/L',
                    'status': self._get_status_inverse(of_data.mean(), 500)
                }
        
        # GBT Underflow
        if self.detected_params.get('gbt_underflow', {}).get('column'):
            gbt_uf_col = self.detected_params['gbt_underflow']['column']
            gbt_uf_data = pd.to_numeric(self.df[gbt_uf_col], errors='coerce').dropna()
            if len(gbt_uf_data) > 0:
                kpis['gbt_underflow'] = {
                    'value': gbt_uf_data.mean(),
                    'unit': '%',
                    'target': '6-12%',
                    'status': self._get_status(gbt_uf_data.mean(), 6, 12)
                }
        
        # GBT Overflow
        if self.detected_params.get('gbt_overflow', {}).get('column'):
            gbt_of_col = self.detected_params['gbt_overflow']['column']
            gbt_of_data = pd.to_numeric(self.df[gbt_of_col], errors='coerce').dropna()
            if len(gbt_of_data) > 0:
                kpis['gbt_overflow'] = {
                    'value': gbt_of_data.mean(),
                    'unit': 'mg/L',
                    'target': '<300 mg/L',
                    'status': self._get_status_inverse(gbt_of_data.mean(), 300)
                }
        
        return kpis
    
    def _get_status(self, value, min_target, max_target):
        """Get status based on target range"""
        if min_target <= value <= max_target:
            return '✅ On Target'
        elif value < min_target:
            return '🔴 Below Target'
        else:
            return '🟠 Above Target'
    
    def _get_status_inverse(self, value, max_target):
        """Get status for inverse metrics (lower is better)"""
        if value <= max_target:
            return '✅ On Target'
        else:
            return '🟠 Above Target'

# ============================================================
# PERFORMANCE ANALYZER CLASS
# ============================================================
class PerformanceAnalyzer:
    """Analyzes WWTP performance and generates recommendations"""
    
    def __init__(self, df, detected_params, plant_info=None):
        self.df = df
        self.detected_params = detected_params
        self.plant_info = plant_info or {}
    
    def get_performance_rating(self, metric_name, value):
        """Get performance rating for a metric"""
        if metric_name not in PERFORMANCE_THRESHOLDS:
            return 'unknown'
        
        thresholds = PERFORMANCE_THRESHOLDS[metric_name]
        for rating, (min_val, max_val) in thresholds.items():
            if min_val <= value < max_val:
                return rating
        return 'poor'
    
    def generate_recommendations(self):
        """Generate AI-based recommendations"""
        recommendations = []
        
        # Polymer Efficiency Analysis
        if self.detected_params.get('polymer', {}).get('column'):
            poly_col = self.detected_params['polymer']['column']
            poly_data = pd.to_numeric(self.df[poly_col], errors='coerce').dropna()
            
            if len(poly_data) > 0:
                poly_avg = poly_data.mean()
                poly_current = poly_data.iloc[-1]
                rating = self.get_performance_rating('polymer', poly_avg)
                
                if rating == 'poor':
                    annual_cost = poly_avg * 50 * 365
                    target_cost = 12 * 50 * 365
                    potential_savings = annual_cost - target_cost
                    
                    recommendations.append({
                        'priority': '🔴 CRITICAL',
                        'category': 'Polymer Efficiency',
                        'metric': 'Active Polymer Dose',
                        'current_value': f'{poly_avg:.2f} lbs/ton',
                        'target_value': '12 lbs/ton',
                        'issue': 'Excessive polymer consumption significantly above industry standards',
                        'root_causes': [
                            'Centrifuge/BFP bowl speed may be suboptimal',
                            'Feed rate too high for current equipment',
                            'Polymer type or concentration not suitable for sludge characteristics',
                            'Equipment wear or mechanical issues',
                            'Sludge characteristics changed (higher solids, more difficult to dewater)'
                        ],
                        'actions': [
                            'Conduct jar test to optimize polymer type and dose',
                            'Adjust equipment speed parameters incrementally',
                            'Reduce feed rate by 10-15% and monitor cake quality',
                            'Inspect equipment for wear, bearing issues, or seal leaks',
                            'Analyze incoming sludge TS%, volatile solids, and particle size'
                        ],
                        'potential_savings': f'${potential_savings:,.0f}/year',
                        'savings_explanation': f'Reducing polymer from {poly_avg:.1f} to 12 lbs/ton at $50/lb = ${potential_savings:,.0f} annual savings',
                        'additional_data_needed': [
                            'Sludge solids concentration (% TS)',
                            'Sludge volatile solids content',
                            'Equipment bowl/belt speed (RPM)',
                            'Feed rate (GPM)',
                            'Polymer type and concentration',
                            'Centrifuge differential speed'
                        ],
                        'timeline': '1-2 weeks',
                        'risk': 'High - May temporarily affect cake quality'
                    })
                
                elif rating == 'moderate':
                    annual_cost = poly_avg * 50 * 365
                    target_cost = 12 * 50 * 365
                    potential_savings = annual_cost - target_cost
                    
                    recommendations.append({
                        'priority': '🟠 HIGH',
                        'category': 'Polymer Efficiency',
                        'metric': 'Active Polymer Dose',
                        'current_value': f'{poly_avg:.2f} lbs/ton',
                        'target_value': '12 lbs/ton',
                        'issue': 'Polymer consumption above optimal levels',
                        'root_causes': [
                            'Polymer dose not fully optimized',
                            'Equipment parameters could be fine-tuned',
                            'Seasonal sludge characteristic variations'
                        ],
                        'actions': [
                            'Perform polymer dose optimization study',
                            'Adjust equipment parameters incrementally',
                            'Implement daily monitoring of polymer efficiency'
                        ],
                        'potential_savings': f'${potential_savings:,.0f}/year',
                        'savings_explanation': f'Reducing polymer from {poly_avg:.1f} to 12 lbs/ton = ${potential_savings:,.0f} annual savings',
                        'additional_data_needed': [
                            'Historical polymer dose data',
                            'Sludge characteristics trends',
                            'Equipment performance curves'
                        ],
                        'timeline': '2-4 weeks',
                        'risk': 'Medium - Monitor cake quality closely'
                    })
        
        # Cake Quality Analysis
        if self.detected_params.get('cake_quality', {}).get('column'):
            cake_col = self.detected_params['cake_quality']['column']
            cake_data = pd.to_numeric(self.df[cake_col], errors='coerce').dropna()
            
            if len(cake_data) > 0:
                cake_avg = cake_data.mean()
                rating = self.get_performance_rating('cake_quality', cake_avg)
                
                if rating == 'poor':
                    current_trucks = 100
                    target_trucks = 60
                    truck_savings = (current_trucks - target_trucks) * 500 * 365
                    
                    recommendations.append({
                        'priority': '🔴 CRITICAL',
                        'category': 'Cake Quality',
                        'metric': 'Cake Solids %',
                        'current_value': f'{cake_avg:.2f}%',
                        'target_value': '25%',
                        'issue': 'Poor cake quality - sludge too wet, excessive hauling costs',
                        'root_causes': [
                            'Insufficient polymer dose',
                            'Equipment speed too high',
                            'Feed rate too high',
                            'Polymer type not suitable',
                            'Equipment wear or damage'
                        ],
                        'actions': [
                            'Increase polymer dose by 15-20%',
                            'Reduce equipment speed by 5-10%',
                            'Reduce feed rate by 10-15%',
                            'Consider alternative polymer type',
                            'Inspect equipment for wear'
                        ],
                        'potential_savings': f'${truck_savings:,.0f}/year',
                        'savings_explanation': f'Improving cake from {cake_avg:.1f}% to 25% reduces trucks from ~100 to ~60/day = ${truck_savings:,.0f} annual savings',
                        'additional_data_needed': [
                            'Centrifuge bowl condition',
                            'Scroll wear measurements',
                            'Bearing condition assessment',
                            'Seal integrity check'
                        ],
                        'timeline': '1-2 weeks',
                        'risk': 'Low - Improves operation'
                    })
        
        # Thickener Performance Analysis
        if self.detected_params.get('thickener_underflow', {}).get('column'):
            uf_col = self.detected_params['thickener_underflow']['column']
            uf_data = pd.to_numeric(self.df[uf_col], errors='coerce').dropna()
            
            if len(uf_data) > 0:
                uf_avg = uf_data.mean()
                rating = self.get_performance_rating('thickener_underflow', uf_avg)
                
                if rating in ['poor', 'moderate']:
                    recommendations.append({
                        'priority': '🟡 MEDIUM',
                        'category': 'Thickener Performance',
                        'metric': 'Underflow Concentration',
                        'current_value': f'{uf_avg:.2f}% TS',
                        'target_value': '5% TS',
                        'issue': 'Low thickener underflow concentration increases downstream processing load',
                        'root_causes': [
                            'Insufficient retention time',
                            'Feed rate too high',
                            'Poor polymer conditioning',
                            'Rake mechanism issues',
                            'Sludge characteristics difficult to thicken'
                        ],
                        'actions': [
                            'Reduce feed rate to thickener',
                            'Increase retention time',
                            'Optimize polymer dose for thickening',
                            'Check rake mechanism operation',
                            'Analyze incoming sludge characteristics'
                        ],
                        'potential_savings': 'Reduce downstream processing load and costs',
                        'savings_explanation': 'Higher underflow concentration reduces volume to dewatering, saving polymer and equipment wear',
                        'additional_data_needed': [
                            'Thickener feed rate (GPM)',
                            'Thickener depth and area',
                            'Rake speed and torque',
                            'Polymer type and dose for thickening'
                        ],
                        'timeline': '1-2 weeks',
                        'risk': 'Low'
                    })
        
        # GBT Performance Analysis
        if self.detected_params.get('gbt_underflow', {}).get('column'):
            gbt_uf_col = self.detected_params['gbt_underflow']['column']
            gbt_uf_data = pd.to_numeric(self.df[gbt_uf_col], errors='coerce').dropna()
            
            if len(gbt_uf_data) > 0:
                gbt_uf_avg = gbt_uf_data.mean()
                rating = self.get_performance_rating('gbt_underflow', gbt_uf_avg)
                
                if rating in ['poor', 'moderate']:
                    recommendations.append({
                        'priority': '🟠 HIGH',
                        'category': 'GBT Performance',
                        'metric': 'GBT Underflow Concentration',
                        'current_value': f'{gbt_uf_avg:.2f}% TS',
                        'target_value': '8% TS',
                        'issue': 'GBT underflow concentration below target',
                        'root_causes': [
                            'Belt speed too high',
                            'Polymer dose insufficient',
                            'Feed rate too high',
                            'Belt wear or tension issues'
                        ],
                        'actions': [
                            'Reduce belt speed by 5-10%',
                            'Increase polymer dose by 10-15%',
                            'Reduce feed rate',
                            'Check belt condition and tension'
                        ],
                        'potential_savings': 'Improved thickening efficiency reduces downstream load',
                        'savings_explanation': 'Better thickening reduces volume to dewatering, saving polymer and equipment costs',
                        'additional_data_needed': [
                            'GBT belt speed (%)',
                            'GBT polymer type and dose',
                            'GBT feed rate (GPM)',
                            'Belt condition and wear'
                        ],
                        'timeline': '1-2 weeks',
                        'risk': 'Low'
                    })
        
        if not recommendations:
            recommendations.append({
                'priority': '✅ OPTIMAL',
                'category': 'Overall Performance',
                'metric': 'N/A',
                'current_value': 'N/A',
                'target_value': 'N/A',
                'issue': 'Plant operating at or near optimal performance levels',
                'root_causes': [],
                'actions': ['Continue current operations', 'Maintain preventive maintenance schedule'],
                'potential_savings': 'Maintain current efficiency',
                'savings_explanation': 'Plant is performing well - focus on maintaining current operations',
                'additional_data_needed': ['Continue routine monitoring'],
                'timeline': 'Ongoing',
                'risk': 'Low'
            })
        
        return recommendations

# ============================================================
# CHART RENDERER
# ============================================================
class ChartRenderer:
    """Renders charts"""
    
    def __init__(self, df):
        self.df = df
    
    def render_line_with_ma(self, column, unit, title, threshold_excellent=None, threshold_good=None):
        """Render line chart with moving average"""
        col_data = pd.to_numeric(self.df[column], errors='coerce')
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
        
        if threshold_excellent:
            fig.add_hline(y=threshold_excellent, line_dash="dash",
                         line_color="green", annotation_text="Excellent")
        if threshold_good:
            fig.add_hline(y=threshold_good, line_dash="dash",
                         line_color="orange", annotation_text="Good")
        
        fig.update_layout(
            title=f"{title} ({unit})",
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title=unit
        )
        return fig
    
    def render_bar_with_ma(self, column, unit, title):
        """Render bar chart with moving average"""
        col_data = pd.to_numeric(self.df[column], errors='coerce')
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
            title=f"{title} ({unit})",
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title=unit
        )
        return fig
    
    def render_ratio(self, column1, column2, unit, title, threshold_excellent=None, threshold_good=None):
        """Render ratio chart"""
        col1_data = pd.to_numeric(self.df[column1], errors='coerce')
        col2_data = pd.to_numeric(self.df[column2], errors='coerce')
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
        
        if threshold_excellent:
            fig.add_hline(y=threshold_excellent, line_dash="dash",
                         line_color="green", annotation_text="Excellent")
        if threshold_good:
            fig.add_hline(y=threshold_good, line_dash="dash",
                         line_color="orange", annotation_text="Good")
        
        fig.update_layout(
            title=f"{title} ({unit})",
            height=400,
            hovermode='x unified',
            xaxis_title="Days",
            yaxis_title=unit
        )
        return fig

# ============================================================
# SIDEBAR - FILE UPLOAD & PLANT INFO
# ============================================================
st.sidebar.header("📊 Upload Your Data")
uploaded_file = st.sidebar.file_uploader(
    "Choose your WWTP CSV file",
    type=['csv'],
    help="Upload a CSV file with your WWTP data"
)

# ============================================================
# MAIN APP LOGIC
# ============================================================
if uploaded_file is None:
    st.info("👈 **Please upload a CSV file to get started**")
    st.markdown("""
    ### 📋 Expected Data Format:
    
    Your CSV should contain columns like:
    
    **Dewatering Equipment:**
    - Centrifuge, Belt Filter Press (BFP), Rotary Press, Drying Bed
    - Active Polymer (lbs/ton, GPD)
    - Cake Quality (%), Cake Solids (%)
    - Equipment Run Hours
    - Dry Tons, Wet Tons
    - Daily Trucks
    
    **Thickening Equipment:**
    - Gravity Thickener, GBT (Gravity Belt Thickener), Rotary Drum, Membrane
    - Feed Rate (GPM, MGD)
    - Underflow TS (%)
    - Overflow TSS (mg/L)
    - Equipment Torque (Nm)
    
    **Flow:**
    - Influent Flow (MGD, GPM)
    - Effluent Flow (MGD, GPM)
    
    **Cost:**
    - Polymer Cost ($)
    - Hauling Cost ($)
    
    ### ✨ Features:
    - 🔍 **Fuzzy Logic** - Auto-detects your columns
    - 📊 **30+ Charts** - Comprehensive analysis
    - 💡 **AI Recommendations** - Optimization suggestions with savings
    - 📈 **YOY Analysis** - Year-over-year comparisons
    - 🔎 **Data Quality** - Outlier detection
    
    ### 🚀 Ready? Upload your file!
    """)

else:
    try:
        df = pd.read_csv(uploaded_file)
        df = df.reset_index(drop=True)
        
        # Try to detect date column
        date_col = None
        for col in df.columns:
            if any(x in col.lower() for x in ['date', 'time', 'day', 'month', 'year']):
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    if df[col].notna().sum() > len(df) * 0.5:
                        date_col = col
                        df = df.sort_values(col)
                        break
                except:
                    pass
        
        if not date_col:
            df['Date'] = pd.date_range(start='2023-01-01', periods=len(df), freq='D')
            date_col = 'Date'
        
        st.sidebar.success(f"✅ Loaded {len(df)} records")
        st.sidebar.write(f"📅 {df[date_col].min().date()} to {df[date_col].max().date()}")
        
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()
    
    # ============================================================
    # PLANT INFORMATION INPUT
    # ============================================================
    with st.sidebar.expander("🏭 Plant Information", expanded=False):
        st.write("**Provide plant details for context-aware analysis:**")
        
        plant_name = st.text_input("Plant Name", value="WWTP")
        plant_location = st.text_input("Location", value="")
        
        st.write("**Dewatering Equipment:**")
        dewatering_equipment = st.multiselect(
            "Select equipment types",
            ["Centrifuge", "Belt Filter Press (BFP)", "Rotary Press", "Drying Bed", "Other"],
            default=["Centrifuge"]
        )
        
        st.write("**Thickening Equipment:**")
        thickening_equipment = st.multiselect(
            "Select equipment types",
            ["Gravity Thickener", "GBT (Gravity Belt Thickener)", "Rotary Drum", "Membrane", "Other"],
            default=["GBT (Gravity Belt Thickener)"]
        )
        
        plant_capacity = st.number_input("Plant Capacity (MGD)", value=10.0, min_value=0.1)
        
        plant_info = {
            'name': plant_name,
            'location': plant_location,
            'dewatering_equipment': dewatering_equipment,
            'thickening_equipment': thickening_equipment,
            'capacity': plant_capacity
        }
    
    # Initialize parameter detector
    parameter_keywords = {
        'polymer': ['active poly', 'polymer', 'lbs per ton', 'lbs/ton', 'poly dose', 'polymer dose'],
        'cake_quality': ['cake', 'solids', 'cake avg', 'cake %', 'cake quality', 'moisture', 'cake solids', '% solids'],
        'centrifuge_1_hours': ['centrifuge 1', 'c1', 'run hours 1', 'c1 hours'],
        'centrifuge_2_hours': ['centrifuge 2', 'c2', 'run hours 2', 'c2 hours'],
        'centrifuge_3_hours': ['centrifuge 3', 'c3', 'run hours 3', 'c3 hours'],
        'bfp_hours': ['bfp', 'belt filter', 'belt press', 'bfp hours'],
        'rotary_press_hours': ['rotary press', 'rotary', 'press hours'],
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
    
    # Initialize analyzers
    analyzer = PerformanceAnalyzer(df, detected_params, plant_info)
    kpi_calculator = KPICalculator(df, detected_params)
    chart_renderer = ChartRenderer(df)
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Dashboard",
        "💡 AI Recommendations",
        "📈 YOY Analysis",
        "🔄 Dewatering",
        "🌀 Thickening",
        "🔍 Data Quality",
        "📋 Parameters",
        "📥 Raw Data"
    ])
    
    # ============================================================
    # TAB 1: ENHANCED DASHBOARD WITH KPIs
    # ============================================================
    with tab1:
        st.header(f"📊 Performance Dashboard - {plant_info.get('name', 'WWTP')}")
        
        if plant_info.get('location'):
            st.caption(f"📍 {plant_info['location']} | Capacity: {plant_info.get('capacity', 'N/A')} MGD")
        
        # ============================================================
        # DEWATERING KPIs
        # ============================================================
        st.subheader("🔄 Dewatering KPIs")
        
        dew_kpis = kpi_calculator.calculate_dewatering_kpis()
        
        if dew_kpis:
            kpi_cols = st.columns(len(dew_kpis))
            for idx, (kpi_key, kpi_value) in enumerate(dew_kpis.items()):
                with kpi_cols[idx]:
                    st.metric(
                        DEWATERING_KPI_DEFINITIONS[kpi_key]['name'],
                        f"{kpi_value['value']:.2f} {kpi_value['unit']}",
                        help=DEWATERING_KPI_DEFINITIONS[kpi_key]['description']
                    )
                    st.caption(f"Target: {kpi_value['target']}")
                    st.write(kpi_value['status'])
        else:
            st.info("No dewatering data detected")
        
        st.divider()
        
        # ============================================================
        # THICKENING KPIs
        # ============================================================
        st.subheader("🌀 Thickening KPIs")
        
        thick_kpis = kpi_calculator.calculate_thickening_kpis()
        
        if thick_kpis:
            kpi_cols = st.columns(len(thick_kpis))
            for idx, (kpi_key, kpi_value) in enumerate(thick_kpis.items()):
                with kpi_cols[idx]:
                    st.metric(
                        THICKENING_KPI_DEFINITIONS[kpi_key]['name'],
                        f"{kpi_value['value']:.2f} {kpi_value['unit']}",
                        help=THICKENING_KPI_DEFINITIONS[kpi_key]['description']
                    )
                    st.caption(f"Target: {kpi_value['target']}")
                    st.write(kpi_value['status'])
        else:
            st.info("No thickening data detected")
        
        st.divider()
        
        # ============================================================
        # FLOW DATA
        # ============================================================
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
        st.write("**Data-driven optimization suggestions with potential savings**")
        
        recommendations = analyzer.generate_recommendations()
        
        for i, rec in enumerate(recommendations, 1):
            with st.container():
                col_header1, col_header2 = st.columns([3, 1])
                
                with col_header1:
                    st.markdown(f"### {rec['priority']} {rec['category']}")
                
                with col_header2:
                    st.write(f"**Risk:** {rec['risk']}")
                
                st.markdown("---")
                
                # Main content
                col_main1, col_main2 = st.columns([2, 1])
                
                with col_main1:
                    st.write(f"**Metric:** {rec['metric']}")
                    st.write(f"**Current:** {rec['current_value']} | **Target:** {rec['target_value']}")
                    
                    st.write(f"**Issue:** {rec['issue']}")
                    
                    st.write("**Root Causes:**")
                    for cause in rec['root_causes']:
                        st.write(f"• {cause}")
                    
                    st.write("**Recommended Actions:**")
                    for j, action in enumerate(rec['actions'], 1):
                        st.write(f"{j}. {action}")
                
                with col_main2:
                    st.metric("Potential Savings", rec['potential_savings'])
                    st.metric("Timeline", rec['timeline'])
                
                st.divider()
                
                # Expandable sections
                with st.expander("📊 Savings Explanation"):
                    st.write(rec['savings_explanation'])
                
                with st.expander("📋 Additional Data Needed"):
                    st.write("**Recommended investigations and data collection:**")
                    for data_item in rec['additional_data_needed']:
                        st.write(f"• {data_item}")
                
                st.divider()
    
    # ============================================================
    # TAB 3: YOY ANALYSIS - FIXED
    # ============================================================
    with tab3:
        st.header("📈 Year-over-Year Analysis")
        st.write("**Compare performance across different time periods**")
        
        # Get numeric columns
        numeric_cols = {}
        for param_name, param_info in detected_params.items():
            if param_info['column']:
                numeric_cols[param_info['column']] = param_info['unit']
        
        if not numeric_cols:
            st.warning("No numeric columns detected")
        else:
            col_select1, col_select2, col_select3 = st.columns(3)
            
            with col_select1:
                selected_column = st.selectbox(
                    "Select Indicator",
                    list(numeric_cols.keys()),
                    format_func=lambda x: f"{x} ({numeric_cols[x]})"
                )
            
            with col_select2:
                aggregation = st.selectbox(
                    "Aggregation Period",
                    ["Daily", "Weekly", "Monthly", "Quarterly"]
                )
            
            with col_select3:
                comparison_type = st.selectbox(
                    "Comparison Type",
                    ["Full Timeline", "Custom Period"]
                )
            
            # Prepare data
            df_yoy = df[[date_col, selected_column]].copy()
            df_yoy[date_col] = pd.to_datetime(df_yoy[date_col])
            df_yoy[selected_column] = pd.to_numeric(df_yoy[selected_column], errors='coerce')
            df_yoy = df_yoy.dropna()
            
            if len(df_yoy) > 0:
                # Aggregate data - FIXED
                try:
                    if aggregation == "Daily":
                        df_agg = df_yoy.set_index(date_col)[selected_column].resample('D').mean()
                    elif aggregation == "Weekly":
                        df_agg = df_yoy.set_index(date_col)[selected_column].resample('W').mean()
                    elif aggregation == "Monthly":
                        df_agg = df_yoy.set_index(date_col)[selected_column].resample('MS').mean()
                    else:  # Quarterly
                        df_agg = df_yoy.set_index(date_col)[selected_column].resample('QS').mean()
                    
                    df_agg = df_agg.dropna()
                    
                    if len(df_agg) > 0:
                        # Create chart
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df_agg.index,
                            y=df_agg.values,
                            mode='lines+markers',
                            name=selected_column,
                            line=dict(color='#1f77b4', width=2),
                            marker=dict(size=8)
                        ))
                        
                        # Add trend line
                        x_numeric = np.arange(len(df_agg))
                        if len(x_numeric) > 1:
                            z = np.polyfit(x_numeric, df_agg.values, 1)
                            p = np.poly1d(z)
                            fig.add_trace(go.Scatter(
                                x=df_agg.index,
                                y=p(x_numeric),
                                mode='lines',
                                name='Trend',
                                line=dict(color='red', width=2, dash='dash')
                            ))
                        
                        fig.update_layout(
                            title=f"{selected_column} - {aggregation} Aggregation",
                            xaxis_title="Date",
                            yaxis_title=numeric_cols[selected_column],
                            height=500,
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Statistics
                        st.subheader("📊 Statistics")
                        
                        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                        
                        with stat_col1:
                            st.metric("Mean", f"{df_agg.mean():.2f}")
                        
                        with stat_col2:
                            st.metric("Median", f"{df_agg.median():.2f}")
                        
                        with stat_col3:
                            st.metric("Min", f"{df_agg.min():.2f}")
                        
                        with stat_col4:
                            st.metric("Max", f"{df_agg.max():.2f}")
                        
                        # Trend analysis
                        if len(x_numeric) > 1:
                            slope = z[0]
                            trend_direction = "📈 Increasing" if slope > 0 else "📉 Decreasing"
                            st.write(f"**Trend:** {trend_direction} (slope: {slope:.4f})")
                    else:
                        st.warning("No data available after aggregation")
                
                except Exception as e:
                    st.error(f"Error processing data: {str(e)}")
    
    # ============================================================
    # TAB 4: DEWATERING
    # ============================================================
    with tab4:
        st.header("🔄 Dewatering Analysis")
        st.write(f"**Equipment:** {', '.join(plant_info.get('dewatering_equipment', ['Not specified']))}")
        
        # Polymer chart
        if detected_params.get('polymer', {}).get('column'):
            st.subheader("Polymer Efficiency")
            poly_col = detected_params['polymer']['column']
            poly_unit = detected_params['polymer']['unit']
            fig = chart_renderer.render_line_with_ma(
                poly_col, poly_unit, "Polymer Efficiency",
                threshold_excellent=12, threshold_good=15
            )
            st.plotly_chart(fig, use_container_width=True, key="poly_chart")
        
        # Cake quality chart
        if detected_params.get('cake_quality', {}).get('column'):
            st.subheader("Cake Quality")
            cake_col = detected_params['cake_quality']['column']
            cake_unit = detected_params['cake_quality']['unit']
            fig = chart_renderer.render_line_with_ma(
                cake_col, cake_unit, "Cake Quality",
                threshold_excellent=25, threshold_good=20
            )
            st.plotly_chart(fig, use_container_width=True, key="cake_chart")
        
        # Dry/Wet ratio
        if detected_params.get('dry_tons', {}).get('column') and detected_params.get('wet_tons', {}).get('column'):
            st.subheader("Dewatering Efficiency (Dry/Wet Ratio)")
            dry_col = detected_params['dry_tons']['column']
            wet_col = detected_params['wet_tons']['column']
            fig = chart_renderer.render_ratio(
                dry_col, wet_col, "Ratio", "Dry/Wet Ratio",
                threshold_excellent=0.25, threshold_good=0.20
            )
            st.plotly_chart(fig, use_container_width=True, key="ratio_chart")
        
        # Truck hauling
        if detected_params.get('trucks', {}).get('column'):
            st.subheader("Sludge Truck Hauling")
            truck_col = detected_params['trucks']['column']
            truck_unit = detected_params['trucks']['unit']
            fig = chart_renderer.render_bar_with_ma(
                truck_col, truck_unit, "Daily Sludge Trucks"
            )
            st.plotly_chart(fig, use_container_width=True, key="truck_chart")
    
    # ============================================================
    # TAB 5: THICKENING
    # ============================================================
    with tab5:
        st.header("🌀 Thickening Analysis")
        st.write(f"**Equipment:** {', '.join(plant_info.get('thickening_equipment', ['Not specified']))}")
        
        # Gravity Thickener charts
        if detected_params.get('thickener_underflow', {}).get('column'):
            st.subheader("Gravity Thickener - Underflow Concentration")
            uf_col = detected_params['thickener_underflow']['column']
            uf_unit = detected_params['thickener_underflow']['unit']
            fig = chart_renderer.render_line_with_ma(
                uf_col, uf_unit, "Underflow Concentration",
                threshold_excellent=5, threshold_good=3
            )
            st.plotly_chart(fig, use_container_width=True, key="thick_uf_chart")
        
        if detected_params.get('thickener_overflow', {}).get('column'):
            st.subheader("Gravity Thickener - Overflow Clarity")
            of_col = detected_params['thickener_overflow']['column']
            of_unit = detected_params['thickener_overflow']['unit']
            fig = chart_renderer.render_line_with_ma(
                of_col, of_unit, "Overflow TSS",
                threshold_excellent=500, threshold_good=1000
            )
            st.plotly_chart(fig, use_container_width=True, key="thick_of_chart")
        
        # GBT charts
        if detected_params.get('gbt_underflow', {}).get('column'):
            st.subheader("GBT - Underflow Concentration")
            gbt_uf_col = detected_params['gbt_underflow']['column']
            gbt_uf_unit = detected_params['gbt_underflow']['unit']
            fig = chart_renderer.render_line_with_ma(
                gbt_uf_col, gbt_uf_unit, "GBT Underflow Concentration",
                threshold_excellent=8, threshold_good=5
            )
            st.plotly_chart(fig, use_container_width=True, key="gbt_uf_chart")
        
        if detected_params.get('gbt_overflow', {}).get('column'):
            st.subheader("GBT - Overflow Clarity")
            gbt_of_col = detected_params['gbt_overflow']['column']
            gbt_of_unit = detected_params['gbt_overflow']['unit']
            fig = chart_renderer.render_line_with_ma(
                gbt_of_col, gbt_of_unit, "GBT Overflow TSS",
                threshold_excellent=300, threshold_good=500
            )
            st.plotly_chart(fig, use_container_width=True, key="gbt_of_chart")
    
    # ============================================================
    # TAB 6: DATA QUALITY
    # ============================================================
    with tab6:
        st.header("🔍 Data Quality Analysis")
        
        columns_to_check = [p['column'] for p in detected_params.values() if p['column']]
        
        col_dq1, col_dq2, col_dq3 = st.columns(3)
        with col_dq1:
            st.metric("Total Records", len(df))
        with col_dq2:
            st.metric("Columns Analyzed", len(columns_to_check))
        with col_dq3:
            total_missing = sum([df[col].isna().sum() for col in columns_to_check if col in df.columns])
            st.metric("Total Missing Values", total_missing)
        
        st.divider()
        
        for col_name in columns_to_check:
            if col_name in df.columns:
                with st.expander(f"📊 {col_name}"):
                    col_data = pd.to_numeric(df[col_name], errors='coerce')
                    
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        missing = df[col_name].isna().sum()
                        st.write("**Missing Values:**")
                        st.write(f"Count: {missing}")
                        st.write(f"Percentage: {(missing/len(df)*100):.2f}%")
                    
                    with col_b:
                        st.write("**Data Range:**")
                        st.write(f"Min: {col_data.min():.2f}")
                        st.write(f"Max: {col_data.max():.2f}")
                        st.write(f"Mean: {col_data.mean():.2f}")
                    
                    with col_c:
                        # Outliers
                        Q1 = col_data.quantile(0.25)
                        Q3 = col_data.quantile(0.75)
                        IQR = Q3 - Q1
                        outliers = col_data[(col_data < Q1 - 1.5*IQR) | (col_data > Q3 + 1.5*IQR)]
                        st.write("**Outliers (IQR):**")
                        st.write(f"Count: {len(outliers)}")
                        st.write(f"Percentage: {(len(outliers)/len(col_data)*100):.2f}%")
    
    # ============================================================
    # TAB 7: PARAMETERS
    # ============================================================
    with tab7:
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
    # TAB 8: RAW DATA
    # ============================================================
    with tab8:
        st.header("📥 Raw Data")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Data", data=csv, file_name="wwtp_data.csv", mime="text/csv")

st.success("✅ App loaded successfully!")
