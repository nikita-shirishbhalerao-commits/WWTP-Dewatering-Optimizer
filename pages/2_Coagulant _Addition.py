import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import warnings
warnings.filterwarnings('ignore')

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import (
    VEOLIA, inject_theme, render_header, status_chip, priority_chip,
    format_threshold_footnote as _format_threshold_footnote,
    PLOTLY_CONFIG, render_chart_with_download,
    load_process_csv, detect_parameters as _detect_parameters,
    render_mapping_editor as _render_mapping_editor,
    CorrelationAnalyzer, ChartRenderer, render_kpi_grid,
    BaseKPICalculator, BaseRecommendationEngine, render_recommendations_tab,
)

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Coagulant Addition Analyzer",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_theme()
render_header("🧪 AI-Powered Coagulant Addition Performance Analyzer")

# ============================================================
# PERFORMANCE THRESHOLDS
# ============================================================
PERFORMANCE_THRESHOLDS = {
    'turbidity_removal': {'excellent': (90, float('inf')), 'good': (80, 90), 'moderate': (60, 80), 'poor': (0, 60)},
    'effluent_turbidity': {'excellent': (0, 2), 'good': (2, 5), 'moderate': (5, 10), 'poor': (10, float('inf'))},
    'residual_alkalinity': {'excellent': (50, float('inf')), 'good': (30, 50), 'moderate': (15, 30), 'poor': (0, 15)},
    'ph_depression': {'excellent': (0, 0.3), 'good': (0.3, 0.6), 'moderate': (0.6, 1.0), 'poor': (1.0, float('inf'))},
    'tss_removal': {'excellent': (85, float('inf')), 'good': (70, 85), 'moderate': (50, 70), 'poor': (0, 50)},
    'tp_removal': {'excellent': (85, float('inf')), 'good': (70, 85), 'moderate': (50, 70), 'poor': (0, 50)},
    'dose_vs_jar_test': {'excellent': (0, 5), 'good': (5, 15), 'moderate': (15, 30), 'poor': (30, float('inf'))},
}


def render_footnote(metric_key, unit="", fallback=None):
    txt = _format_threshold_footnote(PERFORMANCE_THRESHOLDS, metric_key, unit)
    if txt:
        st.caption(f"📊 Performance benchmark — {txt}")
    elif fallback:
        st.caption(fallback)


# ============================================================
# KPI DEFINITIONS
# ============================================================
COAGULANT_KPI_DEFINITIONS = {
    'coagulant_dose': {'name': 'Coagulant Dose (mg/L)', 'description': 'Coagulant applied per unit volume treated. Reported informationally — effective dose varies widely by coagulant type and treatment goal, see the typical range shown for your selected coagulant.'},
    'dose_vs_jar_test': {'name': 'Feed Dose vs. Jar Test Optimal (% deviation)', 'description': 'How far the actual feed dose deviates from the lab-determined optimal dose. This is the most rigorous dose KPI since it compares against your own bench-test result, not a generic literature range.'},
    'turbidity_removal': {'name': 'Turbidity Removal Efficiency (%)', 'description': 'Percentage reduction in turbidity across coagulation/clarification.'},
    'effluent_turbidity': {'name': 'Effluent Turbidity (NTU)', 'description': 'Clarity after coagulant addition and settling/clarification.'},
    'ph_depression': {'name': 'pH Depression (units)', 'description': 'Drop in pH caused by coagulant addition. Most coagulants are acidic salts that consume alkalinity as they react.'},
    'residual_alkalinity': {'name': 'Residual Alkalinity (mg/L as CaCO3)', 'description': 'Buffering capacity remaining after the coagulant reaction. Low residual alkalinity risks pH instability and reduced coagulation efficiency.'},
    'tss_removal': {'name': 'TSS Removal (%)', 'description': 'Percentage reduction in total suspended solids from coagulation/clarification.'},
    'tp_removal': {'name': 'Total Phosphorus Removal (%)', 'description': 'Percentage reduction in total phosphorus, if chemical P removal is practiced.'},
    'effluent_tp': {'name': 'Effluent Total Phosphorus (mg/L)', 'description': 'Effluent TP concentration — compare against your discharge permit limit, which this app does not know.'},
    'coagulant_cost_per_mg': {'name': 'Coagulant Cost per MG Treated ($/MG)', 'description': 'Economic indicator of coagulant chemical cost normalized to flow treated.'},
    'coagulant_efficiency': {'name': 'Coagulant Efficiency (lbs coag/lb TSS removed)', 'description': 'Mass of coagulant used per mass of TSS removed — a chemical efficiency indicator, lower is generally better.'},
    'coagulant_feed_rate': {'name': 'Coagulant Feed Rate (gpd)', 'description': 'Volumetric feed rate of coagulant solution.'},
    'flow_treated': {'name': 'Flow Treated (MGD)', 'description': 'Flow rate through the coagulant addition process.'},
    'coagulant_feed_availability': {'name': 'Coagulant Feed Equipment Availability (%)', 'description': 'Uptime percentage of coagulant feed pumps/equipment.'},
    'rapid_mix_time': {'name': 'Rapid Mix Detention Time (sec)', 'description': 'Contact time for initial coagulant dispersion. Typical design range is 30-60 seconds — too short limits effective charge neutralization.'},
}

COAGULANT_TYPICAL_RANGES = {
    'Ferric Chloride': '20-150 mg/L typical for CEPT/primary treatment (varies by application)',
    'Alum (Aluminum Sulfate)': '20-150 mg/L typical for CEPT/primary treatment (varies by application)',
    'PACl (Polyaluminum Chloride)': '10-80 mg/L — often lower than ferric/alum due to higher basicity',
    'Ferric Sulfate': '20-150 mg/L typical for CEPT/primary treatment (varies by application)',
    'Lime': '100-1000+ mg/L — a very different application (softening/high-pH precipitation)',
    'Other': 'Varies significantly by product — consult the product data sheet',
}

