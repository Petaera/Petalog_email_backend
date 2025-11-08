"""
Daily Reports Email Service
Converts Supabase Edge Function to Python Flask server
Works locally and on Render
Uses AWS SES API instead of SMTP
Sends reports to scheduled users with their specific templates and timezones
ENHANCED: Multi-location support + User-specific scheduling
"""

from flask import Flask, request, jsonify
from supabase import create_client, Client
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import os
import re
from typing import List, Dict, Any, Optional
import logging
import pytz

# Initialize Supabase client with custom options
from supabase.lib.client_options import ClientOptions

# Import template generators
from template1 import generate_template1_html
# template2/3 return MIMEMultipart objects named generate_templateX_email; import and alias to keep main's naming
from template2 import generate_template2_email as generate_template2_html
from template3 import generate_template3_email as generate_template3_html

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CONFIGURATION VARIABLES
load_dotenv()
TEST_EMAIL = os.getenv("TEST_EMAIL")
TEMPLATE_NO = int(os.getenv("TEMPLATE_NO", "1"))

# Create client options
options = ClientOptions(
    schema="public",
    headers={},
    auto_refresh_token=True,
    persist_session=True,
)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

# Initialize AWS SES client
ses_client = None

def get_ses_client():
    """Initialize and return SES client"""
    global ses_client
    if ses_client is None:
        ses_client = boto3.client(
            'ses',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
    return ses_client


def get_owner_display_name(owner: Dict[str, Any]) -> str:
    """Return a display name for an owner using first_name/last_name, fallback to name, email, or id."""
    if not owner:
        return 'Unknown'
    first = (owner.get('first_name') or '').strip()
    last = (owner.get('last_name') or '').strip()
    if first or last:
        return f"{first} {last}".strip()
    # Backwards compatibility if `name` exists
    if owner.get('name'):
        return owner.get('name')
    return owner.get('email') or owner.get('id') or 'Unknown'


def get_owner_locations(owner: Dict[str, Any], locations: List[Dict[str, Any]]) -> List[str]:
    """
    Get all location IDs assigned to an owner.
    Handles both single location (string) and multiple locations (comma-separated or array).
    """
    assigned = owner.get('assigned_location')
    
    if not assigned:
        # If no assignment, owner sees all locations
        return [loc['id'] for loc in locations]
    
    # Handle array format
    if isinstance(assigned, list):
        return assigned
    
    # Handle comma-separated string format
    if isinstance(assigned, str):
        if ',' in assigned:
            return [loc.strip() for loc in assigned.split(',')]
        else:
            return [assigned]
    
    return []


def escape_csv(value: Any) -> str:
    """Escape CSV values properly"""
    if value is None or value == "":
        return ""
    
    str_value = str(value).strip()
    
    if re.search(r'[,"\n\r]', str_value):
        escaped = str_value.replace('"', '""').replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
        return f'"{escaped}"'
    
    return str_value


def generate_no_data_email_html(location_names: str, today_str: str, test_email: Optional[str]) -> MIMEMultipart:
    """Generate HTML for no-data notification email"""
    test_banner = f"""
    <div style="background-color: #ff9800; color: white; padding: 12px 24px; text-align: center; font-weight: bold;">
      TEST MODE - This is a test email
    </div>
    """ if test_email else ""
    
    test_footer = f'<p style="margin: 8px 0 0 0; color: #ff9800; font-size: 12px; font-weight: bold;">Test email sent to: {test_email}</p>' if test_email else ""
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>No Data Report</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
  <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    
    {test_banner}
    
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px 24px; text-align: center;">
      <h1 style="margin: 0; font-size: 32px; font-weight: 600;">📊 Daily Business Report</h1>
      <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">{today_str}</p>
      <p style="margin: 4px 0 0 0; font-size: 14px; opacity: 0.8;">📍 {location_names}</p>
    </div>
    
    <div style="padding: 32px 24px;">
      
      <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); padding: 32px 24px; border-radius: 12px; margin-bottom: 24px; border: 2px solid #ff9800; text-align: center;">
        <div style="font-size: 64px; margin-bottom: 16px;">📭</div>
        <h2 style="margin: 0 0 12px 0; font-size: 24px; color: #e65100;">No Data Available</h2>
        <p style="margin: 0; color: #bf360c; font-size: 16px; line-height: 1.6;">
          No approved transactions were recorded for today across your assigned locations.
        </p>
      </div>
      
      <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; margin-top: 20px;">
        <p style="margin: 0; color: #666; font-size: 14px; line-height: 1.6;">
          <strong>Locations Checked:</strong> {location_names}<br>
          <strong>Status:</strong> No approved transactions found for {today_str}
        </p>
      </div>
      
    </div>
    
    <div style="background-color: #f8f9fa; padding: 20px 24px; border-top: 1px solid #e9ecef; text-align: center;">
      <p style="margin: 0; color: #6c757d; font-size: 12px;">
        Report generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}
      </p>
      {test_footer}
    </div>
    
  </div>
</body>
</html>
    """.strip()
    
    # Wrap in MIME message
    msg = MIMEMultipart('related')
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    return msg


def fetch_today_filtered_logs(location_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch today's filtered logs using database-level filtering"""
    logger.info(f"Fetching today's logs for location: {location_id or 'All locations'}")
    
    query = supabase.table('logs-man').select('*')
    query = query.eq('approval_status', 'approved')
    
    if location_id:
        query = query.eq('location_id', location_id)
    
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)
    start_of_day = today.isoformat()
    end_of_day = (today + timedelta(days=1)).isoformat()
    
    query = query.gte('created_at', start_of_day).lt('created_at', end_of_day)
    
    logger.info(f"Filtering for date range: {start_of_day} to {end_of_day}")
    
    response = query.execute()
    
    if hasattr(response, 'error') and response.error:
        logger.error(f'Error fetching filtered logs: {response.error}')
        raise Exception(f"Failed to fetch logs: {response.error}")
    
    logs = response.data or []
    logger.info(f"Found {len(logs)} approved logs for today")
    
    return logs


