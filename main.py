# """
# Daily Reports Email Service
# Converts Supabase Edge Function to Python Flask server
# Works locally and on Render
# """

# from flask import Flask, request, jsonify
# from supabase import create_client, Client
# import smtplib
# from dotenv import load_dotenv
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.base import MIMEBase
# from email import encoders
# from datetime import datetime, timedelta
# import os
# import re
# from typing import List, Dict, Any, Optional
# import logging
# import asyncio

# # Initialize Supabase client with custom options to avoid proxy parameter issue
# from supabase.lib.client_options import ClientOptions


# # Import template generators
# from template1 import generate_template1_html
# from template2 import generate_template2_html
# from template3 import generate_template3_html

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# app = Flask(__name__)

# # CONFIGURATION VARIABLES
# # Load environment variables from a .env file (if present). This must run before any os.getenv/os.environ usage.
# load_dotenv()
# TEST_EMAIL = os.getenv("TEST_EMAIL")  # Set to None or empty to disable test mode
# TEMPLATE_NO = int(os.getenv("TEMPLATE_NO", "1"))  # 1, 2, or 3


# # Create client options without proxy
# options = ClientOptions(
#     schema="public",
#     headers={},
#     auto_refresh_token=True,
#     persist_session=True,
# )


# url = os.environ.get("SUPABASE_URL")
# key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
# supabase: Client = create_client(url, key)


# def escape_csv(value: Any) -> str:
#     """Escape CSV values properly"""
#     if value is None or value == "":
#         return ""
    
#     str_value = str(value).strip()
    
#     # Check if escaping is needed
#     if re.search(r'[,"\n\r]', str_value):
#         # Escape quotes and remove newlines
#         escaped = str_value.replace('"', '""').replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
#         return f'"{escaped}"'
    
#     return str_value


# def generate_no_data_email_html(location_name: str, today_str: str, test_email: Optional[str]) -> str:
#     """Generate HTML for no-data notification email"""
#     test_banner = f"""
#     <div style="background-color: #ff9800; color: white; padding: 12px 24px; text-align: center; font-weight: bold;">
#       🧪 TEST MODE - This is a test email
#     </div>
#     """ if test_email else ""
    
#     test_footer = f'<p style="margin: 8px 0 0 0; color: #ff9800; font-size: 12px; font-weight: bold;">🧪 Test email sent to: {test_email}</p>' if test_email else ""
    
#     return f"""
# <!DOCTYPE html>
# <html>
# <head>
#   <meta charset="UTF-8">
#   <meta name="viewport" content="width=device-width, initial-scale=1.0">
#   <title>No Data Report</title>
# </head>
# <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
#   <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    
#     {test_banner}
    
#     <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px 24px; text-align: center;">
#       <h1 style="margin: 0; font-size: 28px; font-weight: 600;">🔭 No Data Today</h1>
#       <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">{today_str}</p>
#     </div>
    
#     <div style="padding: 40px 24px;">
#       <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; border-radius: 4px; margin-bottom: 24px;">
#         <h2 style="margin: 0 0 8px 0; font-size: 18px; color: #333;">📍 Location: {location_name}</h2>
#         <p style="margin: 0; color: #666; font-size: 14px;">No approved transactions were recorded for today.</p>
#       </div>
      
#       <div style="text-align: center; padding: 20px; background-color: #fff3cd; border-radius: 4px; border: 1px solid #ffc107;">
#         <p style="margin: 0; color: #856404; font-size: 15px;">
#           ℹ️ There are no approved logs to report for {today_str}.
#         </p>
#       </div>
#     </div>
    
#     <div style="background-color: #f8f9fa; padding: 20px 24px; border-top: 1px solid #e9ecef; text-align: center;">
#       <p style="margin: 0; color: #6c757d; font-size: 12px;">
#         Report generated on {datetime.now().strftime("%d/%m/%Y at %H:%M")}
#       </p>
#       {test_footer}
#     </div>
    
#   </div>
# </body>
# </html>
#     """.strip()


# def fetch_today_filtered_logs(location_id: Optional[str] = None) -> List[Dict[str, Any]]:
#     """Fetch today's filtered logs using database-level filtering"""
#     logger.info(f"🔍 Fetching today's logs for location: {location_id or 'All locations'}")
    
#     # Build the logs query
#     query = supabase.table('logs-man').select('*')
    
#     # Apply approval status filter
#     query = query.eq('approval_status', 'approved')
    
#     # Apply location filter if specified
#     if location_id:
#         query = query.eq('location_id', location_id)
    
#     # Apply date range filter for today
#     now = datetime.now()
#     today = datetime(now.year, now.month, now.day)
#     start_of_day = today.isoformat()
#     end_of_day = (today + timedelta(days=1)).isoformat()
    
#     query = query.gte('created_at', start_of_day).lt('created_at', end_of_day)
    
#     logger.info(f"📅 Filtering for date range: {start_of_day} to {end_of_day}")
    
#     response = query.execute()
    
#     if hasattr(response, 'error') and response.error:
#         logger.error(f'❌ Error fetching filtered logs: {response.error}')
#         raise Exception(f"Failed to fetch logs: {response.error}")
    
#     logs = response.data or []
#     logger.info(f"📊 Found {len(logs)} approved logs for today")
    
#     return logs


# def analyze_data(logs: List[Dict[str, Any]], locations: List[Dict[str, Any]]) -> Dict[str, Any]:
#     """Generate comprehensive data analysis"""
#     logger.info(f"🔍 Analyzing {len(logs)} log entries...")
    
#     total_revenue = sum(log.get('Amount', 0) for log in logs)
#     total_vehicles = len(logs)
#     avg_service = total_revenue / total_vehicles if total_vehicles > 0 else 0
    
#     logger.info(f"💰 Analysis summary: ₹{total_revenue} revenue, {total_vehicles} vehicles, ₹{avg_service:.2f} avg")
    
#     # Payment mode breakdown
#     payment_mode_breakdown = {}
#     for log in logs:
#         payment_mode = log.get('payment_mode', 'Cash')
#         normalized_mode = payment_mode.lower()
        