# ============================================================
# RECOMMENDATION TEMPLATES + PRIORITY MAP
# ============================================================
RECOMMENDATION_TEMPLATES = {
    'dose_vs_jar_test': {
        'issue': 'Feed dose is deviating meaningfully from the lab-determined jar test optimum. Coagulation efficiency is '
                 'sharply peaked around the true optimal dose — both under- and overdosing reduce turbidity/TSS removal, '
                 'and overdosing also re-stabilizes colloids via charge reversal in some coagulant systems.',
        'root_causes': [
            'Jar test hasn\'t been re-run recently against current raw water/wastewater characteristics',
            'Feed pump calibration drift (stroke length, speed, or diaphragm wear changing actual delivered dose vs. setpoint)',
            'Coagulant product concentration/strength changed between deliveries without adjusting feed rate',
            'Flow-paced dosing not tracking actual flow accurately (flow meter calibration or pacing signal issue)',
        ],
        'actions': [
            'Re-run a jar test series (typically 6-8 doses bracketing the current feed rate) against a fresh grab sample',
            'Verify feed pump calibration - measure actual delivered volume over a timed interval against the displayed rate',
            'Confirm current coagulant product concentration (% by weight or specific gravity) matches what the feed rate calculation assumes',
            'Check flow-pacing signal accuracy if dose is flow-proportional',
        ],
        'additional_data': ['Recent jar test bench results across multiple doses', 'Feed pump calibration log', 'Coagulant delivery certificates of analysis (product strength)'],
        'timeline': '1-2 weeks', 'risk': 'Low',
    },
    'turbidity_removal': {
        'issue': 'Turbidity removal below target usually reflects incomplete charge neutralization (destabilization) or '
                 'insufficient floc formation/settling time, rather than a single simple cause - the diagnostic sequence '
                 'matters here.',
        'root_causes': [
            'Coagulant underdosed relative to current raw water turbidity/particle load (higher influent turbidity generally needs more coagulant, not a fixed dose)',
            'Rapid mix (flash mix) energy or detention time insufficient for full charge neutralization before particles re-aggregate poorly',
            'pH outside the effective coagulation range for the product in use (each coagulant has an optimal pH band - ferric salts typically work well pH 5-8.5, alum narrower around 5.5-7.5)',
            'Insufficient flocculation time/energy downstream of rapid mix, preventing microflocs from growing to settleable size',
            'Clarifier hydraulic loading too high, carrying floc over before it can settle',
        ],
        'actions': [
            'Cross-check influent turbidity trend - if it has risen, dose likely needs to scale with it rather than staying fixed',
            'Verify rapid mix G-value/detention time against design (typical target ~30-60 sec at high mixing intensity)',
            'Check pH at the point of coagulant addition against the optimal band for your product',
            'Inspect flocculation basin mixing energy - too vigorous shears floc, too gentle doesn\'t grow it',
            'Review clarifier hydraulic loading rate against design capacity',
        ],
        'additional_data': ['Influent turbidity trend', 'Rapid mix G-value/detention time', 'pH at coagulant addition point', 'Clarifier hydraulic loading rate'],
        'timeline': '1-2 weeks', 'risk': 'Low',
    },
    'effluent_turbidity': {
        'issue': 'Effluent turbidity is the end-to-end result of dose, mixing, flocculation, and clarification all working '
                 'together - treat this as the summary metric and use Turbidity Removal Efficiency plus the process '
                 'checks below to isolate which stage is underperforming.',
        'root_causes': ['See Turbidity Removal Efficiency diagnosis - same underlying mechanisms', 'Clarifier short-circuiting or hydraulic loading above design'],
        'actions': ['Work through the Turbidity Removal Efficiency root causes first', 'If removal % is actually fine but influent turbidity has spiked, the fix is upstream (source control) or temporary dose increase, not the coagulation process itself'],
        'additional_data': ['See Turbidity Removal Efficiency KPI'],
        'timeline': '1-2 weeks', 'risk': 'Low',
    },
    'ph_depression': {
        'issue': 'Coagulant salts are acidic and consume alkalinity as they hydrolyze (e.g. FeCl3 + 3HCO3- → Fe(OH)3 + '
                 '3CO2 + 3Cl-). Large pH depression means the dose is consuming more buffering capacity than the water '
                 'has to spare, which can push pH outside the optimal coagulation range and create downstream corrosion '
                 'or biological process concerns.',
        'root_causes': ['Coagulant dose high relative to available alkalinity', 'Low influent alkalinity (seasonal or source-water driven) reducing buffering capacity', 'No alkalinity supplementation (caustic/lime) in a system that needs it at current dose'],
        'actions': ['Check Residual Alkalinity KPI - if it\'s also low, alkalinity supplementation may be needed rather than reducing dose', 'Compare pH depression against the dose trend - if they move together, the dose is the lever to pull', 'Consider a coagulant switch to a less acidic product (e.g. PACl generally depresses pH less than ferric/alum for equivalent performance) if pH control is a recurring problem'],
        'additional_data': ['Influent alkalinity trend', 'Whether alkalinity supplementation (caustic, lime, soda ash) is in use'],
        'timeline': '2-4 weeks', 'risk': 'Low',
    },
    'residual_alkalinity': {
        'issue': 'Residual alkalinity below roughly 30-50 mg/L as CaCO3 leaves little buffering capacity, risking pH '
                 'instability with normal dose variation and reduced coagulation efficiency since optimal coagulation '
                 'occurs within a defined pH band.',
        'root_causes': ['Coagulant dose consuming more alkalinity than the water naturally provides', 'Low source-water alkalinity (can be seasonal, e.g. spring snowmelt/runoff events)', 'No supplemental alkalinity feed where the process needs one'],
        'actions': ['Evaluate adding supplemental alkalinity (caustic soda, lime, or soda ash) if this is a recurring rather than occasional condition', 'Cross-check against pH Depression - both flagged together confirms an alkalinity-limited condition', 'Consider a lower-alkalinity-demand coagulant product if switching is feasible'],
        'additional_data': ['Influent alkalinity trend and seasonality', 'Alkalinity supplementation chemical availability'],
        'timeline': '2-4 weeks', 'risk': 'Low',
    },
    'tss_removal': {
        'issue': 'TSS removal shares the same coagulation/flocculation/clarification mechanism as turbidity removal - the '
                 'two KPIs usually move together, so check both before concluding the driver.',
        'root_causes': ['Same drivers as Turbidity Removal - dose, mixing, pH, flocculation, clarifier loading'],
        'actions': ['Work through the Turbidity Removal Efficiency diagnosis - the mechanisms are shared'],
        'additional_data': ['See Turbidity Removal Efficiency KPI'],
        'timeline': '1-2 weeks', 'risk': 'Low',
    },
    'tp_removal': {
        'issue': 'Chemical phosphorus removal depends on forming insoluble metal-phosphate precipitates (e.g. FePO4, '
                 'AlPO4) in addition to the charge-neutralization/turbidity-removal mechanism - a dose adequate for '
                 'turbidity control is not automatically adequate for P removal, since P removal typically needs a '
                 'metal:P molar ratio well above stoichiometric (commonly 1.5-3x) to reach low effluent TP.',
        'root_causes': ['Coagulant dose adequate for turbidity but insufficient metal:P molar ratio for the target effluent TP', 'pH outside the optimal precipitation range for the metal-phosphate compound', 'Competing reactions (e.g. metal reacting with alkalinity/hydroxide preferentially over phosphate at certain pH)'],
        'actions': ['Calculate the metal:P molar ratio being fed against influent TP and compare to literature guidance (commonly 1.5-3x stoichiometric for low effluent TP targets)', 'If dose is already high but TP removal is still poor, check pH - precipitation efficiency is pH-dependent for both iron and aluminum phosphates', 'Consider a second/polishing dose point if the permit requires very low effluent TP and single-point dosing has a practical floor'],
        'additional_data': ['Influent TP concentration and metal:P molar ratio being fed', 'pH at the dose point', 'Permit effluent TP limit'],
        'timeline': '2-4 weeks', 'risk': 'Low',
    },
    'coagulant_cost_per_mg': {
        'issue': 'Coagulant cost per MG treated is elevated by either dose (a process problem) or unit price (a '
                 'procurement problem) - check Feed Dose vs. Jar Test Optimal first to see which is driving it.',
        'root_causes': ['Dose above jar-test optimum (see Feed Dose vs. Jar Test Optimal)', 'Coagulant unit price above current market rate for the product class/volume tier'],
        'actions': ['If dose is also flagged, fix that first - cost will follow', 'If dose is on-target but cost is still high, benchmark unit pricing against 2-3 competing suppliers'],
        'additional_data': ['Coagulant contract pricing and volume tier'],
        'timeline': '4-6 weeks', 'risk': 'Low',
    },
    'coagulant_feed_availability': {
        'issue': 'Coagulant feed equipment downtime directly compromises treatment - unlike some processes, there is no '
                 'buffering capacity for a coagulation step to "catch up" once it falls behind.',
        'root_causes': ['Unplanned pump/feed system downtime', 'Recurring mechanical failure mode not yet root-caused (diaphragm wear, tubing degradation from chemical exposure, calibration drift)'],
        'actions': ['Pull maintenance work order history and categorize by cause code', 'Evaluate whether wetted-parts replacement intervals (diaphragms, tubing, check valves) match actual chemical-exposure wear rates, which are often faster than generic PM schedules assume'],
        'additional_data': ['Maintenance work order history with downtime cause codes'],
        'timeline': '4-8 weeks', 'risk': 'Medium - directly compromises treatment during downtime',
    },
}

