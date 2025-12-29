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
from datetime import datetime, timedelta, timezone, time
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

# Create client options
options = ClientOptions(
    schema="public",
    headers={},
    auto_refresh_token=True,
    persist_session=True,
)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key, options=options)

# Table names (configurable for schema changes)
LOGS_TABLE = os.getenv("SUPABASE_LOGS_TABLE", "log-man")

# Initialize AWS SES client
ses_client = None

# Timezone configuration (fix 5:30 hrs behind by using IST everywhere)
IST_TZ = pytz.timezone('Asia/Kolkata')

def now_ist() -> datetime:
    return datetime.now(timezone.utc).astimezone(IST_TZ)

def format_now_ist(fmt: str = "%d/%m/%Y at %H:%M") -> str:
    return now_ist().strftime(fmt)

def ist_day_utc_bounds(target_dt_ist: Optional[datetime] = None) -> (str, str):
    """Return ISO UTC start/end of the day for IST calendar day.

    This ensures daily reports align with India time (UTC+05:30).
    """
    dt_ist = target_dt_ist or now_ist()
    day = dt_ist.date()
    start_ist = IST_TZ.localize(datetime.combine(day, time(0, 0, 0)))
    end_ist = start_ist + timedelta(days=1)
    start_utc = start_ist.astimezone(timezone.utc).isoformat()
    end_utc = end_ist.astimezone(timezone.utc).isoformat()
    return start_utc, end_utc

def parse_iso_to_ist(iso_str: str) -> datetime:
    if not iso_str:
        return now_ist()
    # Ensure timezone-aware parsing (treat 'Z' as UTC)
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST_TZ)
    except Exception:
        return now_ist()

def format_iso_as_ist(iso_str: str, fmt: str = "%d/%m/%Y %H:%M") -> str:
    return parse_iso_to_ist(iso_str).strftime(fmt)

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


