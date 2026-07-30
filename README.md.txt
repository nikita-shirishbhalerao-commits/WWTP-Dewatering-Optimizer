# 🌊 WWTP Dewatering Optimizer

AI-powered analysis of wastewater treatment plant dewatering performance using fuzzy logic.

## ✨ Features

- **🔍 Automatic Column Detection** - AI identifies your data columns automatically, even with different names
- **📊 Real-Time Dashboard** - Interactive visualizations of key metrics
- **💡 AI Recommendations** - Get actionable optimization suggestions
- **💰 Cost Analysis** - Calculate potential savings
- **📈 Trend Analysis** - Track performance over time
- **📥 Data Export** - Download analysis results

## 🎯 What It Analyzes

### Key Metrics:
- **Polymer Efficiency** (lbs/ton) - Lower is better
- **Cake Quality** (%) - Higher is better
- **Equipment Utilization** (%) - 40-70% is optimal
- **Dewatering Efficiency** (Dry/Wet Ratio) - Higher is better
- **Sludge Truck Costs** - Minimize hauling
- **Flow Balance** - Influent vs Effluent

## 📋 Data Format

Your CSV should contain columns like:
- **Date** - Any date format
- **Influent Flow** (MGD)
- **Effluent Flow** (MGD)
- **Active Poly** (lbs/ton)
- **Cake Quality** (%)
- **Centrifuge Run Hours**
- **Dry/Wet Tons**
- **Daily Trucks**

The AI will automatically match your column names!

## 🚀 How to Use

### Online (No Installation)
1. Go to: [WWTP Optimizer Web App](https://wwtp-optimizer.streamlit.app)
2. Upload your CSV file
3. View instant analysis
4. Get recommendations

### Local Installation
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/wwtp-optimizer.git
cd wwtp-optimizer

# Install dependencies
pip install -r requirements.txt

# Run app
streamlit run app.py