PRIORITY_MAP = {
    'dose_vs_jar_test': '🟠 HIGH', 'turbidity_removal': '🟠 HIGH', 'effluent_turbidity': '🟡 MEDIUM',
    'ph_depression': '🟡 MEDIUM', 'residual_alkalinity': '🟡 MEDIUM', 'tss_removal': '🟡 MEDIUM',
    'tp_removal': '🟠 HIGH', 'coagulant_cost_per_mg': '🟡 MEDIUM', 'coagulant_feed_availability': '🟠 HIGH',
}


def estimate_savings(key, val):
    if key == 'dose_vs_jar_test':
        return ("Reduced chemical cost", "Aligning feed dose to jar-test optimum typically reduces coagulant consumption without sacrificing removal performance - exact $ savings depend on your coagulant unit price and current dose deviation.")
    if key == 'coagulant_cost_per_mg':
        return ("Reduced chemical cost", "Specific dollar savings require site-specific pricing and dose data - see the linked KPIs above.")
    return ("Improves process efficiency", "Specific dollar savings require site-specific cost data not available from the uploaded dataset.")


# ============================================================
# PARAMETER KEYWORDS
# ============================================================
PARAMETER_KEYWORDS = {
    'coagulant_dose': ['coagulant dose mg l', 'alum dose', 'ferric dose mg l', 'pacl dose', 'coagulant dose'],
    'coagulant_feed_gpd': ['coagulant feed gpd', 'coagulant feed rate gpd', 'chemical feed gpd'],
    'coagulant_cost': ['coagulant cost dollars', 'chemical cost coagulant', 'alum cost', 'ferric cost'],
    'influent_turbidity': ['influent turbidity ntu', 'raw turbidity', 'pre coagulation turbidity', 'inlet turbidity'],
    'effluent_turbidity': ['effluent turbidity ntu', 'clarified turbidity', 'post coagulation turbidity', 'settled turbidity', 'final turbidity'],
    'influent_ph': ['influent ph', 'raw ph', 'pre coagulation ph', 'inlet ph'],
    'effluent_ph': ['effluent ph', 'clarified ph', 'post coagulation ph', 'final ph'],
    'influent_alkalinity': ['influent alkalinity', 'raw alkalinity', 'alkalinity mg l caco3'],
    'effluent_alkalinity': ['effluent alkalinity', 'residual alkalinity', 'post coagulation alkalinity'],
    'jar_test_dose': ['jar test dose', 'jar test optimal dose', 'bench test dose', 'optimal dose jar test'],
    'influent_tp': ['influent total phosphorus', 'influent tp mg l', 'raw phosphorus'],
    'effluent_tp': ['effluent total phosphorus', 'effluent tp mg l', 'final phosphorus'],
    'influent_tss': ['influent tss mg l', 'raw tss'],
    'effluent_tss': ['effluent tss mg l', 'clarified tss', 'final tss'],
    'flow_treated': ['flow treated mgd', 'plant flow mgd', 'influent flow mgd'],
    'coagulant_feed_hours': ['coagulant feed pump hours', 'chemical feed run hours', 'coagulant pump run hours'],
    'rapid_mix_time': ['rapid mix detention time', 'flash mix time seconds', 'rapid mix seconds'],
    'coagulant_solids_produced': ['chemical sludge produced lbs', 'coagulant solids produced'],
}

EXPECTED_UNIT_FAMILIES = {
    'coagulant_dose': {'mg/L'},
    'coagulant_feed_gpd': {'GPD'},
    'coagulant_cost': {'$'},
    'influent_turbidity': {'NTU'},
    'effluent_turbidity': {'NTU'},
    'influent_ph': {'pH'},
    'effluent_ph': {'pH'},
    'influent_alkalinity': {'mg/L'},
    'effluent_alkalinity': {'mg/L'},
    'jar_test_dose': {'mg/L'},
    'influent_tp': {'mg/L'},
    'effluent_tp': {'mg/L'},
    'influent_tss': {'mg/L'},
    'effluent_tss': {'mg/L'},
    'flow_treated': {'MGD', 'GPM', 'GPD'},
    'coagulant_feed_hours': {'Hours'},
    'coagulant_solids_produced': {'Dry Tons', 'Wet Tons', 'Tons'},
}

REQUIRED_TOKEN_GROUPS = {
    'influent_turbidity': [['influent', 'raw', 'inlet']],
    'effluent_turbidity': [['effluent', 'clarified', 'settled', 'final']],
    'influent_ph': [['influent', 'raw', 'inlet'], ['ph']],
    'effluent_ph': [['effluent', 'clarified', 'final'], ['ph']],
    'influent_alkalinity': [['influent', 'raw'], ['alkalinity']],
    'effluent_alkalinity': [['effluent', 'residual', 'clarified'], ['alkalinity']],
    'influent_tp': [['influent', 'raw'], ['phosphorus', 'tp']],
    'effluent_tp': [['effluent', 'final'], ['phosphorus', 'tp']],
    'influent_tss': [['influent', 'raw'], ['tss']],
    'effluent_tss': [['effluent', 'clarified', 'final'], ['tss']],
}

EXCLUDE_TOKENS = {
    'influent_turbidity': ['effluent', 'clarified', 'final', 'settled'],
    'effluent_turbidity': ['influent', 'raw', 'inlet'],
    'influent_ph': ['effluent', 'clarified', 'final'],
    'effluent_ph': ['influent', 'raw', 'inlet'],
    'influent_alkalinity': ['effluent', 'residual', 'clarified'],
    'effluent_alkalinity': ['influent', 'raw', 'inlet'],
    'influent_tp': ['effluent', 'final', 'clarified'],
    'effluent_tp': ['influent', 'raw', 'inlet'],
    'influent_tss': ['effluent', 'final', 'clarified'],
    'effluent_tss': ['influent', 'raw', 'inlet'],
}


def categorize_param(key):
    if key.startswith('influent_'):
        return 'Influent'
    if key.startswith('effluent_'):
        return 'Effluent'
    if 'coagulant' in key:
        return 'Coagulant'
    return 'Process'


