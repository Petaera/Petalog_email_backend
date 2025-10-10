"""
Template 2: Enhanced Daily Report Email Template
"""

from datetime import datetime
from typing import Dict, Any


def generate_template2_html(analysis: Dict[str, Any], location_name: str, 
                            today_str: str) -> str:
    """Generate HTML for Template 2 (Enhanced)"""
    test_banner = ""
    test_footer = ""
    # Payment breakdown cards
    payment_cards = ""
    for item in analysis['paymentModeBreakdown']:
        upi_details = ""
        if item['mode'].lower() == 'upi' and item.get('upiAccounts'):
            upi_items = ""
            for account_name, account_data in item['upiAccounts'].items():
                upi_items += f'<div style="padding: 8px 12px; background-color: #e3f2fd; border-radius: 4px; margin-top: 8px;"><span style="font-weight: 600; color: #1976d2;">{account_name}</span><br><span style="font-size: 13px; color: #666;">₹{account_data["amount"]:,} • {account_data["count"]} vehicles</span></div>'
            upi_details = f'<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e0e0e0;"><strong style="color: #555; font-size: 14px;">UPI Breakdown:</strong>{upi_items}</div>'
        
        payment_cards += f"""
        <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); border-left: 4px solid #667eea;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h3 style="margin: 0; color: #333; font-size: 18px;">{item['mode']}</h3>
            <span style="background-color: #667eea; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">{item['percentage']:.1f}%</span>
          </div>
          <div style="display: flex; justify-content: space-between; color: #666; font-size: 14px;">
            <div>
              <span style="color: #999; font-size: 12px;">Revenue</span><br>
              <strong style="color: #333; font-size: 20px;">₹{item['revenue']:,}</strong>
            </div>
            <div style="text-align: right;">
              <span style="color: #999; font-size: 12px;">Vehicles</span><br>
              <strong style="color: #333; font-size: 20px;">{item['count']}</strong>
            </div>
          </div>
          {upi_details}
        </div>
        """
    
    # Service breakdown cards
    service_cards = ""
    for item in analysis['serviceBreakdown']:
        service_cards += f"""
        <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); border-left: 4px solid #f093fb;">
          <h3 style="margin: 0 0 12px 0; color: #333; font-size: 18px;">{item['service']}</h3>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; color: #666; font-size: 14px;">
            <div>
              <span style="color: #999; font-size: 12px;">Count</span><br>
              <strong style="color: #333; font-size: 18px;">{item['count']}</strong>
            </div>
            <div>
              <span style="color: #999; font-size: 12px;">Revenue</span><br>
              <strong style="color: #333; font-size: 18px;">₹{item['revenue']:,}</strong>
            </div>
            <div>
              <span style="color: #999; font-size: 12px;">Avg Price</span><br>
              <strong style="color: #333; font-size: 18px;">₹{round(item['price'])}</strong>
            </div>
          </div>
        </div>
        """
    
    # Vehicle bars
    vehicle_bars = ""
    for item in analysis['vehicleDistribution']:
        vehicle_bars += f"""
        <div style="margin-bottom: 16px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span style="font-weight: 600; color: #333;">{item['type']}</span>
            <span style="color: #666;">{item['count']} vehicles ({item['percentage']:.1f}%)</span>
          </div>
          <div style="background-color: #e0e0e0; height: 8px; border-radius: 4px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%); height: 100%; width: {item['percentage']}%; border-radius: 4px;"></div>
          </div>
        </div>
        """
    
    # Hourly chart (simplified bar representation)
    hourly_bars = ""
    max_amount = max((item['amount'] for item in analysis['hourlyBreakdown']), default=1)
    for item in analysis['hourlyBreakdown']:
        bar_height = (item['amount'] / max_amount * 100) if max_amount > 0 else 0
        hourly_bars += f"""
        <div style="flex: 1; min-width: 60px; text-align: center;">
          <div style="height: 100px; display: flex; align-items: flex-end; justify-content: center; margin-bottom: 8px;">
            <div style="width: 100%; background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); border-radius: 4px 4px 0 0; height: {bar_height}%; min-height: 2px;"></div>
          </div>
          <div style="font-size: 11px; color: #666; margin-bottom: 2px;">{item['display']}</div>
          <div style="font-size: 10px; color: #999;">{item['count']}v</div>
          <div style="font-size: 11px; font-weight: 600; color: #333;">₹{item['amount']:,}</div>
        </div>
        """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Enhanced Daily Report</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5;">
  <div style="max-width: 800px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    
    {test_banner}
    
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 32px; text-align: center;">
      <h1 style="margin: 0; font-size: 36px; font-weight: 700;">📊 Daily Business Report</h1>
      <p style="margin: 12px 0 0 0; font-size: 18px; opacity: 0.95;">{today_str}</p>
      <p style="margin: 4px 0 0 0; font-size: 15px; opacity: 0.85;">📍 {location_name}</p>
    </div>
    
    <div style="padding: 32px;">
      
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 40px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px; border-radius: 12px; text-align: center; box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);">
          <p style="margin: 0; font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Total Revenue</p>
          <h2 style="margin: 12px 0 0 0; font-size: 32px; font-weight: 800;">₹{analysis['totalRevenue']:,}</h2>
        </div>
        
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 24px; border-radius: 12px; text-align: center; box-shadow: 0 4px 8px rgba(240, 147, 251, 0.3);">
          <p style="margin: 0; font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Vehicles</p>
          <h2 style="margin: 12px 0 0 0; font-size: 32px; font-weight: 800;">{analysis['totalVehicles']}</h2>
        </div>
        
        <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 24px; border-radius: 12px; text-align: center; box-shadow: 0 4px 8px rgba(79, 172, 254, 0.3);">
          <p style="margin: 0; font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Avg Service</p>
          <h2 style="margin: 12px 0 0 0; font-size: 32px; font-weight: 800;">₹{round(analysis['avgService'])}</h2>
        </div>
      </div>
      
      <div style="margin-bottom: 40px;">
        <h2 style="color: #333; font-size: 24px; margin: 0 0 20px 0; font-weight: 700;">💳 Payment Breakdown</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
          {payment_cards}
        </div>
      </div>
      
      <div style="margin-bottom: 40px;">
        <h2 style="color: #333; font-size: 24px; margin: 0 0 20px 0; font-weight: 700;">🛠️ Service Performance</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
          {service_cards}
        </div>
      </div>
      
      <div style="margin-bottom: 40px;">
        <h2 style="color: #333; font-size: 24px; margin: 0 0 20px 0; font-weight: 700;">🚗 Vehicle Distribution</h2>
        <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
          {vehicle_bars}
        </div>
      </div>
      
      <div style="margin-bottom: 40px;">
        <h2 style="color: #333; font-size: 24px; margin: 0 0 20px 0; font-weight: 700;">⏰ Hourly Performance</h2>
        <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); overflow-x: auto;">
          <div style="display: flex; gap: 8px; min-width: 600px;">
            {hourly_bars}
          </div>
        </div>
      </div>
      
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px; border-radius: 12px; text-align: center;">
        <p style="margin: 0; font-size: 15px; line-height: 1.6;">
          📎 <strong>Attachments Included:</strong> This email contains 3 detailed CSV reports with complete transaction data, payment analytics, and service breakdowns.
        </p>
      </div>
      
    </div>
    
    <div style="background-color: #f8f9fa; padding: 24px 32px; border-top: 1px solid #e9ecef; text-align: center;">
      <p style="margin: 0; color: #6c757d; font-size: 13px;">
        Report generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}
      </p>
      {test_footer}
    </div>
    
  </div>
</body>
</html>
    """.strip()