#         if normalized_mode not in payment_mode_breakdown:
#             payment_mode_breakdown[normalized_mode] = {
#                 'mode': payment_mode,
#                 'displayName': payment_mode,
#                 'count': 0,
#                 'transactions': 0,
#                 'revenue': 0,
#                 'percentage': 0,
#                 'upiAccounts': {},
#                 'details': {}
#             }
        
#         payment_mode_breakdown[normalized_mode]['count'] += 1
#         payment_mode_breakdown[normalized_mode]['transactions'] += 1
#         payment_mode_breakdown[normalized_mode]['revenue'] += log.get('Amount', 0)
        
#         # Track UPI accounts
#         if normalized_mode == 'upi' and log.get('upi_account_name'):
#             account_name = log['upi_account_name']
#             if account_name not in payment_mode_breakdown[normalized_mode]['upiAccounts']:
#                 payment_mode_breakdown[normalized_mode]['upiAccounts'][account_name] = {
#                     'count': 0,
#                     'amount': 0
#                 }
#                 payment_mode_breakdown[normalized_mode]['details'][account_name] = {
#                     'count': 0,
#                     'amount': 0
#                 }
            
#             payment_mode_breakdown[normalized_mode]['upiAccounts'][account_name]['count'] += 1
#             payment_mode_breakdown[normalized_mode]['upiAccounts'][account_name]['amount'] += log.get('Amount', 0)
#             payment_mode_breakdown[normalized_mode]['details'][account_name]['count'] += 1
#             payment_mode_breakdown[normalized_mode]['details'][account_name]['amount'] += log.get('Amount', 0)
    
#     # Calculate percentages
#     for payment in payment_mode_breakdown.values():
#         payment['percentage'] = (payment['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
    
#     # Service breakdown
#     service_breakdown = {}
#     for log in logs:
#         service = log.get('service', 'Unknown')
#         if service not in service_breakdown:
#             service_breakdown[service] = {
#                 'service': service,
#                 'name': service,
#                 'count': 0,
#                 'revenue': 0,
#                 'price': 0,
#                 'averagePrice': 0,
#                 'revenueShare': 0
#             }
        
#         service_breakdown[service]['count'] += 1
#         service_breakdown[service]['revenue'] += log.get('Amount', 0)
#         service_breakdown[service]['price'] = service_breakdown[service]['revenue'] / service_breakdown[service]['count']
#         service_breakdown[service]['averagePrice'] = service_breakdown[service]['price']
    
#     # Calculate service revenue shares
#     for service in service_breakdown.values():
#         service['revenueShare'] = (service['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
    
#     # Vehicle type distribution
#     vehicle_distribution = {}
#     for log in logs:
#         vtype = log.get('vehicle_type', 'Unknown')
#         if vtype not in vehicle_distribution:
#             vehicle_distribution[vtype] = {
#                 'type': vtype,
#                 'count': 0,
#                 'percentage': 0
#             }
#         vehicle_distribution[vtype]['count'] += 1
    
#     # Calculate vehicle percentages
#     for vehicle in vehicle_distribution.values():
#         vehicle['percentage'] = (vehicle['count'] / total_vehicles * 100) if total_vehicles > 0 else 0
    
#     # Hourly breakdown
#     hourly_breakdown = []
#     for i in range(24):
#         hour_12 = 12 if i % 12 == 0 else i % 12
#         period = 'AM' if i < 12 else 'PM'
#         hourly_breakdown.append({
#             'hour': i,
#             'label': f"{hour_12:02d} {period}",
#             'period': period,
#             'display': f"{hour_12}:00 {period}",
#             'amount': 0,
#             'count': 0,
#             'transactions': 0,
#             'revenue': 0
#         })
    
#     for log in logs:
#         created = datetime.fromisoformat(log['created_at'].replace('Z', '+00:00'))
#         hour = created.hour
#         hourly_breakdown[hour]['amount'] += log.get('Amount', 0)
#         hourly_breakdown[hour]['count'] += 1
#         hourly_breakdown[hour]['transactions'] += 1
#         hourly_breakdown[hour]['revenue'] += log.get('Amount', 0)
    
#     # Find peak metrics
#     peak_hour = max(hourly_breakdown, key=lambda x: x['revenue'])
#     service_list = list(service_breakdown.values())
#     peak_service = max(service_list, key=lambda x: x['revenue']) if service_list else {'name': 'N/A', 'revenue': 0}
    
#     # Convert to arrays
#     payment_mode_breakdown_array = list(payment_mode_breakdown.values())
#     service_breakdown_array = sorted(service_breakdown.values(), key=lambda x: x['revenue'], reverse=True)
#     vehicle_distribution_array = sorted(vehicle_distribution.values(), key=lambda x: x['count'], reverse=True)
#     hourly_breakdown_filtered = [h for h in hourly_breakdown if h['count'] > 0 or h['amount'] > 0]
    
#     return {
#         'totalRevenue': total_revenue,
#         'totalVehicles': total_vehicles,
#         'avgService': avg_service,
#         'paymentModeBreakdown': payment_mode_breakdown_array,
#         'serviceBreakdown': service_breakdown_array,
#         'vehicleDistribution': vehicle_distribution_array,
#         'hourlyBreakdown': hourly_breakdown_filtered,
#         'summary': {
#             'totalRevenue': total_revenue,
#             'totalTransactions': total_vehicles,
#             'averageTransaction': avg_service,
#             'peakHour': peak_hour['display'],
#             'peakHourRevenue': peak_hour['revenue']
#         },
#         'payments': payment_mode_breakdown_array,
#         'services': service_breakdown_array,
#         'vehicles': vehicle_distribution_array,
#         'hourlyData': hourly_breakdown_filtered,
#         'insights': {
#             'topService': peak_service['name'],
#             'topServiceRevenue': peak_service['revenue'],
#             'busyHours': len(hourly_breakdown_filtered)
#         }
#     }


