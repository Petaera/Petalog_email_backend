"""
Template 2: Enhanced Daily Report Email Template with CID Charts
Generates charts as images, attaches them as CIDs, and returns HTML ready for SES.
"""

from datetime import datetime
from typing import Dict, Any, Tuple, List
import matplotlib.pyplot as plt
import io
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def plot_bar_chart(labels: List[str], values: List[int], title: str, color: str = '#667eea') -> io.BytesIO:
    """Generate bar chart as BytesIO object"""
    fig, ax = plt.subplots(figsize=(6,4))
    ax.bar(labels, values, color=color)
    ax.set_title(title)
    ax.set_ylabel('Revenue (₹)')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(rotation=30, ha='right')
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def plot_doughnut_chart(labels: List[str], values: List[int], title: str, colors: List[str] = None) -> io.BytesIO:
    """Generate doughnut chart as BytesIO object"""
    fig, ax = plt.subplots(figsize=(6,4))
    if colors is None:
        colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe']
    wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90, wedgeprops=dict(width=0.5))
    ax.set_title(title)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def generate_template2_email(analysis: Dict[str, Any], location_name: str, today_str: str) -> MIMEMultipart:
    """
    Returns MIMEMultipart email object ready to send via SES with CID charts.
    """
    msg = MIMEMultipart('related')
    msg['Subject'] = f"📊 Daily Report - {today_str} - {location_name}"
    msg['From'] = 'reports@yourdomain.com'
    
    # Create HTML body with placeholder CIDs
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: sans-serif; background-color: #f0f2f5; margin: 0; padding: 0;">
      <div style="max-width:800px; margin: 20px auto; background:white; border-radius:12px; padding:24px;">
        <h1 style="color:#333;">📊 Daily Business Report</h1>
        <p style="color:#555;">Date: {today_str}</p>
        <p style="color:#555;">Location: {location_name}</p>
        
        <h2>💳 Payment Revenue Distribution</h2>
        <img src="cid:paymentChart" style="max-width:100%; border-radius:8px;" alt="Payment Chart"/>
        
        <h2>🛠️ Service Performance</h2>
        <img src="cid:serviceChart" style="max-width:100%; border-radius:8px;" alt="Service Chart"/>
        
        <h2>🚗 Vehicle Distribution</h2>
        <img src="cid:vehicleChart" style="max-width:100%; border-radius:8px;" alt="Vehicle Chart"/>
        
        <h2>⏰ Hourly Performance</h2>
        <img src="cid:hourlyChart" style="max-width:100%; border-radius:8px;" alt="Hourly Chart"/>
        
        <p style="color:#777; font-size:12px; margin-top:24px;">Report generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}</p>
      </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_body, 'html'))
    
    # Generate charts and attach as CIDs
    # Payment Chart
    payment_labels = [item['mode'] for item in analysis['paymentModeBreakdown']]
    payment_values = [item['revenue'] for item in analysis['paymentModeBreakdown']]
    payment_chart = plot_bar_chart(payment_labels, payment_values, 'Payment Revenue Distribution')
    img = MIMEImage(payment_chart.read(), _subtype='png')
    img.add_header('Content-ID', '<paymentChart>')
    img.add_header('Content-Disposition', 'inline', filename='payment_chart.png')
    msg.attach(img)
    
    # Service Chart
    service_labels = [item['service'] for item in analysis['serviceBreakdown']]
    service_values = [item['revenue'] for item in analysis['serviceBreakdown']]
    service_chart = plot_bar_chart(service_labels, service_values, 'Service Revenue Comparison', color='#f093fb')
    img = MIMEImage(service_chart.read(), _subtype='png')
    img.add_header('Content-ID', '<serviceChart>')
    img.add_header('Content-Disposition', 'inline', filename='service_chart.png')
    msg.attach(img)
    
    # Vehicle Distribution Chart
    vehicle_labels = [item['type'] for item in analysis['vehicleDistribution']]
    vehicle_values = [item['count'] for item in analysis['vehicleDistribution']]
    vehicle_chart = plot_doughnut_chart(vehicle_labels, vehicle_values, 'Vehicle Distribution')
    img = MIMEImage(vehicle_chart.read(), _subtype='png')
    img.add_header('Content-ID', '<vehicleChart>')
    img.add_header('Content-Disposition', 'inline', filename='vehicle_chart.png')
    msg.attach(img)
    
    # Hourly Performance Chart
    hourly_labels = [item['display'] for item in analysis['hourlyBreakdown']]
    hourly_values = [item['amount'] for item in analysis['hourlyBreakdown']]
    hourly_chart = plot_bar_chart(hourly_labels, hourly_values, 'Hourly Performance', color='#4facfe')
    img = MIMEImage(hourly_chart.read(), _subtype='png')
    img.add_header('Content-ID', '<hourlyChart>')
    img.add_header('Content-Disposition', 'inline', filename='hourly_chart.png')
    msg.attach(img)
    
    return msg