def generate_no_data_email_html(location_names: str, today_str: str) -> MIMEMultipart:
    """Generate HTML for no-data notification email"""
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
    
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px 24px; text-align: center;">
      <h1 style="margin: 0; font-size: 32px; font-weight: 600;">📊 Daily Business Report</h1>
      <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">{today_str}</p>
      <p style="margin: 4px 0 0 0; font-size: 14px; opacity: 0.8;">📍 {location_names}</p>
    </div>
    
    <div style="padding: 32px 24px;">
      
      <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); padding: 32px 24px; border-radius: 12px; margin-bottom: 24px; border: 2px solid #ff9800; text-align: center;">
        <div style="font-size: 64px; margin-bottom: 16px;">🔭</div>
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
                Report generated on {format_now_ist()}
            </p>
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
    """Fetch today's approved logs with joins to new split tables.

    New schema: main table `log-man` with FKs to `vehicle` and `cust`.
    We join needed fields and map results back to legacy keys used by
    analysis and CSV functions to avoid broad code changes.

    Args:
        location_id: Optional location ID to filter by (maps to `loc_id`).

    Returns:
        List of dicts shaped like the old `logs-man` rows (selected fields).
    """
    logger.info(f"Fetching today's logs (new schema) for location: {location_id or 'All locations'}")

    # Build base query from configurable logs table
    # Join related tables for vehicle and customer details
    # PostgREST join syntax via select: alias:fk_column(*)
    select_cols = (
        "id,created_at,approval_status,entry_time,exit_time,entry_type,service,"
        "payment_mode,amount,discount,total,loc_id,veh_id,cust_id,"
        "vehicle:veh_id(id,number_plate,type,veh_det),"
        "cust:cust_id(id,name,phone)"
    )

    query = supabase.table(LOGS_TABLE).select(select_cols)
    query = query.eq('approval_status', 'approved')

    if location_id:
        # In new schema, location is stored as `loc_id`
        query = query.eq('loc_id', location_id)

    # Date range: IST day boundaries converted to UTC
    start_of_day, end_of_day = ist_day_utc_bounds()

    query = query.gte('created_at', start_of_day).lt('created_at', end_of_day)

    logger.info(
        f"Filtering for date range: {start_of_day} to {end_of_day} (table: {LOGS_TABLE}, location: {location_id or 'all'})"
    )

    try:
        response = query.execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error fetching filtered logs: {response.error}")
            raise Exception(f"Failed to fetch logs: {response.error}")

        rows = response.data or []

        # Prefetch vehicle models via veh_det from Vehicles_in_india
        veh_det_ids = list({(r.get('vehicle') or {}).get('veh_det') for r in rows if (r.get('vehicle') or {}).get('veh_det')})
        models_map: Dict[str, Any] = {}
        if veh_det_ids:
            try:
                # Column name has capital letter and space-sensitive schema -> quote the column
                model_resp = supabase.table('Vehicles_in_india').select('id,"Models"').in_('id', veh_det_ids).execute()
                for m in (model_resp.data or []):
                    # Map model text from "Models" column
                    models_map[m.get('id')] = m.get('Models')
            except Exception as me:
                logger.warning(f"Failed to fetch vehicle models: {me}")

        def map_row(row: Dict[str, Any]) -> Dict[str, Any]:
            vehicle = (row or {}).get('vehicle') or {}
            cust = (row or {}).get('cust') or {}

            amount_val = None
            if row.get('amount') is not None:
                amount_val = row.get('amount')
            elif row.get('Total') is not None:
                amount_val = row.get('Total')
            elif row.get('total') is not None:
                amount_val = row.get('total')

            mapped = {
                # Keep most original keys so downstream code works unchanged
                'id': row.get('id'),
                'created_at': row.get('created_at'),
                'approval_status': row.get('approval_status'),
                'entry_time': row.get('entry_time'),
                'exit_time': row.get('exit_time'),
                'entry_type': row.get('entry_type'),
                'service': row.get('service'),
                'payment_mode': row.get('payment_mode'),
                'Amount': amount_val,  # legacy key expected by analysis/CSV
                'discount': row.get('discount'),
                # Map new schema FKs to legacy field names
                'location_id': row.get('loc_id') or row.get('location_id'),
                'vehicle_id': row.get('veh_id') or row.get('vehicle_id'),
                'customer_id': row.get('cust_id') or row.get('customer_id'),
                # Flatten joined details to legacy names
                'vehicle_number': vehicle.get('number_plate'),
                'vehicle_type': vehicle.get('type'),
                'Name': cust.get('name'),
                'Phone_no': cust.get('phone'),
                # Fields that may not exist in new schema but are referenced safely
                'upi_account_name': row.get('upi_account_name'),
                'vehicle_model': models_map.get(vehicle.get('veh_det')),
                'remarks': row.get('remarks'),
                'image_url': row.get('image_url'),
                'workshop': row.get('workshop'),
            }
            return mapped

        logs = [map_row(r) for r in rows]
        logger.info(f"Found {len(logs)} approved logs for today (new schema)")
        return logs
    except Exception as e:
        logger.error(f"Error fetching logs for location {location_id}: {e}")
        raise


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
        created = parse_iso_to_ist(log['created_at'])
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
            "Date": escape_csv(format_iso_as_ist(log['created_at'], "%d/%m/%Y %H:%M")),
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
    
    # Generate individual location sections
    location_sections = []
    for location_id, data in location_data.items():
        analysis = data['analysis']
        location_name = data['location_name']
        
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
                Report generated on {format_now_ist()}
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
        status_icon = '✅' if result.get('status') == 'success' else '❌' if result.get('status') == 'failed' else '⭐️'
        
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
                Report generated on {format_now_ist()}
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
        # Testing convenience: allow overriding destination email without hitting Supabase
        email_override = request_data.get('email_override') or request_data.get('email')
        templateno_override = request_data.get('templateno')
        timezone_override = request_data.get('timezone')
        location_ids_override = request_data.get('location_ids')  # optional list of location IDs
        
        logger.info(f"Trigger source: {trigger_source}")
        logger.info(f"Scheduled users count: {len(scheduled_users)}")
        
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
        
        # Get today's date in IST (fix 5:30 hrs behind)
        today_str = now_ist().strftime("%d/%m/%Y")
        
        logger.info(f"Generating reports for date: {today_str}")
        
        # Get locations
        try:
            response = supabase.table('locations').select('*').execute()
            locations = response.data
        except Exception as e:
            logger.error(f"Failed to fetch locations: {e}")
            raise Exception(f"Failed to fetch locations: {str(e)}")
        
        if not locations:
            raise Exception("Failed to fetch locations")
        
        logger.info(f"Found {len(locations)} locations")
        
        # If email_override is provided, bypass Supabase user lookup entirely
        owners = None
        if email_override:
            # Build a synthetic owner object for testing
            try:
                templ_no_val = int(templateno_override) if templateno_override is not None else 1
            except (ValueError, TypeError):
                templ_no_val = 1

            owners = [{
                'id': 'override',
                'email': email_override,
                'assigned_location': location_ids_override,  # None means all locations
                'role': 'owner',
                'first_name': request_data.get('first_name'),
                'last_name': request_data.get('last_name'),
                'templateno': templ_no_val,
                'timezone': timezone_override or 'UTC'
            }]
            logger.info(f"Using email_override for testing: {email_override}; template={templ_no_val}; tz={timezone_override or 'UTC'}; locations={(location_ids_override or 'ALL')} ")

        # Fetch owners based on scheduled users (normal flow)
        if owners is None and scheduled_users:
            # Get only the scheduled users
            user_ids = [user.get('user_id') for user in scheduled_users if user.get('user_id')]
            if not user_ids:
                raise Exception("No valid user_id values found in request payload")
            
            logger.info(f"Fetching scheduled users from database: {user_ids}")
            
            # Fetch users from database
            response = supabase.table('users').select('id,email,assigned_location,role,first_name,last_name').in_('id', user_ids).eq('role', 'owner').execute()
            owners = response.data
            
            # Fetch schedules for these users
            try:
                user_ids_list = [owner['id'] for owner in owners]
                if user_ids_list:
                    schedule_response = supabase.table('user_schedules').select('user_id,templateno,timezone').in_('user_id', user_ids_list).execute()
                    schedules_map = {sched['user_id']: sched for sched in (schedule_response.data or [])}
                    logger.info(f"Fetched {len(schedules_map)} user schedules")
                else:
                    schedules_map = {}
            except Exception as e:
                logger.error(f"Failed to fetch schedules batch: {e}")
                schedules_map = {}
            
            # Map schedule data to owners
            for owner in owners:
                user_id = owner['id']
                schedule_data = schedules_map.get(user_id)
                
                if schedule_data:
                    templateno_from_db = schedule_data.get('templateno')
                    timezone_from_db = schedule_data.get('timezone', 'UTC')
                    
                    if templateno_from_db is not None:
                        try:
                            owner['templateno'] = int(templateno_from_db)
                            logger.info(f"✓ Using templateno={owner['templateno']} from user_schedules for user {user_id}")
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid templateno value '{templateno_from_db}' for user {user_id}, defaulting to 1")
                            owner['templateno'] = 1
                    else:
                        logger.warning(f"templateno not found for user {user_id}, defaulting to 1")
                        owner['templateno'] = 1
                    
                    owner['timezone'] = timezone_from_db
                    logger.info(f"✓ Using timezone={timezone_from_db} for user {user_id}")
                else:
                    logger.warning(f"No schedule found for user {user_id}, using defaults")
                    owner['templateno'] = 1
                    owner['timezone'] = 'UTC'
        elif owners is None:
            # Fallback: fetch all owners (backward compatibility)
            logger.warning("No scheduled users provided - using backward compatibility mode")
            response = supabase.table('users').select('id,email,assigned_location,role,first_name,last_name').eq('role', 'owner').execute()
            owners = response.data
            
            # Fetch schedules for all owners
            try:
                user_ids_list = [owner['id'] for owner in owners]
                if user_ids_list:
                    schedule_response = supabase.table('user_schedules').select('user_id,templateno,timezone').in_('user_id', user_ids_list).execute()
                    schedules_map = {sched['user_id']: sched for sched in (schedule_response.data or [])}
                    logger.info(f"Fetched {len(schedules_map)} user schedules")
                else:
                    schedules_map = {}
            except Exception as e:
                logger.error(f"Failed to fetch schedules batch: {e}")
                schedules_map = {}
            
            # Map schedule data to owners
            for owner in owners:
                user_id = owner['id']
                schedule_data = schedules_map.get(user_id)
                
                if schedule_data:
                    try:
                        owner['templateno'] = int(schedule_data.get('templateno', 1))
                    except (ValueError, TypeError):
                        owner['templateno'] = 1
                    owner['timezone'] = schedule_data.get('timezone', 'UTC')
                else:
                    owner['templateno'] = 1
                    owner['timezone'] = 'UTC'
        
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
            
            # Get template and timezone from user_schedules (now stored in owner dict)
            owner_template_no = owner.get('templateno', 1) or 1
            owner_timezone = owner.get('timezone', 'UTC')
            is_multi_location = len(owner_location_ids) > 1
            
            logger.info(f"Processing owner {owner['email']} - {len(owner_location_ids)} location(s), Template {owner_template_no}, Timezone: {owner_timezone}")
            
            # Fetch data for each location
            location_data = {}
            has_any_data = False
            all_logs = []
            
            # Fetch logs for all locations (ENTIRE DAY - old version logic)
            for location_id in owner_location_ids:
                try:
                    # OLD VERSION: Fetch entire day's data
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
                    # Continue with other locations even if one fails
            
            # If no data at all locations, send no-data email
            if not has_any_data:
                logger.info(f"No data across all locations for {owner['email']}")
                try:
                    location_names = ", ".join([loc['name'] for loc in locations if loc['id'] in owner_location_ids])
                    no_data_html = generate_no_data_email_html(location_names, today_str)
                    no_data_text = f"""No Data Report - {today_str}

Locations: {location_names}
Status: No approved transactions recorded for today across all assigned locations.
Timezone: {owner_timezone}

Generated on: {format_now_ist()}"""
                    
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
                date_str = now_ist().strftime("%Y-%m-%d")
                
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
Generated on: {format_now_ist()}"""
                
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

Generated on: {format_now_ist()}"""
            
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
            'filteringApproach': 'Database-level filtering (entire day)',
            'authMethod': 'Bearer token authentication',
            'deliveryMethod': 'AWS SES API',
            'multiLocationSupport': 'Enabled',
            'schedulingSupport': 'Enabled',
            'templateSource': 'user_schedules table',
            'results': email_results
        }), 200
        
    except Exception as err:
        logger.error(f"Error: {err}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(err),
            'filteringApproach': 'Database-level filtering (entire day)',
            'authMethod': 'Bearer token authentication',
            'deliveryMethod': 'AWS SES API',
            'multiLocationSupport': 'Enabled',
            'schedulingSupport': 'Enabled',
            'templateSource': 'user_schedules table'
        }), 500