# def generate_report_csv(logs: List[Dict[str, Any]], locations: List[Dict[str, Any]]) -> str:
#     """Generate main report CSV"""
#     logger.info(f"📄 Generating main report CSV for {len(logs)} logs...")
    
#     rows = []
#     for log in logs:
#         location_name = "Unknown"
#         for loc in locations:
#             if loc['id'] == log.get('location_id'):
#                 location_name = loc['name']
#                 break
        
#         rows.append({
#             "Vehicle Number": escape_csv(log.get('vehicle_number')),
#             "Owner Name": escape_csv(log.get('Name')),
#             "Phone": escape_csv(log.get('Phone_no')),
#             "Vehicle Model": escape_csv(log.get('vehicle_model')),
#             "Service Type": escape_csv(log.get('service')),
#             "Price": escape_csv(log.get('Amount')),
#             "Payment Mode": escape_csv(log.get('payment_mode')),
#             "UPI Account": escape_csv(log.get('upi_account_name')),
#             "Entry Type": escape_csv(log.get('entry_type')),
#             "Date": escape_csv(datetime.fromisoformat(log['created_at'].replace('Z', '+00:00')).strftime("%d/%m/%Y %H:%M")),
#             "Location": escape_csv(location_name)
#         })
    
#     if not rows:
#         return ""
    
#     headers = list(rows[0].keys())
#     csv_lines = [",".join(headers)]
    
#     for row in rows:
#         csv_lines.append(",".join(str(row[h]) for h in headers))
    
#     return "\n".join(csv_lines)


# def generate_payment_breakdown_csv(logs: List[Dict[str, Any]]) -> str:
#     """Generate payment breakdown CSV"""
#     logger.info("💳 Generating payment breakdown CSV...")
    
#     analysis = analyze_data(logs, [])
    
#     rows = []
#     for item in analysis['paymentModeBreakdown']:
#         upi_accounts = 'N/A'
#         if item['mode'].lower() == 'upi' and item.get('upiAccounts'):
#             accounts = []
#             for account_name, account_data in item['upiAccounts'].items():
#                 accounts.append(f"{account_name}: ₹{account_data['amount']} ({account_data['count']} vehicles)")
#             upi_accounts = '; '.join(accounts)
        
#         rows.append({
#             "Payment Mode": escape_csv(item['mode']),
#             "Total Revenue": escape_csv(item['revenue']),
#             "Vehicle Count": escape_csv(item['count']),
#             "Percentage of Total": escape_csv(f"{item['percentage']:.1f}%"),
#             "UPI Accounts": escape_csv(upi_accounts)
#         })
    
#     if not rows:
#         return ""
    
#     headers = list(rows[0].keys())
#     csv_lines = [",".join(headers)]
    
#     for row in rows:
#         csv_lines.append(",".join(str(row[h]) for h in headers))
    
#     return "\n".join(csv_lines)


# def generate_service_breakdown_csv(logs: List[Dict[str, Any]]) -> str:
#     """Generate service breakdown CSV"""
#     logger.info("🛠️ Generating service breakdown CSV...")
    
#     analysis = analyze_data(logs, [])
    
#     rows = []
#     for item in analysis['serviceBreakdown']:
#         percentage = (item['revenue'] / analysis['totalRevenue'] * 100) if analysis['totalRevenue'] > 0 else 0
#         rows.append({
#             "Service Type": escape_csv(item['service']),
#             "Total Revenue": escape_csv(item['revenue']),
#             "Vehicle Count": escape_csv(item['count']),
#             "Average Price": escape_csv(round(item['price'])),
#             "Percentage of Revenue": escape_csv(f"{percentage:.1f}%")
#         })
    
#     if not rows:
#         return ""
    
#     headers = list(rows[0].keys())
#     csv_lines = [",".join(headers)]
    
#     for row in rows:
#         csv_lines.append(",".join(str(row[h]) for h in headers))
    
#     return "\n".join(csv_lines)


# def generate_email_html(analysis: Dict[str, Any], location_name: str, today_str: str, 
#                        test_email: Optional[str], template_no: int) -> str:
#     """Generate email HTML using selected template"""
#     if template_no == 3:
#         return generate_template3_html(analysis, location_name, today_str, test_email)
#     elif template_no == 2:
#         return generate_template2_html(analysis, location_name, today_str, test_email)
#     else:
#         return generate_template1_html(analysis, location_name, today_str, test_email)


# def send_email_with_attachments(from_email: str, to_email: str, subject: str, 
#                                 html_content: str, text_content: str, 
#                                 attachments: List[Dict[str, Any]]) -> None:
#     """Send email with attachments using AWS SES SMTP"""
#     msg = MIMEMultipart('alternative')
#     msg['From'] = from_email
#     msg['To'] = to_email
#     msg['Subject'] = subject
    
#     # Attach text and HTML versions
#     msg.attach(MIMEText(text_content, 'plain'))
#     msg.attach(MIMEText(html_content, 'html'))
    
#     # Attach CSV files
#     for attachment in attachments:
#         part = MIMEBase('application', 'octet-stream')
#         part.set_payload(attachment['content'].encode('utf-8'))
#         encoders.encode_base64(part)
#         part.add_header('Content-Disposition', f'attachment; filename={attachment["filename"]}')
#         msg.attach(part)
    
#     # Send email
#     with smtplib.SMTP_SSL('email-smtp.us-east-1.amazonaws.com', 465) as server:
#         server.login(os.getenv('AWS_SMTP_USER'), os.getenv('AWS_SMTP_PASS'))
#         server.send_message(msg)


# @app.route('/send-reports', methods=['POST'])
# def send_reports():
#     """Main endpoint to send daily reports"""
    
#     # Check authorization
#     auth_header = request.headers.get('Authorization')
#     if not auth_header or not auth_header.startswith('Bearer '):
#         logger.error('❌ Unauthorized: Missing or invalid Authorization header')
#         return jsonify({
#             'success': False,
#             'error': 'Unauthorized - Missing or invalid Authorization header',
#             'message': 'Please provide a valid Authorization header with Bearer token'
#         }), 401
    
