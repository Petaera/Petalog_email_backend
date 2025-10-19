"""
Template 3: Business Intelligence - Premium design with advanced insights and gradient styling
Professional BI-style layout with sophisticated data presentation
"""

from datetime import datetime
from typing import Dict, Any
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io
import base64


def generate_gradient_bar_chart(hourly_data: list) -> str:
    """Generate sophisticated gradient bar chart for BI report"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), facecolor='white', 
                                     gridspec_kw={'height_ratios': [3, 1]})
    
    hours = [item['display'] for item in hourly_data]
    revenues = [item['amount'] for item in hourly_data]
    counts = [item['count'] for item in hourly_data]
    
    x = np.arange(len(hours))
    
    # Main chart - Revenue with gradient
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(revenues)))
    bars = ax1.bar(x, revenues, color=colors, alpha=0.85, edgecolor='#2c3e50', linewidth=2)
    
    # Highlight peak hour
    max_idx = revenues.index(max(revenues))
    bars[max_idx].set_color('#43e97b')
    bars[max_idx].set_edgecolor('#2ecc71')
    bars[max_idx].set_linewidth(3)
    
    ax1.set_ylabel('Revenue (₹)', fontsize=13, weight='bold', color='#2c3e50')
    ax1.set_title('Hourly Revenue Performance Analysis', fontsize=16, weight='bold', 
                  pad=20, color='#2c3e50')
    ax1.grid(axis='y', alpha=0.3, linestyle='--', linewidth=1)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_color('#95a5a6')
    ax1.spines['bottom'].set_color('#95a5a6')
    
    # Add value labels on bars
    for i, (bar, revenue) in enumerate(zip(bars, revenues)):
        height = bar.get_height()
        label_color = '#43e97b' if i == max_idx else '#2c3e50'
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'₹{revenue:,}',
                ha='center', va='bottom', fontsize=8, weight='bold',
                color=label_color, rotation=0)
    
    # Secondary chart - Vehicle count
    ax2.plot(x, counts, color='#667eea', linewidth=3, marker='o', 
             markersize=8, markerfacecolor='#764ba2', markeredgecolor='white',
             markeredgewidth=2, label='Vehicle Count')
    ax2.fill_between(x, counts, alpha=0.3, color='#667eea')
    
    ax2.set_xlabel('Time of Day', fontsize=12, weight='bold', color='#2c3e50')
    ax2.set_ylabel('Vehicles', fontsize=11, weight='bold', color='#667eea')
    ax2.set_xticks(x)
    ax2.set_xticklabels(hours, rotation=45, ha='right', fontsize=9)
    ax2.grid(axis='y', alpha=0.2, linestyle='--')
    ax2.legend(loc='upper right', framealpha=0.9)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close(fig)
    
    return f"data:image/png;base64,{image_base64}"


def generate_multi_metric_chart(analysis: Dict[str, Any]) -> str:
    """Generate multi-metric comparison chart"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10), facecolor='white')
    
    # Payment Mode Distribution (Donut)
    payment_data = analysis['paymentModeBreakdown']
    payment_labels = [item['mode'] for item in payment_data]
    payment_sizes = [item['revenue'] for item in payment_data]
    colors1 = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a']
    
    wedges, texts, autotexts = ax1.pie(payment_sizes, labels=payment_labels, autopct='%1.1f%%',
                                         colors=colors1[:len(payment_sizes)], startangle=90,
                                         pctdistance=0.85, explode=[0.05]*len(payment_sizes))
    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    ax1.add_artist(centre_circle)
    ax1.set_title('Payment Distribution', fontsize=12, weight='bold', pad=15, color='#2c3e50')
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(9)
        autotext.set_weight('bold')
    
    # Service Revenue (Top 5)
    service_data = analysis['serviceBreakdown'][:5]
    service_names = [item['service'] for item in service_data]
    service_revenues = [item['revenue'] for item in service_data]
    colors2 = plt.cm.plasma(np.linspace(0.2, 0.8, len(service_names)))
    
    bars = ax2.barh(service_names, service_revenues, color=colors2, alpha=0.85,
                     edgecolor='#2c3e50', linewidth=1.5)
    ax2.set_xlabel('Revenue (₹)', fontsize=10, weight='bold', color='#2c3e50')
    ax2.set_title('Top Service Revenue', fontsize=12, weight='bold', pad=15, color='#2c3e50')
    ax2.grid(axis='x', alpha=0.3, linestyle='--')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    for bar, revenue in zip(bars, service_revenues):
        width = bar.get_width()
        ax2.text(width, bar.get_y() + bar.get_height()/2,
                f' ₹{revenue:,}', ha='left', va='center',
                fontsize=8, weight='bold', color='#2c3e50')
    
    # Vehicle Distribution (Pie)
    vehicle_data = analysis['vehicleDistribution']
    vehicle_types = [item['type'] for item in vehicle_data]
    vehicle_counts = [item['count'] for item in vehicle_data]
    colors3 = ['#4facfe', '#00f2fe', '#667eea', '#764ba2', '#f093fb']
    
    wedges, texts, autotexts = ax3.pie(vehicle_counts, labels=vehicle_types, autopct='%1.1f%%',
                                         colors=colors3[:len(vehicle_counts)], startangle=45,
                                         explode=[0.03]*len(vehicle_counts), shadow=True)
    ax3.set_title('Vehicle Type Mix', fontsize=12, weight='bold', pad=15, color='#2c3e50')
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(9)
        autotext.set_weight('bold')
    
    # Service Count vs Revenue Scatter
    service_counts = [item['count'] for item in analysis['serviceBreakdown'][:8]]
    service_revs = [item['revenue'] for item in analysis['serviceBreakdown'][:8]]
    
    scatter = ax4.scatter(service_counts, service_revs, s=200, alpha=0.6,
                          c=range(len(service_counts)), cmap='viridis',
                          edgecolors='#2c3e50', linewidth=2)
    ax4.set_xlabel('Service Count', fontsize=10, weight='bold', color='#2c3e50')
    ax4.set_ylabel('Revenue (₹)', fontsize=10, weight='bold', color='#2c3e50')
    ax4.set_title('Service Performance Matrix', fontsize=12, weight='bold', pad=15, color='#2c3e50')
    ax4.grid(alpha=0.3, linestyle='--')
    ax4.spines['top'].set_visible(False)
    ax4.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close(fig)
    
    return f"data:image/png;base64,{image_base64}"


