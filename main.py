"""
Daily Reports Email Service
Modified to fetch data from ONE owner and send to a DIFFERENT email
Hardcode the email addresses at the top of this file
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

# Initialize Supabase client with custom options
from supabase.lib.client_options import ClientOptions

# Import template generators
from template1 import generate_template1_html
from template2 import generate_template2_html
from template3 import generate_template3_html

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ============================================================================
# HARDCODE THESE EMAIL ADDRESSES
# ============================================================================
SOURCE_OWNER_EMAIL = "joswinmjlm10@gmail.com"  # Email of the owner whose data to fetch
SEND_REPORT_TO_EMAIL = "a6hinandh@gmail.com"  # Email where the report should be sent
# ============================================================================

# CONFIGURATION VARIABLES
load_dotenv()

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
    if owner.get('name'):
        return owner.get('name')
    return owner.get('email') or owner.get('id') or 'Unknown'


def escape_csv(value: Any) -> str:
    """Escape CSV values properly"""
    if value is None or value == "":
        return ""
    
    str_value = str(value).strip()
    
    if re.search(r'[,"\n\r]', str_value):
        escaped = str_value.replace('"', '""').replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
        return f'"{escaped}"'
    
    return str_value


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
                       template_no: int) -> str:
    """Generate email HTML using selected template"""
    if template_no == 3:
        return generate_template3_html(analysis, location_name, today_str)
    elif template_no == 2:
        return generate_template2_html(analysis, location_name, today_str)
    else:
        return generate_template1_html(analysis, location_name, today_str)


def send_email_with_attachments_ses(from_email: str, to_email: str, subject: str, 
                                    html_content: str, text_content: str, 
                                    attachments: List[Dict[str, Any]]) -> None:
    """Send email with attachments using AWS SES API"""
    
    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    
    msg_body = MIMEMultipart('alternative')
    
    text_part = MIMEText(text_content, 'plain', 'utf-8')
    html_part = MIMEText(html_content, 'html', 'utf-8')
    
    msg_body.attach(text_part)
    msg_body.attach(html_part)
    
    msg.attach(msg_body)
    
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
    """Main endpoint to send daily report from one owner to another email"""
    
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
        logger.info(f"Starting report generation for owner: {SOURCE_OWNER_EMAIL}")
        logger.info(f"Report will be sent to: {SEND_REPORT_TO_EMAIL}")
        
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
        
        logger.info(f"Generating report for date: {today_str}")
        
        # Get locations
        response = supabase.table('locations').select('*').execute()
        locations = response.data
        
        if not locations:
            raise Exception("Failed to fetch locations")
        
        logger.info(f"Found {len(locations)} locations")
        
        # Fetch the specific owner by email
        response = supabase.table('users').select('id,email,assigned_location,role,first_name,last_name,templateno').eq('email', SOURCE_OWNER_EMAIL).eq('role', 'owner').execute()
        
        if not response.data or len(response.data) == 0:
            raise Exception(f"Owner not found with email: {SOURCE_OWNER_EMAIL}")
        
        owner = response.data[0]
        logger.info(f"Found owner: {get_owner_display_name(owner)}")
        
        # Verify SES connection
        try:
            ses = get_ses_client()
            quota = ses.get_send_quota()
            logger.info(f"SES connection verified. Daily quota: {quota['Max24HourSend']}, sent today: {quota['SentLast24Hours']}")
        except Exception as e:
            logger.error(f"SES verification failed: {e}")
            raise Exception(f"SES configuration invalid: {str(e)}")
        
        # Get template number for this owner (default to 1)
        owner_template_no = owner.get('templateno', 1)
        if owner_template_no is None:
            owner_template_no = 1
        
        # Determine location context
        current_location = owner.get('assigned_location')
        
        logger.info(f"Owner location: {current_location or 'All locations'}, Template: {owner_template_no}")
        
        # Fetch logs for this owner
        try:
            owner_today_logs = fetch_today_filtered_logs(current_location)
        except Exception as e:
            logger.error(f"Failed to fetch logs for owner {owner['email']}: {e}")
            raise Exception(f"Failed to fetch data: {str(e)}")
        
        # Determine location name
        location_name = "All Locations"
        if current_location:
            for loc in locations:
                if loc['id'] == current_location:
                    location_name = loc['name']
                    break
        
        # Check if there's any data
        if len(owner_today_logs) == 0:
            logger.info(f"No data found for {location_name}")
            return jsonify({
                'success': True,
                'message': f"No approved transactions found for {location_name} on {today_str}",
                'emailsSent': 0,
                'dataOwner': get_owner_display_name(owner),
                'dataOwnerEmail': SOURCE_OWNER_EMAIL,
                'recipientEmail': SEND_REPORT_TO_EMAIL,
                'recordCount': 0,
                'revenue': 0,
                'location': location_name,
                'reportDate': today_str
            }), 200
        
        # Send full report
        logger.info(f"Processing {len(owner_today_logs)} approved records for {location_name} (Template {owner_template_no})")
        
        # Generate analysis
        analysis = analyze_data(owner_today_logs, locations)
        
        # Generate CSVs
        report_csv = generate_report_csv(owner_today_logs, locations)
        payment_csv = generate_payment_breakdown_csv(owner_today_logs)
        service_csv = generate_service_breakdown_csv(owner_today_logs)
        
        # Generate HTML with owner's template
        html_content = generate_email_html(analysis, location_name, today_str, owner_template_no)
        
        # Generate text version
        text_content = f"""{'Business Intelligence Report' if owner_template_no == 3 else 'Daily Business Report'} - {today_str}