#     # Verify token
#     token = auth_header.replace('Bearer ', '')
#     service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
#     anon_key = os.getenv('SUPABASE_ANON_KEY')
    
#     if token not in [service_key, anon_key]:
#         logger.error('❌ Unauthorized: Invalid token')
#         return jsonify({
#             'success': False,
#             'error': 'Unauthorized - Invalid token',
#             'message': 'The provided token is not valid'
#         }), 401
    
#     logger.info('✅ Authorization verified successfully')
    
#     try:
#         logger.info("🚀 Starting daily reports generation...")
        
#         test_email = TEST_EMAIL
#         template_no = TEMPLATE_NO
        
#         if test_email:
#             logger.info(f"🧪 TEST MODE ENABLED: Will send to {test_email} only")
#         else:
#             logger.info("📧 PRODUCTION MODE: Will send to all owners")
        
#         logger.info(f"🎨 Using Template {template_no}")
        
#         # Validate environment variables
#         required_vars = ['AWS_SMTP_USER', 'AWS_SMTP_PASS', 'SES_VERIFIED_FROM']
#         for var in required_vars:
#             if not os.getenv(var):
#                 raise Exception(f"Missing required environment variable: {var}")
        
#         from_email = os.getenv('SES_VERIFIED_FROM')
        
#         # Validate email format
#         email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
#         clean_email = re.search(r'<([^>]+)>', from_email)
#         clean_email = clean_email.group(1) if clean_email else from_email
        
#         if not re.match(email_regex, clean_email):
#             raise Exception(f"Invalid email format in SES_VERIFIED_FROM: {from_email}")
        
#         logger.info(f"📧 Using FROM email: {from_email}")
        
#         # Get today's date
#         today = datetime.now()
#         today_str = today.strftime("%d/%m/%Y")
        
#         logger.info(f"📅 Generating reports for date: {today_str}")
        
#         # Get owners
#         if test_email:
#             owners = [{
#                 'id': 'test-owner',
#                 'email': "a6hinandh@gmail.com",
#                 'assigned_location': None,
#                 'role': 'owner',
#                 'name': 'Test Owner'
#             }]
#             logger.info(f"🧪 Using test owner: {test_email}")
#         else:
#             response = supabase.table('users').select('id,email,assigned_location,role,name').eq('role', 'owner').execute()
#             owners = response.data
#             logger.info(f"👥 Found {len(owners) if owners else 0} owners")
        
#         # Get locations
#         response = supabase.table('locations').select('*').execute()
#         locations = response.data
        
#         if not locations:
#             raise Exception("Failed to fetch locations")
        
#         logger.info(f"📍 Found {len(locations)} locations")
        
#         # Verify SMTP connection
#         try:
#             with smtplib.SMTP_SSL('email-smtp.us-east-1.amazonaws.com', 465) as server:
#                 server.login(os.getenv('AWS_SMTP_USER'), os.getenv('AWS_SMTP_PASS'))
#             logger.info("✅ SMTP connection verified successfully")
#         except Exception as e:
#             logger.error(f"❌ SMTP verification failed: {e}")
#             raise Exception(f"SMTP configuration invalid: {str(e)}")
        
#         emails_sent = 0
#         email_results = []
        
#         # Process each owner
#         for owner in (owners or []):
#             if not owner.get('email'):
#                 logger.info(f"⏭️ Skipping owner {owner['id']}: no email")
#                 email_results.append({
#                     'owner': owner.get('name', owner['id']),
#                     'email': owner.get('email', 'No email'),
#                     'status': 'skipped',
#                     'reason': 'No email address'
#                 })
#                 continue
            
#             # Determine location context
#             current_location = None
#             if owner['role'] == 'manager':
#                 current_location = owner.get('assigned_location')
#             elif owner['role'] == 'owner' and owner.get('assigned_location'):
#                 current_location = owner.get('assigned_location')
            
#             logger.info(f"👤 Processing owner {owner['email']} (Role: {owner['role']}, Location: {current_location or 'All locations'})")
            
#             # Fetch logs - CHANGED: Remove async/await, call function directly
#             try:
#                 owner_today_logs = fetch_today_filtered_logs(current_location)
#             except Exception as e:
#                 logger.error(f"❌ Failed to fetch logs for owner {owner['email']}: {e}")
#                 email_results.append({
#                     'owner': owner.get('name', owner['email']),
#                     'email': owner['email'],
#                     'status': 'failed',
#                     'error': f"Failed to fetch data: {str(e)}"
#                 })
#                 continue
            
#             # Determine location name
#             location_name = "All Locations"
#             if current_location:
#                 for loc in locations:
#                     if loc['id'] == current_location:
#                         location_name = loc['name']
#                         break
            
#             # Send no-data email if no logs
#             if len(owner_today_logs) == 0:
#                 logger.info(f"🔭 Sending no-data notification to {owner['email']} for {location_name}")
#                 try:
#                     no_data_html = generate_no_data_email_html(location_name, today_str, test_email)
#                     no_data_text = f"""{'[TEST] ' if test_email else ''}No Data Report - {today_str}

# Location: {location_name}
# Status: No approved transactions recorded for today.

# Generated on: {datetime.now().strftime("%d/%m/%Y at %H:%M")}
# {'🧪 Test Mode: Sent to ' + test_email if test_email else ''}"""
                    
#                     send_email_with_attachments(
#                         from_email,
#                         owner['email'],
#                         f"{'[TEST] ' if test_email else ''}🔭 No Data Today - {today_str} - {location_name}",
#                         no_data_html,
#                         no_data_text,
#                         []
#                     )
                    
#                     emails_sent += 1
#                     logger.info(f"✅ No-data email sent to {owner['email']}")
#                     email_results.append({
#                         'owner': owner.get('name', owner['email']),
#                         'email': owner['email'],
#                         'status': 'success',
#                         'recordCount': 0,
#                         'revenue': 0,
#                         'location': location_name,
#                         'emailType': 'no-data'
#                     })
#                 except Exception as e:
#                     logger.error(f"❌ Failed to send no-data email to {owner['email']}: {e}")
#                     email_results.append({
#                         'owner': owner.get('name', owner['email']),
#                         'email': owner['email'],
#                         'status': 'failed',
#                         'error': str(e)
#                     })
#                 continue
            