def analyze_data(logs: List[Dict[str, Any]], locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate comprehensive data analysis"""
    logger.info(f"Analyzing {len(logs)} log entries...")
    
    total_revenue = sum(log.get('Amount', 0) for log in logs)
    total_vehicles = len(logs)
    avg_service = total_revenue / total_vehicles if total_vehicles > 0 else 0
    
    logger.info(f"Analysis summary: ₹{total_revenue} revenue, {total_vehicles} vehicles, ₹{avg_service:.2f} avg")
    
    # Payment mode breakdown
    payment_mode_breakdown = {}
    for log in logs:
        payment_mode = log.get('payment_mode', 'Cash')
        normalized_mode = payment_mode.lower()
        
        if normalized_mode not in payment_mode_breakdown:
            payment_mode_breakdown[normalized_mode] = {
                'mode': payment_mode,
                'displayName': payment_mode,
                'count': 0,
                'transactions': 0,
                'revenue': 0,
                'percentage': 0,
                'upiAccounts': {},
                'details': {}
            }
        
        payment_mode_breakdown[normalized_mode]['count'] += 1
        payment_mode_breakdown[normalized_mode]['transactions'] += 1
        payment_mode_breakdown[normalized_mode]['revenue'] += log.get('Amount', 0)
        
        if normalized_mode == 'upi' and log.get('upi_account_name'):
            account_name = log['upi_account_name']
            if account_name not in payment_mode_breakdown[normalized_mode]['upiAccounts']:
                payment_mode_breakdown[normalized_mode]['upiAccounts'][account_name] = {
                    'count': 0,
                    'amount': 0
                }
                payment_mode_breakdown[normalized_mode]['details'][account_name] = {
                    'count': 0,
                    'amount': 0
                }
            
            payment_mode_breakdown[normalized_mode]['upiAccounts'][account_name]['count'] += 1
            payment_mode_breakdown[normalized_mode]['upiAccounts'][account_name]['amount'] += log.get('Amount', 0)
            payment_mode_breakdown[normalized_mode]['details'][account_name]['count'] += 1
            payment_mode_breakdown[normalized_mode]['details'][account_name]['amount'] += log.get('Amount', 0)
    
    for payment in payment_mode_breakdown.values():
        payment['percentage'] = (payment['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
    
    # Service breakdown
    service_breakdown = {}
    for log in logs:
        service = log.get('service', 'Unknown')
        if service not in service_breakdown:
            service_breakdown[service] = {
                'service': service,
                'name': service,
                'count': 0,
                'revenue': 0,
                'price': 0,
                'averagePrice': 0,
                'revenueShare': 0
            }
        
        service_breakdown[service]['count'] += 1
        service_breakdown[service]['revenue'] += log.get('Amount', 0)
        service_breakdown[service]['price'] = service_breakdown[service]['revenue'] / service_breakdown[service]['count']
        service_breakdown[service]['averagePrice'] = service_breakdown[service]['price']
    
    for service in service_breakdown.values():
        service['revenueShare'] = (service['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
    
    # Vehicle type distribution
    vehicle_distribution = {}
    for log in logs:
        vtype = log.get('vehicle_type', 'Unknown')
        if vtype not in vehicle_distribution:
            vehicle_distribution[vtype] = {
                'type': vtype,
                'count': 0,
                'percentage': 0
            }
        vehicle_distribution[vtype]['count'] += 1
    
    for vehicle in vehicle_distribution.values():
        vehicle['percentage'] = (vehicle['count'] / total_vehicles * 100) if total_vehicles > 0 else 0
    
    # Hourly breakdown
    hourly_breakdown = []
    for i in range(24):
        hour_12 = 12 if i % 12 == 0 else i % 12
        period = 'AM' if i < 12 else 'PM'
        hourly_breakdown.append({
            'hour': i,
            'label': f"{hour_12:02d} {period}",
            'period': period,
            'display': f"{hour_12}:00 {period}",
            'amount': 0,
            'count': 0,
            'transactions': 0,
            'revenue': 0
        })
    
    for log in logs:
        created = datetime.fromisoformat(log['created_at'].replace('Z', '+00:00'))
        hour = created.hour
        hourly_breakdown[hour]['amount'] += log.get('Amount', 0)
        hourly_breakdown[hour]['count'] += 1
        hourly_breakdown[hour]['transactions'] += 1
        hourly_breakdown[hour]['revenue'] += log.get('Amount', 0)
    
    peak_hour = max(hourly_breakdown, key=lambda x: x['revenue'])
    service_list = list(service_breakdown.values())
    peak_service = max(service_list, key=lambda x: x['revenue']) if service_list else {'name': 'N/A', 'revenue': 0}
    
    payment_mode_breakdown_array = list(payment_mode_breakdown.values())
    service_breakdown_array = sorted(service_breakdown.values(), key=lambda x: x['revenue'], reverse=True)
    vehicle_distribution_array = sorted(vehicle_distribution.values(), key=lambda x: x['count'], reverse=True)
    hourly_breakdown_filtered = [h for h in hourly_breakdown if h['count'] > 0 or h['amount'] > 0]
    
    return {
        'totalRevenue': total_revenue,
        'totalVehicles': total_vehicles,
        'avgService': avg_service,
        'paymentModeBreakdown': payment_mode_breakdown_array,
        'serviceBreakdown': service_breakdown_array,
        'vehicleDistribution': vehicle_distribution_array,
        'hourlyBreakdown': hourly_breakdown_filtered,
        'summary': {
            'totalRevenue': total_revenue,
            'totalTransactions': total_vehicles,
            'averageTransaction': avg_service,
            'peakHour': peak_hour['display'],
            'peakHourRevenue': peak_hour['revenue']
        },
        'payments': payment_mode_breakdown_array,
        'services': service_breakdown_array,
        'vehicles': vehicle_distribution_array,
        'hourlyData': hourly_breakdown_filtered,
        'insights': {
            'topService': peak_service['name'],
            'topServiceRevenue': peak_service['revenue'],
            'busyHours': len(hourly_breakdown_filtered)
        }
    }


def generate_report_csv(logs: List[Dict[str, Any]], locations: List[Dict[str, Any]]) -> str:
    """Generate main report CSV"""
    logger.info(f"Generating main report CSV for {len(logs)} logs...")
    
    rows = []
    for log in logs:
        location_name = "Unknown"
        for loc in locations:
            if loc['id'] == log.get('location_id'):
                location_name = loc['name']
                break
        
        rows.append({
            "Vehicle Number": escape_csv(log.get('vehicle_number')),
            "Owner Name": escape_csv(log.get('Name')),
            "Phone": escape_csv(log.get('Phone_no')),
            "Vehicle Model": escape_csv(log.get('vehicle_model')),
            "Service Type": escape_csv(log.get('service')),
            "Price": escape_csv(log.get('Amount')),
            "Payment Mode": escape_csv(log.get('payment_mode')),
            "UPI Account": escape_csv(log.get('upi_account_name')),
            "Entry Type": escape_csv(log.get('entry_type')),
            "Date": escape_csv(datetime.fromisoformat(log['created_at'].replace('Z', '+00:00')).strftime("%d/%m/%Y %H:%M")),
            "Location": escape_csv(location_name)
        })
    
    if not rows:
        return ""
    
    headers = list(rows[0].keys())
    csv_lines = [",".join(headers)]
    
    for row in rows:
        csv_lines.append(",".join(str(row[h]) for h in headers))
    
    return "\n".join(csv_lines)


def generate_payment_breakdown_csv(logs: List[Dict[str, Any]]) -> str:
    """Generate payment breakdown CSV"""
    logger.info("Generating payment breakdown CSV...")
    
    analysis = analyze_data(logs, [])
    
    rows = []
    for item in analysis['paymentModeBreakdown']:
        upi_accounts = 'N/A'
        if item['mode'].lower() == 'upi' and item.get('upiAccounts'):
            accounts = []
            for account_name, account_data in item['upiAccounts'].items():
                accounts.append(f"{account_name}: ₹{account_data['amount']} ({account_data['count']} vehicles)")
            upi_accounts = '; '.join(accounts)
        
        rows.append({
            "Payment Mode": escape_csv(item['mode']),
            "Total Revenue": escape_csv(item['revenue']),
            "Vehicle Count": escape_csv(item['count']),
            "Percentage of Total": escape_csv(f"{item['percentage']:.1f}%"),
            "UPI Accounts": escape_csv(upi_accounts)
        })
    
    if not rows:
        return ""
    
    headers = list(rows[0].keys())
    csv_lines = [",".join(headers)]
    
    for row in rows:
        csv_lines.append(",".join(str(row[h]) for h in headers))
    
    return "\n".join(csv_lines)


def generate_service_breakdown_csv(logs: List[Dict[str, Any]]) -> str:
    """Generate service breakdown CSV"""
    logger.info("Generating service breakdown CSV...")
    
    analysis = analyze_data(logs, [])
    
    rows = []
    for item in analysis['serviceBreakdown']:
        percentage = (item['revenue'] / analysis['totalRevenue'] * 100) if analysis['totalRevenue'] > 0 else 0
        rows.append({
            "Service Type": escape_csv(item['service']),
            "Total Revenue": escape_csv(item['revenue']),
            "Vehicle Count": escape_csv(item['count']),
            "Average Price": escape_csv(round(item['price'])),
            "Percentage of Revenue": escape_csv(f"{percentage:.1f}%")
        })
    
    if not rows:
        return ""
    
    headers = list(rows[0].keys())
    csv_lines = [",".join(headers)]
    
    for row in rows:
        csv_lines.append(",".join(str(row[h]) for h in headers))
    
    return "\n".join(csv_lines)


def generate_email_html(analysis: Dict[str, Any], location_name: str, today_str: str,
                       template_no: int):
    """Generate email content using selected template.

    Returns a MIMEMultipart object (so CID images are preserved). For templates
    that only return HTML (template1), we wrap the HTML into a related multipart.
    """
    # Template 2 and 3 already return a MIMEMultipart (related) object
    if template_no == 3:
        return generate_template3_html(analysis, location_name, today_str)
    elif template_no == 2:
        return generate_template2_html(analysis, location_name, today_str)

    # Template 1 returns an HTML string; wrap it into a MIMEMultipart
    html = generate_template1_html(analysis, location_name, today_str)
    msg = MIMEMultipart('related')
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    return msg


def generate_multi_location_report_html(location_data: Dict[str, Dict[str, Any]], 
                                       locations: List[Dict[str, Any]], 
                                       today_str: str, 
                                       template_no: int) -> MIMEMultipart:
    """Generate multi-location report HTML"""
    
    # Calculate totals
    total_revenue = sum(data['analysis']['totalRevenue'] for data in location_data.values())
    total_vehicles = sum(data['analysis']['totalVehicles'] for data in location_data.values())
    total_locations = len(location_data)
    avg_per_location = total_revenue / total_locations if total_locations > 0 else 0
    
    # Generate location comparison table rows
    location_rows = ""
    for data in location_data.values():
        location_rows += f"""
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e9ecef; font-size: 13px;">{data['location_name']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e9ecef; text-align: right; font-weight: 600; font-size: 13px;">₹{data['analysis']['totalRevenue']:,}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e9ecef; text-align: center; font-size: 13px;">{data['analysis']['totalVehicles']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e9ecef; text-align: right; font-size: 13px;">{(data['analysis']['totalRevenue']/total_revenue*100):.1f}%</td>
              </tr>
              """
    
    # Generate individual location sections using template functions
    location_sections = []
    for location_id, data in location_data.items():
        analysis = data['analysis']
        location_name = data['location_name']
        
        # Use the appropriate template for each location
        if template_no == 3:
            location_html = generate_template3_html(analysis, location_name, today_str)
            # Extract HTML from MIMEMultipart if needed
            if isinstance(location_html, MIMEMultipart):
                # For multi-location, we'll create a simplified section
                location_sections.append(f"""
        <div style="margin-bottom: 32px; padding: 24px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">
          <h3 style="margin: 0 0 16px 0; font-size: 20px; color: #333;">📍 {location_name}</h3>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
            <div style="background: white; padding: 16px; border-radius: 8px; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #666;">Total Revenue</p>
              <h4 style="margin: 8px 0 0 0; font-size: 24px; font-weight: 700; color: #667eea;">₹{analysis['totalRevenue']:,}</h4>
            </div>
            <div style="background: white; padding: 16px; border-radius: 8px; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #666;">Vehicles</p>
              <h4 style="margin: 8px 0 0 0; font-size: 24px; font-weight: 700; color: #f093fb;">{analysis['totalVehicles']}</h4>
            </div>
            <div style="background: white; padding: 16px; border-radius: 8px; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #666;">Avg Service</p>
              <h4 style="margin: 8px 0 0 0; font-size: 24px; font-weight: 700; color: #4facfe;">₹{round(analysis['avgService'])}</h4>
            </div>
          </div>
        </div>
                """)
            else:
                location_sections.append(location_html)
        elif template_no == 2:
            location_html = generate_template2_html(analysis, location_name, today_str)
            # Simplified section for multi-location
            location_sections.append(f"""
        <div style="margin-bottom: 32px; padding: 24px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">
          <h3 style="margin: 0 0 16px 0; font-size: 20px; color: #333;">📍 {location_name}</h3>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
            <div style="background: white; padding: 16px; border-radius: 8px; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #666;">Total Revenue</p>
              <h4 style="margin: 8px 0 0 0; font-size: 24px; font-weight: 700; color: #667eea;">₹{analysis['totalRevenue']:,}</h4>
            </div>
            <div style="background: white; padding: 16px; border-radius: 8px; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #666;">Vehicles</p>
              <h4 style="margin: 8px 0 0 0; font-size: 24px; font-weight: 700; color: #f093fb;">{analysis['totalVehicles']}</h4>
            </div>
            <div style="background: white; padding: 16px; border-radius: 8px; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #666;">Avg Service</p>
              <h4 style="margin: 8px 0 0 0; font-size: 24px; font-weight: 700; color: #4facfe;">₹{round(analysis['avgService'])}</h4>
            </div>
          </div>
        </div>
                """)
        else:
            # Template 1 - use the HTML string directly
            location_html_str = generate_template1_html(analysis, location_name, today_str)
            # Extract just the content section from template1
            location_sections.append(f"""
        <div style="margin-bottom: 32px; padding: 24px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">
          <h3 style="margin: 0 0 16px 0; font-size: 20px; color: #333;">📍 {location_name}</h3>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
            <div style="background: white; padding: 16px; border-radius: 8px; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #666;">Total Revenue</p>
              <h4 style="margin: 8px 0 0 0; font-size: 24px; font-weight: 700; color: #667eea;">₹{analysis['totalRevenue']:,}</h4>
            </div>
            <div style="background: white; padding: 16px; border-radius: 8px; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #666;">Vehicles</p>
              <h4 style="margin: 8px 0 0 0; font-size: 24px; font-weight: 700; color: #f093fb;">{analysis['totalVehicles']}</h4>
            </div>
            <div style="background: white; padding: 16px; border-radius: 8px; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #666;">Avg Service</p>
              <h4 style="margin: 8px 0 0 0; font-size: 24px; font-weight: 700; color: #4facfe;">₹{round(analysis['avgService'])}</h4>
            </div>
          </div>
        </div>
                """)
    
    location_sections_html = ''.join(location_sections)
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Multi-Location Business Report</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
  <div style="max-width: 900px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px 24px; text-align: center;">
      <h1 style="margin: 0; font-size: 32px; font-weight: 600;">📊 Multi-Location Business Report</h1>
      <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">{today_str}</p>
      <p style="margin: 4px 0 0 0; font-size: 14px; opacity: 0.8;">🏢 {total_locations} Locations</p>
    </div>
    
    <div style="padding: 32px 24px;">
      
      <!-- Consolidated Summary -->
      <div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); padding: 24px; border-radius: 12px; margin-bottom: 32px; border: 2px solid #4caf50;">
        <h2 style="margin: 0 0 16px 0; font-size: 22px; color: #2e7d32; text-align: center;">📈 Consolidated Summary</h2>
        
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
          <div style="background: white; padding: 16px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase;">Total Revenue</p>
            <h3 style="margin: 6px 0 0 0; font-size: 26px; font-weight: 700; color: #2e7d32;">₹{total_revenue:,}</h3>
          </div>
          <div style="background: white; padding: 16px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase;">Total Vehicles</p>
            <h3 style="margin: 6px 0 0 0; font-size: 26px; font-weight: 700; color: #2e7d32;">{total_vehicles}</h3>
          </div>
          <div style="background: white; padding: 16px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase;">Locations</p>
            <h3 style="margin: 6px 0 0 0; font-size: 26px; font-weight: 700; color: #2e7d32;">{total_locations}</h3>
          </div>
          <div style="background: white; padding: 16px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase;">Avg/Location</p>
            <h3 style="margin: 6px 0 0 0; font-size: 26px; font-weight: 700; color: #2e7d32;">₹{round(avg_per_location):,}</h3>
          </div>
        </div>
        
        <!-- Location Performance Comparison -->
        <div style="margin-top: 20px; background: white; padding: 16px; border-radius: 8px;">
          <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #333;">Location Performance Comparison</h3>
          <table style="width: 100%; border-collapse: collapse;">
            <thead>
              <tr style="background-color: #f5f5f5;">
                <th style="padding: 8px; text-align: left; font-size: 12px; border-bottom: 1px solid #ddd;">Location</th>
                <th style="padding: 8px; text-align: right; font-size: 12px; border-bottom: 1px solid #ddd;">Revenue</th>
                <th style="padding: 8px; text-align: center; font-size: 12px; border-bottom: 1px solid #ddd;">Vehicles</th>
                <th style="padding: 8px; text-align: right; font-size: 12px; border-bottom: 1px solid #ddd;">% of Total</th>
              </tr>
            </thead>
            <tbody>
              {location_rows}
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- Individual Location Reports -->
      <h2 style="color: #333; font-size: 24px; margin: 0 0 20px 0; text-align: center; border-bottom: 2px solid #667eea; padding-bottom: 12px;">📍 Location-wise Detailed Reports</h2>
      
      {location_sections_html}
      
      <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; margin-top: 20px;">
        <p style="margin: 0; color: #666; font-size: 14px;">
          🔎 This email includes separate CSV attachments for each location with detailed transaction data, payment breakdowns, and service analysis.
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
    
    msg = MIMEMultipart('related')
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    return msg


def generate_summary_report_html(summary_data: Dict[str, Any], today_str: str) -> str:
    """Generate HTML for admin summary report"""
    
    success_count = summary_data.get('successCount', 0)
    failed_count = summary_data.get('failedCount', 0)
    skipped_count = summary_data.get('skippedCount', 0)
    total_count = summary_data.get('totalCount', 0)
    total_revenue = summary_data.get('totalRevenue', 0)
    total_records = summary_data.get('totalRecords', 0)
    results = summary_data.get('results', [])
    
    # Calculate success rate (avoid division by zero)
    success_rate = (success_count/total_count*100) if total_count > 0 else 0.0
    
    # Generate results table rows
    results_rows = ""
    for result in results:
        status_color = '#28a745' if result.get('status') == 'success' else '#dc3545' if result.get('status') == 'failed' else '#ffc107'
        status_icon = '✅' if result.get('status') == 'success' else '❌' if result.get('status') == 'failed' else '⏭️'
        
        revenue = result.get('revenue', 0)
        record_count = result.get('recordCount', 0)
        locations = result.get('locations', 0)
        template = result.get('templateUsed', 'N/A')
        timezone = result.get('timezone', 'N/A')
        
        results_rows += f"""
        <tr>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; font-size: 13px;">{result.get('owner', 'N/A')}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; font-size: 13px;">{result.get('email', 'N/A')}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: center; font-size: 13px;">
            <span style="color: {status_color}; font-weight: 600;">{status_icon} {result.get('status', 'unknown').upper()}</span>
          </td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: right; font-size: 13px;">₹{revenue:,}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: center; font-size: 13px;">{record_count}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: center; font-size: 13px;">{locations}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; text-align: center; font-size: 13px;">{template}</td>
          <td style="padding: 12px; border-bottom: 1px solid #e9ecef; font-size: 13px;">{result.get('error', 'N/A')}</td>
        </tr>
        """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Reports Summary</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
  <div style="max-width: 1200px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px 24px; text-align: center;">
      <h1 style="margin: 0; font-size: 32px; font-weight: 600;">📊 Daily Reports Summary</h1>
      <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">{today_str}</p>
    </div>
    
    <div style="padding: 32px 24px;">
      
      <!-- Summary Stats -->
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px;">
        <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
          <p style="margin: 0; font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.5px;">Successful</p>
          <h2 style="margin: 8px 0 0 0; font-size: 28px; font-weight: 700;">{success_count}</h2>
        </div>
        
        <div style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
          <p style="margin: 0; font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.5px;">Failed</p>
          <h2 style="margin: 8px 0 0 0; font-size: 28px; font-weight: 700;">{failed_count}</h2>
        </div>
        
        <div style="background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
          <p style="margin: 0; font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.5px;">Skipped</p>
          <h2 style="margin: 8px 0 0 0; font-size: 28px; font-weight: 700;">{skipped_count}</h2>
        </div>
        
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
          <p style="margin: 0; font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.5px;">Total Revenue</p>
          <h2 style="margin: 8px 0 0 0; font-size: 28px; font-weight: 700;">₹{total_revenue:,}</h2>
        </div>
      </div>
      
      <!-- Overall Stats -->
      <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 32px;">
        <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #333;">Overall Statistics</h2>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
          <div>
            <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase;">Total Users</p>
            <p style="margin: 4px 0 0 0; font-size: 24px; font-weight: 700; color: #333;">{total_count}</p>
          </div>
          <div>
            <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase;">Total Records</p>
            <p style="margin: 4px 0 0 0; font-size: 24px; font-weight: 700; color: #333;">{total_records:,}</p>
          </div>
          <div>
            <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase;">Success Rate</p>
            <p style="margin: 4px 0 0 0; font-size: 24px; font-weight: 700; color: #333;">{success_rate:.1f}%</p>
          </div>
        </div>
      </div>
      
      <!-- Results Table -->
      <div style="margin-bottom: 32px;">
        <h2 style="color: #333; font-size: 20px; margin: 0 0 16px 0; border-bottom: 2px solid #667eea; padding-bottom: 8px;">📋 Detailed Results</h2>
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <thead>
              <tr style="background-color: #667eea; color: white;">
                <th style="padding: 12px; text-align: left; font-weight: 600;">Owner</th>
                <th style="padding: 12px; text-align: left; font-weight: 600;">Email</th>
                <th style="padding: 12px; text-align: center; font-weight: 600;">Status</th>
                <th style="padding: 12px; text-align: right; font-weight: 600;">Revenue</th>
                <th style="padding: 12px; text-align: center; font-weight: 600;">Records</th>
                <th style="padding: 12px; text-align: center; font-weight: 600;">Locations</th>
                <th style="padding: 12px; text-align: center; font-weight: 600;">Template</th>
                <th style="padding: 12px; text-align: left; font-weight: 600;">Error</th>
              </tr>
            </thead>
            <tbody>
              {results_rows}
            </tbody>
          </table>
        </div>
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


def send_email_with_attachments_ses(from_email: str, to_email: str, subject: str,
                                    html_content_or_msg, text_content: str,
                                    attachments: List[Dict[str, Any]]):
    """Send email with attachments using AWS SES API.

    html_content_or_msg may be either a string (HTML) or a prebuilt
    MIMEMultipart message (used by template2/3 which embed CID images). This
    function will attach CSVs to the outgoing message and send the final raw
    MIME via SES so inline images (CIDs) are preserved.
    """

    # If caller supplied a MIMEMultipart (template with inline images), use it
    if isinstance(html_content_or_msg, MIMEMultipart):
        msg = html_content_or_msg
        # Ensure headers
        msg['Subject'] = msg.get('Subject', subject)
        msg['From'] = msg.get('From', from_email)
        msg['To'] = msg.get('To', to_email)

        # Attach CSV files to the top-level message. If the message is
        # 'related', wrap it in a 'mixed' container so attachments are separate.
        if msg.get_content_type() == 'multipart/related':
            mixed = MIMEMultipart('mixed')
            # copy headers
            mixed['Subject'] = msg['Subject']
            mixed['From'] = msg['From']
            mixed['To'] = msg['To']
            # move existing related part into mixed
            mixed.attach(msg)
            msg = mixed
    else:
        # html_content_or_msg is an HTML string
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email

        msg_body = MIMEMultipart('alternative')
        text_part = MIMEText(text_content, 'plain', 'utf-8')
        html_part = MIMEText(str(html_content_or_msg), 'html', 'utf-8')
        msg_body.attach(text_part)
        msg_body.attach(html_part)
        msg.attach(msg_body)

    # Attach CSV files
    for attachment in attachments:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment['content'].encode('utf-8'))
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={attachment["filename"]}')
        msg.attach(part)

    try:
        ses = get_ses_client()
        response = ses.send_raw_email(
            Source=from_email,
            Destinations=[to_email],
            RawMessage={'Data': msg.as_string()}
        )
        logger.info(f"SES API response: MessageId {response['MessageId']}")
        return response
    except ClientError as e:
        logger.error(f"SES API error: {e.response['Error']['Message']}")
        raise Exception(f"Failed to send email via SES: {e.response['Error']['Message']}")


@app.route('/send-reports', methods=['POST'])
def send_reports():
    """Main endpoint to send daily reports - now with scheduling support"""
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.error('Unauthorized: Missing or invalid Authorization header')
        return jsonify({
            'success': False,
            'error': 'Unauthorized - Missing or invalid Authorization header',
            'message': 'Please provide a valid Authorization header with Bearer token'
        }), 401
    
    token = auth_header.replace('Bearer ', '')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    if token not in [service_key, anon_key]:
        logger.error('Unauthorized: Invalid token')
        return jsonify({
            'success': False,
            'error': 'Unauthorized - Invalid token',
            'message': 'The provided token is not valid'
        }), 401
    
    logger.info('Authorization verified successfully')
    
    try:
        logger.info("Starting daily reports generation...")
        
        # Get request body for scheduled users
        request_data = request.get_json() or {}
        scheduled_users = request_data.get('users', [])
        trigger_source = request_data.get('trigger', 'manual')
        
        logger.info(f"Trigger source: {trigger_source}")
        logger.info(f"Scheduled users count: {len(scheduled_users)}")
        
        test_email = TEST_EMAIL
        
        if test_email:
            logger.info(f"TEST MODE ENABLED: Will send to {test_email} only")
        else:
            logger.info("PRODUCTION MODE: Will send to scheduled users")
        
        # Validate environment variables
        required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'SES_VERIFIED_FROM']
        for var in required_vars:
            if not os.getenv(var):
                raise Exception(f"Missing required environment variable: {var}")
        
        from_email = os.getenv('SES_VERIFIED_FROM')
        
        # Validate email format
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+'
        clean_email = re.search(r'<([^>]+)>', from_email)
        clean_email = clean_email.group(1) if clean_email else from_email
        
        if not re.match(email_regex, clean_email):
            raise Exception(f"Invalid email format in SES_VERIFIED_FROM: {from_email}")
        
        logger.info(f"Using FROM email: {from_email}")
        
        # Get today's date
        today = datetime.now()
        today_str = today.strftime("%d/%m/%Y")
        
        logger.info(f"Generating reports for date: {today_str}")
        
        # Get locations
        response = supabase.table('locations').select('*').execute()
        locations = response.data
        
        if not locations:
            raise Exception("Failed to fetch locations")
        
        logger.info(f"Found {len(locations)} locations")
        
        # Create a mapping of scheduled user data for quick lookup
        scheduled_user_map = {user['user_id']: user for user in scheduled_users}
        
        # Fetch owners based on scheduled users
        if scheduled_users:
            # Get only the scheduled users
            user_ids = [user['user_id'] for user in scheduled_users]
            logger.info(f"Fetching scheduled users: {user_ids}")
            
            response = supabase.table('users').select('id,email,assigned_location,role,first_name,last_name').in_('id', user_ids).eq('role', 'owner').execute()
            owners = response.data
            
            # Merge template and timezone info from the request payload
            for owner in owners:
                scheduled_data = scheduled_user_map.get(owner['id'])
                if scheduled_data:
                    # Get templateno and timezone directly from the request
                    owner['templateno'] = scheduled_data.get('templateno', 1)
                    owner['timezone'] = scheduled_data.get('timezone', 'UTC')
                else:
                    # Fallback if somehow not in map
                    owner['templateno'] = 1
                    owner['timezone'] = 'UTC'
        else:
            # Fallback: fetch all owners (backward compatibility)
            response = supabase.table('users').select('id,email,assigned_location,role,first_name,last_name').eq('role', 'owner').execute()
            owners = response.data
            # Set default timezone and template for all
            for owner in owners:
                owner['timezone'] = 'UTC'
                owner['templateno'] = 1
        
        logger.info(f"Found {len(owners) if owners else 0} owners to process")
        
        # Verify SES connection
        try:
            ses = get_ses_client()
            quota = ses.get_send_quota()
            logger.info(f"SES connection verified. Daily quota: {quota['Max24HourSend']}, sent today: {quota['SentLast24Hours']}")
        except Exception as e:
            logger.error(f"SES verification failed: {e}")
            raise Exception(f"SES configuration invalid: {str(e)}")
        
        emails_sent = 0
        emails_failed = 0
        emails_skipped = 0
        email_results = []
        total_revenue_summary = 0
        total_records_summary = 0
        
        # Process each owner
        for owner in (owners or []):
            if not owner.get('email'):
                logger.info(f"Skipping owner {owner['id']}: no email")
                emails_skipped += 1
                email_results.append({
                    'owner': get_owner_display_name(owner),
                    'email': owner.get('email', 'No email'),
                    'status': 'skipped',
                    'reason': 'No email address',
                    'timezone': owner.get('timezone', 'N/A')
                })
                continue
            
            # Get all locations for this owner
            owner_location_ids = get_owner_locations(owner, locations)
            
            if not owner_location_ids:
                logger.info(f"Skipping owner {owner['email']}: no locations assigned")
                emails_skipped += 1
                email_results.append({
                    'owner': get_owner_display_name(owner),
                    'email': owner['email'],
                    'status': 'skipped',
                    'reason': 'No locations assigned',
                    'timezone': owner.get('timezone', 'N/A')
                })
                continue
            
            # Get template and timezone from the merged owner data (from request payload)
            owner_template_no = owner.get('templateno', 1) or 1
            owner_timezone = owner.get('timezone', 'UTC')
            is_multi_location = len(owner_location_ids) > 1
            
            logger.info(f"Processing owner {owner['email']} - {len(owner_location_ids)} location(s), Template {owner_template_no}, Timezone: {owner_timezone}")
            
            # Fetch data for each location
            location_data = {}
            has_any_data = False
            all_logs = []
            
            for location_id in owner_location_ids:
                try:
                    location_logs = fetch_today_filtered_logs(location_id)
                    
                    # Find location name
                    location_name = "Unknown Location"
                    for loc in locations:
                        if loc['id'] == location_id:
                            location_name = loc['name']
                            break
                    
                    if len(location_logs) > 0:
                        has_any_data = True
                        all_logs.extend(location_logs)
                        
                        # Generate analysis for this location
                        analysis = analyze_data(location_logs, locations)
                        
                        location_data[location_id] = {
                            'analysis': analysis,
                            'logs': location_logs,
                            'location_name': location_name
                        }
                        
                        logger.info(f"  - {location_name}: {len(location_logs)} records, ₹{analysis['totalRevenue']:,}")
                    else:
                        logger.info(f"  - {location_name}: No data")
                        
                except Exception as e:
                    logger.error(f"Failed to fetch logs for location {location_id}: {e}")
            
            # If no data at all locations, send no-data email
            if not has_any_data:
                logger.info(f"No data across all locations for {owner['email']}")
                try:
                    location_names = ", ".join([loc['name'] for loc in locations if loc['id'] in owner_location_ids])
                    no_data_html = generate_no_data_email_html(location_names, today_str, None)
                    no_data_text = f"""No Data Report - {today_str}

Locations: {location_names}
Status: No approved transactions recorded for today across all assigned locations.
Timezone: {owner_timezone}

Generated on: {datetime.now().strftime("%d/%m/%Y at %H:%M")}"""
                    
                    send_email_with_attachments_ses(
                        from_email,
                        owner['email'],
                        f"No Data Today - {today_str}",
                        no_data_html,
                        no_data_text,
                        []
                    )
                    
                    emails_sent += 1
                    email_results.append({
                        'owner': get_owner_display_name(owner),
                        'email': owner['email'],
                        'status': 'success',
                        'recordCount': 0,
                        'revenue': 0,
                        'locations': len(owner_location_ids),
                        'emailType': 'no-data',
                        'templateUsed': owner_template_no,
                        'timezone': owner_timezone
                    })
                except Exception as e:
                    logger.error(f"Failed to send no-data email to {owner['email']}: {e}")
                    emails_failed += 1
                    email_results.append({
                        'owner': get_owner_display_name(owner),
                        'email': owner['email'],
                        'status': 'failed',
                        'error': str(e),
                        'templateUsed': owner_template_no,
                        'timezone': owner_timezone
                    })
                continue
            
            # Send report with data
            try:
                # Generate appropriate HTML based on location count
                if is_multi_location:
                    # Multi-location report
                    html_content = generate_multi_location_report_html(
                        location_data, locations, today_str, owner_template_no
                    )
                    subject_suffix = f"{len(location_data)} Locations"
                else:
                    # Single location report (use existing templates)
                    single_location_data = list(location_data.values())[0]
                    analysis = single_location_data['analysis']
                    location_name = single_location_data['location_name']
                    
                    html_content = generate_email_html(analysis, location_name, today_str, owner_template_no)
                    subject_suffix = location_name
                
                # Generate CSV attachments for each location
                attachments = []
                date_str = datetime.now().strftime("%Y-%m-%d")
                
                for location_id, data in location_data.items():
                    location_safe = re.sub(r'[^a-zA-Z0-9]', '-', data['location_name']).lower()
                    
                    report_csv = generate_report_csv(data['logs'], locations)
                    payment_csv = generate_payment_breakdown_csv(data['logs'])
                    service_csv = generate_service_breakdown_csv(data['logs'])
                    
                    attachments.extend([
                        {
                            'filename': f"report_{date_str}_{location_safe}.csv",
                            'content': report_csv
                        },
                        {
                            'filename': f"payment_{date_str}_{location_safe}.csv",
                            'content': payment_csv
                        },
                        {
                            'filename': f"service_{date_str}_{location_safe}.csv",
                            'content': service_csv
                        }
                    ])
                
                # Calculate totals
                total_revenue_owner = sum(d['analysis']['totalRevenue'] for d in location_data.values())
                total_records_owner = len(all_logs)
                
                # Generate text version
                text_content = f"""{'Business Intelligence Report' if owner_template_no == 3 else 'Daily Business Report'} - {today_str}

{'Multi-Location Report' if is_multi_location else subject_suffix}
Total Locations: {len(location_data)}
Total Revenue: ₹{total_revenue_owner:,}
Total Transactions: {total_records_owner}
Timezone: {owner_timezone}

LOCATION BREAKDOWN:
{chr(10).join(f"{data['location_name']}: ₹{data['analysis']['totalRevenue']:,} ({data['analysis']['totalVehicles']} vehicles)" for data in location_data.values())}

Template Used: {owner_template_no}
Generated on: {datetime.now().strftime("%d/%m/%Y at %H:%M")}"""
                
                # Send email
                send_email_with_attachments_ses(
                    from_email,
                    owner['email'],
                    f"{'Business Intelligence Report' if owner_template_no == 3 else 'Daily Report'} - {today_str} - {subject_suffix}",
                    html_content,
                    text_content,
                    attachments
                )
                
                emails_sent += 1
                total_revenue_summary += total_revenue_owner
                total_records_summary += total_records_owner
                
                logger.info(f"Email sent to {owner['email']} ({len(location_data)} location(s), {total_records_owner} records, ₹{total_revenue_owner:,}, Template {owner_template_no}, TZ: {owner_timezone})")
                
                email_results.append({
                    'owner': get_owner_display_name(owner),
                    'email': owner['email'],
                    'status': 'success',
                    'recordCount': total_records_owner,
                    'revenue': total_revenue_owner,
                    'locations': len(location_data),
                    'locationNames': ', '.join([d['location_name'] for d in location_data.values()]),
                    'attachments': len(attachments),
                    'templateUsed': owner_template_no,
                    'timezone': owner_timezone,
                    'emailType': 'multi-location' if is_multi_location else 'single-location'
                })
                
            except Exception as e:
                logger.error(f"Failed to send email to {owner['email']}: {e}")
                emails_failed += 1
                email_results.append({
                    'owner': get_owner_display_name(owner),
                    'email': owner['email'],
                    'status': 'failed',
                    'error': str(e),
                    'templateUsed': owner_template_no,
                    'timezone': owner_timezone
                })
        
        # Prepare summary data
        summary_data = {
            'successCount': emails_sent,
            'failedCount': emails_failed,
            'skippedCount': emails_skipped,
            'totalCount': len(owners) if owners else 0,
            'totalRevenue': total_revenue_summary,
            'totalRecords': total_records_summary,
            'results': email_results
        }
        
        # Generate and send summary report to admin email
        try:
            summary_html = generate_summary_report_html(summary_data, today_str)
            summary_text = f"""Daily Reports Summary - {today_str}

Trigger: {trigger_source}
Scheduled Users: {len(scheduled_users)}

Successful: {emails_sent}
Failed: {emails_failed}
Skipped: {emails_skipped}
Total Users: {len(owners) if owners else 0}

Total Revenue: ₹{total_revenue_summary:,}
Total Records: {total_records_summary}

Generated on: {datetime.now().strftime("%d/%m/%Y at %H:%M")}"""
            
            send_email_with_attachments_ses(
                from_email,
                from_email,
                f"Daily Reports Summary - {today_str} ({trigger_source})",
                summary_html,
                summary_text,
                []
            )
            
            logger.info(f"Summary report sent to admin email: {from_email}")
        except Exception as e:
            logger.error(f"Failed to send summary report: {e}")
        
        logger.info(f"Daily reports completed. Emails sent: {emails_sent}/{len(owners) if owners else 0}")
        logger.info(f"Total revenue: ₹{total_revenue_summary:,}, Total records: {total_records_summary}")
        
        return jsonify({
            'success': True,
            'message': f"Daily reports sent successfully",
            'trigger': trigger_source,
            'scheduledUsersCount': len(scheduled_users),
            'emailsSent': emails_sent,
            'emailsFailed': emails_failed,
            'emailsSkipped': emails_skipped,
            'totalOwners': len(owners) if owners else 0,
            'totalRevenue': total_revenue_summary,
            'totalRecords': total_records_summary,
            'reportDate': today_str,
            'summaryEmailSent': True,
            'summaryEmailTo': from_email,
            'filteringApproach': 'Database-level filtering',
            'authMethod': 'Bearer token authentication',
            'deliveryMethod': 'AWS SES API',
            'multiLocationSupport': 'Enabled',
            'schedulingSupport': 'Enabled',
            'results': email_results
        }), 200
        
    except Exception as err:
        logger.error(f"Error: {err}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(err),
            'filteringApproach': 'Database-level filtering',
            'authMethod': 'Bearer token authentication',
            'deliveryMethod': 'AWS SES API',
            'multiLocationSupport': 'Enabled',
            'schedulingSupport': 'Enabled'
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'service': 'daily-reports', 
        'delivery': 'AWS SES API',
        'features': 'Multi-location + User scheduling enabled'
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)