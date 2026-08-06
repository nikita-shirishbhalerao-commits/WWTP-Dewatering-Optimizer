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
    render_mapping_editor as _render_mapping_editor, render_date_column_selector,
    CorrelationAnalyzer, ChartRenderer, render_kpi_grid,
    BaseKPICalculator, BaseRecommendationEngine, render_recommendations_tab,
)

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Disinfection Analyzer",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_theme()
render_header("🦠 AI-Powered Disinfection Performance Analyzer")

# ============================================================
# PERFORMANCE THRESHOLDS
# ============================================================
PERFORMANCE_THRESHOLDS = {
    'chlorine_residual_precontact': {'excellent': (1.0, float('inf')), 'good': (0.5, 1.0), 'moderate': (0.2, 0.5), 'poor': (0, 0.2)},
    'chlorine_residual_final': {'excellent': (0, 0.05), 'good': (0.05, 0.1), 'moderate': (0.1, 0.2), 'poor': (0.2, float('inf'))},
    'uv_dose': {'excellent': (40, float('inf')), 'good': (30, 40), 'moderate': (20, 30), 'poor': (0, 20)},
    'disinfection_equipment_availability': {'excellent': (98, float('inf')), 'good': (95, 98), 'moderate': (90, 95), 'poor': (0, 90)},
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
DISINFECTION_KPI_DEFINITIONS = {
    'chlorine_dose': {'name': 'Chlorine Dose (mg/L)', 'description': 'Chlorine (as Cl2) applied per unit volume treated. Reported informationally — required dose depends heavily on chlorine demand of the wastewater, which this app cannot measure directly.'},
    'chlorine_residual_precontact': {'name': 'Chlorine Residual - Pre-Dechlorination (mg/L)', 'description': 'Residual chlorine at/near the end of the contact tank, before dechlorination. This is the value that actually drives CT (disinfection) credit.'},
    'chlorine_residual_final': {'name': 'Chlorine Residual - Final Effluent (mg/L)', 'description': 'Residual chlorine after dechlorination, at discharge. Most permits require this to be very low to near-zero to protect aquatic life.'},
    'contact_time': {'name': 'Contact Time (minutes)', 'description': 'Hydraulic detention time in the disinfection contact tank/channel.'},
    'ct_value': {'name': 'CT Value (mg/L·min)', 'description': 'Concentration × Time — the standard disinfection compliance metric for chlorine systems. Required CT varies by regulation, temperature, and pH; reported informationally.'},
    'uv_dose': {'name': 'UV Dose (mJ/cm²)', 'description': 'Delivered UV dose. Many state guidance documents cite ≥30 mJ/cm² as a common minimum for disinfection credit — verify your specific permit requirement.'},
    'uv_transmittance': {'name': 'UV Transmittance (%UVT)', 'description': 'Water clarity at the UV wavelength. Typical secondary effluent runs 55-75% UVT; lower UVT reduces delivered dose for a given lamp output.'},
    'effluent_bacteria': {'name': 'Effluent Bacteria (CFU or MPN/100mL)', 'description': 'Fecal coliform, E. coli, or enterococci as logged. Compare against your specific discharge permit limit, which this app does not know.'},
    'dechlor_dose': {'name': 'Dechlorination Chemical Dose (mg/L)', 'description': 'Sulfur dioxide or sodium bisulfite (or similar) dose used to neutralize residual chlorine before discharge.'},
    'disinfectant_cost_per_mg': {'name': 'Disinfectant Cost per MG Treated ($/MG)', 'description': 'Economic indicator of disinfection chemical/power cost normalized to flow treated.'},
    'flow_disinfected': {'name': 'Flow Disinfected (MGD)', 'description': 'Flow rate through the disinfection process.'},
    'disinfection_equipment_availability': {'name': 'Disinfection Equipment Availability (%)', 'description': 'Uptime percentage of disinfection equipment (chlorinator, UV bank, or ozone generator). Disinfection is typically a permit-critical process with little tolerance for downtime.'},
    'chlorine_feed_rate': {'name': 'Chlorine Feed Rate (lbs/day or gpd)', 'description': 'Feed rate of chlorine or hypochlorite solution.'},
    'ozone_dose': {'name': 'Ozone Dose (mg/L)', 'description': 'Ozone applied per unit volume treated, if ozone disinfection is used.'},
    'hypochlorite_strength': {'name': 'Hypochlorite Solution Strength (%)', 'description': 'Available chlorine strength of the stored/fed hypochlorite solution. Trade strength is typically 10-15% (commonly 12.5%), but it degrades over time — faster with heat, sunlight, and age — so the *effective* dose delivered can fall even when the feed rate setpoint stays constant.'},
}

# ============================================================
# RECOMMENDATION TEMPLATES + PRIORITY MAP
# ============================================================
RECOMMENDATION_TEMPLATES = {
    'chlorine_residual_precontact': {
        'issue': 'Chlorine residual ahead of dechlorination is the value that actually drives CT (concentration × time) '
                 'disinfection credit - a low residual here means inadequate pathogen inactivation is likely occurring '
                 'regardless of how the dose is set, since demand (not dose) determines how much residual survives to '
                 'do disinfection work.',
        'root_causes': [
            'Chlorine demand of the wastewater has increased (higher ammonia, organics, or industrial loading consuming chlorine before it can act as a disinfectant residual)',
            'Feed dose set too low for current demand - dose and demand are not the same thing, and demand can drift independently of flow',
            'Feed equipment underperforming (pump calibration, gas feeder issue, hypochlorite degradation in storage - hypochlorite loses strength over time, faster in heat/sunlight)',
            'Contact tank short-circuiting reducing effective contact even if dose/residual at the sample point look adequate',
        ],
        'actions': [
            'Check influent ammonia-nitrogen trend - breakpoint chlorination demand rises sharply with ammonia, and this is a very common driver of "unexplained" residual drops',
            'Verify feed equipment calibration and, for hypochlorite, confirm stored solution strength hasn\'t degraded (test % available chlorine against the delivery certificate)',
            'Increase dose incrementally and confirm residual responds proportionally - a flat response despite dose increases points to a demand or equipment issue, not a dose-setpoint issue',
            'If using hypochlorite, review storage conditions (temperature, sunlight exposure, age) - degradation is a frequently overlooked cause of "the same dose stopped working"',
        ],
        'additional_data': ['Influent ammonia-nitrogen trend', 'Hypochlorite storage tank age/conditions if applicable', 'Feed equipment calibration log'],
        'timeline': '1 week - this affects disinfection compliance', 'risk': 'High - potential compliance/public health issue',
    },
    'chlorine_residual_final': {
        'issue': 'Elevated final effluent chlorine residual after dechlorination is a common cause of aquatic toxicity '
                 'permit exceedances - chlorine and its byproducts are toxic to aquatic life at very low concentrations, '
                 'which is why most permits require near-complete dechlorination.',
        'root_causes': ['Dechlorination chemical dose insufficient for the actual pre-dechlorination residual (which may be varying more than the dechlorination feed is tracking)', 'Dechlorination feed not flow- or residual-paced, so it doesn\'t track chlorine residual swings', 'Insufficient mixing/contact time for the dechlorination reaction to complete', 'Dechlorination feed equipment issue (similar failure modes to chlorine feed - calibration, chemical strength)'],
        'actions': ['Compare the dechlorination dose trend against the pre-dechlorination chlorine residual trend - if the latter varies but the former doesn\'t track it, that\'s the fix', 'Consider residual-paced (rather than flow-paced only) dechlorination control if not already in place', 'Verify adequate mixing at the dechlorination injection point'],
        'additional_data': ['Pre-dechlorination chlorine residual trend for comparison', 'Dechlorination control strategy (flow-paced vs. residual-paced)'],
        'timeline': '1-2 weeks - potential permit compliance issue', 'risk': 'High - potential aquatic toxicity/compliance issue',
    },
    'uv_dose': {
        'issue': 'UV dose below common regulatory minimums (many states cite ≥30 mJ/cm² - verify your specific permit) '
                 'risks inadequate pathogen inactivation. UV dose is a function of both lamp output/intensity and the '
                 'water\'s UV transmittance, so a dose shortfall can come from either side.',
        'root_causes': ['UV transmittance has dropped (higher effluent color/organics/TSS absorbing UV light before it reaches target organisms)', 'Lamp output declining (lamp aging - UV output typically derates over lamp life and is usually rated for a specific service life)', 'Quartz sleeve fouling reducing UV transmission from lamp to water', 'Flow rate too high for the validated dose-delivery curve of the UV system at current UVT'],
        'actions': ['Check UV Transmittance KPI - if it has dropped, the fix may be upstream (better upstream solids/organics removal) rather than the UV system itself', 'Review lamp age against rated service life and replacement schedule', 'Inspect/clean quartz sleeves if fouling is suspected (mineral scale, biofilm)', 'Confirm flow rate is within the system\'s validated dose curve at current UVT - some systems throttle dose delivery at high flow'],
        'additional_data': ['UV transmittance trend', 'Lamp age/hours since installation', 'Quartz sleeve cleaning schedule and last-cleaned date'],
        'timeline': '1-2 weeks - potential compliance issue', 'risk': 'High - potential compliance/public health issue',
    },
    'disinfection_equipment_availability': {
        'issue': 'Disinfection equipment downtime is a direct public health/compliance risk in a way most other unit '
                 'processes are not - there is typically no buffering capacity, and many permits treat any disinfection '
                 'downtime during flow as a reportable event.',
        'root_causes': ['Unplanned equipment failure (chlorinator, UV bank, or ozone generator)', 'Insufficient redundancy for maintenance windows (single train, no standby capacity)', 'Recurring failure mode not yet root-caused'],
        'actions': ['Pull maintenance work order history and categorize by cause code to find the dominant failure mode', 'Evaluate standby/redundant capacity - given the compliance criticality of this process, redundancy standards here are typically higher than for other unit processes', 'Prioritize root-causing any recurring failure mode given the compliance stakes'],
        'additional_data': ['Maintenance work order history with downtime cause codes', 'Standby/redundant equipment configuration'],
        'timeline': '2-4 weeks - high priority given compliance criticality', 'risk': 'High - direct compliance/public health risk during downtime',
    },
    'disinfectant_cost_per_mg': {
        'issue': 'Disinfectant cost per MG treated elevated by either dose (a process/demand problem) or unit price (a '
                 'procurement problem) - check the residual/dose KPIs first to see which is driving it.',
        'root_causes': ['Dose above what\'s needed for the chlorine/UV/ozone demand actually present', 'Chemical unit price above current market rate'],
        'actions': ['If chlorine residual is well above the excellent threshold, dose may be higher than needed - a controlled reduction with residual monitoring can cut cost without compromising disinfection', 'If dose/residual look appropriate, benchmark chemical pricing against competing suppliers'],
        'additional_data': ['Chlorine/UV power/ozone contract pricing'],
        'timeline': '4-6 weeks', 'risk': 'Low',
    },
    'hypochlorite_strength': {
        'issue': 'Sodium hypochlorite solution degrades over time - faster with heat, sunlight exposure, and higher '
                 'initial concentration. A strength drop below ~10% means your feed rate setpoint is delivering less '
                 'actual chlorine than it was calibrated for, which shows up as an unexplained residual/CT shortfall '
                 'even though "nothing changed" on the feed system.',
        'root_causes': [
            'Stored solution has aged past its effective shelf life (degradation accelerates significantly in the first few weeks for higher-strength products)',
            'Storage tank exposed to heat (direct sun, uninsulated tank in a hot climate) or not shielded from UV light',
            'Delivered product was already lower-strength than ordered (received strength should be verified against the delivery certificate, not assumed)',
            'Excess inventory / low turnover - ordering more than is used within the effective shelf life means older, weaker product is always in the tank',
        ],
        'actions': [
            'Verify delivered strength against the supplier\'s certificate of analysis at time of delivery, and periodically titrate stored solution to track degradation over time',
            'Review storage conditions - shade/insulate tanks if exposed to direct sun or high ambient heat, since degradation rate roughly doubles for every ~10-15°F increase',
            'Right-size delivery/order quantity to inventory turnover so stored solution doesn\'t sit long enough to degrade significantly before use',
            'If strength is confirmed low, compensate feed rate upward until fresh product arrives, then recalibrate - don\'t just leave the setpoint unchanged and accept the residual shortfall',
        ],
        'additional_data': ['Delivery certificates of analysis (received strength)', 'Storage tank conditions (shaded/insulated vs. exposed)', 'Typical time-in-storage before use'],
        'timeline': '1 week - directly affects delivered disinfection dose', 'risk': 'Medium - can cause an unexplained residual/CT shortfall',
    },
}

PRIORITY_MAP = {
    'chlorine_residual_precontact': '🔴 CRITICAL', 'chlorine_residual_final': '🔴 CRITICAL',
    'uv_dose': '🔴 CRITICAL', 'disinfection_equipment_availability': '🟠 HIGH',
    'disinfectant_cost_per_mg': '🟡 MEDIUM', 'hypochlorite_strength': '🟠 HIGH',
}


def estimate_savings(key, val):
    if key in ('chlorine_residual_precontact', 'chlorine_residual_final', 'uv_dose', 'disinfection_equipment_availability'):
        return ("Compliance risk reduction", "This KPI is about disinfection adequacy/compliance rather than direct cost savings - the primary value of fixing it is avoiding a permit exceedance or public health risk, not a dollar figure this app can estimate.")
    return ("Improves process efficiency", "Specific dollar savings require site-specific cost data not available from the uploaded dataset.")


# ============================================================
# PARAMETER KEYWORDS
# ============================================================
PARAMETER_KEYWORDS = {
    'chlorine_dose': ['chlorine dose mg l', 'cl2 dose', 'sodium hypochlorite dose', 'chlorine applied dose', 'naocl dose', 'naocl dose gal mg', 'naocl dose lbs mg', 'sodium hypo dose'],
    'chlorine_residual_precontact': ['chlorine residual mg l', 'total residual chlorine', 'free chlorine residual', 'contact tank residual chlorine', 'chlorine residual pre dechlor', 'chlorine residual pre de chlor'],
    'chlorine_residual_final': ['final chlorine residual', 'effluent chlorine residual', 'discharge chlorine residual', 'residual chlorine after dechlorination'],
    'contact_time': ['contact time minutes', 'chlorine contact time', 'detention time disinfection'],
    'uv_dose': ['uv dose mj cm2', 'uv dose', 'ultraviolet dose'],
    'uv_transmittance': ['uv transmittance percent', 'uvt percent', 'uv transmittance'],
    'effluent_bacteria': ['fecal coliform', 'e coli effluent', 'enterococci effluent', 'effluent bacteria cfu'],
    'dechlor_dose': ['dechlorination dose', 'sodium bisulfite dose', 'sulfur dioxide dose', 'so2 dose'],
    'disinfectant_cost': ['disinfection cost dollars', 'chlorine cost', 'hypochlorite cost', 'uv power cost'],
    'flow_disinfected': ['flow disinfected mgd', 'effluent flow mgd', 'plant flow mgd disinfection'],
    'disinfection_run_hours': ['disinfection equipment run hours', 'uv system run hours', 'chlorinator run hours'],
    'chlorine_feed_rate': ['chlorine feed rate lbs day', 'hypochlorite feed gpd', 'chlorine feed lbs', 'naocl used gallons', 'sodium hypo used', 'naocl feed rate'],
    'ozone_dose': ['ozone dose mg l', 'ozone applied dose'],
    'hypochlorite_strength': ['hypochlorite strength percent', 'naocl strength', 'available chlorine percent', 'hypo strength percent'],
}

EXPECTED_UNIT_FAMILIES = {
    'chlorine_dose': {'mg/L', 'lbs/MG', 'gal/MG'},
    'chlorine_residual_precontact': {'mg/L'},
    'chlorine_residual_final': {'mg/L'},
    'dechlor_dose': {'mg/L'},
    'disinfectant_cost': {'$'},
    'flow_disinfected': {'MGD', 'GPM', 'GPD'},
    'disinfection_run_hours': {'Hours'},
    'ozone_dose': {'mg/L'},
    'hypochlorite_strength': {'%'},
}

REQUIRED_TOKEN_GROUPS = {
    'chlorine_residual_precontact': [['chlorine', 'cl2', 'hypochlorite', 'naocl']],
    'chlorine_residual_final': [['chlorine', 'cl2', 'hypochlorite', 'naocl'], ['final', 'effluent', 'discharge']],
    'chlorine_dose': [['chlorine', 'cl2', 'hypochlorite', 'naocl']],
    'chlorine_feed_rate': [['chlorine', 'cl2', 'hypochlorite', 'naocl']],
    'uv_dose': [['uv', 'ultraviolet']],
    'uv_transmittance': [['uv', 'uvt', 'transmittance']],
    'ozone_dose': [['ozone']],
    'hypochlorite_strength': [['hypo', 'naocl', 'hypochlorite']],
}

EXCLUDE_TOKENS = {
    'chlorine_residual_precontact': ['final', 'discharge', 'dose', 'effluent'],
    'chlorine_dose': ['residual'],
    'uv_dose': ['transmittance', 'uvt'],
    'uv_transmittance': ['dose'],
    'chlorine_residual_final': ['dose'],
}


def categorize_param(key):
    if 'chlorine' in key or 'dechlor' in key or 'hypochlorite' in key:
        return 'Chlorination'
    if 'uv' in key:
        return 'UV'
    if 'ozone' in key:
        return 'Ozone'
    return 'Process'


# ============================================================
# KPI CALCULATOR
# ============================================================
class KPICalculator(BaseKPICalculator):
    def calculate_disinfection_kpis(self):
        k = {}
        method = self.plant_info.get('disinfection_method', 'Sodium Hypochlorite')

        dose_col = self.dp.get('chlorine_dose', {}).get('column')
        dose = self._col('chlorine_dose')
        if dose is not None:
            k['chlorine_dose'] = {'value': dose.mean(), 'unit': 'mg/L', 'target': 'Varies by chlorine demand', 'status': 'ℹ️ Informational',
                                   'basis': f"Average of **{dose_col}**."}
        else:
            k['chlorine_dose'] = self._insufficient(['Chlorine dose (mg/L) column'])

        pre_col = self.dp.get('chlorine_residual_precontact', {}).get('column')
        pre = self._col('chlorine_residual_precontact')
        if pre is not None:
            v = pre.mean()
            k['chlorine_residual_precontact'] = {'value': v, 'unit': 'mg/L', 'target': '>0.5 mg/L (common reference minimum - verify your CT/permit requirement)', 'status': self._status_lower(v, 0.5),
                                                  'basis': f"Average of **{pre_col}**."}
        else:
            k['chlorine_residual_precontact'] = self._insufficient(['Chlorine residual before dechlorination (mg/L) column'])

        fin_col = self.dp.get('chlorine_residual_final', {}).get('column')
        fin = self._col('chlorine_residual_final')
        if fin is not None:
            v = fin.mean()
            k['chlorine_residual_final'] = {'value': v, 'unit': 'mg/L', 'target': '<0.1 mg/L (common reference for aquatic toxicity - verify your specific permit)', 'status': self._status_upper(v, 0.1),
                                             'basis': f"Average of **{fin_col}**."}
        else:
            k['chlorine_residual_final'] = self._insufficient(['Final/discharge chlorine residual (mg/L) column'])

        ct_col = self.dp.get('contact_time', {}).get('column')
        ct = self._col('contact_time')
        if ct is not None:
            k['contact_time'] = {'value': ct.mean(), 'unit': 'min', 'target': 'Verify against your CT/permit requirement', 'status': 'ℹ️ Informational',
                                  'basis': f"Average of **{ct_col}**."}
        else:
            k['contact_time'] = self._insufficient(['Contact time (minutes) column'])

        if pre is not None and ct is not None:
            ct_value = pre.mean() * ct.mean()
            k['ct_value'] = {'value': ct_value, 'unit': 'mg/L·min', 'target': 'Required CT varies by regulation/temperature/pH - verify your permit', 'status': 'ℹ️ Informational',
                              'basis': f"Average **{pre_col}** × average **{ct_col}**."}
        else:
            k['ct_value'] = self._insufficient(['Both chlorine residual (pre-dechlorination) and contact time columns'])

        uv_col = self.dp.get('uv_dose', {}).get('column')
        uv = self._col('uv_dose')
        if uv is not None:
            v = uv.mean()
            k['uv_dose'] = {'value': v, 'unit': 'mJ/cm²', 'target': '>30 mJ/cm² (common reference minimum - verify your specific permit)', 'status': self._status_lower(v, 30),
                             'basis': f"Average of **{uv_col}**."}
        else:
            k['uv_dose'] = self._insufficient(['UV dose (mJ/cm²) column'])

        uvt_col = self.dp.get('uv_transmittance', {}).get('column')
        uvt = self._col('uv_transmittance')
        if uvt is not None:
            k['uv_transmittance'] = {'value': uvt.mean(), 'unit': '%', 'target': 'Typical secondary effluent: 55-75% UVT', 'status': 'ℹ️ Informational',
                                      'basis': f"Average of **{uvt_col}**."}
        else:
            k['uv_transmittance'] = self._insufficient(['UV transmittance (%UVT) column'])

        bact_col = self.dp.get('effluent_bacteria', {}).get('column')
        bact = self._col('effluent_bacteria')
        if bact is not None:
            k['effluent_bacteria'] = {'value': bact.mean(), 'unit': self.dp.get('effluent_bacteria', {}).get('unit', 'CFU or MPN/100mL'), 'target': 'Compare to your discharge permit limit', 'status': 'ℹ️ Informational',
                                       'basis': f"Average of **{bact_col}**."}
        else:
            k['effluent_bacteria'] = self._insufficient(['Effluent fecal coliform/E. coli/enterococci column'])

        dechlor_col = self.dp.get('dechlor_dose', {}).get('column')
        dechlor = self._col('dechlor_dose')
        if dechlor is not None:
            k['dechlor_dose'] = {'value': dechlor.mean(), 'unit': 'mg/L', 'target': 'Track alongside pre-dechlorination residual', 'status': 'ℹ️ Informational',
                                  'basis': f"Average of **{dechlor_col}**."}
        else:
            k['dechlor_dose'] = self._insufficient(['Dechlorination chemical dose (mg/L) column'])

        cost_col = self.dp.get('disinfectant_cost', {}).get('column')
        flow_col = self.dp.get('flow_disinfected', {}).get('column')
        if cost_col and flow_col:
            cost_series = pd.to_numeric(self.df[cost_col], errors='coerce')
            flow_series = pd.to_numeric(self.df[flow_col], errors='coerce')
            ratio = (cost_series / flow_series).replace([np.inf, -np.inf], np.nan).dropna()
            if len(ratio) > 0:
                k['disinfectant_cost_per_mg'] = {'value': ratio.mean(), 'unit': '$/MG', 'target': 'Varies by method and contract pricing', 'status': 'ℹ️ Informational',
                                                  'basis': f"Average of (**{cost_col}** ÷ **{flow_col}**), assuming {cost_col} is a $/day total cost and {flow_col} is in MGD."}
            else:
                k['disinfectant_cost_per_mg'] = self._insufficient(['Disinfectant cost ($/day) and flow disinfected (MGD) columns (valid paired data)'])
        else:
            k['disinfectant_cost_per_mg'] = self._insufficient(['Disinfectant cost ($/day) column together with flow disinfected (MGD) column'])

        if flow_col:
            flow_series = pd.to_numeric(self.df[flow_col], errors='coerce').dropna()
            if len(flow_series) > 0:
                k['flow_disinfected'] = {'value': flow_series.mean(), 'unit': 'MGD', 'target': 'Informational', 'status': 'ℹ️ Informational',
                                          'basis': f"Average of **{flow_col}**."}
            else:
                k['flow_disinfected'] = self._insufficient(['Flow disinfected (MGD) column'])
        else:
            k['flow_disinfected'] = self._insufficient(['Flow disinfected (MGD) column'])

        hrs_col = self.dp.get('disinfection_run_hours', {}).get('column')
        hrs = self._col('disinfection_run_hours')
        if hrs is not None:
            period_days = self.plant_info.get('period_days', 1.0)
            hours_available = 24 * period_days
            v = (hrs / hours_available * 100).clip(upper=100).mean()
            k['disinfection_equipment_availability'] = {'value': v, 'unit': '%', 'target': '>98%', 'status': self._status_lower(v, 95),
                                                          'basis': f"Average of (**{hrs_col}** ÷ {hours_available:.0f} possible hours per record [24 × "
                                                                    f"{period_days:.0f}-day reporting period] × 100)."}
        else:
            k['disinfection_equipment_availability'] = self._insufficient(['Disinfection equipment run-hours column'])

        feed_col = self.dp.get('chlorine_feed_rate', {}).get('column')
        feed = self._col('chlorine_feed_rate')
        if feed is not None:
            k['chlorine_feed_rate'] = {'value': feed.mean(), 'unit': self.dp.get('chlorine_feed_rate', {}).get('unit', 'units'), 'target': 'Varies by equipment', 'status': 'ℹ️ Informational',
                                        'basis': f"Average of **{feed_col}**."}
        else:
            k['chlorine_feed_rate'] = self._insufficient(['Chlorine feed rate column'])

        ozone_col = self.dp.get('ozone_dose', {}).get('column')
        ozone = self._col('ozone_dose')
        if ozone is not None:
            k['ozone_dose'] = {'value': ozone.mean(), 'unit': 'mg/L', 'target': 'Varies by ozone demand and application', 'status': 'ℹ️ Informational',
                                'basis': f"Average of **{ozone_col}**."}
        else:
            k['ozone_dose'] = self._insufficient(['Ozone dose (mg/L) column'])

        hypo_col = self.dp.get('hypochlorite_strength', {}).get('column')
        hypo = self._col('hypochlorite_strength')
        if hypo is not None:
            v = hypo.mean()
            k['hypochlorite_strength'] = {'value': v, 'unit': '%', 'target': '10-15% trade strength (commonly 12.5%) - flagged below 10%', 'status': self._status_lower(v, 10),
                                           'basis': f"Average of **{hypo_col}**."}
        else:
            k['hypochlorite_strength'] = self._insufficient(['Hypochlorite/NaOCl solution strength (%) column - if you titrate or receive a certificate of analysis for delivered strength, logging it here catches degradation-driven dose shortfalls that feed-rate data alone won\'t show'])

        return k


# ============================================================
# SIDEBAR - FILE UPLOAD
# ============================================================
st.sidebar.header("📊 Upload Your Data")
uploaded_file = st.sidebar.file_uploader("Choose your Disinfection CSV file", type=['csv'], help="Upload a CSV file with your disinfection data")

if uploaded_file is None:
    st.info("👈 **Please upload a CSV file to get started**")
    st.markdown("""
    ### 📋 Expected Data Format

    Your CSV should contain columns like:

    **Chlorination:** Chlorine Dose (mg/L), Chlorine Residual (pre- and post-dechlorination), Contact Time,
    Dechlorination Dose, Chlorine Feed Rate

    **UV:** UV Dose (mJ/cm²), UV Transmittance (%UVT), UV System Run Hours

    **Ozone:** Ozone Dose (mg/L)

    **Compliance:** Effluent Fecal Coliform/E. coli/Enterococci, Flow Disinfected (MGD)

    **Cost:** Disinfectant Cost

    ### ✨ Features
    - 🔍 Fuzzy Logic auto-detects your columns — confirm/correct the mapping before anything is calculated
    - 📊 AI-derived KPI dashboard (only shows what can be computed from your data, no assumed units)
    - 💡 Technically-grounded recommendations (chlorination/UV/ozone process engineering, no external API needed)
    - 📈 Trend, custom-period, and Period A vs Period B benchmark comparison
    - 🔗 Correlation analysis between parameters
    - 🔎 Data quality / outlier detection

    ### 🚀 Ready? Upload your file!
    """)
else:
    try:
        df, date_col, used_synthetic_dates = load_process_csv(uploaded_file)
        st.sidebar.success(f"✅ Loaded {len(df)} records")
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()

    st.subheader("📅 Confirm Date Column")
    df, date_col, period_days, period_label, ma_window = render_date_column_selector(df, date_col, used_synthetic_dates, key_prefix="dis")
    st.sidebar.write(f"📅 {df[date_col].min().date()} to {df[date_col].max().date()}")
    st.sidebar.caption(f"Reporting frequency: {period_label}")
    st.divider()

    with st.sidebar.expander("🏭 Plant Information", expanded=False):
        plant_name = st.text_input("Plant Name", value="WWTP", key="dis_plant_name")
        plant_location = st.text_input("Location", value="", key="dis_plant_location")
        disinfection_method = st.selectbox("Disinfection Method", ["Sodium Hypochlorite", "Chlorine Gas", "UV Disinfection", "Ozone", "Combination/Other"], key="dis_method")
        plant_capacity = st.number_input("Plant Capacity (MGD)", value=10.0, min_value=0.1, key="dis_capacity")

        plant_info = {
            'name': plant_name, 'location': plant_location, 'disinfection_method': disinfection_method,
            'capacity': plant_capacity, 'period_days': period_days, 'period_label': period_label,
        }

    # ------------------------------------------------------
    # PARAMETER DETECTION + CONFIRM/EDIT MAPPING
    # ------------------------------------------------------
    auto_detected_params = _detect_parameters(df, PARAMETER_KEYWORDS, EXPECTED_UNIT_FAMILIES, REQUIRED_TOKEN_GROUPS, EXCLUDE_TOKENS, threshold=55, exclude_columns=[date_col])

    st.header("🔧 Confirm Data Mapping")
    st.write(
        "This is exactly what we matched your columns to, with a confidence score. **Every KPI, chart, and "
        "recommendation below uses only this table** — fix any row that picked the wrong column, or set it to "
        "**'— None detected —'** if you don't have that data. Nothing is assumed beyond what you confirm here."
    )
    with st.expander("📝 Review & edit detected columns", expanded=True):
        detected_params = _render_mapping_editor(auto_detected_params, df.columns, key_prefix="dis_main", categorize_fn=categorize_param)

    st.divider()

    st.sidebar.subheader("🔍 Confirmed Parameters")
    detected_count = sum(1 for p in detected_params.values() if p['column'])
    for param_name, param_info in detected_params.items():
        if param_info['column']:
            st.sidebar.write(f"✅ {param_name}: **{param_info['column']}** ({param_info['unit']})")
    st.sidebar.write(f"\n**Confirmed: {detected_count}/{len(detected_params)} parameters**")

    analyzer = BaseRecommendationEngine(
        [DISINFECTION_KPI_DEFINITIONS], RECOMMENDATION_TEMPLATES, PRIORITY_MAP, savings_estimator=estimate_savings,
    )
    kpi_calculator = KPICalculator(df, detected_params, plant_info)
    correlation_analyzer = CorrelationAnalyzer(df, detected_params)
    chart_renderer = ChartRenderer(df, ma_window=ma_window, ma_label=f"{ma_window}-period Avg ({period_label})")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Dashboard", "💡 AI Recommendations", "📈 Trend / Benchmark", "🔗 Correlation Analysis",
        "🦠 Disinfection Performance", "🔍 Data Quality", "📋 Parameters", "📥 Raw Data",
    ])

    # ============================================================
    # TAB 1: DASHBOARD
    # ============================================================
    with tab1:
        header_col, year_col = st.columns([3, 1])
        with header_col:
            st.header(f"📊 Performance Dashboard - {plant_info.get('name', 'WWTP')}")
            if plant_info.get('location'):
                st.caption(f"📍 {plant_info['location']} | Capacity: {plant_info.get('capacity', 'N/A')} MGD | Method: {plant_info.get('disinfection_method')}")

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
            selected_year_str = st.selectbox("Year", year_options, index=default_index, key="dis_dashboard_year_filter")

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
        dis_kpis = dashboard_kpi_calculator.calculate_disinfection_kpis()

        st.subheader("🦠 Disinfection KPIs")
        render_kpi_grid(dis_kpis, DISINFECTION_KPI_DEFINITIONS)

    # ============================================================
    # TAB 2: AI RECOMMENDATIONS
    # ============================================================
    with tab2:
        st.header("💡 AI-Powered Recommendations")
        st.write("Generated from the KPIs on the Dashboard tab, using only the parameters you confirmed above. Purely "
                 "rule-based (no external API/key needed) - grounded in chlorination/UV/ozone process engineering.")

        dis_kpis = kpi_calculator.calculate_disinfection_kpis()
        recommendations, good_items = analyzer.generate_recommendations(dis_kpis)
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
                                     help="A ratio lets you build any custom metric on the fly (pick a numerator and a denominator column), e.g. Disinfectant Cost ÷ Flow Disinfected.",
                                     key="dis_analyze_mode")

            if analyze_mode == "Single Indicator":
                selected_column = st.selectbox("Select Indicator", list(numeric_cols.keys()), format_func=lambda x: f"{x} ({numeric_cols[x]})", key="dis_selected_column")
                working_label = selected_column
                working_unit = numeric_cols[selected_column]
                working_series = pd.to_numeric(df[selected_column], errors='coerce')
            else:
                rc1, rc2 = st.columns(2)
                col_list = list(numeric_cols.keys())
                with rc1:
                    numerator_col = st.selectbox("Numerator", col_list, format_func=lambda x: f"{x} ({numeric_cols[x]})", key="dis_ratio_numerator")
                with rc2:
                    default_denom_idx = 1 if len(col_list) > 1 else 0
                    denominator_col = st.selectbox("Denominator", col_list, index=default_denom_idx, format_func=lambda x: f"{x} ({numeric_cols[x]})", key="dis_ratio_denominator")
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
                aggregation = st.selectbox("Aggregation Period", ["Daily", "Weekly", "Monthly", "Quarterly"], key="dis_aggregation")
            with col_s3:
                agg_method = st.selectbox("Aggregation Method", ["Average", "Total"], key="dis_agg_method")

            agg_func = 'sum' if agg_method == 'Total' else 'mean'
            freq_map = {"Daily": 'D', "Weekly": 'W', "Monthly": 'MS', "Quarterly": 'QS'}

            mode = st.radio("Analysis Mode", ["Full Timeline", "Custom Period", "Period A vs Period B (Benchmark)"], horizontal=True, key="dis_mode")

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
                    render_chart_with_download(fig, key="dis_trend_single_chart")

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
                    date_range = st.date_input("Select Date Range", value=(data_min, data_max), min_value=data_min, max_value=data_max, key="dis_custom_period")
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
                        a_range = st.date_input("Period A date range", value=(data_min, midpoint), min_value=data_min, max_value=data_max, key="dis_period_a_range")
                    with pc2:
                        st.markdown("**Period B**")
                        b_range = st.date_input("Period B date range", value=(midpoint, data_max), min_value=data_min, max_value=data_max, key="dis_period_b_range")

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
                                render_chart_with_download(fig, key="dis_trend_benchmark_chart")

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
        st.write("Analyze relationships between confirmed disinfection parameters.")

        corr_matrix = correlation_analyzer.calculate_correlations()

        if corr_matrix is None or len(corr_matrix.columns) < 2:
            st.warning("Not enough confirmed numeric parameters for correlation analysis. Check **Confirm Data Mapping** above.")
        else:
            st.subheader("📊 Correlation Heatmap")
            fig_heatmap = correlation_analyzer.create_correlation_heatmap()
            if fig_heatmap:
                render_chart_with_download(fig_heatmap, key="dis_corr_heatmap")

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
                x_var = st.selectbox("X-axis", numeric_col_list, index=numeric_col_list.index(default_x) if default_x in numeric_col_list else 0, key="dis_scatter_x_var")
            with sc2:
                y_default_idx = numeric_col_list.index(default_y) if default_y in numeric_col_list else (1 if len(numeric_col_list) > 1 else 0)
                y_var = st.selectbox("Y-axis", numeric_col_list, index=y_default_idx, key="dis_scatter_y_var")
            if x_var == y_var:
                st.info("Pick two different parameters to see a scatter plot.")
            else:
                fig_scatter = correlation_analyzer.create_scatter_plot(x_var, y_var)
                render_chart_with_download(fig_scatter, key="dis_interactive_scatter")

    # ============================================================
    # TAB 5: DISINFECTION PERFORMANCE
    # ============================================================
    with tab5:
        st.header("🦠 Disinfection Performance")
        st.write(f"**Method:** {plant_info.get('disinfection_method', 'Not specified')}")

        if detected_params.get('chlorine_residual_precontact', {}).get('column'):
            st.subheader("Chlorine Residual (Pre-Dechlorination)")
            ccol = detected_params['chlorine_residual_precontact']['column']
            cunit = detected_params['chlorine_residual_precontact']['unit']
            st.caption(f"Column used: **{ccol}**")
            fig = chart_renderer.render_line_with_ma(ccol, cunit, "Chlorine Residual (Pre-Dechlorination)", threshold_excellent=1.0, threshold_good=0.5)
            render_chart_with_download(fig, key="dis_pre_residual_chart")
            render_footnote('chlorine_residual_precontact', ' mg/L')

        if detected_params.get('chlorine_residual_final', {}).get('column'):
            st.subheader("Chlorine Residual (Final Effluent)")
            ccol = detected_params['chlorine_residual_final']['column']
            cunit = detected_params['chlorine_residual_final']['unit']
            st.caption(f"Column used: **{ccol}**")
            fig = chart_renderer.render_line_with_ma(ccol, cunit, "Chlorine Residual (Final Effluent)", threshold_excellent=0.05, threshold_good=0.1)
            render_chart_with_download(fig, key="dis_final_residual_chart")
            render_footnote('chlorine_residual_final', ' mg/L')

        if detected_params.get('uv_dose', {}).get('column'):
            st.subheader("UV Dose")
            ucol = detected_params['uv_dose']['column']
            uunit = detected_params['uv_dose']['unit']
            st.caption(f"Column used: **{ucol}**")
            fig = chart_renderer.render_line_with_ma(ucol, uunit, "UV Dose", threshold_excellent=40, threshold_good=30)
            render_chart_with_download(fig, key="dis_uv_dose_chart")
            render_footnote('uv_dose', ' mJ/cm²')

        if detected_params.get('uv_transmittance', {}).get('column'):
            st.subheader("UV Transmittance")
            ucol = detected_params['uv_transmittance']['column']
            uunit = detected_params['uv_transmittance']['unit']
            st.caption(f"Column used: **{ucol}**")
            fig = chart_renderer.render_line_with_ma(ucol, uunit, "UV Transmittance")
            render_chart_with_download(fig, key="dis_uvt_chart")
            st.caption("ℹ️ No fixed benchmark — typical secondary effluent runs 55-75% UVT.")

        if detected_params.get('effluent_bacteria', {}).get('column'):
            st.subheader("Effluent Bacteria")
            bcol = detected_params['effluent_bacteria']['column']
            bunit = detected_params['effluent_bacteria']['unit']
            st.caption(f"Column used: **{bcol}**")
            fig = chart_renderer.render_line_with_ma(bcol, bunit, "Effluent Bacteria")
            render_chart_with_download(fig, key="dis_bacteria_chart")
            st.caption("ℹ️ No fixed benchmark — compare against your specific discharge permit limit.")

        if not any(detected_params.get(k, {}).get('column') for k in ['chlorine_residual_precontact', 'chlorine_residual_final', 'uv_dose', 'uv_transmittance', 'effluent_bacteria']):
            st.info("No disinfection indicators are confirmed yet. Check **Confirm Data Mapping** above.")

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
        st.download_button("📥 Download Parameters", data=csv, file_name="disinfection_parameters.csv", mime="text/csv")

    # ============================================================
    # TAB 8: RAW DATA
    # ============================================================
    with tab8:
        st.header("📥 Raw Data")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Data", data=csv, file_name="disinfection_data.csv", mime="text/csv")

st.success("✅ Module loaded successfully!")