#             # Send full report
#             try:
#                 logger.info(f"📄 Processing {owner['email']} - {len(owner_today_logs)} approved records for {location_name} (Template {template_no})")
                
#                 # Generate analysis
#                 analysis = analyze_data(owner_today_logs, locations)
                
#                 # Generate CSVs
#                 report_csv = generate_report_csv(owner_today_logs, locations)
#                 payment_csv = generate_payment_breakdown_csv(owner_today_logs)
#                 service_csv = generate_service_breakdown_csv(owner_today_logs)
                
#                 # Generate HTML
#                 html_content = generate_email_html(analysis, location_name, today_str, test_email, template_no)
                
#                 # Generate text version
#                 text_content = f"""{'[TEST] ' if test_email else ''}{'Business Intelligence Report' if template_no == 3 else 'Daily Business Report'} - {today_str}

# Location: {location_name}
# Total Revenue: ₹{analysis['totalRevenue']:,}  
# {'Transactions' if template_no == 3 else 'Vehicles Served'}: {analysis['totalVehicles']}
# Average {'Transaction' if template_no == 3 else 'Service'}: ₹{round(analysis['avgService'])}

# PAYMENT BREAKDOWN:
# {chr(10).join(f"{item['mode']}: ₹{item['revenue']:,} ({item['count']} {'transactions' if template_no == 3 else 'vehicles'}, {item['percentage']:.1f}%)" for item in analysis['paymentModeBreakdown'])}

# SERVICE BREAKDOWN:
# {chr(10).join(f"{item['service']}: {item['count']} {'services' if template_no == 3 else 'vehicles'}, ₹{item['revenue']:,} revenue (avg ₹{round(item['price'])})" for item in analysis['serviceBreakdown'])}

# Template Used: {template_no} {'(Modern Business Intelligence)' if template_no == 3 else ''}
# Generated on: {datetime.now().strftime("%d/%m/%Y at %H:%M")}
# {'🧪 Test Mode: Sent to ' + test_email if test_email else ''}"""
                
#                 # Prepare attachments
#                 location_safe = re.sub(r'[^a-zA-Z0-9]', '-', location_name).lower()
#                 date_str = today.strftime("%Y-%m-%d")
#                 attachments = [
#                     {
#                         'filename': f"{'TEST_' if test_email else ''}{'transaction_report' if template_no == 3 else 'daily_report'}_{date_str}_{location_safe}.csv",
#                         'content': report_csv
#                     },
#                     {
#                         'filename': f"{'TEST_' if test_email else ''}payment_{'analytics' if template_no == 3 else 'breakdown'}_{date_str}_{location_safe}.csv",
#                         'content': payment_csv
#                     },
#                     {
#                         'filename': f"{'TEST_' if test_email else ''}service_{'performance' if template_no == 3 else 'breakdown'}_{date_str}_{location_safe}.csv",
#                         'content': service_csv
#                     }
#                 ]
                
#                 # Send email
#                 send_email_with_attachments(
#                     from_email,
#                     owner['email'],
#                     f"{'[TEST] ' if test_email else ''}{'📊 Business Intelligence Report' if template_no == 3 else 'Daily Report'} - {today_str} - {location_name}",
#                     html_content,
#                     text_content,
#                     attachments
#                 )
                
#                 emails_sent += 1
#                 logger.info(f"✅ Email sent to {owner['email']} ({len(owner_today_logs)} approved records, ₹{analysis['totalRevenue']:,}, {len(attachments)} attachments, Template {template_no})")
                
#                 email_results.append({
#                     'owner': owner.get('name', owner['email']),
#                     'email': owner['email'],
#                     'status': 'success',
#                     'recordCount': len(owner_today_logs),
#                     'revenue': analysis['totalRevenue'],
#                     'location': location_name,
#                     'attachments': len(attachments),
#                     'templateUsed': template_no,
#                     'emailType': 'full-report'
#                 })
#             except Exception as e:
#                 logger.error(f"❌ Failed to send email to {owner['email']}: {e}")
#                 email_results.append({
#                     'owner': owner.get('name', owner['email']),
#                     'email': owner['email'],
#                     'status': 'failed',
#                     'error': str(e)
#                 })
        
#         # Get total approved logs - CHANGED: Remove async/await
#         total_approved_logs = fetch_today_filtered_logs()
        
#         logger.info(f"🎉 Daily reports completed. Emails sent: {emails_sent}/{len(owners) if owners else 0} using Template {template_no}")
#         logger.info(f"📊 Total approved logs for today: {len(total_approved_logs)}")
        
#         return jsonify({
#             'success': True,
#             'message': f"✅ {'Modern business intelligence reports' if template_no == 3 else 'Daily reports'} sent successfully {'(TEST MODE)' if test_email else ''} using Template {template_no}",
#             'emailsSent': emails_sent,
#             'totalOwners': len(owners) if owners else 0,
#             'todayLogsCount': len(total_approved_logs),
#             'reportDate': today_str,
#             'testMode': bool(test_email),
#             'testEmail': test_email,
#             'templateUsed': template_no,
#             'attachmentsPerEmail': 3,
#             'filteringApproach': 'Database-level filtering (matching Reports.tsx)',
#             'authMethod': 'Bearer token authentication',
#             'noDataEmailsEnabled': True,
#             'results': email_results
#         }), 200
        
#     except Exception as err:
#         logger.error(f"❌ Error: {err}", exc_info=True)
#         return jsonify({
#             'success': False,
#             'error': str(err),
#             'testMode': bool(TEST_EMAIL),
#             'templateUsed': TEMPLATE_NO,
#             'filteringApproach': 'Database-level filtering (matching Reports.tsx)',
#             'authMethod': 'Bearer token authentication'
#         }), 500


