"""
Template 3: Modern Business Intelligence Report Email Template
Professional, data-driven design with advanced analytics presentation
"""

from datetime import datetime
from typing import Dict, Any, Optional


def generate_template3_html(analysis: Dict[str, Any], location_name: str, 
                            today_str: str, test_email: Optional[str]) -> str:
    """Generate HTML for Template 3 (Modern Business Intelligence)"""
    
    test_banner = """
    <div style="background-color: #ff9800; color: white; padding: 14px 32px; text-align: center; font-weight: 600; font-size: 14px;">
      🧪 TEST MODE ACTIVE - This is a test email for validation purposes
    </div>
    """ if test_email else ""
    
    test_footer = f'<p style="margin: 10px 0 0 0; color: #ff9800; font-size: 13px; font-weight: 600;">🧪 Test Mode: Email delivered to {test_email}</p>' if test_email else ""
    
    # Key metrics with trend indicators
    peak_hour = analysis['summary']['peakHour']
    peak_revenue = analysis['summary']['peakHourRevenue']
    top_service = analysis['insights']['topService']
    top_service_revenue = analysis['insights']['topServiceRevenue']
    
    # Payment analytics cards with enhanced styling
    payment_cards = ""
    for idx, item in enumerate(analysis['paymentModeBreakdown']):
        gradient_colors = [
            "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
            "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
            "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",
            "linear-gradient(135deg, #fa709a 0%, #fee140 100%)"
        ]
        gradient = gradient_colors[idx % len(gradient_colors)]
        
        upi_breakdown = ""
        if item['mode'].lower() == 'upi' and item.get('upiAccounts'):
            upi_rows = ""
            for account_name, account_data in item['upiAccounts'].items():
                percentage = (account_data['amount'] / item['revenue'] * 100) if item['revenue'] > 0 else 0
                upi_rows += f"""
                <div style="background-color: #f8f9fa; padding: 12px 16px; border-radius: 6px; margin-top: 8px; border-left: 3px solid #667eea;">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-weight: 600; color: #333; font-size: 14px;">{account_name}</span>
                    <span style="background-color: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600;">{percentage:.1f}%</span>
                  </div>
                  <div style="display: flex; justify-content: space-between; font-size: 13px; color: #666;">
                    <span>💰 ₹{account_data['amount']:,}</span>
                    <span>🚗 {account_data['count']} transactions</span>
                  </div>
                </div>
                """
            upi_breakdown = f"""
            <div style="margin-top: 16px; padding-top: 16px; border-top: 2px solid #f0f0f0;">
              <div style="font-weight: 600; color: #555; font-size: 14px; margin-bottom: 8px; display: flex; align-items: center;">
                <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); width: 4px; height: 16px; display: inline-block; margin-right: 8px; border-radius: 2px;"></span>
                UPI Account Distribution
              </div>
              {upi_rows}
            </div>
            """
        
        payment_cards += f"""
        <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 3px 10px rgba(0,0,0,0.08); border-top: 4px solid transparent; border-image: {gradient}; border-image-slice: 1; position: relative; overflow: hidden;">
          <div style="position: absolute; top: 0; right: 0; width: 100px; height: 100px; background: {gradient}; opacity: 0.05; border-radius: 0 0 0 100%;"></div>
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px; position: relative; z-index: 1;">
            <div>
              <h3 style="margin: 0; color: #1a1a1a; font-size: 20px; font-weight: 700;">{item['mode']}</h3>
              <p style="margin: 4px 0 0 0; color: #666; font-size: 13px;">Payment Method</p>
            </div>
            <div style="background: {gradient}; color: white; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; box-shadow: 0 2px 6px rgba(0,0,0,0.15);">
              {item['percentage']:.1f}%
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 20px; position: relative; z-index: 1;">
            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px;">
              <div style="color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; font-weight: 600;">Total Revenue</div>
              <div style="color: #1a1a1a; font-size: 24px; font-weight: 800;">₹{item['revenue']:,}</div>
            </div>
            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px; border-radius: 8px;">
              <div style="color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; font-weight: 600;">Transactions</div>
              <div style="color: #1a1a1a; font-size: 24px; font-weight: 800;">{item['count']}</div>
            </div>
          </div>
          {upi_breakdown}
        </div>
        """
    
    # Service performance cards with revenue share visualization
    service_cards = ""
    for idx, item in enumerate(analysis['serviceBreakdown'][:6]):  # Top 6 services
        revenue_width = (item['revenue'] / analysis['totalRevenue'] * 100) if analysis['totalRevenue'] > 0 else 0
        color_options = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#ff6b6b']
        color = color_options[idx % len(color_options)]
        
        service_cards += f"""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid {color}; margin-bottom: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h4 style="margin: 0; color: #1a1a1a; font-size: 17px; font-weight: 700;">{item['service']}</h4>
            <span style="background-color: {color}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700;">{item['revenueShare']:.1f}%</span>
          </div>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px;">
            <div>
              <div style="color: #666; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Count</div>
              <div style="color: #1a1a1a; font-size: 18px; font-weight: 700;">{item['count']}</div>
            </div>
            <div>
              <div style="color: #666; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Revenue</div>
              <div style="color: #1a1a1a; font-size: 18px; font-weight: 700;">₹{item['revenue']:,}</div>
            </div>
            <div>
              <div style="color: #666; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Avg Price</div>
              <div style="color: #1a1a1a; font-size: 18px; font-weight: 700;">₹{round(item['price'])}</div>
            </div>
          </div>
          <div style="background-color: #f0f0f0; height: 6px; border-radius: 3px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, {color} 0%, {color}cc 100%); height: 100%; width: {revenue_width}%; border-radius: 3px; transition: width 0.3s ease;"></div>
          </div>
        </div>
        """
    
    # Vehicle distribution with percentage bars
    vehicle_bars = ""
    for item in analysis['vehicleDistribution']:
        vehicle_bars += f"""
        <div style="margin-bottom: 18px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-weight: 700; color: #1a1a1a; font-size: 15px;">{item['type']}</span>
            <div style="text-align: right;">
              <span style="color: #666; font-size: 14px; font-weight: 600;">{item['count']} units</span>
              <span style="color: #999; font-size: 13px; margin-left: 8px;">({item['percentage']:.1f}%)</span>
            </div>
          </div>
          <div style="background-color: #e9ecef; height: 10px; border-radius: 5px; overflow: hidden; position: relative;">
            <div style="background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%); height: 100%; width: {item['percentage']}%; border-radius: 5px; box-shadow: 0 2px 4px rgba(79, 172, 254, 0.3);"></div>
          </div>
        </div>
        """
    
    # Hourly revenue chart with enhanced visualization
    hourly_chart = ""
    max_revenue = max((item['revenue'] for item in analysis['hourlyBreakdown']), default=1)
    for item in analysis['hourlyBreakdown']:
        bar_height = (item['revenue'] / max_revenue * 100) if max_revenue > 0 else 0
        is_peak = item['display'] == peak_hour
        
        hourly_chart += f"""
        <div style="flex: 1; min-width: 70px; text-align: center;">
          <div style="height: 120px; display: flex; align-items: flex-end; justify-content: center; margin-bottom: 10px;">
            <div style="width: 100%; background: {'linear-gradient(180deg, #43e97b 0%, #38f9d7 100%)' if is_peak else 'linear-gradient(180deg, #667eea 0%, #764ba2 100%)'}; border-radius: 6px 6px 0 0; height: {max(bar_height, 2)}%; position: relative; box-shadow: 0 -2px 8px rgba(0,0,0,0.1);">
              {f'<div style="position: absolute; top: -20px; left: 50%; transform: translateX(-50%); background: #43e97b; color: white; padding: 2px 6px; border-radius: 10px; font-size: 9px; font-weight: 700; white-space: nowrap;">PEAK</div>' if is_peak else ''}
            </div>
          </div>
          <div style="font-size: 12px; color: {'#43e97b' if is_peak else '#666'}; margin-bottom: 3px; font-weight: {'700' if is_peak else '600'};">{item['display']}</div>
          <div style="font-size: 10px; color: #999; margin-bottom: 2px;">{item['count']} txn</div>
          <div style="font-size: 12px; font-weight: 700; color: #1a1a1a;">₹{item['revenue']:,}</div>
        </div>
        """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Business Intelligence Report</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);">
  <div style="max-width: 900px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.12);">
    
    {test_banner}
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 48px 40px; position: relative; overflow: hidden;">
      <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(255,255,255,0.1); border-radius: 50%;"></div>
      <div style="position: absolute; bottom: -30px; left: -30px; width: 150px; height: 150px; background: rgba(255,255,255,0.08); border-radius: 50%;"></div>
      <div style="position: relative; z-index: 1;">
        <div style="font-size: 14px; text-transform: uppercase; letter-spacing: 2px; opacity: 0.9; font-weight: 600; margin-bottom: 8px;">📊 Business Intelligence Report</div>
        <h1 style="margin: 0; font-size: 42px; font-weight: 800; line-height: 1.2;">{today_str}</h1>
        <div style="margin-top: 12px; font-size: 16px; opacity: 0.95; display: flex; align-items: center; gap: 8px;">
          <span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 12px; font-weight: 600;">📍 {location_name}</span>
        </div>
      </div>
    </div>
    
    <div style="padding: 40px;">
      
      <!-- KPI Dashboard -->
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 40px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px 20px; border-radius: 12px; text-align: center; box-shadow: 0 6px 20px rgba(102, 126, 234, 0.35);">
          <div style="font-size: 12px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-bottom: 8px;">Total Revenue</div>
          <div style="font-size: 28px; font-weight: 900; line-height: 1;">₹{analysis['totalRevenue']:,}</div>
        </div>
        
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 24px 20px; border-radius: 12px; text-align: center; box-shadow: 0 6px 20px rgba(240, 147, 251, 0.35);">
          <div style="font-size: 12px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-bottom: 8px;">Transactions</div>
          <div style="font-size: 28px; font-weight: 900; line-height: 1;">{analysis['totalVehicles']}</div>
        </div>
        
        <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 24px 20px; border-radius: 12px; text-align: center; box-shadow: 0 6px 20px rgba(79, 172, 254, 0.35);">
          <div style="font-size: 12px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-bottom: 8px;">Avg Transaction</div>
          <div style="font-size: 28px; font-weight: 900; line-height: 1;">₹{round(analysis['avgService'])}</div>
        </div>
        
        <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; padding: 24px 20px; border-radius: 12px; text-align: center; box-shadow: 0 6px 20px rgba(67, 233, 123, 0.35);">
          <div style="font-size: 12px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-bottom: 8px;">Peak Hour</div>
          <div style="font-size: 20px; font-weight: 900; line-height: 1.2;">{peak_hour}<br><span style="font-size: 14px; opacity: 0.9;">₹{peak_revenue:,}</span></div>
        </div>
      </div>
      
      <!-- Key Insights -->
      <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 24px; border-radius: 12px; margin-bottom: 40px; border-left: 5px solid #667eea;">
        <h3 style="margin: 0 0 16px 0; color: #1a1a1a; font-size: 20px; font-weight: 700; display: flex; align-items: center;">
          <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); width: 5px; height: 24px; display: inline-block; margin-right: 12px; border-radius: 3px;"></span>
          💡 Key Insights
        </h3>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
          <div style="background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
            <div style="color: #666; font-size: 13px; margin-bottom: 6px; font-weight: 600;">🏆 Top Service</div>
            <div style="color: #1a1a1a; font-size: 18px; font-weight: 800;">{top_service}</div>
            <div style="color: #667eea; font-size: 14px; font-weight: 600; margin-top: 4px;">₹{top_service_revenue:,} revenue</div>
          </div>
          <div style="background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
            <div style="color: #666; font-size: 13px; margin-bottom: 6px; font-weight: 600;">⏰ Active Hours</div>
            <div style="color: #1a1a1a; font-size: 18px; font-weight: 800;">{analysis['insights']['busyHours']} hours</div>
            <div style="color: #667eea; font-size: 14px; font-weight: 600; margin-top: 4px;">Operational activity</div>
          </div>
        </div>
      </div>
      
      <!-- Payment Analytics -->
      <div style="margin-bottom: 40px;">
        <h2 style="color: #1a1a1a; font-size: 26px; margin: 0 0 20px 0; font-weight: 800; display: flex; align-items: center;">
          <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); width: 6px; height: 28px; display: inline-block; margin-right: 12px; border-radius: 3px;"></span>
          💳 Payment Analytics
        </h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
          {payment_cards}
        </div>
      </div>
      
      <!-- Service Performance -->
      <div style="margin-bottom: 40px;">
        <h2 style="color: #1a1a1a; font-size: 26px; margin: 0 0 20px 0; font-weight: 800; display: flex; align-items: center;">
          <span style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); width: 6px; height: 28px; display: inline-block; margin-right: 12px; border-radius: 3px;"></span>
          🛠️ Service Performance
        </h2>
        <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 3px 10px rgba(0,0,0,0.08);">
          {service_cards}
        </div>
      </div>
      
      <!-- Vehicle Analytics -->
      <div style="margin-bottom: 40px;">
        <h2 style="color: #1a1a1a; font-size: 26px; margin: 0 0 20px 0; font-weight: 800; display: flex; align-items: center;">
          <span style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); width: 6px; height: 28px; display: inline-block; margin-right: 12px; border-radius: 3px;"></span>
          🚗 Vehicle Analytics
        </h2>
        <div style="background: white; padding: 28px; border-radius: 12px; box-shadow: 0 3px 10px rgba(0,0,0,0.08);">
          {vehicle_bars}
        </div>
      </div>
      
      <!-- Hourly Revenue Trend -->
      <div style="margin-bottom: 40px;">
        <h2 style="color: #1a1a1a; font-size: 26px; margin: 0 0 20px 0; font-weight: 800; display: flex; align-items: center;">
          <span style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); width: 6px; height: 28px; display: inline-block; margin-right: 12px; border-radius: 3px;"></span>
          📈 Hourly Revenue Trend
        </h2>
        <div style="background: white; padding: 28px; border-radius: 12px; box-shadow: 0 3px 10px rgba(0,0,0,0.08); overflow-x: auto;">
          <div style="display: flex; gap: 6px; min-width: 800px;">
            {hourly_chart}
          </div>
        </div>
      </div>
      
      <!-- Attachments Notice -->
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 28px; border-radius: 12px; text-align: center; box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);">
        <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">📎 Detailed Analytics Attached</div>
        <p style="margin: 0; font-size: 15px; line-height: 1.6; opacity: 0.95;">
          This email includes 3 comprehensive CSV reports:<br>
          <strong>Transaction Report • Payment Analytics • Service Performance</strong>
        </p>
      </div>
      
    </div>
    
    <!-- Footer -->
    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 28px 40px; border-top: 1px solid #dee2e6; text-align: center;">
      <p style="margin: 0; color: #6c757d; font-size: 13px; font-weight: 600;">
        Report generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}
      </p>
      <p style="margin: 8px 0 0 0; color: #999; font-size: 12px;">
        Powered by Advanced Business Intelligence Analytics
      </p>
      {test_footer}
    </div>
    
  </div>
</body>
</html>
    """.strip()