"""
Template 2: Modern Analytics - Chart-focused design with interactive visual elements
Uses matplotlib to generate actual pie charts and bar graphs
"""

from datetime import datetime
from typing import Dict, Any
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import io
import base64


def generate_pie_chart(data: list, title: str) -> str:
    """Generate a pie chart and return as base64 string"""
    fig, ax = plt.subplots(figsize=(6, 6), facecolor='white')
    
    labels = [item['mode'] if 'mode' in item else item.get('service', item.get('type', '')) for item in data]
    sizes = [item.get('revenue', item.get('count', 0)) for item in data]
    
    colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140', '#30cfd0']
    explode = tuple([0.05 if i == 0 else 0 for i in range(len(sizes))])
    
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                        startangle=90, colors=colors[:len(sizes)],
                                        explode=explode, shadow=True,
                                        textprops={'fontsize': 11, 'weight': 'bold'})
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)
        autotext.set_weight('bold')
    
    ax.set_title(title, fontsize=14, weight='bold', pad=20, color='#2c3e50')
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close(fig)
    
    return f"data:image/png;base64,{image_base64}"


def generate_bar_chart(hourly_data: list) -> str:
    """Generate a bar chart for hourly performance"""
    fig, ax = plt.subplots(figsize=(12, 5), facecolor='white')
    
    hours = [item['display'] for item in hourly_data]
    revenues = [item['amount'] for item in hourly_data]
    counts = [item['count'] for item in hourly_data]
    
    x = range(len(hours))
    width = 0.35
    
    bars1 = ax.bar([i - width/2 for i in x], revenues, width, label='Revenue (₹)', 
                    color='#667eea', alpha=0.8, edgecolor='#4a5568', linewidth=1.5)
    
    ax2 = ax.twinx()
    bars2 = ax2.bar([i + width/2 for i in x], counts, width, label='Vehicle Count',
                     color='#f093fb', alpha=0.8, edgecolor='#c2185b', linewidth=1.5)
    
    ax.set_xlabel('Time of Day', fontsize=12, weight='bold', color='#2c3e50')
    ax.set_ylabel('Revenue (₹)', fontsize=12, weight='bold', color='#667eea')
    ax2.set_ylabel('Vehicle Count', fontsize=12, weight='bold', color='#f093fb')
    
    ax.set_title('Hourly Performance Analysis', fontsize=14, weight='bold', pad=20, color='#2c3e50')
    ax.set_xticks(x)
    ax.set_xticklabels(hours, rotation=45, ha='right', fontsize=9)
    
    ax.legend(loc='upper left', framealpha=0.9)
    ax2.legend(loc='upper right', framealpha=0.9)
    
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close(fig)
    
    return f"data:image/png;base64,{image_base64}"


