"""
Template 1: Classic Daily Report Email Template
"""

from datetime import datetime
from typing import Dict, Any


def generate_template1_html(analysis: Dict[str, Any], location_name: str, 
                            today_str: str) -> str:
    """Generate HTML for Template 1 (Classic)"""
    
    # Payment breakdown rows
    payment_rows = ""
    for item in analysis['paymentModeBreakdown']:
        upi_details = ""
        if item['mode'].lower() == 'upi' and item.get('upiAccounts'):
            upi_list = "<ul style='margin: 4px 0; padding-left: 20px;'>"
            for account_name, account_data in item['upiAccounts'].items():
                upi_list += f"<li style='font-size: 13px;'>{account_name}: ₹{account_data['amount']:,} ({account_data['count']} vehicles)</li>"
            upi_list += "</ul>"
            upi_details = f"""
            <tr>
              <td colspan="4" style="padding: 8px 12px; background-color: #f8f9fa; border-bottom: 1px solid #e9ecef;">
                <strong style="color: #495057;">UPI Account Breakdown:</strong>
                {upi_list}
              </td>
            </tr>
            """
        
        payment_rows += f"""
        <tr>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef;">{item['mode']}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: right; font-weight: 600;">₹{item['revenue']:,}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: center;">{item['count']}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: right;">{item['percentage']:.1f}%</td>
        </tr>
        {upi_details}
        """
    
    # Service breakdown rows
    service_rows = ""
    for item in analysis['serviceBreakdown']:
        service_rows += f"""
        <tr>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef;">{item['service']}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: center;">{item['count']}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: right; font-weight: 600;">₹{item['revenue']:,}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: right;">₹{round(item['price'])}</td>
        </tr>
        """
    
    # Vehicle distribution rows
    vehicle_rows = ""
    for item in analysis['vehicleDistribution']:
        vehicle_rows += f"""
        <tr>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef;">{item['type']}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: center;">{item['count']}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: right;">{item['percentage']:.1f}%</td>
        </tr>
        """
    
    # Hourly breakdown rows
    hourly_rows = ""
    for item in analysis['hourlyBreakdown']:
        hourly_rows += f"""
        <tr>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef;">{item['display']}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: center;">{item['count']}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: right; font-weight: 600;">₹{item['amount']:,}</td>
        </tr>
        """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Business Report</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
  <div style="max-width: 700px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px 24px; text-align: center;">
      <h1 style="margin: 0; font-size: 32px; font-weight: 600;">📊 Daily Business Report</h1>
      <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">{today_str}</p>
      <p style="margin: 4px 0 0 0; font-size: 14px; opacity: 0.8;">📍 {location_name}</p>
    </div>
    
    <div style="padding: 32px 24px;">
      
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
          <p style="margin: 0; font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.5px;">Total Revenue</p>
          <h2 style="margin: 8px 0 0 0; font-size: 28px; font-weight: 700;">₹{analysis['totalRevenue']:,}</h2>
        </div>
        
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
          <p style="margin: 0; font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.5px;">Vehicles Served</p>
          <h2 style="margin: 8px 0 0 0; font-size: 28px; font-weight: 700;">{analysis['totalVehicles']}</h2>
        </div>
        
        <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
          <p style="margin: 0; font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.5px;">Avg Service</p>
          <h2 style="margin: 8px 0 0 0; font-size: 28px; font-weight: 700;">₹{round(analysis['avgService'])}</h2>
        </div>
      </div>
      
      <div style="margin-bottom: 32px;">
        <h2 style="color: #333; font-size: 20px; margin: 0 0 16px 0; border-bottom: 2px solid #667eea; padding-bottom: 8px;">💳 Payment Mode Breakdown</h2>
        <table style="width: 100%; border-collapse: collapse; background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <thead>
            <tr style="background-color: #667eea; color: white;">
              <th style="padding: 12px; text-align: left; font-weight: 600;">Payment Mode</th>
              <th style="padding: 12px; text-align: right; font-weight: 600;">Revenue</th>
              <th style="padding: 12px; text-align: center; font-weight: 600;">Count</th>
              <th style="padding: 12px; text-align: right; font-weight: 600;">% of Total</th>
            </tr>
          </thead>
          <tbody>
            {payment_rows}
          </tbody>
        </table>
      </div>
      
      <div style="margin-bottom: 32px;">
        <h2 style="color: #333; font-size: 20px; margin: 0 0 16px 0; border-bottom: 2px solid #f093fb; padding-bottom: 8px;">🛠️ Service Breakdown</h2>
        <table style="width: 100%; border-collapse: collapse; background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <thead>
            <tr style="background-color: #f093fb; color: white;">
              <th style="padding: 12px; text-align: left; font-weight: 600;">Service Type</th>
              <th style="padding: 12px; text-align: center; font-weight: 600;">Count</th>
              <th style="padding: 12px; text-align: right; font-weight: 600;">Revenue</th>
              <th style="padding: 12px; text-align: right; font-weight: 600;">Avg Price</th>
            </tr>
          </thead>
          <tbody>
            {service_rows}
          </tbody>
        </table>
      </div>
      
      <div style="margin-bottom: 32px;">
        <h2 style="color: #333; font-size: 20px; margin: 0 0 16px 0; border-bottom: 2px solid #4facfe; padding-bottom: 8px;">🚗 Vehicle Type Distribution</h2>
        <table style="width: 100%; border-collapse: collapse; background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <thead>
            <tr style="background-color: #4facfe; color: white;">
              <th style="padding: 12px; text-align: left; font-weight: 600;">Vehicle Type</th>
              <th style="padding: 12px; text-align: center; font-weight: 600;">Count</th>
              <th style="padding: 12px; text-align: right; font-weight: 600;">Percentage</th>
            </tr>
          </thead>
          <tbody>
            {vehicle_rows}
          </tbody>
        </table>
      </div>
      
      <div style="margin-bottom: 32px;">
        <h2 style="color: #333; font-size: 20px; margin: 0 0 16px 0; border-bottom: 2px solid #43e97b; padding-bottom: 8px;">⏰ Hourly Performance</h2>
        <table style="width: 100%; border-collapse: collapse; background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <thead>
            <tr style="background-color: #43e97b; color: white;">
              <th style="padding: 12px; text-align: left; font-weight: 600;">Time</th>
              <th style="padding: 12px; text-align: center; font-weight: 600;">Vehicles</th>
              <th style="padding: 12px; text-align: right; font-weight: 600;">Revenue</th>
            </tr>
          </thead>
          <tbody>
            {hourly_rows}
          </tbody>
        </table>
      </div>
      
      <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;">
        <p style="margin: 0; color: #666; font-size: 14px;">
          📎 This email includes 3 CSV attachments with detailed transaction data, payment breakdowns, and service analysis.
        </p>
      </div>
      
    </div>
    
    <div style="background-color: #f8f9fa; padding: 20px 24px; border-top: 1px solid #e9ecef; text-align: center;">
      <p style="margin: 0; color: #6c757d; font-size: 12px;">
        Report generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}
      </p>
    </div>
    
  </div>
</body>
</html>
    """.strip()