# @app.route('/health', methods=['GET'])
# def health():
#     """Health check endpoint"""
#     return jsonify({'status': 'healthy', 'service': 'daily-reports'}), 200


# if __name__ == '__main__':
#     port = int(os.getenv('PORT', 5000))
#     app.run(host='0.0.0.0', port=port, debug=False)

























"""
Daily Reports Email Service
Converts Supabase Edge Function to Python Flask server
Works locally and on Render
Uses AWS SES API instead of SMTP
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

# Initialize Supabase client with custom options to avoid proxy parameter issue
from supabase.lib.client_options import ClientOptions


# Import template generators
from template1 import generate_template1_html
from template2 import generate_template2_html
from template3 import generate_template3_html

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CONFIGURATION VARIABLES
# Load environment variables from a .env file (if present). This must run before any os.getenv/os.environ usage.
load_dotenv()
TEST_EMAIL = os.getenv("TEST_EMAIL")  # Set to None or empty to disable test mode
TEMPLATE_NO = int(os.getenv("TEMPLATE_NO", "1"))  # 1, 2, or 3


# Create client options without proxy
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


def escape_csv(value: Any) -> str:
    """Escape CSV values properly"""
    if value is None or value == "":
        return ""
    
    str_value = str(value).strip()
    
    # Check if escaping is needed
    if re.search(r'[,"\n\r]', str_value):
        # Escape quotes and remove newlines
        escaped = str_value.replace('"', '""').replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
        return f'"{escaped}"'
    
    return str_value


def generate_no_data_email_html(location_name: str, today_str: str, test_email: Optional[str]) -> str:
    """Generate HTML for no-data notification email"""
    test_banner = f"""
    <div style="background-color: #ff9800; color: white; padding: 12px 24px; text-align: center; font-weight: bold;">
      🧪 TEST MODE - This is a test email
    </div>
    """ if test_email else ""
    
    test_footer = f'<p style="margin: 8px 0 0 0; color: #ff9800; font-size: 12px; font-weight: bold;">🧪 Test email sent to: {test_email}</p>' if test_email else ""
    
    return f"""
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
      <h1 style="margin: 0; font-size: 28px; font-weight: 600;">🔭 No Data Today</h1>
      <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">{today_str}</p>
    </div>
    
    <div style="padding: 40px 24px;">
      <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; border-radius: 4px; margin-bottom: 24px;">
        <h2 style="margin: 0 0 8px 0; font-size: 18px; color: #333;">📍 Location: {location_name}</h2>
        <p style="margin: 0; color: #666; font-size: 14px;">No approved transactions were recorded for today.</p>
      </div>
      
      <div style="text-align: center; padding: 20px; background-color: #fff3cd; border-radius: 4px; border: 1px solid #ffc107;">
        <p style="margin: 0; color: #856404; font-size: 15px;">
          ℹ️ There are no approved logs to report for {today_str}.
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


def fetch_today_filtered_logs(location_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch today's filtered logs using database-level filtering"""
    logger.info(f"🔍 Fetching today's logs for location: {location_id or 'All locations'}")
    
    # Build the logs query
    query = supabase.table('logs-man').select('*')
    
    # Apply approval status filter
    query = query.eq('approval_status', 'approved')
    
    # Apply location filter if specified
    if location_id:
        query = query.eq('location_id', location_id)
    
    # Apply date range filter for today
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)
    start_of_day = today.isoformat()
    end_of_day = (today + timedelta(days=1)).isoformat()
    
    query = query.gte('created_at', start_of_day).lt('created_at', end_of_day)
    
    logger.info(f"📅 Filtering for date range: {start_of_day} to {end_of_day}")
    
    response = query.execute()
    
    if hasattr(response, 'error') and response.error:
        logger.error(f'❌ Error fetching filtered logs: {response.error}')
        raise Exception(f"Failed to fetch logs: {response.error}")
    
    logs = response.data or []
    logger.info(f"📊 Found {len(logs)} approved logs for today")
    
    return logs


