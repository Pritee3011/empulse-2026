from flask import Flask, render_template, request, flash, redirect, url_for
from flask_pymongo import PyMongo
from flask_mail import Mail, Message
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
app.secret_key = os.environ.get("SECRET_KEY", "empulse_voyage_2026_secure_key")

# 1. Cloudinary Setup
cloudinary.config( 
    cloud_name = os.environ.get("CLOUDINARY_NAME"), 
    api_key = os.environ.get("CLOUDINARY_KEY"), 
    api_secret = os.environ.get("CLOUDINARY_SECRET") 
)

# 2. MongoDB Setup
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
mongo = PyMongo(app)

# 3. Mail Setup
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=False,         # Disabled TLS
    MAIL_USE_SSL=True,          # Enabled SSL
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"), # 16-character App Password
    MAX_CONTENT_LENGTH=5 * 1024 * 1024
)
mail = Mail(app)

# --- HELPER FUNCTIONS ---

def send_async_email(app, msg):
    """Sends email in a background thread to prevent the UI from hanging."""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Background Mail Error: {e}")

# --- ANTI-SLEEP HEARTBEAT ---

def pulse_check():
    """Pings the app every 14 minutes to prevent Render Free Tier sleep."""
    RENDER_URL = "https://empulse-2026.onrender.com/"
    time.sleep(30)
    while True:
        try:
            requests.get(RENDER_URL, timeout=10)
        except Exception:
            pass
        time.sleep(840) 

threading.Thread(target=pulse_check, daemon=True).start()

# --- DIGITAL IMPRESSION TRACKER ---

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
            {"$set": {"last_visited": datetime.now(), "user_agent": user_agent}, "$inc": {"visit_count": 1}},
            upsert=True
        )
    except Exception as e:
        print(f"Stats Error: {e}")

# --- CORE ROUTES ---

@app.route('/')
def home(): return render_template('index.html')

@app.route('/events')
def events(): return render_template('events.html')

@app.route('/register')
def register(): return render_template('register.html')

@app.route('/success')
def success_page():
    event = request.args.get('event', 'Registration')
    uid = request.args.get('uid', '')
    return render_template('success.html', event=event, unique_id=uid)

# Rulebook Routes
@app.route('/events/hackathon')
def hackathon_rules(): return render_template('hackathon.html')

@app.route('/events/investify')
def investify_rules(): return render_template('investify.html')

@app.route('/events/wreckage')
def wreckage_rules(): return render_template('wreckage.html')

@app.route('/events/table-talks')
def table_talks_rules(): return render_template('table-talks.html')

@app.route('/events/bollywood-pitch')
def bollywood_rules(): return render_template('bollywood-pitch.html')

@app.route('/events/startup-showcase')
def startup_showcase_rules(): return render_template('startup-showcase.html')

# --- SUBMISSION HANDLERS ---

@app.route('/submit_registration', methods=['POST'])
def submit():
    form_data = request.form.to_dict()
    raw_event_name = form_data.get('event_name', 'General_Registrations')
    collection_name = raw_event_name.lower().replace(" ", "_").replace("’", "").replace("'", "")

    # Cloudinary Upload
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

    form_data['timestamp'] = datetime.now()
    mongo.db[collection_name].insert_one(form_data)

    # Email Logic
    recipients = [form_data.get(f'm{i}_email') for i in range(1, 6) if form_data.get(f'm{i}_email')]
    recipients = list(set([e for e in recipients if "@" in e]))

    if recipients:
        msg = Message(subject=f"Registration Confirmed: {raw_event_name}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=recipients)
        
        msg.body = f"Greetings Team {form_data.get('team_name')}, your registration is confirmed. Join WhatsApp: https://chat.whatsapp.com/F2JN4fCz50P2prDJqpas2S"
        
        msg.html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 10px; overflow: hidden;">
            <div style="background: #8b4513; color: white; padding: 20px; text-align: center;"><h1>Voyage Confirmed!</h1></div>
            <div style="padding: 20px;">
                <p>Greetings Team <strong>{form_data.get('team_name')}</strong>,</p>
                <p>Your registration for <strong>{raw_event_name}</strong> has been recorded successfully.</p>
                <div style="background: #e8f5e9; border-left: 5px solid #25d366; padding: 15px; margin: 20px 0;">
                    <strong>⚓ Stay Updated:</strong><br>Join the WhatsApp community: <br>
                    <a href="https://chat.whatsapp.com/F2JN4fCz50P2prDJqpas2S" style="display: inline-block; margin-top: 10px; padding: 10px 15px; background: #25d366; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Join Community</a>
                </div>
                <p>Regards,<br><strong>Team E-Cell Yukta</strong></p>
            </div>
        </div>
        """
        threading.Thread(target=send_async_email, args=(app, msg)).start()

    return redirect(url_for('success_page', event=raw_event_name))

@app.route('/submit_showcase', methods=['POST'])
def submit_showcase():
    data = request.form.to_dict()
    unique_id = f"ECYUKTA-2026-{str(uuid.uuid4())[:4].upper()}"
    data['unique_id'], data['registration_date'] = unique_id, datetime.now()

    mongo.db.startup_showcase.insert_one(data)

    msg = Message(f"Startup Showcase ID: {unique_id}",
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[data['email']])
    msg.body = f"Hello {data['full_name']}, Your ID is: {unique_id}. Join WhatsApp: https://chat.whatsapp.com/F2JN4fCz50P2prDJqpas2S"
    
    threading.Thread(target=send_async_email, args=(app, msg)).start()
    return redirect(url_for('success_page', event="Startup Showcase", uid=unique_id))

@app.errorhandler(413)
def request_entity_too_large(error):
    return "<h1>File too large (Max 5MB)</h1><a href='/register'>Try Again</a>", 413

if __name__ == '__main__':
    app.run(debug=True)
