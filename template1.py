"""
Template 1: Classic Business - Improved & Responsive
Clean, professional layout with comprehensive data breakdown
"""

from datetime import datetime
from typing import Dict, Any, Optional


def generate_template1_html(analysis: Dict[str, Any], location_name: str, 
                            today_str: str) -> str:
    """Generate HTML for Template 1 (Classic Business) - Improved & Responsive"""
    
    test_banner = ""
    test_footer = ""
    
    # Payment breakdown rows
    payment_rows = ""
    for item in analysis['paymentModeBreakdown']:
        upi_details = ""
        if item['mode'].lower() == 'upi' and item.get('upiAccounts'):
            upi_list = "<ul style='margin: 8px 0; padding-left: 20px; list-style: none;'>"
            for account_name, account_data in item['upiAccounts'].items():
                upi_list += f"<li style='font-size: 13px; padding: 4px 0; color: #495057;'>• {account_name}: ₹{account_data['amount']:,} ({account_data['count']} vehicles)</li>"
            upi_list += "</ul>"
            upi_details = f"""
            <tr>
              <td colspan="4" style="padding: 12px 16px; background-color: #f8f9fa; border-bottom: 1px solid #e9ecef;">
                <strong style="color: #495057; font-size: 13px;">UPI Account Breakdown:</strong>
                {upi_list}
              </td>
            </tr>
            """
        
        payment_rows += f"""
        <tr>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; font-size: 14px; color: #333;">{item['mode']}</td>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; text-align: right; font-weight: 600; font-size: 14px; color: #2c3e50;">₹{item['revenue']:,}</td>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; text-align: center; font-size: 14px; color: #555;">{item['count']}</td>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; text-align: right; font-size: 14px; color: #7f8c8d;">{item['percentage']:.1f}%</td>
        </tr>
        {upi_details}
        """
    
    # Service breakdown rows
    service_rows = ""
    for item in analysis['serviceBreakdown']:
        service_rows += f"""
        <tr>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; font-size: 14px; color: #333;">{item['service']}</td>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; text-align: center; font-size: 14px; color: #555;">{item['count']}</td>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; text-align: right; font-weight: 600; font-size: 14px; color: #2c3e50;">₹{item['revenue']:,}</td>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; text-align: right; font-size: 14px; color: #7f8c8d;">₹{round(item['price'])}</td>
        </tr>
        """
    
    # Vehicle distribution rows
    vehicle_rows = ""
    for item in analysis['vehicleDistribution']:
        vehicle_rows += f"""
        <tr>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; font-size: 14px; color: #333;">{item['type']}</td>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; text-align: center; font-size: 14px; color: #555;">{item['count']}</td>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; text-align: right; font-size: 14px; color: #7f8c8d;">{item['percentage']:.1f}%</td>
        </tr>
        """
    
    # Hourly breakdown rows
    hourly_rows = ""
    for item in analysis['hourlyBreakdown']:
        hourly_rows += f"""
        <tr>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; font-size: 14px; color: #333;">{item['display']}</td>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; text-align: center; font-size: 14px; color: #555;">{item['count']}</td>
          <td style="padding: 14px 16px; border-bottom: 1px solid #e9ecef; text-align: right; font-weight: 600; font-size: 14px; color: #2c3e50;">₹{item['amount']:,}</td>
        </tr>
        """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Business Report - Classic</title>
  <style>
    /* Reset and base styles */
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}
    
    body {{
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background-color: #f5f7fa;
      line-height: 1.6;
    }}
    
    /* Container */
    .email-container {{
      max-width: 650px;
      margin: 0 auto;
      background-color: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }}
    
    /* Header */
    .header {{
      background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%);
      color: white;
      padding: 32px 24px;
      text-align: center;
    }}
    
    .header h1 {{
      margin: 0;
      font-size: 26px;
      font-weight: 600;
      letter-spacing: -0.5px;
    }}
    
    .header .date {{
      margin: 10px 0 0 0;
      font-size: 15px;
      opacity: 0.95;
      font-weight: 500;
    }}
    
    .header .location {{
      margin: 6px 0 0 0;
      font-size: 14px;
      opacity: 0.85;
    }}
    
    /* Content */
    .content {{
      padding: 32px 24px;
    }}
    
    /* Summary cards */
    .summary-cards {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-bottom: 32px;
    }}
    
    .summary-card {{
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 24px 20px;
      border-radius: 10px;
      text-align: center;
      box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
    }}
    
    .summary-card:nth-child(2) {{
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }}
    
    .summary-card:nth-child(3) {{
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }}
    
    .summary-card .label {{
      font-size: 12px;
      opacity: 0.9;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      font-weight: 600;
      margin-bottom: 8px;
    }}
    
    .summary-card .value {{
      font-size: 28px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }}
    
    /* Section */
    .section {{
      margin-bottom: 32px;
    }}
    
    .section-title {{
      color: #2c3e50;
      font-size: 18px;
      font-weight: 600;
      margin: 0 0 16px 0;
      padding-bottom: 10px;
      border-bottom: 3px solid #667eea;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    
    .section:nth-child(3) .section-title {{
      border-bottom-color: #f093fb;
    }}
    
    .section:nth-child(4) .section-title {{
      border-bottom-color: #4facfe;
    }}
    
    .section:nth-child(5) .section-title {{
      border-bottom-color: #43e97b;
    }}
    
    /* Table */
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      background-color: #fff;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
      border: 1px solid #e9ecef;
    }}
    
    .data-table thead tr {{
      background-color: #f8f9fa;
      border-bottom: 2px solid #dee2e6;
    }}
    
    .data-table th {{
      padding: 14px 16px;
      text-align: left;
      font-weight: 600;
      font-size: 13px;
      color: #495057;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    
    .data-table tbody tr:hover {{
      background-color: #f8f9fa;
    }}
    
    .data-table tbody tr:last-child td {{
      border-bottom: none;
    }}
    
    /* Footer note */
    .footer-note {{
      background-color: #f8f9fa;
      padding: 20px;
      border-radius: 8px;
      border-left: 4px solid #667eea;
      margin-top: 24px;
    }}
    
    .footer-note p {{
      margin: 0;
      color: #6c757d;
      font-size: 13px;
      line-height: 1.6;
    }}
    
    /* Footer */
    .footer {{
      background-color: #f8f9fa;
      padding: 20px 24px;
      border-top: 1px solid #e9ecef;
      text-align: center;
    }}
    
    .footer p {{
      margin: 0;
      color: #6c757d;
      font-size: 12px;
    }}
    
    /* Responsive styles */
    @media only screen and (max-width: 600px) {{
      .email-container {{
        border-radius: 0;
        margin: 0;
      }}
      
      .header {{
        padding: 24px 16px;
      }}
      
      .header h1 {{
        font-size: 22px;
      }}
      
      .header .date {{
        font-size: 14px;
      }}
      
      .content {{
        padding: 24px 16px;
      }}
      
      .summary-cards {{
        grid-template-columns: 1fr;
        gap: 12px;
      }}
      
      .summary-card {{
        padding: 20px 16px;
      }}
      
      .summary-card .value {{
        font-size: 24px;
      }}
      
      .section {{
        margin-bottom: 24px;
      }}
      
      .section-title {{
        font-size: 16px;
        margin-bottom: 12px;
      }}
      
      .data-table {{
        font-size: 13px;
      }}
      
      .data-table th,
      .data-table td {{
        padding: 10px 12px;
      }}
      
      .footer-note {{
        padding: 16px;
      }}
      
      .footer {{
        padding: 16px;
      }}
    }}
    
    @media only screen and (max-width: 480px) {{
      .summary-card .value {{
        font-size: 22px;
      }}
      
      .data-table {{
        font-size: 12px;
      }}
      
      .data-table th,
      .data-table td {{
        padding: 8px 10px;
      }}
    }}
  </style>
</head>
<body>
  <div class="email-container">
    
    {test_banner}
    
    <div class="header">
      <h1>📊 Daily Business Report</h1>
      <p class="date">{today_str}</p>
      <p class="location">📍 {location_name}</p>
    </div>
    
    <div class="content">
      
      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="summary-card">
          <div class="label">Total Revenue</div>
          <div class="value">₹{analysis['totalRevenue']:,}</div>
        </div>
        
        <div class="summary-card">
          <div class="label">Vehicles Served</div>
          <div class="value">{analysis['totalVehicles']}</div>
        </div>
        
        <div class="summary-card">
          <div class="label">Avg Service</div>
          <div class="value">₹{round(analysis['avgService'])}</div>
        </div>
      </div>
      
      <!-- Payment Mode Breakdown -->
      <div class="section">
        <h2 class="section-title">💳 Payment Mode Breakdown</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th>Payment Mode</th>
              <th style="text-align: right;">Revenue</th>
              <th style="text-align: center;">Count</th>
              <th style="text-align: right;">% of Total</th>
            </tr>
          </thead>
          <tbody>
            {payment_rows}
          </tbody>
        </table>
      </div>
      
      <!-- Service Breakdown -->
      <div class="section">
        <h2 class="section-title">🛠️ Service Breakdown</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th>Service Type</th>
              <th style="text-align: center;">Count</th>
              <th style="text-align: right;">Revenue</th>
              <th style="text-align: right;">Avg Price</th>
            </tr>
          </thead>
          <tbody>
            {service_rows}
          </tbody>
        </table>
      </div>
      
      <!-- Vehicle Type Distribution -->
      <div class="section">
        <h2 class="section-title">🚗 Vehicle Type Distribution</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th>Vehicle Type</th>
              <th style="text-align: center;">Count</th>
              <th style="text-align: right;">Percentage</th>
            </tr>
          </thead>
          <tbody>
            {vehicle_rows}
          </tbody>
        </table>
      </div>
      
      <!-- Hourly Performance -->
      <div class="section">
        <h2 class="section-title">⏰ Hourly Performance</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th style="text-align: center;">Vehicles</th>
              <th style="text-align: right;">Revenue</th>
            </tr>
          </thead>
          <tbody>
            {hourly_rows}
          </tbody>
        </table>
      </div>
      
      <!-- Footer Note -->
      <div class="footer-note">
        <p>
          📎 This email includes 3 CSV attachments with detailed transaction data, payment breakdowns, and service analysis for your records.
        </p>
      </div>
      
    </div>
    
    <div class="footer">
      <p>Report generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}</p>
      {test_footer}
    </div>
    
  </div>
</body>
</html>
    """.strip()