@app.route('/dev/send-reports', methods=['GET', 'POST'])
def dev_send_reports():
    """Temporary local-only route to manually test report generation.

    - No auth required (proxies to /send-reports with a generated Bearer token)
    - Only available when ENABLE_DEV_ROUTE=true
    - Restricted to localhost requests (127.0.0.1 or ::1)
    """

    # Feature toggle: keep disabled by default to avoid exposure
    if (os.getenv('ENABLE_DEV_ROUTE', 'false').lower() != 'true'):
        return jsonify({'success': False, 'error': 'Dev route disabled'}), 404

    # Local-only guard
    remote_ip = (request.remote_addr or '').strip()
    if remote_ip not in ('127.0.0.1', '::1'):
        return jsonify({'success': False, 'error': 'Forbidden - local only'}), 403

    # Prepare request payload (optional JSON body like /send-reports)
    req_json = {}
    try:
        if request.is_json:
            req_json = request.get_json() or {}
    except Exception:
        req_json = {}
    req_json.setdefault('trigger', 'dev')

    # Generate an internal Authorization token using local env keys
    token = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY') or ''
    if not token:
        return jsonify({'success': False, 'error': 'Missing Supabase keys (SERVICE_ROLE_KEY/ANON_KEY) in environment'}), 500

    # Proxy the request to the existing /send-reports handler within a test context
    with app.test_request_context(
        '/send-reports',
        method='POST',
        json=req_json,
        headers={'Authorization': f'Bearer {token}'}
    ):
        return send_reports()

