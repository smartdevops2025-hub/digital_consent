import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a_fallback_secret_key')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///consent.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model for nurses and doctors
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'nurse' or 'doctor'

# Consent model
class Consent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    procedure = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    relative_signature = db.Column(db.Text, nullable=True)
    nurse_signature = db.Column(db.Text, nullable=True)
    doctor_signature = db.Column(db.Text, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)

# Create the database and default users
with app.app_context():
    db.create_all()
    # Create default users if they don't exist
    if not User.query.filter_by(username='nurse').first():
        nurse = User(username='nurse', password_hash=generate_password_hash('nurse123'), role='nurse')
        db.session.add(nurse)
    if not User.query.filter_by(username='doctor').first():
        doctor = User(username='doctor', password_hash=generate_password_hash('doctor123'), role='doctor')
        db.session.add(doctor)
    db.session.commit()

# Routes
@app.route('/')
def index():
    return redirect(url_for('consent_form'))

@app.route('/consent_form', methods=['GET', 'POST'])
def consent_form():
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        procedure = request.form['procedure']
        
        new_consent = Consent(patient_name=patient_name, procedure=procedure)
        db.session.add(new_consent)
        db.session.commit()
        
        session['consent_id'] = new_consent.id
        return redirect(url_for('signature', step='relative'))
    
    return render_template('consent_form.html')

@app.route('/signature/<step>', methods=['GET', 'POST'])
def signature(step):
    consent_id = session.get('consent_id')
    if not consent_id:
        return redirect(url_for('consent_form'))
    
    consent = Consent.query.get(consent_id)
    if not consent:
        return redirect(url_for('consent_form'))
    
    if request.method == 'POST':
        signature_data = request.form['signature_data']
        
        if step == 'relative':
            consent.relative_signature = signature_data
        elif step == 'nurse':
            consent.nurse_signature = signature_data
        elif step == 'doctor':
            consent.doctor_signature = signature_data
            consent.is_completed = True
        
        db.session.commit()
        
        # Determine next step
        if step == 'relative':
            return redirect(url_for('login', role='nurse'))
        elif step == 'nurse':
            return redirect(url_for('login', role='doctor'))
        elif step == 'doctor':
            return redirect(url_for('generate_pdf', consent_id=consent.id))
    
    return render_template('signature.html', step=step)

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username, role=role).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_role'] = role
            return redirect(url_for('signature', step=role))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html', role=role)

@app.route('/generate_pdf/<int:consent_id>')
def generate_pdf(consent_id):
    consent = Consent.query.get(consent_id)
    if not consent:
        return "Consent not found", 404
    
    # Create a PDF
    pdf_buffer = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    c = canvas.Canvas(pdf_buffer.name, pagesize=letter)
    
    # Add content to PDF
    c.drawString(100, 750, "Digital Consent Form")
    c.drawString(100, 730, f"Patient: {consent.patient_name}")
    c.drawString(100, 710, f"Procedure: {consent.procedure}")
    c.drawString(100, 690, f"Date: {consent.date_created.strftime('%Y-%m-%d %H:%M')}")
    
    # Add signatures
    y = 670
    if consent.relative_signature:
        c.drawString(100, y, "Patient/Relative Signature: Received")
        y -= 20
    if consent.nurse_signature:
        c.drawString(100, y, "Nurse Signature: Received")
        y -= 20
    if consent.doctor_signature:
        c.drawString(100, y, "Doctor Signature: Received")
        y -= 20
    
    c.save()
    
    # For now, we just offer the PDF for download. In a real scenario, you would upload to HIS EMR.
    return send_file(pdf_buffer.name, as_attachment=True, download_name=f"consent_{consent_id}.pdf")

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port, debug=os.environ.get('DEBUG', False))