def generate_horizontal_bar_chart(service_data: list) -> str:
    """Generate horizontal bar chart for service breakdown"""
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
    
    services = [item['service'] for item in service_data[:8]]  # Top 8
    revenues = [item['revenue'] for item in service_data[:8]]
    
    colors_gradient = plt.cm.viridis(range(0, 256, 256 // len(services)))
    
    bars = ax.barh(services, revenues, color=colors_gradient, alpha=0.85, 
                   edgecolor='#2c3e50', linewidth=1.5)
    
    ax.set_xlabel('Revenue (₹)', fontsize=12, weight='bold', color='#2c3e50')
    ax.set_title('Service Revenue Analysis', fontsize=14, weight='bold', pad=20, color='#2c3e50')
    
    # Add value labels
    for i, (bar, revenue) in enumerate(zip(bars, revenues)):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2, 
                f' ₹{revenue:,}', ha='left', va='center', 
                fontsize=10, weight='bold', color='#2c3e50')
    
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close(fig)
    
    return f"data:image/png;base64,{image_base64}"


def generate_template2_html(analysis: Dict[str, Any], location_name: str, 
                            today_str: str) -> str:
    """Generate HTML for Template 2 (Modern Analytics) with actual charts"""
    
    test_banner = ""
    test_footer = ""
    
    # Generate charts
    payment_pie = generate_pie_chart(analysis['paymentModeBreakdown'], 'Payment Mode Distribution')
    vehicle_pie = generate_pie_chart(analysis['vehicleDistribution'], 'Vehicle Type Distribution')
    hourly_bar = generate_bar_chart(analysis['hourlyBreakdown'])
    service_bar = generate_horizontal_bar_chart(analysis['serviceBreakdown'])
    
    # Payment breakdown cards with enhanced stats
    payment_cards = ""
    for item in analysis['paymentModeBreakdown']:
        upi_details = ""
        if item['mode'].lower() == 'upi' and item.get('upiAccounts'):
            upi_items = ""
            for account_name, account_data in item['upiAccounts'].items():
                upi_items += f'''
                <div style="padding: 10px 14px; background-color: #e3f2fd; border-radius: 6px; margin-top: 8px; border-left: 3px solid #1976d2;">
                    <span style="font-weight: 600; color: #1976d2; font-size: 13px;">{account_name}</span><br>
                    <span style="font-size: 12px; color: #555;">₹{account_data["amount"]:,} • {account_data["count"]} transactions</span>
                </div>
                '''
            upi_details = f'<div style="margin-top: 14px; padding-top: 14px; border-top: 1px solid #e0e0e0;"><strong style="color: #555; font-size: 13px;">UPI Account Details:</strong>{upi_items}</div>'
        
        payment_cards += f"""
        <div style="background: white; padding: 22px; border-radius: 10px; box-shadow: 0 3px 10px rgba(0,0,0,0.08); border-left: 5px solid #667eea; transition: transform 0.2s;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
            <h3 style="margin: 0; color: #2c3e50; font-size: 17px; font-weight: 700;">{item['mode']}</h3>
            <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 5px 14px; border-radius: 15px; font-size: 12px; font-weight: 700; box-shadow: 0 2px 6px rgba(102, 126, 234, 0.3);">{item['percentage']:.1f}%</span>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <div>
              <span style="color: #95a5a6; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Revenue</span><br>
              <strong style="color: #2c3e50; font-size: 22px; font-weight: 700;">₹{item['revenue']:,}</strong>
            </div>
            <div style="text-align: right;">
              <span style="color: #95a5a6; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Count</span><br>
              <strong style="color: #2c3e50; font-size: 22px; font-weight: 700;">{item['count']}</strong>
            </div>
          </div>
          {upi_details}
        </div>
        """
    
    # Service statistics cards
    service_cards = ""
    for i, item in enumerate(analysis['serviceBreakdown'][:6]):  # Top 6 services
        gradient_colors = [
            'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
            'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
            'linear-gradient(135deg, #30cfd0 0%, #330867 100%)'
        ]
        
        service_cards += f"""
        <div style="background: white; padding: 22px; border-radius: 10px; box-shadow: 0 3px 10px rgba(0,0,0,0.08); border-top: 4px solid; border-image: {gradient_colors[i % 6]} 1;">
          <h3 style="margin: 0 0 14px 0; color: #2c3e50; font-size: 16px; font-weight: 700;">{item['service']}</h3>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;">
            <div>
              <span style="color: #95a5a6; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Count</span><br>
              <strong style="color: #2c3e50; font-size: 20px; font-weight: 700;">{item['count']}</strong>
            </div>
            <div>
              <span style="color: #95a5a6; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Revenue</span><br>
              <strong style="color: #2c3e50; font-size: 20px; font-weight: 700;">₹{item['revenue']:,}</strong>
            </div>
            <div>
              <span style="color: #95a5a6; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Avg</span><br>
              <strong style="color: #2c3e50; font-size: 20px; font-weight: 700;">₹{round(item['price'])}</strong>
            </div>
          </div>
        </div>
        """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Modern Analytics Report</title>
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
      background-color: #f0f4f8;
      line-height: 1.6;
    }}
    
    .container {{
      max-width: 900px;
      margin: 0 auto;
      background-color: #ffffff;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 10px 40px rgba(0,0,0,0.12);
    }}
    
    .header {{
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 48px 32px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }}
    
    .header::before {{
      content: '';
      position: absolute;
      top: -50%;
      left: -50%;
      width: 200%;
      height: 200%;
      background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
    }}
    
    .header h1 {{
      margin: 0;
      font-size: 38px;
      font-weight: 800;
      letter-spacing: -0.5px;
      position: relative;
      z-index: 1;
    }}
    
    .header .date {{
      margin: 14px 0 0 0;
      font-size: 18px;
      opacity: 0.95;
      font-weight: 600;
      position: relative;
      z-index: 1;
    }}
    
    .header .location {{
      margin: 6px 0 0 0;
      font-size: 15px;
      opacity: 0.85;
      position: relative;
      z-index: 1;
    }}
    
    .content {{
      padding: 40px 32px;
    }}
    
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
      margin-bottom: 48px;
    }}
    
    .stat-card {{
      padding: 28px 24px;
      border-radius: 14px;
      text-align: center;
      box-shadow: 0 6px 20px rgba(0,0,0,0.12);
      position: relative;
      overflow: hidden;
    }}
    
    .stat-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      opacity: 0.95;
    }}
    
    .stat-card:nth-child(1)::before {{
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }}
    
    .stat-card:nth-child(2)::before {{
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }}
    
    .stat-card:nth-child(3)::before {{
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }}
    
    .stat-card .label {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      font-weight: 700;
      margin-bottom: 10px;
      opacity: 0.9;
      position: relative;
      color: white;
    }}
    
    .stat-card .value {{
      font-size: 34px;
      font-weight: 800;
      letter-spacing: -1px;
      position: relative;
      color: white;
    }}
    
    .section {{
      margin-bottom: 48px;
    }}
    
    .section-title {{
      color: #2c3e50;
      font-size: 26px;
      font-weight: 800;
      margin: 0 0 24px 0;
      display: flex;
      align-items: center;
      gap: 12px;
      letter-spacing: -0.5px;
    }}
    
    .chart-container {{
      background: white;
      padding: 32px;
      border-radius: 14px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.08);
      margin-bottom: 28px;
      border: 1px solid #e8edf2;
    }}
    
    .chart-container img {{
      width: 100%;
      height: auto;
      border-radius: 8px;
    }}
    
    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;
    }}
    
    .footer-banner {{
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 28px;
      border-radius: 14px;
      text-align: center;
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
      margin-top: 48px;
    }}
    
    .footer-banner p {{
      margin: 0;
      font-size: 15px;
      line-height: 1.7;
      font-weight: 500;
    }}
    
    .footer {{
      background-color: #f8f9fa;
      padding: 28px 32px;
      border-top: 1px solid #e8edf2;
      text-align: center;
    }}
    
    .footer p {{
      margin: 0;
      color: #6c757d;
      font-size: 13px;
      font-weight: 500;
    }}
    
    @media only screen and (max-width: 768px) {{
      .container {{
        border-radius: 0;
        margin: 0;
      }}
      
      .header {{
        padding: 36px 20px;
      }}
      
      .header h1 {{
        font-size: 28px;
      }}
      
      .content {{
        padding: 28px 20px;
      }}
      
      .stats-grid {{
        grid-template-columns: 1fr;
        gap: 16px;
      }}
      
      .cards-grid {{
        grid-template-columns: 1fr;
      }}
      
      .section-title {{
        font-size: 22px;
      }}
      
      .chart-container {{
        padding: 20px;
      }}
    }}
    
    @media only screen and (max-width: 480px) {{
      .header h1 {{
        font-size: 24px;
      }}
      
      .stat-card .value {{
        font-size: 28px;
      }}
      
      .section-title {{
        font-size: 20px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    
    {test_banner}
    
    <div class="header">
      <h1>📊 Business Analytics Report</h1>
      <p class="date">{today_str}</p>
      <p class="location">📍 {location_name}</p>
    </div>
    
    <div class="content">
      
      <!-- Key Metrics -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="label">Total Revenue</div>
          <div class="value">₹{analysis['totalRevenue']:,}</div>
        </div>
        
        <div class="stat-card">
          <div class="label">Vehicles Served</div>
          <div class="value">{analysis['totalVehicles']}</div>
        </div>
        
        <div class="stat-card">
          <div class="label">Average Service</div>
          <div class="value">₹{round(analysis['avgService'])}</div>
        </div>
      </div>
      
      <!-- Payment Distribution Chart -->
      <div class="section">
        <h2 class="section-title">💳 Payment Distribution Analysis</h2>
        <div class="chart-container">
          <img src="{payment_pie}" alt="Payment Mode Distribution">
        </div>
        <div class="cards-grid">
          {payment_cards}
        </div>
      </div>
      
      <!-- Service Performance Chart -->
      <div class="section">
        <h2 class="section-title">🛠️ Service Performance Metrics</h2>
        <div class="chart-container">
          <img src="{service_bar}" alt="Service Revenue Analysis">
        </div>
        <div class="cards-grid">
          {service_cards}
        </div>
      </div>
      
      <!-- Vehicle Distribution Chart -->
      <div class="section">
        <h2 class="section-title">🚗 Vehicle Type Distribution</h2>
        <div class="chart-container">
          <img src="{vehicle_pie}" alt="Vehicle Type Distribution">
        </div>
      </div>
      
      <!-- Hourly Performance Chart -->
      <div class="section">
        <h2 class="section-title">⏰ Hourly Performance Trends</h2>
        <div class="chart-container">
          <img src="{hourly_bar}" alt="Hourly Performance Analysis">
        </div>
      </div>
      
      <!-- Footer Banner -->
      <div class="footer-banner">
        <p>
          📎 <strong>Comprehensive Data Package:</strong> This report includes 3 detailed CSV attachments with complete transaction data, advanced payment analytics, and in-depth service performance metrics for further analysis.
        </p>
      </div>
      
    </div>
    
    <div class="footer">
      <p>Advanced Analytics Report Generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}</p>
      {test_footer}
    </div>
    
  </div>
</body>
</html>
    """.strip()