from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io
import os
import base64
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///consent_forms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class ConsentForm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    procedure = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='draft')
    signatures = db.relationship('Signature', backref='consent_form', lazy=True)

class Signature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consent_form_id = db.Column(db.Integer, db.ForeignKey('consent_form.id'), nullable=False)
    signer_type = db.Column(db.String(20), nullable=False)  # patient, nurse, doctor
    signature_data = db.Column(db.Text, nullable=False)  # base64 encoded signature
    signed_at = db.Column(db.DateTime, default=datetime.utcnow)
    signer_name = db.Column(db.String(100))

# Create tables
with app.app_context():
    db.create_all()

# Sample users for demo (in production, use proper authentication)
USERS = {
    'nurse': {'password': 'nurse123', 'role': 'nurse', 'name': 'Nurse Jane Smith'},
    'doctor': {'password': 'doctor123', 'role': 'doctor', 'name': 'Dr. John Davis'}
}

@app.route('/')
def index():
    """Home page - list all consent forms"""
    forms = ConsentForm.query.all()
    return render_template('index.html', forms=forms)

@app.route('/consent/new', methods=['GET', 'POST'])
def new_consent():
    """Create new consent form"""
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        procedure = request.form['procedure']
        
        new_form = ConsentForm(patient_name=patient_name, procedure=procedure)
        db.session.add(new_form)
        db.session.commit()
        
        session['current_form_id'] = new_form.id
        return redirect(url_for('signature_page'))
    
    return render_template('consent_form.html')

@app.route('/signature')
def signature_page():
    """Signature workflow page"""
    form_id = session.get('current_form_id')
    if not form_id:
        return redirect(url_for('new_consent'))
    
    consent_form = ConsentForm.query.get(form_id)
    return render_template('signature.html', consent_form=consent_form)

@app.route('/api/signature/save', methods=['POST'])
def save_signature():
    """Save signature for current step"""
    form_id = session.get('current_form_id')
    if not form_id:
        return jsonify({'error': 'No active form'}), 400
    
    data = request.json
    signer_type = data.get('signer_type')
    signature_data = data.get('signature_data')
    
    # Remove data URL prefix if present
    if signature_data.startswith('data:image'):
        signature_data = re.sub('^data:image/.+;base64,', '', signature_data)
    
    # Save signature to database
    signature = Signature(
        consent_form_id=form_id,
        signer_type=signer_type,
        signature_data=signature_data
    )
    
    if signer_type == 'nurse':
        signature.signer_name = USERS.get('nurse', {}).get('name', 'Nurse')
    elif signer_type == 'doctor':
        signature.signer_name = USERS.get('doctor', {}).get('name', 'Doctor')
    
    db.session.add(signature)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/login', methods=['POST'])
def login():
    """Handle nurse/doctor login"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = USERS.get(username)
    if user and user['password'] == password:
        session['user'] = {
            'username': username,
            'role': user['role'],
            'name': user['name']
        }
        return jsonify({'success': True, 'user': session['user']})
    
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/logout')
def logout():
    """Logout current user"""
    session.pop('user', None)
    return jsonify({'success': True})

@app.route('/generate-pdf/<int:form_id>')
def generate_pdf(form_id):
    """Generate PDF for completed consent form"""
    consent_form = ConsentForm.query.get_or_404(form_id)
    signatures = Signature.query.filter_by(consent_form_id=form_id).all()
    
    # Create PDF in memory
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle(f"Consent Form - {consent_form.patient_name}")
    
    # Add content to PDF
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(100, 750, "MEDICAL CONSENT FORM")
    pdf.line(100, 745, 500, 745)
    
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 720, f"Patient Name: {consent_form.patient_name}")
    pdf.drawString(100, 700, f"Procedure: {consent_form.procedure}")
    pdf.drawString(100, 680, f"Date: {consent_form.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    y_position = 650
    for signature in signatures:
        pdf.drawString(100, y_position, f"{signature.signer_type.title()} Signature:")
        
        # Decode and add signature image
        try:
            signature_img = ImageReader(io.BytesIO(base64.b64decode(signature.signature_data)))
            pdf.drawImage(signature_img, 100, y_position - 50, width=200, height=40)
        except:
            pdf.drawString(120, y_position - 30, "[Signature Image]")
        
        pdf.drawString(350, y_position - 30, f"Signed by: {signature.signer_name}")
        pdf.drawString(350, y_position - 45, f"At: {signature.signed_at.strftime('%H:%M')}")
        
        y_position -= 100
    
    pdf.save()
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"consent_form_{consent_form.patient_name.replace(' ', '_')}.pdf",
        mimetype='application/pdf'
    )

@app.route('/api/form/status/<int:form_id>')
def get_form_status(form_id):
    """Get current signature status for a form"""
    consent_form = ConsentForm.query.get_or_404(form_id)
    signatures = {sig.signer_type: True for sig in consent_form.signatures}
    
    return jsonify({
        'patient_signed': 'patient' in signatures,
        'nurse_signed': 'nurse' in signatures,
        'doctor_signed': 'doctor' in signatures,
        'completed': len(signatures) == 3
    })

if __name__ == '__main__':
    # Run in debug mode for development
    # For production, use: app.run(host='0.0.0.0', port=5000, debug=False)
    app.run(debug=True)