# ============================================================
# KPI CALCULATOR
# ============================================================
class KPICalculator(BaseKPICalculator):
    def calculate_coagulant_kpis(self):
        k = {}
        coag_type = self.plant_info.get('coagulant_type', 'Other')

        dose_col = self.dp.get('coagulant_dose', {}).get('column')
        dose = self._col('coagulant_dose')
        jar_col = self.dp.get('jar_test_dose', {}).get('column')
        jar = self._col('jar_test_dose')

        if dose is not None:
            typical = COAGULANT_TYPICAL_RANGES.get(coag_type, COAGULANT_TYPICAL_RANGES['Other'])
            k['coagulant_dose'] = {'value': dose.mean(), 'unit': 'mg/L', 'target': f'Typical for {coag_type}: {typical}', 'status': 'ℹ️ Informational',
                                    'basis': f"Average of **{dose_col}**."}
        else:
            k['coagulant_dose'] = self._insufficient(['Coagulant dose (mg/L) column'])

        if dose is not None and jar is not None and jar.mean() > 0:
            dev = (dose.mean() - jar.mean()) / jar.mean() * 100
            k['dose_vs_jar_test'] = {'value': dev, 'unit': '%', 'target': 'Within ±15% of jar-test optimum', 'status': self._status_range(abs(dev), 0, 15),
                                      'basis': f"(Average **{dose_col}** − average **{jar_col}**) ÷ average **{jar_col}** × 100."}
        else:
            k['dose_vs_jar_test'] = self._insufficient(['Jar test optimal dose column, alongside coagulant dose'])

        inf_turb_col = self.dp.get('influent_turbidity', {}).get('column')
        inf_turb = self._col('influent_turbidity')
        eff_turb_col = self.dp.get('effluent_turbidity', {}).get('column')
        eff_turb = self._col('effluent_turbidity')

        if inf_turb is not None and eff_turb is not None and inf_turb.mean() > 0:
            removal = max(0, min(100, (inf_turb.mean() - eff_turb.mean()) / inf_turb.mean() * 100))
            k['turbidity_removal'] = {'value': removal, 'unit': '%', 'target': '>90%', 'status': self._status_lower(removal, 90),
                                       'basis': f"(Average **{inf_turb_col}** − average **{eff_turb_col}**) ÷ average **{inf_turb_col}** × 100."}
        else:
            k['turbidity_removal'] = self._insufficient(['Both influent and effluent turbidity (NTU) columns'])

        if eff_turb is not None:
            k['effluent_turbidity'] = {'value': eff_turb.mean(), 'unit': 'NTU', 'target': '<2 NTU (excellent)', 'status': self._status_upper(eff_turb.mean(), 5),
                                        'basis': f"Average of **{eff_turb_col}**."}
        else:
            k['effluent_turbidity'] = self._insufficient(['Effluent turbidity (NTU) column'])

        inf_ph_col = self.dp.get('influent_ph', {}).get('column')
        inf_ph = self._col('influent_ph')
        eff_ph_col = self.dp.get('effluent_ph', {}).get('column')
        eff_ph = self._col('effluent_ph')

        if inf_ph is not None and eff_ph is not None:
            depression = inf_ph.mean() - eff_ph.mean()
            k['ph_depression'] = {'value': depression, 'unit': 'units', 'target': '<0.3 units (excellent)', 'status': self._status_upper(depression, 0.6),
                                   'basis': f"Average **{inf_ph_col}** − average **{eff_ph_col}**."}
        else:
            k['ph_depression'] = self._insufficient(['Both influent and effluent pH columns'])

        eff_alk_col = self.dp.get('effluent_alkalinity', {}).get('column')
        eff_alk = self._col('effluent_alkalinity')
        if eff_alk is not None:
            k['residual_alkalinity'] = {'value': eff_alk.mean(), 'unit': 'mg/L as CaCO3', 'target': '>50 mg/L as CaCO3', 'status': self._status_lower(eff_alk.mean(), 30),
                                         'basis': f"Average of **{eff_alk_col}**."}
        else:
            k['residual_alkalinity'] = self._insufficient(['Effluent/residual alkalinity (mg/L as CaCO3) column'])

        inf_tss_col = self.dp.get('influent_tss', {}).get('column')
        inf_tss = self._col('influent_tss')
        eff_tss_col = self.dp.get('effluent_tss', {}).get('column')
        eff_tss = self._col('effluent_tss')
        if inf_tss is not None and eff_tss is not None and inf_tss.mean() > 0:
            tss_removal = max(0, min(100, (inf_tss.mean() - eff_tss.mean()) / inf_tss.mean() * 100))
            k['tss_removal'] = {'value': tss_removal, 'unit': '%', 'target': '>85%', 'status': self._status_lower(tss_removal, 85),
                                 'basis': f"(Average **{inf_tss_col}** − average **{eff_tss_col}**) ÷ average **{inf_tss_col}** × 100."}
        else:
            k['tss_removal'] = self._insufficient(['Both influent and effluent TSS (mg/L) columns'])

        inf_tp_col = self.dp.get('influent_tp', {}).get('column')
        inf_tp = self._col('influent_tp')
        eff_tp_col = self.dp.get('effluent_tp', {}).get('column')
        eff_tp = self._col('effluent_tp')
        if inf_tp is not None and eff_tp is not None and inf_tp.mean() > 0:
            tp_removal = max(0, min(100, (inf_tp.mean() - eff_tp.mean()) / inf_tp.mean() * 100))
            k['tp_removal'] = {'value': tp_removal, 'unit': '%', 'target': '>85%', 'status': self._status_lower(tp_removal, 85),
                                'basis': f"(Average **{inf_tp_col}** − average **{eff_tp_col}**) ÷ average **{inf_tp_col}** × 100."}
        else:
            k['tp_removal'] = self._insufficient(['Both influent and effluent Total Phosphorus (mg/L) columns'])

        if eff_tp is not None:
            k['effluent_tp'] = {'value': eff_tp.mean(), 'unit': 'mg/L', 'target': 'Compare to your discharge permit limit', 'status': 'ℹ️ Informational',
                                 'basis': f"Average of **{eff_tp_col}**."}
        else:
            k['effluent_tp'] = self._insufficient(['Effluent Total Phosphorus (mg/L) column'])

        cost_col = self.dp.get('coagulant_cost', {}).get('column')
        flow_col = self.dp.get('flow_treated', {}).get('column')
        if cost_col and flow_col:
            cost_series = pd.to_numeric(self.df[cost_col], errors='coerce')
            flow_series = pd.to_numeric(self.df[flow_col], errors='coerce')
            ratio = (cost_series / flow_series).replace([np.inf, -np.inf], np.nan).dropna()
            if len(ratio) > 0:
                k['coagulant_cost_per_mg'] = {'value': ratio.mean(), 'unit': '$/MG', 'target': 'Varies by coagulant type and contract pricing', 'status': 'ℹ️ Informational',
                                               'basis': f"Average of (**{cost_col}** ÷ **{flow_col}**), assuming {cost_col} is a $/day total cost and {flow_col} is in MGD."}
            else:
                k['coagulant_cost_per_mg'] = self._insufficient(['Coagulant cost ($/day) and flow treated (MGD) columns (valid paired data)'])
        else:
            k['coagulant_cost_per_mg'] = self._insufficient(['Coagulant cost ($/day) column together with flow treated (MGD) column'])

        if dose is not None and flow_col and inf_tss is not None and eff_tss is not None:
            flow_series = pd.to_numeric(self.df[flow_col], errors='coerce')
            coag_lbs_day = dose.mean() * flow_series.mean() * 8.34
            tss_removed_lbs_day = (inf_tss.mean() - eff_tss.mean()) * flow_series.mean() * 8.34
            if tss_removed_lbs_day > 0:
                eff_ratio = coag_lbs_day / tss_removed_lbs_day
                k['coagulant_efficiency'] = {'value': eff_ratio, 'unit': 'lbs coag/lb TSS removed', 'target': 'Lower is generally better', 'status': 'ℹ️ Informational',
                                              'basis': (f"(Average **{dose_col}** × average **{flow_col}** × 8.34) ÷ ((average **{inf_tss_col}** − average **{eff_tss_col}**) "
                                                        f"× average **{flow_col}** × 8.34). Assumes {dose_col} is on an as-applied product mass basis.")}
            else:
                k['coagulant_efficiency'] = self._insufficient(['Positive TSS removal (influent TSS must exceed effluent TSS) to compute this ratio'])
        else:
            k['coagulant_efficiency'] = self._insufficient(['Coagulant dose, flow treated, and both influent/effluent TSS columns'])

        feed_col = self.dp.get('coagulant_feed_gpd', {}).get('column')
        feed = self._col('coagulant_feed_gpd')
        if feed is not None:
            k['coagulant_feed_rate'] = {'value': feed.mean(), 'unit': 'gpd', 'target': 'Varies by equipment', 'status': 'ℹ️ Informational',
                                         'basis': f"Average of **{feed_col}**."}
        else:
            k['coagulant_feed_rate'] = self._insufficient(['Coagulant feed rate (gpd) column'])

        if flow_col:
            flow_series = pd.to_numeric(self.df[flow_col], errors='coerce').dropna()
            if len(flow_series) > 0:
                k['flow_treated'] = {'value': flow_series.mean(), 'unit': 'MGD', 'target': 'Informational', 'status': 'ℹ️ Informational',
                                      'basis': f"Average of **{flow_col}**."}
            else:
                k['flow_treated'] = self._insufficient(['Flow treated (MGD) column'])
        else:
            k['flow_treated'] = self._insufficient(['Flow treated (MGD) column'])

        hrs_col = self.dp.get('coagulant_feed_hours', {}).get('column')
        hrs = self._col('coagulant_feed_hours')
        if hrs is not None:
            v = (hrs / 24 * 100).clip(upper=100).mean()
            k['coagulant_feed_availability'] = {'value': v, 'unit': '%', 'target': '>95%', 'status': self._status_lower(v, 95),
                                                 'basis': f"Average of (**{hrs_col}** ÷ 24 × 100)."}
        else:
            k['coagulant_feed_availability'] = self._insufficient(['Coagulant feed pump/equipment run-hours column'])

        rmt_col = self.dp.get('rapid_mix_time', {}).get('column')
        rmt = self._col('rapid_mix_time')
        if rmt is not None:
            k['rapid_mix_time'] = {'value': rmt.mean(), 'unit': 'sec', 'target': '30-60 sec (typical design range)', 'status': self._status_range(rmt.mean(), 30, 60),
                                    'basis': f"Average of **{rmt_col}**."}
        else:
            k['rapid_mix_time'] = self._insufficient(['Rapid mix/flash mix detention time (seconds) column'])

        return k