def analyze_data(logs: List[Dict[str, Any]], locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate comprehensive data analysis"""
    logger.info(f"🔍 Analyzing {len(logs)} log entries...")
    
    total_revenue = sum(log.get('Amount', 0) for log in logs)
    total_vehicles = len(logs)
    avg_service = total_revenue / total_vehicles if total_vehicles > 0 else 0
    
    logger.info(f"💰 Analysis summary: ₹{total_revenue} revenue, {total_vehicles} vehicles, ₹{avg_service:.2f} avg")
    
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
        
        # Track UPI accounts
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
    
    # Calculate percentages
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
    
    # Calculate service revenue shares
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
    
    # Calculate vehicle percentages
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
    
    # Find peak metrics
    peak_hour = max(hourly_breakdown, key=lambda x: x['revenue'])
    service_list = list(service_breakdown.values())
    peak_service = max(service_list, key=lambda x: x['revenue']) if service_list else {'name': 'N/A', 'revenue': 0}
    
    # Convert to arrays
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
    logger.info(f"📄 Generating main report CSV for {len(logs)} logs...")
    
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
    logger.info("💳 Generating payment breakdown CSV...")
    
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
    logger.info("🛠️ Generating service breakdown CSV...")
    
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
                       test_email: Optional[str], template_no: int) -> str:
    """Generate email HTML using selected template"""
    if template_no == 3:
        return generate_template3_html(analysis, location_name, today_str, test_email)
    elif template_no == 2:
        return generate_template2_html(analysis, location_name, today_str, test_email)
    else:
        return generate_template1_html(analysis, location_name, today_str, test_email)


def send_email_with_attachments_ses(from_email: str, to_email: str, subject: str, 
                                    html_content: str, text_content: str, 
                                    attachments: List[Dict[str, Any]]) -> None:
    """Send email with attachments using AWS SES API"""
    
    # Create a multipart/mixed parent container
    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    
    # Create a multipart/alternative child container for the body
    msg_body = MIMEMultipart('alternative')
    
    # Add text and HTML parts
    text_part = MIMEText(text_content, 'plain', 'utf-8')
    html_part = MIMEText(html_content, 'html', 'utf-8')
    
    msg_body.attach(text_part)
    msg_body.attach(html_part)
    
    # Attach the multipart/alternative child container to the multipart/mixed parent
    msg.attach(msg_body)
    
    # Add attachments
    for attachment in attachments:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment['content'].encode('utf-8'))
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={attachment["filename"]}')
        msg.attach(part)
    
    # Send the email using SES
    try:
        ses = get_ses_client()
        response = ses.send_raw_email(
            Source=from_email,
            Destinations=[to_email],
            RawMessage={'Data': msg.as_string()}
        )
        logger.info(f"✅ SES API response: MessageId {response['MessageId']}")
        return response
    except ClientError as e:
        logger.error(f"❌ SES API error: {e.response['Error']['Message']}")
        raise Exception(f"Failed to send email via SES: {e.response['Error']['Message']}")


@app.route('/send-reports', methods=['POST'])
def send_reports():
    """Main endpoint to send daily reports"""
    
    # Check authorization
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.error('❌ Unauthorized: Missing or invalid Authorization header')
        return jsonify({
            'success': False,
            'error': 'Unauthorized - Missing or invalid Authorization header',
            'message': 'Please provide a valid Authorization header with Bearer token'
        }), 401
    
    # Verify token
    token = auth_header.replace('Bearer ', '')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    if token not in [service_key, anon_key]:
        logger.error('❌ Unauthorized: Invalid token')
        return jsonify({
            'success': False,
            'error': 'Unauthorized - Invalid token',
            'message': 'The provided token is not valid'
        }), 401
    
    logger.info('✅ Authorization verified successfully')
    
    try:
        logger.info("🚀 Starting daily reports generation...")
        
        test_email = TEST_EMAIL
        template_no = TEMPLATE_NO
        
        if test_email:
            logger.info(f"🧪 TEST MODE ENABLED: Will send to {test_email} only")
        else:
            logger.info("📧 PRODUCTION MODE: Will send to all owners")
        
        logger.info(f"🎨 Using Template {template_no}")
        
        # Validate environment variables
        required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'SES_VERIFIED_FROM']
        for var in required_vars:
            if not os.getenv(var):
                raise Exception(f"Missing required environment variable: {var}")
        
        from_email = os.getenv('SES_VERIFIED_FROM')
        
        # Validate email format
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        clean_email = re.search(r'<([^>]+)>', from_email)
        clean_email = clean_email.group(1) if clean_email else from_email
        
        if not re.match(email_regex, clean_email):
            raise Exception(f"Invalid email format in SES_VERIFIED_FROM: {from_email}")
        
        logger.info(f"📧 Using FROM email: {from_email}")
        
        # Get today's date
        today = datetime.now()
        today_str = today.strftime("%d/%m/%Y")
        
        logger.info(f"📅 Generating reports for date: {today_str}")
        
        # Get owners
        if test_email:
            owners = [{
                'id': 'test-owner',
                'email': "a6hinandh@gmail.com",
                'assigned_location': None,
                'role': 'owner',
                'name': 'Test Owner'
            }]
            logger.info(f"🧪 Using test owner: {test_email}")
        else:
            response = supabase.table('users').select('id,email,assigned_location,role,name').eq('role', 'owner').execute()
            owners = response.data
            logger.info(f"👥 Found {len(owners) if owners else 0} owners")
        
        # Get locations
        response = supabase.table('locations').select('*').execute()
        locations = response.data
        
        if not locations:
            raise Exception("Failed to fetch locations")
        
        logger.info(f"📍 Found {len(locations)} locations")
        
        # Verify SES connection
        try:
            ses = get_ses_client()
            # Test SES by getting sending quota
            quota = ses.get_send_quota()
            logger.info(f"✅ SES connection verified. Daily quota: {quota['Max24HourSend']}, sent today: {quota['SentLast24Hours']}")
        except Exception as e:
            logger.error(f"❌ SES verification failed: {e}")
            raise Exception(f"SES configuration invalid: {str(e)}")
        
        emails_sent = 0
        email_results = []
        
        # Process each owner
        for owner in (owners or []):
            if not owner.get('email'):
                logger.info(f"⏭️ Skipping owner {owner['id']}: no email")
                email_results.append({
                    'owner': owner.get('name', owner['id']),
                    'email': owner.get('email', 'No email'),
                    'status': 'skipped',
                    'reason': 'No email address'
                })
                continue
            
            # Determine location context
            current_location = None
            if owner['role'] == 'manager':
                current_location = owner.get('assigned_location')
            elif owner['role'] == 'owner' and owner.get('assigned_location'):
                current_location = owner.get('assigned_location')
            
            logger.info(f"👤 Processing owner {owner['email']} (Role: {owner['role']}, Location: {current_location or 'All locations'})")
            
            # Fetch logs
            try:
                owner_today_logs = fetch_today_filtered_logs(current_location)
            except Exception as e:
                logger.error(f"❌ Failed to fetch logs for owner {owner['email']}: {e}")
                email_results.append({
                    'owner': owner.get('name', owner['email']),
                    'email': owner['email'],
                    'status': 'failed',
                    'error': f"Failed to fetch data: {str(e)}"
                })
                continue
            
            # Determine location name
            location_name = "All Locations"
            if current_location:
                for loc in locations:
                    if loc['id'] == current_location:
                        location_name = loc['name']
                        break
            
            # Send no-data email if no logs
            if len(owner_today_logs) == 0:
                logger.info(f"🔭 Sending no-data notification to {owner['email']} for {location_name}")
                try:
                    no_data_html = generate_no_data_email_html(location_name, today_str, test_email)
                    no_data_text = f"""{'[TEST] ' if test_email else ''}No Data Report - {today_str}

Location: {location_name}
Status: No approved transactions recorded for today.

Generated on: {datetime.now().strftime("%d/%m/%Y at %H:%M")}
{'🧪 Test Mode: Sent to ' + test_email if test_email else ''}"""
                    
                    send_email_with_attachments_ses(
                        from_email,
                        owner['email'],
                        f"{'[TEST] ' if test_email else ''}🔭 No Data Today - {today_str} - {location_name}",
                        no_data_html,
                        no_data_text,
                        []
                    )
                    
                    emails_sent += 1
                    logger.info(f"✅ No-data email sent to {owner['email']}")
                    email_results.append({
                        'owner': owner.get('name', owner['email']),
                        'email': owner['email'],
                        'status': 'success',
                        'recordCount': 0,
                        'revenue': 0,
                        'location': location_name,
                        'emailType': 'no-data'
                    })
                except Exception as e:
                    logger.error(f"❌ Failed to send no-data email to {owner['email']}: {e}")
                    email_results.append({
                        'owner': owner.get('name', owner['email']),
                        'email': owner['email'],
                        'status': 'failed',
                        'error': str(e)
                    })
                continue
            
            # Send full report
            try:
                logger.info(f"📄 Processing {owner['email']} - {len(owner_today_logs)} approved records for {location_name} (Template {template_no})")
                
                # Generate analysis
                analysis = analyze_data(owner_today_logs, locations)
                
                # Generate CSVs
                report_csv = generate_report_csv(owner_today_logs, locations)
                payment_csv = generate_payment_breakdown_csv(owner_today_logs)
                service_csv = generate_service_breakdown_csv(owner_today_logs)
                
                # Generate HTML
                html_content = generate_email_html(analysis, location_name, today_str, test_email, template_no)
                
                # Generate text version
                text_content = f"""{'[TEST] ' if test_email else ''}{'Business Intelligence Report' if template_no == 3 else 'Daily Business Report'} - {today_str}

Location: {location_name}
Total Revenue: ₹{analysis['totalRevenue']:,}  
{'Transactions' if template_no == 3 else 'Vehicles Served'}: {analysis['totalVehicles']}
Average {'Transaction' if template_no == 3 else 'Service'}: ₹{round(analysis['avgService'])}

PAYMENT BREAKDOWN:
{chr(10).join(f"{item['mode']}: ₹{item['revenue']:,} ({item['count']} {'transactions' if template_no == 3 else 'vehicles'}, {item['percentage']:.1f}%)" for item in analysis['paymentModeBreakdown'])}

SERVICE BREAKDOWN:
{chr(10).join(f"{item['service']}: {item['count']} {'services' if template_no == 3 else 'vehicles'}, ₹{item['revenue']:,} revenue (avg ₹{round(item['price'])})" for item in analysis['serviceBreakdown'])}

Template Used: {template_no} {'(Modern Business Intelligence)' if template_no == 3 else ''}
Generated on: {datetime.now().strftime("%d/%m/%Y at %H:%M")}
{'🧪 Test Mode: Sent to ' + test_email if test_email else ''}"""
                
                # Prepare attachments
                location_safe = re.sub(r'[^a-zA-Z0-9]', '-', location_name).lower()
                date_str = today.strftime("%Y-%m-%d")
                attachments = [
                    {
                        'filename': f"{'TEST_' if test_email else ''}{'transaction_report' if template_no == 3 else 'daily_report'}_{date_str}_{location_safe}.csv",
                        'content': report_csv
                    },
                    {
                        'filename': f"{'TEST_' if test_email else ''}payment_{'analytics' if template_no == 3 else 'breakdown'}_{date_str}_{location_safe}.csv",
                        'content': payment_csv
                    },
                    {
                        'filename': f"{'TEST_' if test_email else ''}service_{'performance' if template_no == 3 else 'breakdown'}_{date_str}_{location_safe}.csv",
                        'content': service_csv
                    }
                ]
                
                # Send email using SES API
                send_email_with_attachments_ses(
                    from_email,
                    owner['email'],
                    f"{'[TEST] ' if test_email else ''}{'📊 Business Intelligence Report' if template_no == 3 else 'Daily Report'} - {today_str} - {location_name}",
                    html_content,
                    text_content,
                    attachments
                )
                
                emails_sent += 1
                logger.info(f"✅ Email sent to {owner['email']} ({len(owner_today_logs)} approved records, ₹{analysis['totalRevenue']:,}, {len(attachments)} attachments, Template {template_no})")
                
                email_results.append({
                    'owner': owner.get('name', owner['email']),
                    'email': owner['email'],
                    'status': 'success',
                    'recordCount': len(owner_today_logs),
                    'revenue': analysis['totalRevenue'],
                    'location': location_name,
                    'attachments': len(attachments),
                    'templateUsed': template_no,
                    'emailType': 'full-report'
                })
            except Exception as e:
                logger.error(f"❌ Failed to send email to {owner['email']}: {e}")
                email_results.append({
                    'owner': owner.get('name', owner['email']),
                    'email': owner['email'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Get total approved logs
        total_approved_logs = fetch_today_filtered_logs()
        
        logger.info(f"🎉 Daily reports completed. Emails sent: {emails_sent}/{len(owners) if owners else 0} using Template {template_no}")
        logger.info(f"📊 Total approved logs for today: {len(total_approved_logs)}")
        
        return jsonify({
            'success': True,
            'message': f"✅ {'Modern business intelligence reports' if template_no == 3 else 'Daily reports'} sent successfully {'(TEST MODE)' if test_email else ''} using Template {template_no}",
            'emailsSent': emails_sent,
            'totalOwners': len(owners) if owners else 0,
            'todayLogsCount': len(total_approved_logs),
            'reportDate': today_str,
            'testMode': bool(test_email),
            'testEmail': test_email,
            'templateUsed': template_no,
            'attachmentsPerEmail': 3,
            'filteringApproach': 'Database-level filtering (matching Reports.tsx)',
            'authMethod': 'Bearer token authentication',
            'deliveryMethod': 'AWS SES API',
            'noDataEmailsEnabled': True,
            'results': email_results
        }), 200
        
    except Exception as err:
        logger.error(f"❌ Error: {err}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(err),
            'testMode': bool(TEST_EMAIL),
            'templateUsed': TEMPLATE_NO,
            'filteringApproach': 'Database-level filtering (matching Reports.tsx)',
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