from flask import Flask, render_template, request, flash, redirect, url_for
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
import os
import uuid 
import threading
import requests
import time
import cloudinary
import cloudinary.uploader
from datetime import datetime

app = Flask(__name__)

# --- SECURE CONFIGURATION ---
# Use a random secret key for production
app.secret_key = os.environ.get("SECRET_KEY", "empulse_voyage_2026_default_key")

# 1. Cloudinary Setup (Variables pulled from Render Environment)
cloudinary.config( 
  cloud_name = os.environ.get("CLOUDINARY_NAME"), 
  api_key = os.environ.get("CLOUDINARY_KEY"), 
  api_secret = os.environ.get("CLOUDINARY_SECRET") 
)

# 2. Render Heartbeat Setup
RENDER_EXTERNAL_URL = "https://empulse-2026.onrender.com/" 

# 3. MongoDB Setup
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
mongo = PyMongo(app)

app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("MAIL_DEFAULT_SENDER")

# Security: Limit uploads to 5MB
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# --- ANTI-SLEEP HEARTBEAT ---
def pulse_check():
    """Pings the app every 14 minutes to prevent Render Free Tier sleep."""
    time.sleep(30)
    while True:
        try:
            # We use the URL to 'poke' the server from the inside
            requests.get(RENDER_EXTERNAL_URL, timeout=10)
        except Exception as e:
            print(f"Heartbeat failed: {e}")
        time.sleep(840) # 14 Minutes

threading.Thread(target=pulse_check, daemon=True).start()

# --- DIGITAL IMPRESSION TRACKER (UNIQUE IP) ---
@app.before_request
def log_visitor_impression():
    user_agent = request.headers.get('User-Agent', '')
    if (request.path.startswith('/static') or request.path == '/favicon.ico' or "python-requests" in user_agent.lower()):
        return

    ip_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_addr:
        ip_addr = ip_addr.split(',')[0] 

    try:
        mongo.db.unique_visitors.update_one(
            {"ip_address": ip_addr},
            {
                "$set": {
                    "last_visited": datetime.now(),
                    "user_agent": user_agent 
                },
                "$inc": {"visit_count": 1} 
            },
            upsert=True
        )
    except Exception as e:
        print(f"Stats Error: {e}")

# --- CORE ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/events')
def events():
    return render_template('events.html')

@app.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')

@app.route('/speakers')
def speakers():
    return render_template('speakers.html')

@app.route('/sponsors')
def sponsors():
    return render_template('sponsors.html')

@app.route('/agenda')
def agenda():
    return render_template('agenda.html')

@app.route('/register')
def register():
    return render_template('register.html')

# --- EVENT RULEBOOK ROUTES ---
@app.route('/events/hackathon')
def hackathon_rules():
    return render_template('hackathon.html')

@app.route('/events/investify')
def investify_rules():
    return render_template('investify.html')

@app.route('/events/wreckage')
def wreckage_rules():
    return render_template('wreckage.html')

@app.route('/events/table-talks')
def table_talks_rules():
    return render_template('table-talks.html')

@app.route('/events/bollywood-pitch')
def bollywood_rules():
    return render_template('bollywood-pitch.html')

@app.route('/events/startup-showcase')
def startup_showcase_rules():
    return render_template('startup-showcase.html')
# --- REGISTRATION SUBMISSION ---
@app.route('/submit_registration', methods=['POST'])
def submit():
    form_data = request.form.to_dict()
    raw_event_name = form_data.get('event_name', 'General_Registrations')
    collection_name = raw_event_name.lower().replace(" ", "_").replace("’", "").replace("'", "")

    # --- File Upload ---
    if 'screenshot' in request.files:
        file = request.files['screenshot']
        if file and file.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder=f"empulse_2026/{collection_name}",
                    public_id=f"{form_data.get('team_name', 'unknown')}_{uuid.uuid4().hex[:4]}"
                )
                form_data['payment_proof_url'] = upload_result['secure_url']
            except Exception as e:
                print(f"Upload failed: {e}")
                form_data['payment_proof_url'] = "Failed_to_upload"

    # --- Save to DB ---
    form_data['timestamp'] = datetime.now()
    mongo.db[collection_name].insert_one(form_data)

    # --- Prepare email recipients ---
    recipients = [form_data.get(f'm{i}_email') for i in range(1, 6) if form_data.get(f'm{i}_email')]
    recipients = list(set([e for e in recipients if "@" in e]))

    # --- Send Email via SendGrid API ---
    if recipients:
        subject = f"Registration Confirmed: {raw_event_name}"
        content = f"""Greetings Team {form_data.get('team_name')},

Your registration for {raw_event_name} has been successfully recorded.

Regards,
E-Cell Yukta"""

        threading.Thread(
            target=send_email_api,
            args=(recipients, subject, content)
        ).start()

    # --- Instant Response ---
    return render_template('success.html', event=raw_event_name)
def send_email_api(to_emails, subject, content):
    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {os.environ.get('MAIL_PASSWORD')}",
                "Content-Type": "application/json"
            },
            json={
                "personalizations": [
                    {
                        "to": [{"email": email} for email in to_emails]
                    }
                ],
                "from": {
                    "email": os.environ.get("MAIL_DEFAULT_SENDER")
                },
                "subject": subject,
                "content": [
                    {
                        "type": "text/plain",
                        "value": content
                    }
                ]
            }
        )

        print("SendGrid Status:", response.status_code)

    except Exception as e:
        print("Email API failed:", e)
# --- STARTUP SHOWCASE ---
@app.route('/events/register-showcase')
def showcase_reg_page():
    return render_template('startup-reg.html')

@app.route('/submit_showcase', methods=['POST'])
def submit_showcase():
    data = request.form.to_dict()
    unique_id = f"ECYUKTA-2026-{str(uuid.uuid4())[:4].upper()}"
    data['unique_id'] = unique_id
    data['registration_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    mongo.db.startup_showcase.insert_one(data)

    try:
        if data.get('email'):
            subject = f"Startup Showcase ID: {unique_id}"
            content = f"""Hello {data['full_name']},

Your Startup Showcase ID: {unique_id}

Regards,
E-Cell Yukta"""

            threading.Thread(
                target=send_email_api,
                args=([data['email']], subject, content)
            ).start()
    except Exception as e:
        print(f"Mail failed: {e}")
  
    return render_template('success.html', event="Startup Showcase", unique_id=unique_id)

@app.errorhandler(413)
def request_entity_too_large(error):
    return "<h1>File is too large!</h1><p>Please keep your screenshot under 5MB.</p><a href='/register'>Try Again</a>", 413

if __name__ == '__main__':
    app.run(debug=True, port=5000)