def render_kpi_grid_local(kpis, definitions, per_row=4):
    render_kpi_grid(kpis, definitions, per_row=per_row)


# ============================================================
# SIDEBAR - FILE UPLOAD
# ============================================================
st.sidebar.header("📊 Upload Your Data")
uploaded_file = st.sidebar.file_uploader("Choose your Coagulant Addition CSV file", type=['csv'], help="Upload a CSV file with your coagulant addition data")

if uploaded_file is None:
    st.info("👈 **Please upload a CSV file to get started**")
    st.markdown("""
    ### 📋 Expected Data Format

    Your CSV should contain columns like:

    **Dosing:** Coagulant Dose (mg/L), Coagulant Feed Rate (gpd), Coagulant Cost, Jar Test Optimal Dose

    **Water Quality:** Influent/Effluent Turbidity (NTU), Influent/Effluent pH, Influent/Effluent Alkalinity,
    Influent/Effluent TSS, Influent/Effluent Total Phosphorus

    **Process:** Flow Treated (MGD), Rapid Mix Detention Time, Coagulant Feed Pump Run Hours

    ### ✨ Features
    - 🔍 Fuzzy Logic auto-detects your columns — confirm/correct the mapping before anything is calculated
    - 📊 AI-derived KPI dashboard (only shows what can be computed from your data, no assumed units)
    - 💡 Technically-grounded recommendations (coagulation/flocculation chemistry, no external API needed)
    - 📈 Trend, custom-period, and Period A vs Period B benchmark comparison
    - 🔗 Correlation analysis between parameters
    - 🔎 Data quality / outlier detection

    ### 🚀 Ready? Upload your file!
    """)
