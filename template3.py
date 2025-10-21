"""
Template 3: Modern Business Intelligence Report with Chart.js
Clean BI-style layout with data visualizations
"""

from datetime import datetime
from typing import Dict, Any
import json


def generate_template3_html(analysis: Dict[str, Any], location_name: str, 
                            today_str: str) -> str:
    """Generate HTML for Template 3 (BI-Style with Charts)"""
    
    peak_hour = analysis['summary']['peakHour']
    peak_revenue = analysis['summary']['peakHourRevenue']
    top_service = analysis['insights']['topService']
    top_service_revenue = analysis['insights']['topServiceRevenue']
    
    # Prepare chart data
    payment_labels = [item['mode'] for item in analysis['paymentModeBreakdown']]
    payment_data = [item['revenue'] for item in analysis['paymentModeBreakdown']]
    
    service_labels = [item['service'] for item in analysis['serviceBreakdown']]
    service_revenue = [item['revenue'] for item in analysis['serviceBreakdown']]
    service_counts = [item['count'] for item in analysis['serviceBreakdown']]
    
    vehicle_labels = [item['type'] for item in analysis['vehicleDistribution']]
    vehicle_counts = [item['count'] for item in analysis['vehicleDistribution']]
    
    hourly_labels = [item['display'] for item in analysis['hourlyBreakdown']]
    hourly_amounts = [item['revenue'] for item in analysis['hourlyBreakdown']]
    hourly_counts = [item['count'] for item in analysis['hourlyBreakdown']]
    
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Business Intelligence Report</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa;">
  
  <div style="max-width: 1200px; margin: 0 auto; padding: 20px;">
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 20px;">
      <h1 style="margin: 0; font-size: 28px; font-weight: 700;">Business Intelligence Report</h1>
      <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">{today_str} • {location_name}</p>
    </div>
    
    <!-- KPIs -->
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px;">
      <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;">
        <div style="color: #666; font-size: 12px; margin-bottom: 5px;">TOTAL REVENUE</div>
        <div style="color: #1a1a1a; font-size: 24px; font-weight: 700;">₹{analysis['totalRevenue']:,}</div>
      </div>
      <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #f093fb;">
        <div style="color: #666; font-size: 12px; margin-bottom: 5px;">TRANSACTIONS</div>
        <div style="color: #1a1a1a; font-size: 24px; font-weight: 700;">{analysis['totalVehicles']}</div>
      </div>
      <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #4facfe;">
        <div style="color: #666; font-size: 12px; margin-bottom: 5px;">AVG TRANSACTION</div>
        <div style="color: #1a1a1a; font-size: 24px; font-weight: 700;">₹{round(analysis['avgService'])}</div>
      </div>
      <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #43e97b;">
        <div style="color: #666; font-size: 12px; margin-bottom: 5px;">PEAK HOUR</div>
        <div style="color: #1a1a1a; font-size: 24px; font-weight: 700;">{peak_hour}</div>
      </div>
    </div>
    
    <!-- Charts Grid -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
      
      <!-- Payment Chart -->
      <div style="background: white; padding: 20px; border-radius: 8px;">
        <h3 style="margin: 0 0 15px 0; font-size: 16px; color: #1a1a1a;">Payment Distribution</h3>
        <canvas id="paymentChart" style="max-height: 300px;"></canvas>
      </div>
      
      <!-- Service Chart -->
      <div style="background: white; padding: 20px; border-radius: 8px;">
        <h3 style="margin: 0 0 15px 0; font-size: 16px; color: #1a1a1a;">Service Revenue</h3>
        <canvas id="serviceChart" style="max-height: 300px;"></canvas>
      </div>
      
    </div>
    
    <!-- Full Width Charts -->
    <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
      <h3 style="margin: 0 0 15px 0; font-size: 16px; color: #1a1a1a;">Hourly Revenue Trend</h3>
      <canvas id="hourlyChart" style="max-height: 300px;"></canvas>
    </div>
    
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
      
      <!-- Vehicle Distribution -->
      <div style="background: white; padding: 20px; border-radius: 8px;">
        <h3 style="margin: 0 0 15px 0; font-size: 16px; color: #1a1a1a;">Vehicle Distribution</h3>
        <canvas id="vehicleChart" style="max-height: 300px;"></canvas>
      </div>
      
      <!-- Top Service -->
      <div style="background: white; padding: 20px; border-radius: 8px;">
        <h3 style="margin: 0 0 15px 0; font-size: 16px; color: #1a1a1a;">Top Performer</h3>
        <div style="padding: 40px 0; text-align: center;">
          <div style="font-size: 32px; font-weight: 700; color: #667eea; margin-bottom: 10px;">{top_service}</div>
          <div style="font-size: 18px; color: #666;">₹{top_service_revenue:,}</div>
        </div>
      </div>
      
    </div>
    
    <!-- Footer -->
    <div style="background: white; padding: 20px; border-radius: 8px; text-align: center;">
      <p style="margin: 0; color: #666; font-size: 13px;">
        Report generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}
      </p>
    </div>
    
  </div>
  
  <script>
    // Payment Chart
    new Chart(document.getElementById('paymentChart'), {{
      type: 'doughnut',
      data: {{
        labels: {json.dumps(payment_labels)},
        datasets: [{{
          data: {json.dumps(payment_data)},
          backgroundColor: ['#667eea', '#f093fb', '#4facfe', '#43e97b']
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: true,
        plugins: {{
          legend: {{ position: 'bottom' }}
        }}
      }}
    }});
    
    // Service Chart
    new Chart(document.getElementById('serviceChart'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(service_labels)},
        datasets: [{{
          label: 'Revenue',
          data: {json.dumps(service_revenue)},
          backgroundColor: '#f093fb'
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{
            beginAtZero: true,
            ticks: {{ callback: function(value) {{ return '₹' + value.toLocaleString(); }} }}
          }}
        }}
      }}
    }});
    
    // Hourly Chart
    new Chart(document.getElementById('hourlyChart'), {{
      type: 'line',
      data: {{
        labels: {json.dumps(hourly_labels)},
        datasets: [{{
          label: 'Revenue',
          data: {json.dumps(hourly_amounts)},
          borderColor: '#667eea',
          backgroundColor: 'rgba(102, 126, 234, 0.1)',
          fill: true,
          tension: 0.4
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{
            beginAtZero: true,
            ticks: {{ callback: function(value) {{ return '₹' + value.toLocaleString(); }} }}
          }}
        }}
      }}
    }});
    
    // Vehicle Chart
    new Chart(document.getElementById('vehicleChart'), {{
      type: 'pie',
      data: {{
        labels: {json.dumps(vehicle_labels)},
        datasets: [{{
          data: {json.dumps(vehicle_counts)},
          backgroundColor: ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#ff6b6b']
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: true,
        plugins: {{
          legend: {{ position: 'bottom' }}
        }}
      }}
    }});
  </script>
  
</body>
</html>
    """.strip()