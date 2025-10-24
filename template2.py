"""
Template 2: Enhanced Daily Report Email Template with CID Charts
Generates charts as images, attaches them as CIDs, and returns HTML ready for SES.
"""

import matplotlib
matplotlib.use('Agg')  # Non-GUI backend for server environments

from datetime import datetime
from typing import Dict, Any, List
import matplotlib.pyplot as plt
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def plot_bar_chart(labels: List[str], values: List[int], title: str, color: str = '#667eea') -> io.BytesIO:
    """Generate high-quality bar chart as BytesIO object"""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
    ax.bar(labels, values, color=color, edgecolor='white', linewidth=1.5)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    ax.set_ylabel('Revenue (₹)', fontsize=11, fontweight='bold')
    ax.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
    ax.set_axisbelow(True)
    plt.xticks(rotation=30, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    
    # Format y-axis with comma separators
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{int(x):,}'))
    
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100, facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf

def plot_doughnut_chart(labels: List[str], values: List[int], title: str, colors: List[str] = None) -> io.BytesIO:
    """Generate high-quality doughnut chart as BytesIO object"""
    fig, ax = plt.subplots(figsize=(7, 5), dpi=100)
    if colors is None:
        colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe']
    
    wedges, texts, autotexts = ax.pie(
        values, 
        labels=labels, 
        autopct='%1.1f%%',
        colors=colors, 
        startangle=90, 
        wedgeprops=dict(width=0.5, edgecolor='white', linewidth=2),
        textprops=dict(fontsize=10)
    )
    
    # Make percentage text bold and white
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(11)
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100, facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf

def generate_template2_email(analysis: Dict[str, Any], location_name: str, today_str: str) -> MIMEMultipart:
    """
    Returns MIMEMultipart email object ready to send via SES with CID charts.
    Uses multipart/related for inline images.
    """
    msg = MIMEMultipart('related')
    
    # Create HTML body with CID references
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f0f2f5; margin: 0; padding: 0;">
    <div style="max-width: 900px; margin: 20px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px 24px; text-align: center;">
            <h1 style="margin: 0; font-size: 32px; font-weight: 700;">📊 Daily Business Report</h1>
            <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.95;">📅 {today_str}</p>
            <p style="margin: 4px 0 0 0; font-size: 14px; opacity: 0.85;">📍 {location_name}</p>
        </div>
        
        <!-- Summary Stats -->
        <div style="padding: 32px 24px; background: #f8f9fa;">
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
                <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; border-top: 3px solid #667eea;">
                    <div style="color: #666; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Total Revenue</div>
                    <div style="color: #1a1a1a; font-size: 28px; font-weight: 700;">₹{analysis['totalRevenue']:,}</div>
                </div>
                <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; border-top: 3px solid #f093fb;">
                    <div style="color: #666; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Vehicles Served</div>
                    <div style="color: #1a1a1a; font-size: 28px; font-weight: 700;">{analysis['totalVehicles']}</div>
                </div>
                <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; border-top: 3px solid #4facfe;">
                    <div style="color: #666; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Avg Service</div>
                    <div style="color: #1a1a1a; font-size: 28px; font-weight: 700;">₹{round(analysis['avgService'])}</div>
                </div>
            </div>
        </div>
        
        <!-- Charts Section -->
        <div style="padding: 24px;">
            
            <!-- Payment Distribution -->
            <div style="margin-bottom: 32px;">
                <h2 style="color: #1a1a1a; font-size: 20px; margin: 0 0 16px 0; font-weight: 600;">💳 Payment Revenue Distribution</h2>
                <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; text-align: center;">
                    <img src="cid:paymentChart" style="max-width: 100%; height: auto; border-radius: 6px;" alt="Payment Distribution Chart"/>
                </div>
            </div>
            
            <!-- Service Performance -->
            <div style="margin-bottom: 32px;">
                <h2 style="color: #1a1a1a; font-size: 20px; margin: 0 0 16px 0; font-weight: 600;">🛠️ Service Performance</h2>
                <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; text-align: center;">
                    <img src="cid:serviceChart" style="max-width: 100%; height: auto; border-radius: 6px;" alt="Service Performance Chart"/>
                </div>
            </div>
            
            <!-- Two Column Layout -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 32px;">
                
                <!-- Vehicle Distribution -->
                <div>
                    <h2 style="color: #1a1a1a; font-size: 20px; margin: 0 0 16px 0; font-weight: 600;">🚗 Vehicle Types</h2>
                    <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; text-align: center;">
                        <img src="cid:vehicleChart" style="max-width: 100%; height: auto; border-radius: 6px;" alt="Vehicle Distribution Chart"/>
                    </div>
                </div>
                
                <!-- Hourly Performance -->
                <div>
                    <h2 style="color: #1a1a1a; font-size: 20px; margin: 0 0 16px 0; font-weight: 600;">⏰ Hourly Trend</h2>
                    <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; text-align: center;">
                        <img src="cid:hourlyChart" style="max-width: 100%; height: auto; border-radius: 6px;" alt="Hourly Performance Chart"/>
                    </div>
                </div>
                
            </div>
            
            <!-- Info Box -->
            <div style="background: #e3f2fd; border-left: 4px solid #2196f3; padding: 16px; border-radius: 4px;">
                <p style="margin: 0; color: #1565c0; font-size: 14px;">
                    📎 <strong>Attachments:</strong> This email includes 3 CSV files with detailed transaction data, payment breakdowns, and service analysis.
                </p>
            </div>
            
        </div>
        
        <!-- Footer -->
        <div style="background: #f8f9fa; padding: 20px 24px; text-align: center; border-top: 1px solid #dee2e6;">
            <p style="margin: 0; color: #6c757d; font-size: 12px;">
                Report generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}
            </p>
        </div>
        
    </div>
</body>
</html>
    """
    
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # Generate and attach charts as CIDs
    try:
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
        
        # Hourly Performance Chart (smaller data set)
        hourly_labels = [item['display'] for item in analysis['hourlyBreakdown'][:12]]  # Limit to prevent overcrowding
        hourly_values = [item['amount'] for item in analysis['hourlyBreakdown'][:12]]
        hourly_chart = plot_bar_chart(hourly_labels, hourly_values, 'Hourly Revenue', color='#4facfe')
        img = MIMEImage(hourly_chart.read(), _subtype='png')
        img.add_header('Content-ID', '<hourlyChart>')
        img.add_header('Content-Disposition', 'inline', filename='hourly_chart.png')
        msg.attach(img)
        
    except Exception as e:
        # Log error but don't fail - return message without charts
        print(f"Warning: Failed to generate charts: {e}")
    
    return msg