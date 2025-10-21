"""
Template 2: Enhanced Daily Report Email Template with Chart.js Visualizations
"""

from datetime import datetime
from typing import Dict, Any
import json


def generate_template2_html(analysis: Dict[str, Any], location_name: str, 
                            today_str: str) -> str:
    """Generate HTML for Template 2 (Enhanced) with Chart.js graphs"""
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
    
    # Prepare data for Chart.js
    # Payment Mode Chart Data
    payment_labels = [item['mode'] for item in analysis['paymentModeBreakdown']]
    payment_data = [item['revenue'] for item in analysis['paymentModeBreakdown']]
    payment_counts = [item['count'] for item in analysis['paymentModeBreakdown']]
    
    # Service Performance Chart Data
    service_labels = [item['service'] for item in analysis['serviceBreakdown']]
    service_revenue = [item['revenue'] for item in analysis['serviceBreakdown']]
    service_counts = [item['count'] for item in analysis['serviceBreakdown']]
    
    # Vehicle Distribution Chart Data
    vehicle_labels = [item['type'] for item in analysis['vehicleDistribution']]
    vehicle_counts = [item['count'] for item in analysis['vehicleDistribution']]
    
    # Hourly Performance Chart Data
    hourly_labels = [item['display'] for item in analysis['hourlyBreakdown']]
    hourly_amounts = [item['amount'] for item in analysis['hourlyBreakdown']]
    hourly_counts = [item['count'] for item in analysis['hourlyBreakdown']]
    
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Enhanced Daily Report</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
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
        
        <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); margin-top: 20px;">
          <h3 style="margin: 0 0 16px 0; color: #555; font-size: 16px;">Payment Revenue Distribution</h3>
          <canvas id="paymentChart" style="max-height: 300px;"></canvas>
        </div>
      </div>
      
      <div style="margin-bottom: 40px;">
        <h2 style="color: #333; font-size: 24px; margin: 0 0 20px 0; font-weight: 700;">🛠️ Service Performance</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
          {service_cards}
        </div>
        
        <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); margin-top: 20px;">
          <h3 style="margin: 0 0 16px 0; color: #555; font-size: 16px;">Service Revenue Comparison</h3>
          <canvas id="serviceChart" style="max-height: 300px;"></canvas>
        </div>
      </div>
      
      <div style="margin-bottom: 40px;">
        <h2 style="color: #333; font-size: 24px; margin: 0 0 20px 0; font-weight: 700;">🚗 Vehicle Distribution</h2>
        <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
          <canvas id="vehicleChart" style="max-height: 300px;"></canvas>
        </div>
      </div>
      
      <div style="margin-bottom: 40px;">
        <h2 style="color: #333; font-size: 24px; margin: 0 0 20px 0; font-weight: 700;">⏰ Hourly Performance</h2>
        <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
          <canvas id="hourlyChart" style="max-height: 350px;"></canvas>
        </div>
      </div>
      
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px; border-radius: 12px; text-align: center;">
        <p style="margin: 0; font-size: 15px; line-height: 1.6;">
          🔎 <strong>Attachments Included:</strong> This email contains 3 detailed CSV reports with complete transaction data, payment analytics, and service breakdowns.
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
  
  <script>
    // Payment Mode Chart
    const paymentCtx = document.getElementById('paymentChart').getContext('2d');
    new Chart(paymentCtx, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(payment_labels)},
        datasets: [{{
          label: 'Revenue (₹)',
          data: {json.dumps(payment_data)},
          backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#4facfe'],
          borderRadius: 6
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: true,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              label: function(context) {{
                const index = context.dataIndex;
                const revenue = context.parsed.y;
                const count = {json.dumps(payment_counts)}[index];
                return `Revenue: ₹${{revenue.toLocaleString()}} | Vehicles: ${{count}}`;
              }}
            }}
          }}
        }},
        scales: {{
          y: {{
            beginAtZero: true,
            ticks: {{
              callback: function(value) {{
                return '₹' + value.toLocaleString();
              }}
            }}
          }}
        }}
      }}
    }});
    
    // Service Performance Chart
    const serviceCtx = document.getElementById('serviceChart').getContext('2d');
    new Chart(serviceCtx, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(service_labels)},
        datasets: [{{
          label: 'Revenue (₹)',
          data: {json.dumps(service_revenue)},
          backgroundColor: '#f093fb',
          borderRadius: 6
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: true,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              label: function(context) {{
                const index = context.dataIndex;
                const revenue = context.parsed.y;
                const count = {json.dumps(service_counts)}[index];
                return `Revenue: ₹${{revenue.toLocaleString()}} | Count: ${{count}}`;
              }}
            }}
          }}
        }},
        scales: {{
          y: {{
            beginAtZero: true,
            ticks: {{
              callback: function(value) {{
                return '₹' + value.toLocaleString();
              }}
            }}
          }}
        }}
      }}
    }});
    
    // Vehicle Distribution Chart
    const vehicleCtx = document.getElementById('vehicleChart').getContext('2d');
    new Chart(vehicleCtx, {{
      type: 'doughnut',
      data: {{
        labels: {json.dumps(vehicle_labels)},
        datasets: [{{
          data: {json.dumps(vehicle_counts)},
          backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe']
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: true,
        plugins: {{
          legend: {{
            position: 'bottom'
          }},
          tooltip: {{
            callbacks: {{
              label: function(context) {{
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const value = context.parsed;
                const percentage = ((value / total) * 100).toFixed(1);
                return `${{context.label}}: ${{value}} vehicles (${{percentage}}%)`;
              }}
            }}
          }}
        }}
      }}
    }});
    
    // Hourly Performance Chart
    const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
    new Chart(hourlyCtx, {{
      type: 'line',
      data: {{
        labels: {json.dumps(hourly_labels)},
        datasets: [{{
          label: 'Revenue (₹)',
          data: {json.dumps(hourly_amounts)},
          borderColor: '#667eea',
          backgroundColor: 'rgba(102, 126, 234, 0.1)',
          fill: true,
          tension: 0.4,
          borderWidth: 2
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: true,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              label: function(context) {{
                const index = context.dataIndex;
                const revenue = context.parsed.y;
                const count = {json.dumps(hourly_counts)}[index];
                return `Revenue: ₹${{revenue.toLocaleString()}} | Vehicles: ${{count}}`;
              }}
            }}
          }}
        }},
        scales: {{
          y: {{
            beginAtZero: true,
            ticks: {{
              callback: function(value) {{
                return '₹' + value.toLocaleString();
              }}
            }}
          }}
        }}
      }}
    }});
  </script>
</body>
</html>
    """.strip()