else:
    try:
        df, date_col = load_process_csv(uploaded_file)
        st.sidebar.success(f"✅ Loaded {len(df)} records")
        st.sidebar.write(f"📅 {df[date_col].min().date()} to {df[date_col].max().date()}")
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()

    with st.sidebar.expander("🏭 Plant Information", expanded=False):
        plant_name = st.text_input("Plant Name", value="WWTP", key="cg_plant_name")
        plant_location = st.text_input("Location", value="", key="cg_plant_location")
        coagulant_type = st.selectbox("Coagulant Type", list(COAGULANT_TYPICAL_RANGES.keys()), key="cg_coagulant_type")
        plant_capacity = st.number_input("Plant Capacity (MGD)", value=10.0, min_value=0.1, key="cg_capacity")

        plant_info = {
            'name': plant_name, 'location': plant_location, 'coagulant_type': coagulant_type, 'capacity': plant_capacity,
        }

    # ------------------------------------------------------
    # PARAMETER DETECTION + CONFIRM/EDIT MAPPING
    # ------------------------------------------------------
    auto_detected_params = _detect_parameters(df, PARAMETER_KEYWORDS, EXPECTED_UNIT_FAMILIES, REQUIRED_TOKEN_GROUPS, EXCLUDE_TOKENS, threshold=55)

    st.header("🔧 Confirm Data Mapping")
    st.write(
        "This is exactly what we matched your columns to, with a confidence score. **Every KPI, chart, and "
        "recommendation below uses only this table** — fix any row that picked the wrong column, or set it to "
        "**'— None detected —'** if you don't have that data. Nothing is assumed beyond what you confirm here."
    )
    with st.expander("📝 Review & edit detected columns", expanded=True):
        detected_params = _render_mapping_editor(auto_detected_params, df.columns, key_prefix="coag_main", categorize_fn=categorize_param)

    st.divider()

    st.sidebar.subheader("🔍 Confirmed Parameters")
    detected_count = sum(1 for p in detected_params.values() if p['column'])
    for param_name, param_info in detected_params.items():
        if param_info['column']:
            st.sidebar.write(f"✅ {param_name}: **{param_info['column']}** ({param_info['unit']})")
    st.sidebar.write(f"\n**Confirmed: {detected_count}/{len(detected_params)} parameters**")

    analyzer = BaseRecommendationEngine(
        [COAGULANT_KPI_DEFINITIONS], RECOMMENDATION_TEMPLATES, PRIORITY_MAP, savings_estimator=estimate_savings,
    )
    kpi_calculator = KPICalculator(df, detected_params, plant_info)
    correlation_analyzer = CorrelationAnalyzer(df, detected_params)
    chart_renderer = ChartRenderer(df)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Dashboard", "💡 AI Recommendations", "📈 Trend / Benchmark", "🔗 Correlation Analysis",
        "🧪 Coagulant Performance", "🔍 Data Quality", "📋 Parameters", "📥 Raw Data",
    ])

    # ============================================================
    # TAB 1: DASHBOARD
    # ============================================================
    with tab1:
        header_col, year_col = st.columns([3, 1])
        with header_col:
            st.header(f"📊 Performance Dashboard - {plant_info.get('name', 'WWTP')}")
            if plant_info.get('location'):
                st.caption(f"📍 {plant_info['location']} | Capacity: {plant_info.get('capacity', 'N/A')} MGD | Coagulant: {plant_info.get('coagulant_type')}")

        available_years = sorted(df[date_col].dt.year.dropna().unique().astype(int).tolist())
        today = date.today()
        current_year = today.year
        year_options = ["All"] + [str(y) for y in available_years]

        if current_year in available_years:
            default_year_str = str(current_year)
        elif available_years:
            default_year_str = str(max(available_years))
        else:
            default_year_str = "All"
        default_index = year_options.index(default_year_str) if default_year_str in year_options else 0

        with year_col:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            selected_year_str = st.selectbox("Year", year_options, index=default_index, key="cg_dashboard_year_filter")

        if selected_year_str == "All":
            dashboard_df = df
            period_caption = f"All data ({df[date_col].min().date()} to {df[date_col].max().date()})"
        else:
            yr = int(selected_year_str)
            if yr == current_year:
                mask = (df[date_col].dt.year == yr) & (df[date_col].dt.date <= today)
                dashboard_df = df[mask]
                period_caption = f"Year to date: Jan 1, {yr} – {today.strftime('%b %d, %Y')}"
            else:
                mask = df[date_col].dt.year == yr
                dashboard_df = df[mask]
                period_caption = f"Full year {yr}"

        if len(dashboard_df) == 0:
            st.warning(f"No records fall in the selected period ({period_caption}). Showing full dataset instead.")
            dashboard_df = df
            period_caption = f"All data ({df[date_col].min().date()} to {df[date_col].max().date()})"

        st.caption(f"📅 {period_caption} &nbsp;·&nbsp; {len(dashboard_df)} record(s) &nbsp;·&nbsp; "
                   f"KPIs below are computed from the columns you confirmed above, averaged over this period.")

        dashboard_kpi_calculator = KPICalculator(dashboard_df, detected_params, plant_info)
        coag_kpis = dashboard_kpi_calculator.calculate_coagulant_kpis()

        st.subheader("🧪 Coagulant Addition KPIs")
        render_kpi_grid(coag_kpis, COAGULANT_KPI_DEFINITIONS)

    # ============================================================
    # TAB 2: AI RECOMMENDATIONS
    # ============================================================
    with tab2:
        st.header("💡 AI-Powered Recommendations")
        st.write("Generated from the KPIs on the Dashboard tab, using only the parameters you confirmed above. Purely "
                 "rule-based (no external API/key needed) - grounded in coagulation/flocculation process engineering.")

        coag_kpis = kpi_calculator.calculate_coagulant_kpis()
        recommendations, good_items = analyzer.generate_recommendations(coag_kpis)
        render_recommendations_tab(recommendations, good_items)

    # ============================================================
    # TAB 3: TREND / BENCHMARK ANALYSIS
    # ============================================================
    with tab3:
        st.header("📈 Trend & Benchmark Analysis")
        st.write("Analyze any column over time, over a custom date range, or benchmark two date ranges side-by-side — all from your one uploaded file.")

        numeric_cols = {}
        for col in df.columns:
            if col == date_col:
                continue
            s = pd.to_numeric(df[col], errors='coerce')
            if s.notna().sum() > 0:
                matched_unit = next((p['unit'] for p in detected_params.values() if p['column'] == col), None)
                numeric_cols[col] = matched_unit or 'Unknown'

        if not numeric_cols:
            st.warning("No numeric columns found in your data.")
        else:
            analyze_mode = st.radio("Analyze", ["Single Indicator", "Ratio"], horizontal=True,
                                     help="A ratio lets you build any custom metric on the fly (pick a numerator and a denominator column), e.g. Coagulant Cost ÷ Flow Treated.",
                                     key="cg_analyze_mode")

            if analyze_mode == "Single Indicator":
                selected_column = st.selectbox("Select Indicator", list(numeric_cols.keys()), format_func=lambda x: f"{x} ({numeric_cols[x]})", key="cg_selected_column")
                working_label = selected_column
                working_unit = numeric_cols[selected_column]
                working_series = pd.to_numeric(df[selected_column], errors='coerce')
            else:
                rc1, rc2 = st.columns(2)
                col_list = list(numeric_cols.keys())
                with rc1:
                    numerator_col = st.selectbox("Numerator", col_list, format_func=lambda x: f"{x} ({numeric_cols[x]})", key="cg_ratio_numerator")
                with rc2:
                    default_denom_idx = 1 if len(col_list) > 1 else 0
                    denominator_col = st.selectbox("Denominator", col_list, index=default_denom_idx, format_func=lambda x: f"{x} ({numeric_cols[x]})", key="cg_ratio_denominator")
                num_series = pd.to_numeric(df[numerator_col], errors='coerce')
                denom_series = pd.to_numeric(df[denominator_col], errors='coerce')
                working_series = (num_series / denom_series).replace([np.inf, -np.inf], np.nan)
                working_label = f"{numerator_col} ÷ {denominator_col}"
                num_unit, denom_unit = numeric_cols[numerator_col], numeric_cols[denominator_col]
                working_unit = f"{num_unit}/{denom_unit}" if 'Unknown' not in (num_unit, denom_unit) else "ratio"
                if numerator_col == denominator_col:
                    st.info("Numerator and denominator are the same column, so this ratio will just be 1.0 - pick two different columns.")

            col_s2, col_s3 = st.columns(2)
            with col_s2:
                aggregation = st.selectbox("Aggregation Period", ["Daily", "Weekly", "Monthly", "Quarterly"], key="cg_aggregation")
            with col_s3:
                agg_method = st.selectbox("Aggregation Method", ["Average", "Total"], key="cg_agg_method")

            agg_func = 'sum' if agg_method == 'Total' else 'mean'
            freq_map = {"Daily": 'D', "Weekly": 'W', "Monthly": 'MS', "Quarterly": 'QS'}

            mode = st.radio("Analysis Mode", ["Full Timeline", "Custom Period", "Period A vs Period B (Benchmark)"], horizontal=True, key="cg_mode")

            df_yoy = pd.DataFrame({date_col: pd.to_datetime(df[date_col]), 'value': working_series}).dropna()

            if len(df_yoy) == 0:
                st.warning("No valid numeric data for this selection.")
            else:
                data_min = df_yoy[date_col].min().date()
                data_max = df_yoy[date_col].max().date()

                def plot_series(df_agg, title):
                    import plotly.graph_objects as go
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df_agg.index, y=df_agg.values, mode='lines+markers', name=working_label, line=dict(color=VEOLIA['turquoise'], width=2), marker=dict(size=6, color=VEOLIA['marine'])))
                    x_numeric = np.arange(len(df_agg))
                    z = None
                    if len(x_numeric) > 1:
                        z = np.polyfit(x_numeric, df_agg.values, 1)
                        p = np.poly1d(z)
                        fig.add_trace(go.Scatter(x=df_agg.index, y=p(x_numeric), mode='lines', name='Trend', line=dict(color=VEOLIA['apricot'], width=2, dash='dash')))
                    fig.update_layout(
                        title=dict(text=title, font=dict(color=VEOLIA['marine'])),
                        xaxis_title="Date", yaxis_title=working_unit, height=500, hovermode='x unified',
                        plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF', font=dict(color=VEOLIA['marine']),
                        xaxis=dict(gridcolor='#E9EEF1'), yaxis=dict(gridcolor='#E9EEF1'),
                    )
                    render_chart_with_download(fig, key="cg_trend_single_chart")

                    stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)
                    with stat_c1:
                        st.metric("Mean", f"{df_agg.mean():.3f}")
                    with stat_c2:
                        st.metric("Median", f"{df_agg.median():.3f}")
                    with stat_c3:
                        st.metric("Min", f"{df_agg.min():.3f}")
                    with stat_c4:
                        st.metric("Max", f"{df_agg.max():.3f}")

                    if z is not None:
                        direction = "📈 Increasing" if z[0] > 0 else "📉 Decreasing"
                        st.write(f"**Trend:** {direction} (slope: {z[0]:.4f} per {aggregation.lower()[:-2] if aggregation != 'Daily' else 'day'})")

                if mode == "Full Timeline":
                    try:
                        df_agg = df_yoy.set_index(date_col)['value'].resample(freq_map[aggregation]).agg(agg_func).dropna()
                        if len(df_agg) > 0:
                            plot_series(df_agg, f"{working_label} - {aggregation} Aggregation (Full Timeline)")
                        else:
                            st.warning("No data available after aggregation")
                    except Exception as e:
                        st.error(f"Error processing data: {e}")

                elif mode == "Custom Period":
                    date_range = st.date_input("Select Date Range", value=(data_min, data_max), min_value=data_min, max_value=data_max, key="cg_custom_period")
                    if isinstance(date_range, tuple) and len(date_range) == 2:
                        start_d, end_d = date_range
                        mask = (df_yoy[date_col].dt.date >= start_d) & (df_yoy[date_col].dt.date <= end_d)
                        df_period = df_yoy[mask]
                        if len(df_period) == 0:
                            st.warning("No data in the selected range")
                        else:
                            try:
                                df_agg = df_period.set_index(date_col)['value'].resample(freq_map[aggregation]).agg(agg_func).dropna()
                                if len(df_agg) > 0:
                                    plot_series(df_agg, f"{working_label} - {start_d.strftime('%b %d, %Y')} to {end_d.strftime('%b %d, %Y')}")
                                else:
                                    st.warning("No data available after aggregation for this range")
                            except Exception as e:
                                st.error(f"Error processing data: {e}")
                    else:
                        st.info("👆 Select both a start and end date to continue")

                else:
                    st.write("**Define two date ranges** and the app will pull the matching data for each and plot them together.")
                    midpoint = data_min + (data_max - data_min) / 2
                    pc1, pc2 = st.columns(2)
                    with pc1:
                        st.markdown("**Period A**")
                        a_range = st.date_input("Period A date range", value=(data_min, midpoint), min_value=data_min, max_value=data_max, key="cg_period_a_range")
                    with pc2:
                        st.markdown("**Period B**")
                        b_range = st.date_input("Period B date range", value=(midpoint, data_max), min_value=data_min, max_value=data_max, key="cg_period_b_range")

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
                                import plotly.graph_objects as go
                                agg_a = df_a.set_index(date_col)['value'].resample(freq_map[aggregation]).agg(agg_func).dropna()
                                agg_b = df_b.set_index(date_col)['value'].resample(freq_map[aggregation]).agg(agg_func).dropna()

                                label_a = f"Period A: {a_start.strftime('%b %d, %Y')} - {a_end.strftime('%b %d, %Y')}"
                                label_b = f"Period B: {b_start.strftime('%b %d, %Y')} - {b_end.strftime('%b %d, %Y')}"

                                date_fmt = '%b %d, %Y' if aggregation in ('Daily', 'Weekly') else '%b %Y'
                                offset_a = list(range(len(agg_a)))
                                offset_b = list(range(len(agg_b)))
                                dates_a_text = [d.strftime(date_fmt) for d in agg_a.index]
                                dates_b_text = [d.strftime(date_fmt) for d in agg_b.index]

                                n = len(offset_a)
                                step = max(1, int(np.ceil(n / 12))) if n else 1
                                tick_idx = list(range(0, n, step))
                                if n and tick_idx[-1] != n - 1:
                                    tick_idx.append(n - 1)
                                tickvals = [offset_a[i] for i in tick_idx]
                                ticktext = [dates_a_text[i] for i in tick_idx]

                                fig = go.Figure()
                                fig.add_trace(go.Scatter(
                                    x=offset_a, y=agg_a.values, mode='lines+markers', name=label_a,
                                    line=dict(color=VEOLIA['turquoise'], width=3), customdata=dates_a_text,
                                    hovertemplate=f"{label_a}<br>%{{customdata}}: %{{y:.3f}}<extra></extra>",
                                ))
                                fig.add_trace(go.Scatter(
                                    x=offset_b, y=agg_b.values, mode='lines+markers', name=label_b,
                                    line=dict(color=VEOLIA['apricot'], width=3), customdata=dates_b_text,
                                    hovertemplate=f"{label_b}<br>%{{customdata}}: %{{y:.3f}}<extra></extra>",
                                ))
                                fig.update_layout(
                                    title=dict(text=f"Benchmark Comparison: {working_label} ({aggregation}, {agg_method})", font=dict(color=VEOLIA['marine'])),
                                    xaxis=dict(title="Date (Period A dates shown; Period B is aligned to the same relative position)",
                                               tickmode='array', tickvals=tickvals, ticktext=ticktext, tickangle=-30, gridcolor='#E9EEF1'),
                                    yaxis=dict(title=working_unit, gridcolor='#E9EEF1'),
                                    height=520, hovermode='closest', margin=dict(b=110),
                                    plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF', font=dict(color=VEOLIA['marine']),
                                )
                                render_chart_with_download(fig, key="cg_trend_benchmark_chart")

                                st.subheader("📊 Comparison Statistics")
                                stat_df = pd.DataFrame({
                                    'Metric': ['Mean', 'Median', 'Min', 'Max', 'Std Dev'],
                                    label_a: [agg_a.mean(), agg_a.median(), agg_a.min(), agg_a.max(), agg_a.std()],
                                    label_b: [agg_b.mean(), agg_b.median(), agg_b.min(), agg_b.max(), agg_b.std()],
                                })
                                stat_df['% Change (A→B)'] = ((stat_df[label_b] - stat_df[label_a]) / stat_df[label_a] * 100)
                                st.dataframe(stat_df.round(4), use_container_width=True)

                                if agg_a.mean() != 0:
                                    pct_change_mean = (agg_b.mean() - agg_a.mean()) / agg_a.mean() * 100
                                    direction = "increased" if pct_change_mean > 0 else "decreased"
                                    st.info(f"**{working_label}** {direction} by **{abs(pct_change_mean):.1f}%** from Period A to Period B")
                            except Exception as e:
                                st.error(f"Error processing comparison: {e}")
                    else:
                        st.info("👆 Select both a start and end date for each period to continue")

    # ============================================================
    # TAB 4: CORRELATION ANALYSIS
    # ============================================================
    with tab4:
        st.header("🔗 Correlation Analysis")
        st.write("Analyze relationships between confirmed coagulant addition parameters.")

        corr_matrix = correlation_analyzer.calculate_correlations()

        if corr_matrix is None or len(corr_matrix.columns) < 2:
            st.warning("Not enough confirmed numeric parameters for correlation analysis. Check **Confirm Data Mapping** above.")
        else:
            st.subheader("📊 Correlation Heatmap")
            fig_heatmap = correlation_analyzer.create_correlation_heatmap()
            if fig_heatmap:
                render_chart_with_download(fig_heatmap, key="cg_corr_heatmap")

            st.divider()
            st.subheader("🔍 Strong Correlations (|r| ≥ 0.7)")
            strong_corrs = correlation_analyzer.find_strong_correlations(threshold=0.7)

            if strong_corrs:
                st.dataframe(pd.DataFrame(strong_corrs), use_container_width=True)
            else:
                st.info("No strong correlations found (threshold: |r| ≥ 0.7)")
                st.subheader("📊 Moderate Correlations (0.5 ≤ |r| < 0.7)")
                moderate_corrs = correlation_analyzer.find_strong_correlations(threshold=0.5)
                moderate_corrs = [c for c in moderate_corrs if abs(c['Correlation']) < 0.7]
                if moderate_corrs:
                    st.dataframe(pd.DataFrame(moderate_corrs), use_container_width=True)
                else:
                    st.info("No moderate correlations found")

            st.divider()
            st.subheader("📈 Explore a Relationship")
            st.write("Pick any two columns from your raw data to plot against each other (not limited to confirmed parameters).")
            numeric_col_list = [c for c in df.columns if pd.to_numeric(df[c], errors='coerce').notna().sum() > 0]
            default_x = strong_corrs[0]['Variable 1'] if strong_corrs else numeric_col_list[0]
            default_y = strong_corrs[0]['Variable 2'] if strong_corrs else (numeric_col_list[1] if len(numeric_col_list) > 1 else numeric_col_list[0])
            sc1, sc2 = st.columns(2)
            with sc1:
                x_var = st.selectbox("X-axis", numeric_col_list, index=numeric_col_list.index(default_x) if default_x in numeric_col_list else 0, key="cg_scatter_x_var")
            with sc2:
                y_default_idx = numeric_col_list.index(default_y) if default_y in numeric_col_list else (1 if len(numeric_col_list) > 1 else 0)
                y_var = st.selectbox("Y-axis", numeric_col_list, index=y_default_idx, key="cg_scatter_y_var")
            if x_var == y_var:
                st.info("Pick two different parameters to see a scatter plot.")
            else:
                fig_scatter = correlation_analyzer.create_scatter_plot(x_var, y_var)
                render_chart_with_download(fig_scatter, key="cg_interactive_scatter")

    # ============================================================
    # TAB 5: COAGULANT PERFORMANCE
    # ============================================================
    with tab5:
        st.header("🧪 Coagulant Performance")
        st.write(f"**Coagulant Type:** {plant_info.get('coagulant_type', 'Not specified')}")

        if detected_params.get('coagulant_dose', {}).get('column'):
            st.subheader("Coagulant Dose")
            dcol = detected_params['coagulant_dose']['column']
            dunit = detected_params['coagulant_dose']['unit']
            st.caption(f"Column used: **{dcol}**")
            fig = chart_renderer.render_line_with_ma(dcol, dunit, "Coagulant Dose")
            render_chart_with_download(fig, key="cg_dose_chart")
            st.caption(f"ℹ️ No fixed benchmark shown — typical range for {plant_info.get('coagulant_type')}: "
                       f"{COAGULANT_TYPICAL_RANGES.get(plant_info.get('coagulant_type'), '')}")

        if detected_params.get('effluent_turbidity', {}).get('column'):
            st.subheader("Effluent Turbidity")
            tcol = detected_params['effluent_turbidity']['column']
            tunit = detected_params['effluent_turbidity']['unit']
            st.caption(f"Column used: **{tcol}**")
            fig = chart_renderer.render_line_with_ma(tcol, tunit, "Effluent Turbidity", threshold_excellent=2, threshold_good=5)
            render_chart_with_download(fig, key="cg_turb_chart")
            render_footnote('effluent_turbidity', ' NTU')

        if detected_params.get('influent_turbidity', {}).get('column') and detected_params.get('effluent_turbidity', {}).get('column'):
            st.subheader("Turbidity Removal Efficiency")
            icol = detected_params['influent_turbidity']['column']
            ecol = detected_params['effluent_turbidity']['column']
            st.caption(f"Columns used: **{icol}** / **{ecol}**")
            inf_s = pd.to_numeric(df[icol], errors='coerce')
            eff_s = pd.to_numeric(df[ecol], errors='coerce')
            removal_series = ((inf_s - eff_s) / inf_s * 100).clip(lower=0, upper=100)
            removal_ma = removal_series.rolling(window=7).mean()
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=removal_series, mode='markers', name='Daily', marker=dict(size=4, color=VEOLIA['sky_blue'], opacity=0.7)))
            fig.add_trace(go.Scatter(x=df.index, y=removal_ma, mode='lines', name='7-day MA', line=dict(color=VEOLIA['marine'], width=2)))
            fig.add_hline(y=90, line_dash="dash", line_color=VEOLIA['forest_green'], annotation_text="Excellent")
            fig.update_layout(title="Turbidity Removal Efficiency (%)", height=400, hovermode='x unified',
                               plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF', font=dict(color=VEOLIA['marine']),
                               xaxis=dict(gridcolor='#E9EEF1', title="Days"), yaxis=dict(gridcolor='#E9EEF1', title='%'))
            render_chart_with_download(fig, key="cg_removal_chart")
            render_footnote('turbidity_removal', '%')

        if detected_params.get('influent_ph', {}).get('column') and detected_params.get('effluent_ph', {}).get('column'):
            st.subheader("pH Depression")
            icol = detected_params['influent_ph']['column']
            ecol = detected_params['effluent_ph']['column']
            st.caption(f"Columns used: **{icol}** / **{ecol}**")
            fig = chart_renderer.render_ratio(icol, ecol, "ratio (informational only - see KPI for depression)", "Influent/Effluent pH Ratio (informational)")
            render_chart_with_download(fig, key="cg_ph_ratio_chart")
            st.caption("ℹ️ For an actual pH depression trend (influent − effluent), see the pH Depression KPI on the Dashboard.")

        if detected_params.get('effluent_alkalinity', {}).get('column'):
            st.subheader("Residual Alkalinity")
            acol = detected_params['effluent_alkalinity']['column']
            aunit = detected_params['effluent_alkalinity']['unit']
            st.caption(f"Column used: **{acol}**")
            fig = chart_renderer.render_line_with_ma(acol, aunit, "Residual Alkalinity", threshold_excellent=50, threshold_good=30)
            render_chart_with_download(fig, key="cg_alk_chart")
            render_footnote('residual_alkalinity', ' mg/L')

        if not any(detected_params.get(k, {}).get('column') for k in ['coagulant_dose', 'effluent_turbidity', 'influent_turbidity', 'effluent_alkalinity']):
            st.info("No coagulant addition indicators are confirmed yet. Check **Confirm Data Mapping** above.")

    # ============================================================
    # TAB 6: DATA QUALITY
    # ============================================================
    with tab6:
        st.header("🔍 Data Quality Analysis")
        columns_to_check = [p['column'] for p in detected_params.values() if p['column']]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Records", len(df))
        with c2:
            st.metric("Columns Confirmed", len(columns_to_check))
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
    # TAB 7: PARAMETERS
    # ============================================================
    with tab7:
        st.header("📋 Confirmed Parameters & Units")
        param_data = []
        for param_name, param_info in detected_params.items():
            param_data.append({
                'Category': categorize_param(param_name),
                'Parameter': param_name,
                'Column': param_info['column'] if param_info['column'] else '— not detected —',
                'Unit': param_info['unit'],
                'Match Score': f"{param_info['score']:.0f}%",
            })
        param_df = pd.DataFrame(param_data).sort_values(['Category', 'Parameter'])
        st.dataframe(param_df, use_container_width=True)
        csv = param_df.to_csv(index=False)
        st.download_button("📥 Download Parameters", data=csv, file_name="coagulant_parameters.csv", mime="text/csv")

    # ============================================================
    # TAB 8: RAW DATA
    # ============================================================
    with tab8:
        st.header("📥 Raw Data")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Data", data=csv, file_name="coagulant_data.csv", mime="text/csv")

st.success("✅ Module loaded successfully!")

