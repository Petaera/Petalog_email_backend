"""
Template 3: Modern Business Intelligence Report with CID Charts
Generates BI-style charts as images and embeds them in the email via CID.
"""

from datetime import datetime
from typing import Dict, Any, List
import matplotlib.pyplot as plt
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def plot_bar_chart(labels: List[str], values: List[int], title: str, color: str = '#667eea') -> io.BytesIO:
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
    fig, ax = plt.subplots(figsize=(6,4))
    if colors is None:
        colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#ff6b6b']
    wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90, wedgeprops=dict(width=0.5))
    ax.set_title(title)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def generate_template3_email(analysis: Dict[str, Any], location_name: str, today_str: str) -> MIMEMultipart:
    """
    Returns MIMEMultipart email object for Template 3 with all charts embedded via CID.
    """
    msg = MIMEMultipart('related')
    msg['Subject'] = f"📊 BI Report - {today_str} - {location_name}"
    msg['From'] = 'reports@yourdomain.com'

    peak_hour = analysis['summary']['peakHour']
    peak_revenue = analysis['summary']['peakHourRevenue']
    top_service = analysis['insights']['topService']
    top_service_revenue = analysis['insights']['topServiceRevenue']

    # HTML with CID placeholders
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: sans-serif; background: #f5f7fa; margin:0; padding:0;">
      <div style="max-width:1200px; margin: 0 auto; padding:20px;">
        
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; padding:30px; border-radius:8px; margin-bottom:20px;">
          <h1 style="margin:0; font-size:28px;">Business Intelligence Report</h1>
          <p style="margin:8px 0 0 0; font-size:16px; opacity:0.9;">{today_str} • {location_name}</p>
        </div>

        <!-- KPIs -->
        <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:15px; margin-bottom:20px;">
          <div style="background:white; padding:20px; border-radius:8px; border-left:4px solid #667eea;">
            <div style="color:#666; font-size:12px;">TOTAL REVENUE</div>
            <div style="color:#1a1a1a; font-size:24px; font-weight:700;">₹{analysis['totalRevenue']:,}</div>
          </div>
          <div style="background:white; padding:20px; border-radius:8px; border-left:4px solid #f093fb;">
            <div style="color:#666; font-size:12px;">TRANSACTIONS</div>
            <div style="color:#1a1a1a; font-size:24px; font-weight:700;">{analysis['totalVehicles']}</div>
          </div>
          <div style="background:white; padding:20px; border-radius:8px; border-left:4px solid #4facfe;">
            <div style="color:#666; font-size:12px;">AVG TRANSACTION</div>
            <div style="color:#1a1a1a; font-size:24px; font-weight:700;">₹{round(analysis['avgService'])}</div>
          </div>
          <div style="background:white; padding:20px; border-radius:8px; border-left:4px solid #43e97b;">
            <div style="color:#666; font-size:12px;">PEAK HOUR</div>
            <div style="color:#1a1a1a; font-size:24px; font-weight:700;">{peak_hour}</div>
          </div>
        </div>

        <!-- Charts -->
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px;">
          <div style="background:white; padding:20px; border-radius:8px;">
            <h3 style="margin:0 0 15px 0; font-size:16px; color:#1a1a1a;">Payment Distribution</h3>
            <img src="cid:paymentChart" style="max-width:100%; border-radius:8px;" alt="Payment Chart"/>
          </div>
          <div style="background:white; padding:20px; border-radius:8px;">
            <h3 style="margin:0 0 15px 0; font-size:16px; color:#1a1a1a;">Service Revenue</h3>
            <img src="cid:serviceChart" style="max-width:100%; border-radius:8px;" alt="Service Chart"/>
          </div>
        </div>

        <div style="background:white; padding:20px; border-radius:8px; margin-bottom:20px;">
          <h3 style="margin:0 0 15px 0; font-size:16px; color:#1a1a1a;">Hourly Revenue Trend</h3>
          <img src="cid:hourlyChart" style="max-width:100%; border-radius:8px;" alt="Hourly Chart"/>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px;">
          <div style="background:white; padding:20px; border-radius:8px;">
            <h3 style="margin:0 0 15px 0; font-size:16px; color:#1a1a1a;">Vehicle Distribution</h3>
            <img src="cid:vehicleChart" style="max-width:100%; border-radius:8px;" alt="Vehicle Chart"/>
          </div>
          <div style="background:white; padding:20px; border-radius:8px;">
            <h3 style="margin:0 0 15px 0; font-size:16px; color:#1a1a1a;">Top Performer</h3>
            <div style="padding:40px 0; text-align:center;">
              <div style="font-size:32px; font-weight:700; color:#667eea; margin-bottom:10px;">{top_service}</div>
              <div style="font-size:18px; color:#666;">₹{top_service_revenue:,}</div>
            </div>
          </div>
        </div>

        <div style="background:white; padding:20px; border-radius:8px; text-align:center;">
          <p style="margin:0; color:#666; font-size:13px;">
            Report generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}
          </p>
        </div>

      </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, 'html'))

    # Charts as CIDs
    # Payment Chart
    payment_labels = [item['mode'] for item in analysis['paymentModeBreakdown']]
    payment_values = [item['revenue'] for item in analysis['paymentModeBreakdown']]
    payment_chart = plot_doughnut_chart(payment_labels, payment_values, 'Payment Distribution')
    img = MIMEImage(payment_chart.read(), _subtype='png')
    img.add_header('Content-ID', '<paymentChart>')
    img.add_header('Content-Disposition', 'inline', filename='payment_chart.png')
    msg.attach(img)

    # Service Chart
    service_labels = [item['service'] for item in analysis['serviceBreakdown']]
    service_values = [item['revenue'] for item in analysis['serviceBreakdown']]
    service_chart = plot_bar_chart(service_labels, service_values, 'Service Revenue', color='#f093fb')
    img = MIMEImage(service_chart.read(), _subtype='png')
    img.add_header('Content-ID', '<serviceChart>')
    img.add_header('Content-Disposition', 'inline', filename='service_chart.png')
    msg.attach(img)

    # Hourly Chart
    hourly_labels = [item['display'] for item in analysis['hourlyBreakdown']]
    hourly_values = [item['revenue'] for item in analysis['hourlyBreakdown']]
    hourly_chart = plot_bar_chart(hourly_labels, hourly_values, 'Hourly Revenue Trend', color='#4facfe')
    img = MIMEImage(hourly_chart.read(), _subtype='png')
    img.add_header('Content-ID', '<hourlyChart>')
    img.add_header('Content-Disposition', 'inline', filename='hourly_chart.png')
    msg.attach(img)

    # Vehicle Chart
    vehicle_labels = [item['type'] for item in analysis['vehicleDistribution']]
    vehicle_values = [item['count'] for item in analysis['vehicleDistribution']]
    vehicle_chart = plot_doughnut_chart(vehicle_labels, vehicle_values, 'Vehicle Distribution')
    img = MIMEImage(vehicle_chart.read(), _subtype='png')
    img.add_header('Content-ID', '<vehicleChart>')
    img.add_header('Content-Disposition', 'inline', filename='vehicle_chart.png')
    msg.attach(img)

    return msg