@app.route('/dev', methods=['GET'])
def dev_ui():
        """Temporary local-only UI to trigger report generation from the browser.

        - Enabled only when ENABLE_DEV_ROUTE=true
        - Restricted to localhost requests (127.0.0.1 or ::1)
        - Provides a simple HTML form that posts to /dev/send-reports
        """

        if (os.getenv('ENABLE_DEV_ROUTE', 'false').lower() != 'true'):
                return jsonify({'success': False, 'error': 'Dev route disabled'}), 404

        remote_ip = (request.remote_addr or '').strip()
        if remote_ip not in ('127.0.0.1', '::1'):
                return jsonify({'success': False, 'error': 'Forbidden - local only'}), 403

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Dev: Send Reports</title>
    <style>
        body {{ font-family: -apple-system, Segoe UI, Tahoma, Arial, sans-serif; background:#f7f7fb; margin:0; }}
        .wrap {{ max-width: 900px; margin: 40px auto; background:#fff; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); overflow:hidden; }}
        header {{ background: linear-gradient(135deg,#667eea,#764ba2); color:#fff; padding: 24px; }}
        header h1 {{ margin:0; font-size: 22px; }}
        main {{ padding: 24px; }}
        .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        .card {{ background:#fafbff; border:1px solid #e8eaf6; border-radius:10px; padding:16px; }}
        label {{ display:block; font-size:12px; color:#555; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.04em; }}
        input, textarea {{ width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #dfe3f0; border-radius:8px; font-size:14px; }}
        textarea {{ min-height:76px; }}
        .actions {{ display:flex; gap:12px; margin-top:16px; }}
        button {{ background:#667eea; color:#fff; border:none; border-radius:8px; padding:10px 14px; font-weight:600; cursor:pointer; }}
        button.secondary {{ background:#4caf50; }}
        pre {{ background:#0b1021; color:#d6e3ff; border-radius:10px; padding:16px; overflow:auto; max-height:320px; }}
        .note {{ font-size:12px; color:#777; margin-top:8px; }}
    </style>
    <script>
        async function postDev(usersArr, triggerVal) {{
            const emailOverride = (document.getElementById('emailOverride').value || '').trim();
            const templateno = (document.getElementById('templateno').value || '').trim();
            const timezone = (document.getElementById('timezone').value || '').trim();
            const locationsRaw = (document.getElementById('locationIds').value || '').trim();
            const location_ids = locationsRaw ? locationsRaw.split(',').map(s => s.trim()).filter(Boolean) : undefined;

            const body = usersArr.length > 0 ? {{ users: usersArr, trigger: triggerVal }} : {{ trigger: triggerVal }};
            if (emailOverride) body.email_override = emailOverride;
            if (templateno) body.templateno = templateno;
            if (timezone) body.timezone = timezone;
            if (location_ids && location_ids.length) body.location_ids = location_ids;
            const res = await fetch('/dev/send-reports', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(body)
            }});
            const text = await res.text();
            document.getElementById('output').textContent = text;
        }}
        function handleSubmitSpecified() {{
            const idsRaw = document.getElementById('ownerIds').value || '';
            const trigger = document.getElementById('trigger').value || 'dev';
            const ids = idsRaw.split(',').map(s => s.trim()).filter(Boolean);
            const users = ids.map(id => ({{ user_id: id }}));
            postDev(users, trigger);
        }}
        function handleSubmitAll() {{
            const trigger = document.getElementById('trigger').value || 'dev';
            postDev([], trigger);
        }}
    </script>
    </head>
    <body>
        <div class="wrap">
            <header>
                <h1>Dev: Manual Daily Reports Trigger</h1>
                <div class="note">Local-only, no auth. Enabled: {os.getenv('ENABLE_DEV_ROUTE','false')}</div>
            </header>
            <main>
                <div class="grid">
                    <div class="card">
                        <label for="ownerIds">Owner IDs (comma-separated)</label>
                        <textarea id="ownerIds" placeholder="uuid-1, uuid-2"></textarea>
                        <div class="note">Leave empty to process ALL owners.</div>

                        <label for="emailOverride" style="margin-top:10px;">Email Override (testing)</label>
                        <input id="emailOverride" placeholder="test@example.com" />
                        <div class="note">If provided, bypasses Supabase user lookup and sends to this email.</div>

                        <div class="grid" style="grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px;">
                            <div>
                                <label for="templateno">Template No</label>
                                <input id="templateno" placeholder="1" />
                            </div>
                            <div>
                                <label for="timezone">Timezone</label>
                                <input id="timezone" placeholder="UTC" />
                            </div>
                        </div>

                        <label for="locationIds" style="margin-top:10px;">Location IDs (comma-separated)</label>
                        <textarea id="locationIds" placeholder="loc-1, loc-2"></textarea>
                        <div class="note">Leave empty to include ALL locations.</div>

                        <label for="trigger" style="margin-top:10px;">Trigger</label>
                        <input id="trigger" value="dev" />

                        <div class="actions">
                            <button onclick="handleSubmitSpecified()">Process specified owners</button>
                            <button class="secondary" onclick="handleSubmitAll()">Process ALL owners</button>
                        </div>
                    </div>
                    <div class="card">
                        <label>Response</label>
                        <pre id="output">(results will appear here)</pre>
                        <div class="note">Endpoint: /dev/send-reports → proxies to /send-reports</div>
                    </div>
                </div>
            </main>
        </div>
    </body>
</html>
        """
        return html

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
    # Optional CLI test mode: prompt for UUID/email and invoke send_reports once, then exit.
    if (os.getenv('CLI_TEST', 'false').lower() == 'true'):
        # Read from environment if provided; otherwise prompt
        cli_uuid = (os.getenv('CLI_UUID') or '').strip()
        cli_email = (os.getenv('CLI_EMAIL') or '').strip()
        cli_template = (os.getenv('CLI_TEMPLATE') or '').strip()
        cli_timezone = (os.getenv('CLI_TIMEZONE') or 'UTC').strip()
        cli_locations_raw = (os.getenv('CLI_LOCATIONS') or '').strip()

        if not cli_uuid:
            try:
                cli_uuid = input('Enter user UUID (optional, press Enter to skip): ').strip()
            except Exception:
                cli_uuid = ''
        if not cli_email:
            try:
                cli_email = input('Enter email to send report to: ').strip()
            except Exception:
                cli_email = ''

        payload = {'trigger': 'cli'}
        if cli_uuid:
            payload['users'] = [{'user_id': cli_uuid}]
        if cli_email:
            payload['email_override'] = cli_email
        if cli_template:
            payload['templateno'] = cli_template
        if cli_timezone:
            payload['timezone'] = cli_timezone
        if cli_locations_raw:
            # Accept comma-separated IDs
            payload['location_ids'] = [s.strip() for s in cli_locations_raw.split(',') if s.strip()]

        token = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY') or ''
        if not token:
            print('Missing Supabase keys (SERVICE_ROLE_KEY/ANON_KEY) in environment')
            raise SystemExit(1)

        with app.test_request_context(
            '/send-reports',
            method='POST',
            json=payload,
            headers={'Authorization': f'Bearer {token}'}
        ):
            resp, status = send_reports()
            # Flask view returns (Response, status_code)
            print(f"CLI Test completed with status {status}")
            try:
                print(resp.get_json())
            except Exception:
                print(resp)
        raise SystemExit(0)

    port = int(os.getenv('PORT', 5000))
    # Configure Flask with timeout settings for Render deployment
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
    # Run with threaded mode to handle multiple requests
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)