Data Owner: {get_owner_display_name(owner)} ({SOURCE_OWNER_EMAIL})
Location: {location_name}
Total Revenue: ₹{analysis['totalRevenue']:,}  
{'Transactions' if owner_template_no == 3 else 'Vehicles Served'}: {analysis['totalVehicles']}
Average {'Transaction' if owner_template_no == 3 else 'Service'}: ₹{round(analysis['avgService'])}

PAYMENT BREAKDOWN:
{chr(10).join(f"{item['mode']}: ₹{item['revenue']:,} ({item['count']} {'transactions' if owner_template_no == 3 else 'vehicles'}, {item['percentage']:.1f}%)" for item in analysis['paymentModeBreakdown'])}

SERVICE BREAKDOWN:
{chr(10).join(f"{item['service']}: {item['count']} {'services' if owner_template_no == 3 else 'vehicles'}, ₹{item['revenue']:,} revenue (avg ₹{round(item['price'])})" for item in analysis['serviceBreakdown'])}

Template Used: {owner_template_no} {'(Modern Business Intelligence)' if owner_template_no == 3 else ''}
Generated on: {datetime.now().strftime("%d/%m/%Y at %H:%M")}"""
        
        # Prepare attachments
        location_safe = re.sub(r'[^a-zA-Z0-9]', '-', location_name).lower()
        date_str = today.strftime("%Y-%m-%d")
        attachments = [
            {
                'filename': f"{'transaction_report' if owner_template_no == 3 else 'daily_report'}_{date_str}_{location_safe}.csv",
                'content': report_csv
            },
            {
                'filename': f"payment_{'analytics' if owner_template_no == 3 else 'breakdown'}_{date_str}_{location_safe}.csv",
                'content': payment_csv
            },
            {
                'filename': f"service_{'performance' if owner_template_no == 3 else 'breakdown'}_{date_str}_{location_safe}.csv",
                'content': service_csv
            }
        ]
        
        # Send email using SES API to the specified recipient
        send_email_with_attachments_ses(
            from_email,
            SEND_REPORT_TO_EMAIL,
            f"{'Business Intelligence Report' if owner_template_no == 3 else 'Daily Report'} - {today_str} - {location_name} [{get_owner_display_name(owner)}]",
            html_content,
            text_content,
            attachments
        )
        
        logger.info(f"Email sent to {SEND_REPORT_TO_EMAIL} with data from {SOURCE_OWNER_EMAIL} ({len(owner_today_logs)} approved records, ₹{analysis['totalRevenue']:,}, {len(attachments)} attachments, Template {owner_template_no})")
        
        return jsonify({
            'success': True,
            'message': f"Report sent successfully",
            'emailsSent': 1,
            'dataOwner': get_owner_display_name(owner),
            'dataOwnerEmail': SOURCE_OWNER_EMAIL,
            'recipientEmail': SEND_REPORT_TO_EMAIL,
            'recordCount': len(owner_today_logs),
            'revenue': analysis['totalRevenue'],
            'location': location_name,
            'attachments': len(attachments),
            'templateUsed': owner_template_no,
            'reportDate': today_str,
            'filteringApproach': 'Database-level filtering',
            'authMethod': 'Bearer token authentication',
            'deliveryMethod': 'AWS SES API'
        }), 200
        
    except Exception as err:
        logger.error(f"Error: {err}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(err),
            'filteringApproach': 'Database-level filtering',
            'authMethod': 'Bearer token authentication',
            'deliveryMethod': 'AWS SES API'
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'daily-reports', 'delivery': 'AWS SES API'}), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)