"""
Template 3: Modern Business Intelligence Report with CID Charts
Generates BI-style charts as images and embeds them in the email via CID.
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
    """Generate high-quality bar chart"""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
    bars = ax.bar(labels, values, color=color, edgecolor='white', linewidth=2)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    ax.set_ylabel('Revenue (₹)', fontsize=11, fontweight='bold')
    ax.grid(axis='y', linestyle='--', alpha=0.3, zorder=0)
    ax.set_axisbelow(True)
    plt.xticks(rotation=30, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'₹{int(height):,}',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Format y-axis
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{int(x):,}'))
    
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100, facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf

def plot_doughnut_chart(labels: List[str], values: List[int], title: str, colors: List[str] = None) -> io.BytesIO:
    """Generate high-quality doughnut chart"""
    fig, ax = plt.subplots(figsize=(7, 5), dpi=100)
    if colors is None:
        colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#ff6b6b', '#feca57']
    
    # Create pie chart
    wedges, texts, autotexts = ax.pie(
        values, 
        labels=labels, 
        autopct='%1.1f%%',
        colors=colors, 
        startangle=90, 
        wedgeprops=dict(width=0.5, edgecolor='white', linewidth=3),
        textprops=dict(fontsize=10, fontweight='bold')
    )
    
    # Style percentage text
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

def generate_template3_email(analysis: Dict[str, Any], location_name: str, today_str: str) -> MIMEMultipart:
    """
    Returns MIMEMultipart email object for Template 3 with all charts embedded via CID.
    Professional Business Intelligence style.
    """
    msg = MIMEMultipart('related')

    peak_hour = analysis['summary']['peakHour']
    peak_revenue = analysis['summary']['peakHourRevenue']
    top_service = analysis['insights']['topService']
    top_service_revenue = analysis['insights']['topServiceRevenue']

    # HTML with modern BI styling and CID placeholders
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f7fa; margin:0; padding:0;">
    <div style="max-width: 1200px; margin: 0 auto; padding: 20px;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 32px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h1 style="margin: 0; font-size: 32px; font-weight: 700;">📈 Business Intelligence Report</h1>
                    <p style="margin: 12px 0 0 0; font-size: 18px; opacity: 0.95; font-weight: 500;">{today_str} • {location_name}</p>
                </div>
            </div>
        </div>

        <!-- KPI Dashboard -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
            
            <div style="background: white; padding: 24px; border-radius: 12px; border-left: 4px solid #667eea; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
                <div style="color: #6c757d; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-bottom: 8px;">TOTAL REVENUE</div>
                <div style="color: #1a1a1a; font-size: 32px; font-weight: 700; line-height: 1;">₹{analysis['totalRevenue']:,}</div>
                <div style="color: #28a745; font-size: 12px; margin-top: 8px; font-weight: 600;">↗ Daily Total</div>
            </div>
            
            <div style="background: white; padding: 24px; border-radius: 12px; border-left: 4px solid #f093fb; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
                <div style="color: #6c757d; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-bottom: 8px;">TRANSACTIONS</div>
                <div style="color: #1a1a1a; font-size: 32px; font-weight: 700; line-height: 1;">{analysis['totalVehicles']}</div>
                <div style="color: #6c757d; font-size: 12px; margin-top: 8px; font-weight: 600;">Total Count</div>
            </div>
            
            <div style="background: white; padding: 24px; border-radius: 12px; border-left: 4px solid #4facfe; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
                <div style="color: #6c757d; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-bottom: 8px;">AVG TRANSACTION</div>
                <div style="color: #1a1a1a; font-size: 32px; font-weight: 700; line-height: 1;">₹{round(analysis['avgService'])}</div>
                <div style="color: #6c757d; font-size: 12px; margin-top: 8px; font-weight: 600;">Per Service</div>
            </div>
            
            <div style="background: white; padding: 24px; border-radius: 12px; border-left: 4px solid #43e97b; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
                <div style="color: #6c757d; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-bottom: 8px;">PEAK HOUR</div>
                <div style="color: #1a1a1a; font-size: 32px; font-weight: 700; line-height: 1;">{peak_hour}</div>
                <div style="color: #6c757d; font-size: 12px; margin-top: 8px; font-weight: 600;">₹{peak_revenue:,}</div>
            </div>
            
        </div>

        <!-- Charts Grid -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            
            <!-- Payment Distribution -->
            <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
                <h3 style="margin: 0 0 20px 0; font-size: 18px; color: #1a1a1a; font-weight: 600; display: flex; align-items: center;">
                    <span style="background: #667eea; width: 4px; height: 20px; display: inline-block; margin-right: 12px; border-radius: 2px;"></span>
                    Payment Distribution
                </h3>
                <div style="text-align: center;">
                    <img src="cid:paymentChart" style="max-width: 100%; height: auto; border-radius: 8px;" alt="Payment Distribution"/>
                </div>
            </div>
            
            <!-- Service Revenue -->
            <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
                <h3 style="margin: 0 0 20px 0; font-size: 18px; color: #1a1a1a; font-weight: 600; display: flex; align-items: center;">
                    <span style="background: #f093fb; width: 4px; height: 20px; display: inline-block; margin-right: 12px; border-radius: 2px;"></span>
                    Service Revenue
                </h3>
                <div style="text-align: center;">
                    <img src="cid:serviceChart" style="max-width: 100%; height: auto; border-radius: 8px;" alt="Service Revenue"/>
                </div>
            </div>
            
        </div>

        <!-- Full Width Hourly Chart -->
        <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); margin-bottom: 20px;">
            <h3 style="margin: 0 0 20px 0; font-size: 18px; color: #1a1a1a; font-weight: 600; display: flex; align-items: center;">
                <span style="background: #4facfe; width: 4px; height: 20px; display: inline-block; margin-right: 12px; border-radius: 2px;"></span>
                Hourly Revenue Trend
            </h3>
            <div style="text-align: center;">
                <img src="cid:hourlyChart" style="max-width: 100%; height: auto; border-radius: 8px;" alt="Hourly Revenue"/>
            </div>
        </div>

        <!-- Bottom Grid -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            
            <!-- Vehicle Distribution -->
            <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
                <h3 style="margin: 0 0 20px 0; font-size: 18px; color: #1a1a1a; font-weight: 600; display: flex; align-items: center;">
                    <span style="background: #43e97b; width: 4px; height: 20px; display: inline-block; margin-right: 12px; border-radius: 2px;"></span>
                    Vehicle Distribution
                </h3>
                <div style="text-align: center;">
                    <img src="cid:vehicleChart" style="max-width: 100%; height: auto; border-radius: 8px;" alt="Vehicle Distribution"/>
                </div>
            </div>
            
            <!-- Top Performer Card -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 24px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); color: white;">
                <h3 style="margin: 0 0 20px 0; font-size: 18px; font-weight: 600; opacity: 0.9;">🏆 Top Performer</h3>
                <div style="text-align: center; padding: 30px 0;">
                    <div style="font-size: 48px; font-weight: 700; margin-bottom: 16px; line-height: 1;">{top_service}</div>
                    <div style="font-size: 28px; font-weight: 600; opacity: 0.95;">₹{top_service_revenue:,}</div>
                    <div style="font-size: 14px; margin-top: 12px; opacity: 0.8;">Highest Revenue Service</div>
                </div>
            </div>
            
        </div>

        <!-- Insights Banner -->
        <div style="background: linear-gradient(to right, #e3f2fd, #fff3e0); padding: 24px; border-radius: 12px; border: 2px solid #2196f3; margin-bottom: 20px;">
            <h3 style="margin: 0 0 16px 0; font-size: 18px; color: #1a1a1a; font-weight: 600;">💡 Key Insights</h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
                <div>
                    <div style="color: #666; font-size: 12px; margin-bottom: 4px;">Peak Performance</div>
                    <div style="color: #1a1a1a; font-size: 16px; font-weight: 600;">{peak_hour} generated ₹{peak_revenue:,}</div>
                </div>
                <div>
                    <div style="color: #666; font-size: 12px; margin-bottom: 4px;">Top Service</div>
                    <div style="color: #1a1a1a; font-size: 16px; font-weight: 600;">{top_service} leads with ₹{top_service_revenue:,}</div>
                </div>
                <div>
                    <div style="color: #666; font-size: 12px; margin-bottom: 4px;">Active Hours</div>
                    <div style="color: #1a1a1a; font-size: 16px; font-weight: 600;">{analysis['insights']['busyHours']} hours operational</div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div style="background: white; padding: 24px; border-radius: 12px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
            <p style="margin: 0 0 8px 0; color: #6c757d; font-size: 13px;">
                📎 This report includes 3 CSV attachments with detailed analytics
            </p>
            <p style="margin: 0; color: #adb5bd; font-size: 12px;">
                Report generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")} • Powered by Business Intelligence System
            </p>
        </div>

    </div>
</body>
</html>
    """

    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    # Generate and attach charts as CIDs
    try:
        # Payment Distribution Chart (Doughnut)
        payment_labels = [item['mode'] for item in analysis['paymentModeBreakdown']]
        payment_values = [item['revenue'] for item in analysis['paymentModeBreakdown']]
        payment_chart = plot_doughnut_chart(payment_labels, payment_values, 'Payment Distribution')
        img = MIMEImage(payment_chart.read(), _subtype='png')
        img.add_header('Content-ID', '<paymentChart>')
        img.add_header('Content-Disposition', 'inline', filename='payment_chart.png')
        msg.attach(img)

        # Service Revenue Chart (Bar)
        service_labels = [item['service'] for item in analysis['serviceBreakdown']]
        service_values = [item['revenue'] for item in analysis['serviceBreakdown']]
        service_chart = plot_bar_chart(service_labels, service_values, 'Service Revenue', color='#f093fb')
        img = MIMEImage(service_chart.read(), _subtype='png')
        img.add_header('Content-ID', '<serviceChart>')
        img.add_header('Content-Disposition', 'inline', filename='service_chart.png')
        msg.attach(img)

        # Hourly Revenue Chart (Bar)
        hourly_labels = [item['display'] for item in analysis['hourlyBreakdown']]
        hourly_values = [item['revenue'] for item in analysis['hourlyBreakdown']]
        hourly_chart = plot_bar_chart(hourly_labels, hourly_values, 'Hourly Revenue Trend', color='#4facfe')
        img = MIMEImage(hourly_chart.read(), _subtype='png')
        img.add_header('Content-ID', '<hourlyChart>')
        img.add_header('Content-Disposition', 'inline', filename='hourly_chart.png')
        msg.attach(img)

        # Vehicle Distribution Chart (Doughnut)
        vehicle_labels = [item['type'] for item in analysis['vehicleDistribution']]
        vehicle_values = [item['count'] for item in analysis['vehicleDistribution']]
        vehicle_chart = plot_doughnut_chart(vehicle_labels, vehicle_values, 'Vehicle Distribution')
        img = MIMEImage(vehicle_chart.read(), _subtype='png')
        img.add_header('Content-ID', '<vehicleChart>')
        img.add_header('Content-Disposition', 'inline', filename='vehicle_chart.png')
        msg.attach(img)

    except Exception as e:
        # Log error but don't fail the email send
        print(f"Warning: Failed to generate charts for Template 3: {e}")

    return msg