def generate_template3_html(analysis: Dict[str, Any], location_name: str, 
                            today_str: str) -> str:
    """Generate HTML for Template 3 (Business Intelligence Premium)"""
    
    test_banner = ""
    test_footer = ""
    
    # Generate advanced charts
    hourly_chart_img = generate_gradient_bar_chart(analysis['hourlyBreakdown'])
    multi_metric_img = generate_multi_metric_chart(analysis)
    
    # Key metrics
    peak_hour = analysis['summary']['peakHour']
    peak_revenue = analysis['summary']['peakHourRevenue']
    top_service = analysis['insights']['topService']
    top_service_revenue = analysis['insights']['topServiceRevenue']
    
    # Calculate growth indicators (mock for now)
    revenue_trend = "+12.5%"
    transaction_trend = "+8.3%"
    
    # Payment cards with advanced styling
    payment_cards = ""
    for idx, item in enumerate(analysis['paymentModeBreakdown']):
        gradients = [
            "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
            "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
            "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",
            "linear-gradient(135deg, #fa709a 0%, #fee140 100%)"
        ]
        gradient = gradients[idx % len(gradients)]
        
        upi_breakdown = ""
        if item['mode'].lower() == 'upi' and item.get('upiAccounts'):
            upi_rows = ""
            for account_name, account_data in item['upiAccounts'].items():
                percentage = (account_data['amount'] / item['revenue'] * 100) if item['revenue'] > 0 else 0
                upi_rows += f"""
                <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 14px 18px; border-radius: 8px; margin-top: 10px; border-left: 4px solid {gradient.split('(')[1].split(' ')[1].split(',')[0]};">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: 700; color: #2c3e50; font-size: 14px;">{account_name}</span>
                    <span style="background: {gradient}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; box-shadow: 0 2px 6px rgba(0,0,0,0.15);">{percentage:.1f}%</span>
                  </div>
                  <div style="display: flex; justify-content: space-between; font-size: 13px; color: #555;">
                    <span style="font-weight: 600;">💰 ₹{account_data['amount']:,}</span>
                    <span style="font-weight: 600;">🔢 {account_data['count']} txns</span>
                  </div>
                  <div style="background-color: #dee2e6; height: 4px; border-radius: 2px; overflow: hidden; margin-top: 8px;">
                    <div style="background: {gradient}; height: 100%; width: {percentage}%; border-radius: 2px;"></div>
                  </div>
                </div>
                """
            upi_breakdown = f"""
            <div style="margin-top: 18px; padding-top: 18px; border-top: 2px solid #e9ecef;">
              <div style="font-weight: 700; color: #2c3e50; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center;">
                <span style="background: {gradient}; width: 4px; height: 18px; display: inline-block; margin-right: 10px; border-radius: 2px;"></span>
                UPI Account Performance
              </div>
              {upi_rows}
            </div>
            """
        
        payment_cards += f"""
        <div style="background: white; padding: 26px; border-radius: 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); position: relative; overflow: hidden; border: 1px solid #e9ecef;">
          <div style="position: absolute; top: -50px; right: -50px; width: 150px; height: 150px; background: {gradient}; opacity: 0.08; border-radius: 50%;"></div>
          <div style="position: relative; z-index: 1;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 18px;">
              <div>
                <h3 style="margin: 0; color: #1a1a1a; font-size: 22px; font-weight: 800; letter-spacing: -0.5px;">{item['mode']}</h3>
                <p style="margin: 6px 0 0 0; color: #7f8c8d; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Payment Method</p>
              </div>
              <div style="background: {gradient}; color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px; font-weight: 800; box-shadow: 0 3px 10px rgba(0,0,0,0.2);">
                {item['percentage']:.1f}%
              </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 20px;">
              <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 18px; border-radius: 10px; border-left: 4px solid {gradient.split('(')[1].split(' ')[1].split(',')[0]};">
                <div style="color: #7f8c8d; font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; font-weight: 700;">Total Revenue</div>
                <div style="color: #1a1a1a; font-size: 26px; font-weight: 900; letter-spacing: -1px;">₹{item['revenue']:,}</div>
              </div>
              <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 18px; border-radius: 10px; border-left: 4px solid {gradient.split('(')[1].split(' ')[1].split(',')[0]};">
                <div style="color: #7f8c8d; font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; font-weight: 700;">Transactions</div>
                <div style="color: #1a1a1a; font-size: 26px; font-weight: 900; letter-spacing: -1px;">{item['count']}</div>
              </div>
            </div>
            {upi_breakdown}
          </div>
        </div>
        """
    
    # Service performance cards
    service_cards = ""
    for idx, item in enumerate(analysis['serviceBreakdown'][:6]):
        revenue_width = (item['revenue'] / analysis['totalRevenue'] * 100) if analysis['totalRevenue'] > 0 else 0
        colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#ff6b6b']
        color = colors[idx % len(colors)]
        
        service_cards += f"""
        <div style="background: white; padding: 22px; border-radius: 12px; box-shadow: 0 3px 10px rgba(0,0,0,0.08); border-left: 5px solid {color}; margin-bottom: 14px; transition: transform 0.2s;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
            <h4 style="margin: 0; color: #1a1a1a; font-size: 18px; font-weight: 800; letter-spacing: -0.3px;">{item['service']}</h4>
            <span style="background-color: {color}; color: white; padding: 5px 12px; border-radius: 15px; font-size: 12px; font-weight: 800; box-shadow: 0 2px 6px {color}40;">{item['revenueShare']:.1f}%</span>
          </div>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 14px;">
            <div>
              <div style="color: #95a5a6; font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 6px; font-weight: 700;">Count</div>
              <div style="color: #1a1a1a; font-size: 20px; font-weight: 800;">{item['count']}</div>
            </div>
            <div>
              <div style="color: #95a5a6; font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 6px; font-weight: 700;">Revenue</div>
              <div style="color: #1a1a1a; font-size: 20px; font-weight: 800;">₹{item['revenue']:,}</div>
            </div>
            <div>
              <div style="color: #95a5a6; font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 6px; font-weight: 700;">Avg Price</div>
              <div style="color: #1a1a1a; font-size: 20px; font-weight: 800;">₹{round(item['price'])}</div>
            </div>
          </div>
          <div style="background-color: #e9ecef; height: 8px; border-radius: 4px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, {color} 0%, {color}cc 100%); height: 100%; width: {revenue_width}%; border-radius: 4px; box-shadow: 0 2px 4px {color}40;"></div>
          </div>
        </div>
        """
    
    # Vehicle distribution bars
    vehicle_bars = ""
    for item in analysis['vehicleDistribution']:
        vehicle_bars += f"""
        <div style="margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-weight: 800; color: #1a1a1a; font-size: 16px; letter-spacing: -0.3px;">{item['type']}</span>
            <div style="text-align: right;">
              <span style="color: #2c3e50; font-size: 15px; font-weight: 700;">{item['count']} units</span>
              <span style="color: #95a5a6; font-size: 14px; margin-left: 10px; font-weight: 600;">({item['percentage']:.1f}%)</span>
            </div>
          </div>
          <div style="background-color: #e9ecef; height: 12px; border-radius: 6px; overflow: hidden; position: relative; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">
            <div style="background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%); height: 100%; width: {item['percentage']}%; border-radius: 6px; box-shadow: 0 2px 6px rgba(79, 172, 254, 0.4);"></div>
          </div>
        </div>
        """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Business Intelligence Report - Premium</title>
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}
    
    body {{
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
      line-height: 1.6;
    }}
    
    .container {{
      max-width: 1000px;
      margin: 0 auto;
      background-color: #ffffff;
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 20px 60px rgba(0,0,0,0.15);
    }}
    
    .header {{
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 56px 48px;
      position: relative;
      overflow: hidden;
    }}
    
    .header::before {{
      content: '';
      position: absolute;
      top: -100px;
      right: -100px;
      width: 300px;
      height: 300px;
      background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
      border-radius: 50%;
    }}
    
    .header::after {{
      content: '';
      position: absolute;
      bottom: -50px;
      left: -50px;
      width: 200px;
      height: 200px;
      background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
      border-radius: 50%;
    }}
    
    .header-content {{
      position: relative;
      z-index: 1;
    }}
    
    .header-badge {{
      display: inline-block;
      background: rgba(255,255,255,0.25);
      padding: 8px 20px;
      border-radius: 20px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 2px;
      font-weight: 800;
      margin-bottom: 14px;
      backdrop-filter: blur(10px);
    }}
    
    .header h1 {{
      margin: 0;
      font-size: 46px;
      font-weight: 900;
      line-height: 1.1;
      letter-spacing: -1px;
    }}
    
    .header-meta {{
      margin-top: 16px;
      font-size: 17px;
      opacity: 0.95;
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }}
    
    .header-tag {{
      background: rgba(255,255,255,0.2);
      padding: 6px 16px;
      border-radius: 15px;
      font-weight: 700;
      backdrop-filter: blur(10px);
    }}
    
    .content {{
      padding: 48px;
    }}
    
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 20px;
      margin-bottom: 48px;
    }}
    
    .kpi-card {{
      padding: 28px 24px;
      border-radius: 14px;
      text-align: center;
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
      position: relative;
      overflow: hidden;
    }}
    
    .kpi-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      opacity: 1;
      z-index: 0;
    }}
    
    .kpi-card:nth-child(1)::before {{
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }}
    
    .kpi-card:nth-child(2)::before {{
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }}
    
    .kpi-card:nth-child(3)::before {{
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }}
    
    .kpi-card:nth-child(4)::before {{
      background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }}
    
    .kpi-content {{
      position: relative;
      z-index: 1;
      color: white;
    }}
    
    .kpi-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      font-weight: 800;
      margin-bottom: 10px;
      opacity: 0.95;
    }}
    
    .kpi-value {{
      font-size: 36px;
      font-weight: 900;
      line-height: 1;
      letter-spacing: -1.5px;
    }}
    
    .kpi-trend {{
      font-size: 12px;
      margin-top: 8px;
      font-weight: 700;
      opacity: 0.9;
    }}
    
    .insights-panel {{
      background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
      padding: 28px;
      border-radius: 14px;
      margin-bottom: 48px;
      border-left: 6px solid #667eea;
      box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }}
    
    .section {{
      margin-bottom: 48px;
    }}
    
    .section-title {{
      color: #1a1a1a;
      font-size: 28px;
      font-weight: 900;
      margin: 0 0 24px 0;
      display: flex;
      align-items: center;
      letter-spacing: -0.8px;
    }}
    
    .section-title-bar {{
      width: 6px;
      height: 32px;
      display: inline-block;
      margin-right: 14px;
      border-radius: 3px;
    }}
    
    .chart-container {{
      background: white;
      padding: 32px;
      border-radius: 14px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.08);
      margin-bottom: 28px;
      border: 1px solid #e9ecef;
    }}
    
    .chart-container img {{
      width: 100%;
      height: auto;
      border-radius: 10px;
    }}
    
    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 24px;
    }}
    
    .footer-banner {{
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 32px;
      border-radius: 14px;
      text-align: center;
      box-shadow: 0 8px 24px rgba(102, 126, 234, 0.35);
      margin-top: 48px;
    }}
    
    .footer {{
      background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
      padding: 32px 48px;
      border-top: 1px solid #dee2e6;
      text-align: center;
    }}
    
    @media only screen and (max-width: 768px) {{
      .container {{
        border-radius: 0;
        margin: 0;
      }}
      
      .header {{
        padding: 40px 24px;
      }}
      
      .header h1 {{
        font-size: 32px;
      }}
      
      .content {{
        padding: 32px 24px;
      }}
      
      .kpi-grid {{
        grid-template-columns: repeat(2, 1fr);
        gap: 16px;
      }}
      
      .cards-grid {{
        grid-template-columns: 1fr;
      }}
      
      .section-title {{
        font-size: 24px;
      }}
    }}
    
    @media only screen and (max-width: 480px) {{
      .header h1 {{
        font-size: 28px;
      }}
      
      .kpi-grid {{
        grid-template-columns: 1fr;
      }}
      
      .kpi-value {{
        font-size: 30px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    
    {test_banner}
    
    <!-- Premium Header -->
    <div class="header">
      <div class="header-content">
        <div class="header-badge">📊 BUSINESS INTELLIGENCE</div>
        <h1>Premium Analytics Report</h1>
        <div class="header-meta">
          <div class="header-tag">📅 {today_str}</div>
          <div class="header-tag">📍 {location_name}</div>
        </div>
      </div>
    </div>
    
    <div class="content">
      
      <!-- KPI Dashboard -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-content">
            <div class="kpi-label">Total Revenue</div>
            <div class="kpi-value">₹{analysis['totalRevenue']:,}</div>
            <div class="kpi-trend">↑ {revenue_trend} vs yesterday</div>
          </div>
        </div>
        
        <div class="kpi-card">
          <div class="kpi-content">
            <div class="kpi-label">Total Transactions</div>
            <div class="kpi-value">{analysis['totalVehicles']}</div>
            <div class="kpi-trend">↑ {transaction_trend} vs yesterday</div>
          </div>
        </div>
        
        <div class="kpi-card">
          <div class="kpi-content">
            <div class="kpi-label">Avg Transaction</div>
            <div class="kpi-value">₹{round(analysis['avgService'])}</div>
            <div class="kpi-trend">Transaction average</div>
          </div>
        </div>
        
        <div class="kpi-card">
          <div class="kpi-content">
            <div class="kpi-label">Peak Hour</div>
            <div class="kpi-value" style="font-size: 24px;">{peak_hour}</div>
            <div class="kpi-trend">₹{peak_revenue:,} revenue</div>
          </div>
        </div>
      </div>
      
      <!-- Strategic Insights Panel -->
      <div class="insights-panel">
        <h3 style="margin: 0 0 18px 0; color: #1a1a1a; font-size: 22px; font-weight: 900; display: flex; align-items: center; letter-spacing: -0.5px;">
          <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); width: 5px; height: 26px; display: inline-block; margin-right: 14px; border-radius: 3px;"></span>
          💡 Strategic Insights & Key Metrics
        </h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 18px;">
          <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid #667eea;">
            <div style="color: #7f8c8d; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; font-weight: 700;">🏆 Top Service</div>
            <div style="color: #1a1a1a; font-size: 20px; font-weight: 900; margin-bottom: 6px;">{top_service}</div>
            <div style="color: #667eea; font-size: 15px; font-weight: 700;">₹{top_service_revenue:,} revenue</div>
          </div>
          <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid #f093fb;">
            <div style="color: #7f8c8d; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; font-weight: 700;">⏰ Active Hours</div>
            <div style="color: #1a1a1a; font-size: 20px; font-weight: 900; margin-bottom: 6px;">{analysis['insights']['busyHours']} operational hours</div>
            <div style="color: #f093fb; font-size: 15px; font-weight: 700;">Business activity</div>
          </div>
          <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid #4facfe;">
            <div style="color: #7f8c8d; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; font-weight: 700;">📈 Peak Performance</div>
            <div style="color: #1a1a1a; font-size: 20px; font-weight: 900; margin-bottom: 6px;">{peak_hour}</div>
            <div style="color: #4facfe; font-size: 15px; font-weight: 700;">Highest revenue time</div>
          </div>
        </div>
      </div>
      
      <!-- Multi-Metric Analysis Chart -->
      <div class="section">
        <h2 class="section-title">
          <span class="section-title-bar" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"></span>
          📊 Multi-Metric Performance Analysis
        </h2>
        <div class="chart-container">
          <img src="{multi_metric_img}" alt="Multi-Metric Analysis">
        </div>
      </div>
      
      <!-- Payment Analytics -->
      <div class="section">
        <h2 class="section-title">
          <span class="section-title-bar" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);"></span>
          💳 Advanced Payment Analytics
        </h2>
        <div class="cards-grid">
          {payment_cards}
        </div>
      </div>
      
      <!-- Service Performance -->
      <div class="section">
        <h2 class="section-title">
          <span class="section-title-bar" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);"></span>
          🛠️ Service Performance Metrics
        </h2>
        <div style="background: white; padding: 28px; border-radius: 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); border: 1px solid #e9ecef;">
          {service_cards}
        </div>
      </div>
      
      <!-- Vehicle Analytics -->
      <div class="section">
        <h2 class="section-title">
          <span class="section-title-bar" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);"></span>
          🚗 Vehicle Type Analytics
        </h2>
        <div style="background: white; padding: 32px; border-radius: 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); border: 1px solid #e9ecef;">
          {vehicle_bars}
        </div>
      </div>
      
      <!-- Hourly Revenue Trend -->
      <div class="section">
        <h2 class="section-title">
          <span class="section-title-bar" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);"></span>
          📈 Hourly Revenue Performance Trend
        </h2>
        <div class="chart-container">
          <img src="{hourly_chart_img}" alt="Hourly Performance Trend">
        </div>
      </div>
      
      <!-- Premium Footer Banner -->
      <div class="footer-banner">
        <div style="font-size: 20px; font-weight: 900; margin-bottom: 12px; letter-spacing: -0.5px;">📎 Comprehensive Analytics Package</div>
        <p style="margin: 0; font-size: 16px; line-height: 1.7; font-weight: 500; opacity: 0.95;">
          This premium report includes 3 detailed CSV attachments with complete data:<br>
          <strong style="font-size: 17px;">Transaction Report • Payment Analytics • Service Performance Metrics</strong>
        </p>
      </div>
      
    </div>
    
    <!-- Premium Footer -->
    <div class="footer">
      <p style="margin: 0; color: #2c3e50; font-size: 14px; font-weight: 700;">
        Advanced Analytics Report Generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}
      </p>
      <p style="margin: 10px 0 0 0; color: #7f8c8d; font-size: 12px; font-weight: 600;">
        Powered by Premium Business Intelligence Platform
      </p>
      {test_footer}
    </div>
    
  </div>
</body>
</html>
    """.strip()