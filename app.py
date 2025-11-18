from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import sqlite3
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch
import io
import shutil
import base64
import requests
import json
import re
import hashlib

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Add this line
app.secret_key = 'mes_medical_college_digital_consent_system_2024'
app.config['UPLOAD_FOLDER'] = 'static/consent_forms'
app.config['GENERATED_FOLDER'] = 'generated_pdfs'
app.config['STATIC_FOLDER'] = 'static'
app.config['MALAYALAM_FONT'] = 'Helvetica'  # Default fallback

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)
os.makedirs(app.config['STATIC_FOLDER'], exist_ok=True)

# Hash password function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Default admin credentials
DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin123'

# Initialize users database
def init_users_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password_hash TEXT,
                  user_type TEXT,
                  full_name TEXT,
                  department TEXT,
                  is_active INTEGER DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  last_login TIMESTAMP)''')
    
    # Create default admin user if not exists
    c.execute('SELECT * FROM users WHERE username = ?', (DEFAULT_ADMIN_USERNAME,))
    if not c.fetchone():
        admin_password_hash = hash_password(DEFAULT_ADMIN_PASSWORD)
        c.execute('INSERT INTO users (username, password_hash, user_type, full_name, department, is_active) VALUES (?, ?, ?, ?, ?, ?)',
                  (DEFAULT_ADMIN_USERNAME, admin_password_hash, 'admin', 'System Administrator', 'IT', 1))
        print("✅ Created default admin user")
    
    # Create some default counsellors, nurses and doctors
    default_users = [
        ('counsellor1', 'password123', 'counsellor', 'Counsellor One', 'Counselling', 1),
        ('counsellor2', 'password123', 'counsellor', 'Counsellor Two', 'Counselling', 1),
        ('nurse1', 'nurse123', 'nurse', 'Nurse One', 'Nursing', 1),
        ('nurse2', 'nurse123', 'nurse', 'Nurse Two', 'Nursing', 1),
        ('doctor1', 'doctor123', 'doctor', 'Dr. Sajid', 'Surgery', 1),
        ('doctor2', 'doctor123', 'doctor', 'Dr. Rahman', 'Medicine', 1)
    ]
    
    for username, password, user_type, full_name, department, is_active in default_users:
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        if not c.fetchone():
            password_hash = hash_password(password)
            c.execute('INSERT INTO users (username, password_hash, user_type, full_name, department, is_active) VALUES (?, ?, ?, ?, ?, ?)',
                      (username, password_hash, user_type, full_name, department, is_active))
            print(f"✅ Created default user: {username}")
    
    conn.commit()
    conn.close()

# Initialize consent database with multi-signature support
def init_database():
    """Initialize the SQLite database with proper schema for multi-signature"""
    conn = sqlite3.connect('consents.db')
    c = conn.cursor()
    
    # Drop and recreate table to ensure all columns exist
    c.execute('DROP TABLE IF EXISTS consents')
    
    # Create new table with ALL required columns including multi-signature support
    c.execute('''CREATE TABLE consents
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  patient_name TEXT,
                  patient_age INTEGER,
                  patient_mrn TEXT,
                  consent_type TEXT,
                  original_pdf TEXT,
                  final_pdf TEXT,
                  patient_signature_data TEXT,
                  relative_signature_data TEXT,
                  nurse_signature_data TEXT,
                  doctor_signature_data TEXT,
                  counsellor_id TEXT,
                  signatory_name TEXT,
                  signatory_relation TEXT,
                  signatory_mobile TEXT,
                  consent_required_for TEXT,
                  consent_required_for_ml TEXT,
                  procedure_details TEXT,
                  procedure_details_ml TEXT,
                  doctor_name TEXT,
                  nurse_signed_by TEXT,
                  nurse_signed_at TIMESTAMP,
                  doctor_signed_by TEXT,
                  doctor_signed_at TIMESTAMP,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    print("✅ Created NEW database with MULTI-SIGNATURE support")
    
    conn.commit()
    conn.close()

# Get all users
def get_all_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id, username, user_type, full_name, department, is_active, created_at, last_login FROM users ORDER BY user_type, username')
    users = c.fetchall()
    conn.close()
    return users

# Get user by username
def get_user_by_username(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    return user

# Add new user
def add_user(username, password, user_type, full_name, department):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        password_hash = hash_password(password)
        c.execute('INSERT INTO users (username, password_hash, user_type, full_name, department, is_active) VALUES (?, ?, ?, ?, ?, ?)',
                  (username, password_hash, user_type, full_name, department, 1))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

# Update user
def update_user(user_id, username, user_type, full_name, department, is_active):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('UPDATE users SET username = ?, user_type = ?, full_name = ?, department = ?, is_active = ? WHERE id = ?',
                  (username, user_type, full_name, department, is_active, user_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

# Reset user password
def reset_user_password(user_id, new_password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    password_hash = hash_password(new_password)
    c.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
    conn.commit()
    conn.close()

# Delete user
def delete_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

# Update last login
def update_last_login(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('UPDATE users SET last_login = ? WHERE username = ?', (current_time, username))
    conn.commit()
    conn.close()

def setup_fonts():
    """Setup Malayalam fonts for PDF generation with better font detection"""
    fonts_dir = "fonts"
    os.makedirs(fonts_dir, exist_ok=True)
    
    # Check for common Malayalam fonts in order of preference
    malayalam_fonts = [
        "Manjari-Regular.ttf",
        "Manjari-Bold.ttf", 
        "NotoSansMalayalam-Regular.ttf",
        "NotoSansMalayalam-Bold.ttf",
        "Rachana-Regular.ttf", 
        "AnjaliOldLipi-Regular.ttf",
        "Arial Unicode MS.ttf"  # Fallback for Windows
    ]
    
    registered_fonts = []
    
    for font_file in malayalam_fonts:
        font_path = os.path.join(fonts_dir, font_file)
        if os.path.exists(font_path):
            try:
                font_name = font_file.replace('.ttf', '').replace('-', '')
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                registered_fonts.append(font_name)
                print(f"✅ Malayalam font loaded: {font_file} as '{font_name}'")
            except Exception as e:
                print(f"⚠️ Failed to load {font_file}: {e}")
    
    if registered_fonts:
        # Use the first successfully loaded font
        app.config['MALAYALAM_FONT'] = registered_fonts[0]
        print(f"✅ Primary Malayalam font set to: {app.config['MALAYALAM_FONT']}")
        return True
    else:
        print("❌ No Malayalam font found. Using system fallback.")
        # Try to use system fonts as fallback
        system_fonts = ['Arial', 'Helvetica']
        for font in system_fonts:
            try:
                pdfmetrics.registerFont(TTFont(font, font))
                print(f"✅ Using system font: {font}")
                app.config['MALAYALAM_FONT'] = font
                return True
            except:
                continue
        app.config['MALAYALAM_FONT'] = 'Helvetica'
        return False

def clean_text_for_pdf(text):
    """Clean text for PDF rendering - preserve Malayalam characters"""
    if not text:
        return ""
    
    # Remove black squares/dots and other unwanted characters but preserve Malayalam
    text = text.replace('■', '').replace('●', '').replace('•', '-')
    
    # Fix common encoding issues but preserve Unicode
    text = text.replace('\x00', '')  # Remove null characters
    
    # Normalize line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove extra whitespace but preserve meaningful spaces
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Clean each line but preserve Malayalam text
        cleaned_line = re.sub(r'[^\u0D00-\u0D7F\s\w\.,!?\-\(\)]', '', line)  # Keep Malayalam range + basic punctuation
        cleaned_line = re.sub(r' +', ' ', cleaned_line)
        cleaned_lines.append(cleaned_line.strip())
    
    return '\n'.join(cleaned_lines)

def draw_wrapped_text(can, text, x, y, max_width, font_name, font_size, line_height):
    """Draw text with proper wrapping - IMPROVED FOR MALAYALAM"""
    if not text:
        return y
    
    # Clean the text while preserving Malayalam
    text = clean_text_for_pdf(text)
    
    # Set font - use Malayalam font if available
    if font_name == "Malayalam" and 'MALAYALAM_FONT' in app.config:
        actual_font = app.config['MALAYALAM_FONT']
        # Use slightly larger font for better readability
        effective_font_size = max(font_size, 10)
    else:
        actual_font = font_name
        effective_font_size = font_size
        
    can.setFont(actual_font, effective_font_size)
    
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append("")
            continue
            
        # For Malayalam, we need to handle text differently
        words = paragraph.split(' ')
        current_line = []
        current_width = 0
        
        for word in words:
            try:
                word_width = can.stringWidth(word + ' ', actual_font, effective_font_size)
            except:
                # Fallback if font doesn't support the character
                word_width = len(word) * effective_font_size * 0.6
                
            if current_width + word_width <= max_width:
                current_line.append(word)
                current_width += word_width
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width
        
        if current_line:
            lines.append(' '.join(current_line))
    
    # Draw lines
    for line in lines:
        if y < 100:  # Bottom margin
            can.showPage()
            add_header_to_new_page(can, width, height)
            y = height - 150
        
        if line.strip():  # Only draw non-empty lines
            try:
                can.drawString(x, y, line)
            except Exception as e:
                print(f"Warning: Could not render text: {line[:50]}... Error: {e}")
                # Fallback: try with basic font
                try:
                    can.setFont("Helvetica", effective_font_size)
                    can.drawString(x, y, line)
                    can.setFont(actual_font, effective_font_size)  # Reset to original font
                except:
                    # Last resort: draw empty line
                    can.drawString(x, y, "")
        y -= line_height
    
    return y

def get_consent_types():
    """Get available consent types from template files"""
    consent_types = {}
    forms_folder = app.config['UPLOAD_FOLDER']
    
    if not os.path.exists(forms_folder):
        os.makedirs(forms_folder)
        # Create sample template files if none exist
        create_sample_templates(forms_folder)
        return get_consent_types()  # Recursive call to read the created templates
    
    for filename in os.listdir(forms_folder):
        if filename.lower().endswith('.txt'):
            # Create a nice display name
            display_name = filename.replace('.txt', '').replace('_', ' ').title()
            
            # Read template content
            template_path = os.path.join(forms_folder, filename)
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read().strip()
            except Exception as e:
                print(f"Error reading template {filename}: {e}")
                template_content = f"Template for {display_name}"
            
            consent_types[filename] = {
                'display_name': display_name,
                'template_content': template_content
            }
    
    return consent_types

def create_sample_templates(forms_folder):
    """Create sample consent template files if none exist"""
    sample_templates = {
        'surgical_consent.txt': """Procedure: Surgery
Description: The patient will undergo surgical procedure as recommended by the doctor.

Risks and Complications:
- Bleeding during or after surgery
- Infection at the surgical site
- Allergic reactions to anesthesia
- Blood clots
- Delayed healing
- Scar formation
- Need for additional procedures

Benefits:
- Resolution of medical condition
- Improved quality of life
- Pain relief
- Restoration of function

Alternatives:
- Conservative management with medications
- Physical therapy
- Non-surgical interventions
- No treatment (with understanding of risks)""",

        'anesthesia_consent.txt': """Procedure: Anesthesia Administration
Description: Administration of anesthesia for surgical procedure.

Risks and Complications:
- Allergic reactions to anesthetic drugs
- Breathing difficulties
- Nausea and vomiting
- Sore throat
- Dental injury
- Nerve injury
- Awareness during surgery
- Cardiovascular complications

Benefits:
- Pain-free surgical experience
- Patient comfort during procedure
- Controlled physiological state
- Facilitates surgical procedure""",

        'blood_transfusion.txt': """Procedure: Blood Transfusion
Description: Administration of blood or blood products.

Risks and Complications:
- Allergic reactions
- Fever and chills
- Transmission of infections
- Hemolytic reactions
- Fluid overload
- Iron overload
- Graft versus host disease

Benefits:
- Restoration of blood volume
- Improved oxygen carrying capacity
- Correction of coagulation disorders
- Life-saving in emergency situations

Alternatives:
- Volume expanders
- Iron supplements
- Erythropoietin therapy
- Autologous blood donation""",

        'lama_consent.txt': """Procedure: Leave Against Medical Advice (LAMA)
Description: Patient wishes to leave hospital against medical advice.

Risks and Complications:
- Worsening of medical condition
- Delayed treatment
- Complications from untreated condition
- Emergency situation developing at home
- Increased risk of mortality
- Financial implications of readmission

Acknowledgements:
- I understand the risks of leaving against medical advice
- I have been explained the consequences
- I take full responsibility for my decision
- I know I can return for treatment if needed"""
    }
    
    for filename, content in sample_templates.items():
        filepath = os.path.join(forms_folder, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created sample template: {filename}")

def add_header_to_new_page(can, width, height):
    """Add header to new pages"""
    header_height = height - 50
    
    # Hospital Information - Perfectly Centered
    can.setFillColorRGB(0.545, 0, 0)  # Dark Red color #8B0000
    
    college_text = "MES MEDICAL COLLEGE"
    location_text = "PERINTHALMANNA"
    consent_text = "DIGITAL CONSENT FORM"
    
    can.setFont("Helvetica-Bold", 18)
    text_width = can.stringWidth(college_text, "Helvetica-Bold", 18)
    college_x = (width - text_width) / 2
    can.drawString(college_x, header_height - 30, college_text)
    
    can.setFont("Helvetica-Bold", 14)
    text_width = can.stringWidth(location_text, "Helvetica-Bold", 14)
    location_x = (width - text_width) / 2
    can.drawString(location_x, header_height - 55, location_text)
    
    can.setFillColorRGB(0, 0, 0)  # Black color for rest of text
    can.setFont("Helvetica-Bold", 16)
    text_width = can.stringWidth(consent_text, "Helvetica-Bold", 16)
    consent_x = (width - text_width) / 2
    can.drawString(consent_x, header_height - 80, consent_text)
    
    # Draw a thick red line under header
    can.setStrokeColorRGB(0.545, 0, 0)  # Dark Red
    can.setLineWidth(2)
    can.line(50, header_height - 100, width - 50, header_height - 100)
    can.setStrokeColorRGB(0, 0, 0)  # Reset to black

def load_logo_image():
    """Load logo image with multiple fallback options - IMPROVED VERSION"""
    # Try multiple logo files with proper path handling
    logo_files = ['mes-logo.jpg', 'mes-logo.png', 'mes-logo-no-bgm.jpg', 'mes-logo-animated.jpg']
    
    for logo_file in logo_files:
        # Try multiple possible locations
        possible_paths = [
            os.path.join(app.config['STATIC_FOLDER'], logo_file),
            os.path.join('static', logo_file),
            logo_file,
            r'D:\Softwares inhouse\digital_consent\static\mes-logo.jpg',  # Direct path you provided
            r'static\mes-logo.jpg',
            r'static\mes-logo.png'
        ]
        
        for logo_path in possible_paths:
            if os.path.exists(logo_path):
                try:
                    print(f"✅ Found logo at: {logo_path}")
                    # Check if file is actually an image by reading first few bytes
                    with open(logo_path, 'rb') as f:
                        header = f.read(8)
                        # Check for common image file signatures
                        if header.startswith(b'\xff\xd8\xff') or header.startswith(b'\x89PNG\r\n\x1a\n') or header.startswith(b'GIF8') or header.startswith(b'BM'):
                            return ImageReader(logo_path)
                        else:
                            print(f"⚠️ File {logo_path} is not a valid image file")
                            continue
                except Exception as e:
                    print(f"❌ Error loading logo from {logo_path}: {e}")
                    continue
    
    print("❌ No valid logo image found in any location")
    return None

def create_complete_consent_pdf(patient_info, patient_signature_data, relative_signature_data, nurse_signature_data, doctor_signature_data, consent_id, nurse_signed_by=None, doctor_signed_by=None):
    """Create a complete PDF consent form with header, content, and ALL signatures"""
    packet = io.BytesIO()
    
    # Use A4 size for better layout
    can = canvas.Canvas(packet, pagesize=A4)
    width, height = A4
    
    # Improved font registration
    malayalam_available = setup_fonts()
    
    # Header Section - Centered MES Medical College Header
    header_height = height - 50
    
    # Load logo with improved error handling
    logo_image = load_logo_image()
    
    if logo_image:
        try:
            # Position logo on left with proper spacing
            can.drawImage(logo_image, 50, header_height - 80, width=70, height=70, preserveAspectRatio=True, mask='auto')
            print("✅ Logo successfully added to PDF")
        except Exception as e:
            print(f"❌ Error drawing logo: {e}")
            # Fallback to text logo
            can.setFillColorRGB(0.545, 0, 0)  # Dark Red
            can.rect(50, header_height - 80, 70, 70, fill=1)
            can.setFillColorRGB(1, 1, 1)  # White text
            can.setFont("Helvetica-Bold", 10)
            can.drawString(55, header_height - 45, "MES")
            can.drawString(55, header_height - 60, "MEDICAL")
            can.setFillColorRGB(0, 0, 0)  # Reset to black
    else:
        # Create text-based header as fallback
        print("⚠️ Using text-based header (no logo available)")
        can.setFillColorRGB(0.545, 0, 0)  # Dark Red
        can.rect(50, header_height - 80, 70, 70, fill=1)
        can.setFillColorRGB(1, 1, 1)  # White text
        can.setFont("Helvetica-Bold", 8)
        can.drawString(55, header_height - 45, "MES")
        can.drawString(55, header_height - 60, "MEDICAL")
        can.setFillColorRGB(0, 0, 0)  # Reset to black
    
    # Hospital Information - Perfectly Centered
    can.setFillColorRGB(0.545, 0, 0)  # Dark Red color #8B0000
    
    college_text = "MES MEDICAL COLLEGE"
    location_text = "PERINTHALMANNA"
    consent_text = "DIGITAL CONSENT FORM"
    
    can.setFont("Helvetica-Bold", 18)
    text_width = can.stringWidth(college_text, "Helvetica-Bold", 18)
    college_x = (width - text_width) / 2
    can.drawString(college_x, header_height - 30, college_text)
    
    can.setFont("Helvetica-Bold", 14)
    text_width = can.stringWidth(location_text, "Helvetica-Bold", 14)
    location_x = (width - text_width) / 2
    can.drawString(location_x, header_height - 55, location_text)
    
    can.setFillColorRGB(0, 0, 0)  # Black color for rest of text
    can.setFont("Helvetica-Bold", 16)
    text_width = can.stringWidth(consent_text, "Helvetica-Bold", 16)
    consent_x = (width - text_width) / 2
    can.drawString(consent_x, header_height - 80, consent_text)
    
    # Draw a thick red line under header
    can.setStrokeColorRGB(0.545, 0, 0)  # Dark Red
    can.setLineWidth(2)
    can.line(50, header_height - 100, width - 50, header_height - 100)
    can.setStrokeColorRGB(0, 0, 0)  # Reset to black
    
    # Patient Information Section
    y_position = header_height - 130
    
    can.setFont("Helvetica-Bold", 12)
    can.drawString(50, y_position, "PATIENT DETAILS:")
    can.setFont("Helvetica", 11)
    can.drawString(50, y_position - 20, f"Name: {patient_info['name']}")
    can.drawString(50, y_position - 40, f"Age: {patient_info['age']}")
    can.drawString(50, y_position - 60, f"MRN: {patient_info['mrn']}")
    can.drawString(300, y_position - 20, f"Doctor: {patient_info.get('doctor', 'Not assigned')}")
    can.drawString(300, y_position - 60, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    y_position -= 90
    
    # Consent Required For Section
    can.setFont("Helvetica-Bold", 14)
    can.drawString(50, y_position, "CONSENT REQUIRED FOR:")
    y_position -= 25
    
    can.setFont("Helvetica", 12)
    consent_english = clean_text_for_pdf(patient_info.get('consent_required_for', 'Not specified'))
    can.drawString(50, y_position, consent_english)
    y_position -= 25
    
    # Procedure/Reason Details Section - IMPROVED MALAYALAM HANDLING
    can.setFont("Helvetica-Bold", 14)
    can.drawString(50, y_position, "PROCEDURE/REASON DETAILS:")
    y_position -= 25
    
    # Procedure Details with proper wrapping - IMPROVED MALAYALAM HANDLING
    procedure_content = patient_info.get('procedure_details', '')
    if procedure_content:
        # Detect if content contains Malayalam characters
        malayalam_chars = re.findall(r'[\u0D00-\u0D7F]', procedure_content)
        if malayalam_chars:
            # Use Malayalam font for Malayalam content
            font_name = "Malayalam"
            font_size = 10
            line_height = 14
        else:
            # Use regular font for English content
            font_name = "Helvetica"
            font_size = 9
            line_height = 12
        
        y_position = draw_wrapped_text(can, procedure_content, 50, y_position, 
                                     width - 100, font_name, font_size, line_height)
        y_position -= 15
    
    # Ensure declaration and signatures stay on one page
    if y_position < 400:  # If not enough space, start new page
        can.showPage()
        add_header_to_new_page(can, width, height)
        y_position = height - 150
    
    # Declaration Section
    can.setFont("Helvetica-Bold", 14)
    can.drawString(50, y_position, "DECLARATION:")
    y_position -= 25
    
    can.setFont("Helvetica", 11)
    declaration_points = [
        "I hereby acknowledge that:",
        "- I have read and understood the consent form",
        "- All my questions have been answered satisfactorily", 
        "- I voluntarily consent to the procedure/treatment"
    ]
    
    for point in declaration_points:
        if y_position < 250:  # Ensure enough space for signatures
            can.showPage()
            add_header_to_new_page(can, width, height)
            y_position = height - 150
        can.drawString(60, y_position, clean_text_for_pdf(point))
        y_position -= 18
    
    y_position -= 30  # Extra space after declaration
    
    # Signatures Section - ALL FOUR SIGNATURES
    can.setFont("Helvetica-Bold", 14)
    can.drawString(50, y_position, "SIGNATURES:")
    y_position -= 40
    
    # Patient Signature
    can.setFont("Helvetica-Bold", 12)
    can.drawString(50, y_position, "Patient Signature:")
    
    patient_signature_y = y_position - 20
    
    if patient_signature_data and patient_signature_data.startswith('data:image'):
        try:
            signature_b64 = patient_signature_data.split(',')[1]
            signature_bytes = base64.b64decode(signature_b64)
            temp_img = io.BytesIO(signature_bytes)
            signature_image = ImageReader(temp_img)
            
            img_width, img_height = signature_image.getSize()
            max_width, max_height = 120, 50
            width_ratio = max_width / img_width
            height_ratio = max_height / img_height
            scale_factor = min(width_ratio, height_ratio)
            new_width = img_width * scale_factor
            new_height = img_height * scale_factor
            
            can.drawImage(signature_image, 50, patient_signature_y - 60, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Patient signature error: {e}")
            can.setLineWidth(1)
            can.line(50, patient_signature_y - 40, 170, patient_signature_y - 40)
    else:
        can.setLineWidth(1)
        can.line(50, patient_signature_y - 40, 170, patient_signature_y - 40)
    
    # Patient signature details
    can.setFont("Helvetica", 8)
    can.drawString(50, patient_signature_y - 75, f"Patient: {patient_info.get('signatory_name', patient_info['name'])}")
    can.drawString(50, patient_signature_y - 90, f"Signed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Relative Signature
    can.setFont("Helvetica-Bold", 12)
    can.drawString(200, y_position, "Relative Signature:")
    
    relative_signature_y = y_position - 20
    
    if relative_signature_data and relative_signature_data.startswith('data:image'):
        try:
            signature_b64 = relative_signature_data.split(',')[1]
            signature_bytes = base64.b64decode(signature_b64)
            temp_img = io.BytesIO(signature_bytes)
            signature_image = ImageReader(temp_img)
            
            img_width, img_height = signature_image.getSize()
            max_width, max_height = 120, 50
            width_ratio = max_width / img_width
            height_ratio = max_height / img_height
            scale_factor = min(width_ratio, height_ratio)
            new_width = img_width * scale_factor
            new_height = img_height * scale_factor
            
            can.drawImage(signature_image, 200, relative_signature_y - 60, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Relative signature error: {e}")
            can.setLineWidth(1)
            can.line(200, relative_signature_y - 40, 320, relative_signature_y - 40)
    else:
        can.setLineWidth(1)
        can.line(200, relative_signature_y - 40, 320, relative_signature_y - 40)
    
    # Relative signature details
    can.setFont("Helvetica", 8)
    can.drawString(200, relative_signature_y - 75, f"Relationship: {patient_info.get('signatory_relation', 'Relative')}")
    can.drawString(200, relative_signature_y - 90, f"Signed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # New page for nurse and doctor signatures if needed
    if y_position < 200:
        can.showPage()
        add_header_to_new_page(can, width, height)
        y_position = height - 150
        can.setFont("Helvetica-Bold", 14)
        can.drawString(50, y_position, "SIGNATURES (CONTINUED):")
        y_position -= 40
    
    # Nurse Signature
    can.setFont("Helvetica-Bold", 12)
    can.drawString(50, y_position, "Nurse Signature:")
    
    nurse_signature_y = y_position - 20
    
    if nurse_signature_data and nurse_signature_data.startswith('data:image'):
        try:
            signature_b64 = nurse_signature_data.split(',')[1]
            signature_bytes = base64.b64decode(signature_b64)
            temp_img = io.BytesIO(signature_bytes)
            signature_image = ImageReader(temp_img)
            
            img_width, img_height = signature_image.getSize()
            max_width, max_height = 120, 50
            width_ratio = max_width / img_width
            height_ratio = max_height / img_height
            scale_factor = min(width_ratio, height_ratio)
            new_width = img_width * scale_factor
            new_height = img_height * scale_factor
            
            can.drawImage(signature_image, 50, nurse_signature_y - 60, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Nurse signature error: {e}")
            can.setLineWidth(1)
            can.line(50, nurse_signature_y - 40, 170, nurse_signature_y - 40)
    else:
        can.setLineWidth(1)
        can.line(50, nurse_signature_y - 40, 170, nurse_signature_y - 40)
        can.setFont("Helvetica", 10)
        can.drawString(50, nurse_signature_y - 60, "Signature Pending")
    
    # Nurse signature details
    can.setFont("Helvetica", 8)
    if nurse_signed_by:
        can.drawString(50, nurse_signature_y - 75, f"Signed by: Nurse {nurse_signed_by}")
        can.drawString(50, nurse_signature_y - 90, f"Signed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        can.drawString(50, nurse_signature_y - 75, "Signed by: Pending")
        can.drawString(50, nurse_signature_y - 90, "Signed at: Pending")
    
    # Doctor Signature
    can.setFont("Helvetica-Bold", 12)
    can.drawString(200, y_position, "Doctor's Signature:")
    
    doctor_signature_y = y_position - 20
    
    if doctor_signature_data and doctor_signature_data.startswith('data:image'):
        try:
            signature_b64 = doctor_signature_data.split(',')[1]
            signature_bytes = base64.b64decode(signature_b64)
            temp_img = io.BytesIO(signature_bytes)
            signature_image = ImageReader(temp_img)
            
            img_width, img_height = signature_image.getSize()
            max_width, max_height = 120, 50
            width_ratio = max_width / img_width
            height_ratio = max_height / img_height
            scale_factor = min(width_ratio, height_ratio)
            new_width = img_width * scale_factor
            new_height = img_height * scale_factor
            
            can.drawImage(signature_image, 200, doctor_signature_y - 60, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Doctor signature error: {e}")
            can.setLineWidth(1)
            can.line(200, doctor_signature_y - 40, 320, doctor_signature_y - 40)
    else:
        can.setLineWidth(1)
        can.line(200, doctor_signature_y - 40, 320, doctor_signature_y - 40)
        can.setFont("Helvetica", 10)
        can.drawString(200, doctor_signature_y - 60, f"Dr. {patient_info.get('doctor', 'Signature Pending')}")
    
    # Doctor signature details
    can.setFont("Helvetica", 8)
    if doctor_signed_by:
        can.drawString(200, doctor_signature_y - 75, f"Signed by: Dr. {doctor_signed_by}")
        can.drawString(200, doctor_signature_y - 90, f"Signed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        can.drawString(200, doctor_signature_y - 75, "Signed by: Pending")
        can.drawString(200, doctor_signature_y - 90, "Signed at: Pending")
    
    # Footer
    y_position = min(patient_signature_y, relative_signature_y, nurse_signature_y, doctor_signature_y) - 120
    
    if y_position < 100:
        can.showPage()
        add_header_to_new_page(can, width, height)
        y_position = height - 150
    
    can.setStrokeColorRGB(0.545, 0, 0)  # Dark Red
    can.setLineWidth(1)
    can.line(50, y_position, width - 50, y_position)
    y_position -= 20
    
    can.setFillColorRGB(0.545, 0, 0)  # Dark Red
    can.setFont("Helvetica-Bold", 10)
    can.drawString(50, y_position, "MES Medical College, Perinthalmanna")
    can.setFillColorRGB(0, 0, 0)  # Black
    can.setFont("Helvetica", 8)
    can.drawString(50, y_position - 15, "Digital Consent System - Generated Electronically")
    
    can.save()
    packet.seek(0)
    return packet

# ========== ROUTES ==========

@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    if 'username' in session:
        user_type = session.get('user_type', 'counsellor')
        if user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user_type == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif user_type == 'nurse':
            return redirect(url_for('nurse_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple authentication - adjust based on your User model
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            
            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('dashboard'))
            elif user.role == 'patient':
                return redirect(url_for('patient_dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            elif user.role == 'nurse':
                return redirect(url_for('nurse_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
    
    # GET request - show login form
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    role = session.get('role')
    if not role:
        return redirect(url_for('login'))
    
    if role == 'patient':
        return redirect(url_for('patient_dashboard'))
    elif role == 'relative':
        return redirect(url_for('relative_dashboard'))
    elif role == 'nurse':
        return redirect(url_for('nurse_dashboard'))
    elif role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/test_templates')
def test_templates():
    """Test if templates are loading correctly"""
    try:
        templates = ['patient_dashboard.html', 'relative_dashboard.html', 
                    'nurse_dashboard.html', 'doctor_dashboard.html', 'base.html']
        results = {}
        for template in templates:
            try:
                render_template(template)
                results[template] = "✓ Loaded successfully"
            except Exception as e:
                results[template] = f"✗ Error: {str(e)}"
        return jsonify(results)
    except Exception as e:
        return f"Template test failed: {str(e)}"

@app.route('/debug_templates')
def debug_templates():
    """Debug template loading issues"""
    templates_to_test = [
        'dashboard.html',
        'nurse_dashboard.html', 
        'doctor_dashboard.html',
        'admin_dashboard.html',
        'signature.html',
        'base.html'
    ]
    
    results = {}
    for template_name in templates_to_test:
        try:
            # Try to render the template
            rendered = render_template(template_name)
            results[template_name] = {
                'status': 'SUCCESS',
                'message': 'Template loaded successfully'
            }
        except TemplateNotFound as e:
            results[template_name] = {
                'status': 'ERROR', 
                'message': f'Template not found: {str(e)}'
            }
        except Exception as e:
            results[template_name] = {
                'status': 'ERROR',
                'message': f'Error loading template: {str(e)}'
            }
    
    return jsonify(results)


@app.route('/patient_dashboard')
def patient_dashboard():
    if session.get('role') != 'patient':
        return redirect(url_for('login'))
    return render_template('patient_dashboard.html')

@app.route('/relative_dashboard')
def relative_dashboard():
    if session.get('role') != 'relative':
        return redirect(url_for('login'))
    return render_template('relative_dashboard.html')


@app.route('/nurse_dashboard')
def nurse_dashboard():
    if 'username' not in session or session.get('user_type') != 'nurse':
        return redirect(url_for('login'))
    
    # Get consents pending nurse signature (after patient signature)
    conn = sqlite3.connect('consents.db')
    c = conn.cursor()
    c.execute('''SELECT id, patient_name, patient_mrn, consent_required_for, doctor_name, created_at 
                 FROM consents 
                 WHERE nurse_signature_data IS NULL AND patient_signature_data IS NOT NULL
                 ORDER BY created_at DESC''')
    pending_consents = c.fetchall()
    conn.close()
    
    return render_template('nurse_dashboard.html',
                         username=session['username'],
                         full_name=session.get('full_name', ''),
                         pending_consents=pending_consents)

@app.route('/admin/add_user', methods=['POST'])
def admin_add_user():
    if 'username' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    username = request.form['username']
    password = request.form['password']
    user_type = request.form['user_type']
    full_name = request.form['full_name']
    department = request.form['department']
    
    if add_user(username, password, user_type, full_name, department):
        return jsonify({'success': True, 'message': 'User created successfully'})
    else:
        return jsonify({'success': False, 'message': 'Username already exists'})

@app.route('/admin/update_user', methods=['POST'])
def admin_update_user():
    if 'username' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user_id = request.form['user_id']
    username = request.form['username']
    user_type = request.form['user_type']
    full_name = request.form['full_name']
    department = request.form['department']
    is_active = request.form.get('is_active', 0)
    
    if update_user(user_id, username, user_type, full_name, department, is_active):
        return jsonify({'success': True, 'message': 'User updated successfully'})
    else:
        return jsonify({'success': False, 'message': 'Username already exists'})

@app.route('/admin/reset_password', methods=['POST'])
def admin_reset_password():
    if 'username' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user_id = request.form['user_id']
    new_password = request.form['new_password']
    
    reset_user_password(user_id, new_password)
    return jsonify({'success': True, 'message': 'Password reset successfully'})

@app.route('/admin/delete_user', methods=['POST'])
def admin_delete_user():
    if 'username' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user_id = request.form['user_id']
    delete_user(user_id)
    return jsonify({'success': True, 'message': 'User deleted successfully'})

@app.route('/start_consent', methods=['POST'])
def start_consent():
    if 'username' not in session or session.get('user_type') not in ['counsellor', 'admin']:
        return redirect(url_for('login'))
    
    consent_type = request.form['consent_type']
    patient_name = request.form['patient_name']
    patient_age = request.form['patient_age']
    patient_mrn = request.form['patient_mrn']
    consent_required_for = request.form['consent_required_for']
    procedure_details = request.form['procedure_details']  # This should have edited content
    patient_doctor = request.form['patient_doctor']
    signatory_name = request.form['signatory_name']
    signatory_relation = request.form['signatory_relation']
    signatory_mobile = request.form['signatory_mobile']
    
    # Get Malayalam content - it's the same as procedure_details now
    procedure_details_ml = request.form.get('procedure_details_ml', procedure_details)
    
    # DEBUG: Print what we're receiving
    print(f"🔍 DEBUG - Procedure Details Received:")
    print(f"   Length: {len(procedure_details)} characters")
    print(f"   First 100 chars: {procedure_details[:100]}...")
    print(f"   Is different from template: {'YES' if procedure_details and 'Template content' not in procedure_details else 'NO'}")
    
    # Store in session for the signature page
    session['current_consent'] = {
        'consent_type': consent_type,
        'patient_name': patient_name,
        'patient_age': patient_age,
        'patient_mrn': patient_mrn,
        'consent_required_for': consent_required_for,
        'consent_required_for_ml': consent_required_for,  # Same as English for now
        'procedure_details': procedure_details,  # This should have the edited content
        'procedure_details_ml': procedure_details_ml,  # This should have the edited content
        'counsellor': session['username'],
        'doctor': patient_doctor,
        'signatory_name': signatory_name,
        'signatory_relation': signatory_relation,
        'signatory_mobile': signatory_mobile
    }
    
    # DEBUG: Print what we're storing in session
    print(f"🔍 DEBUG - Session Data Stored:")
    print(f"   Procedure Details in session: {session['current_consent']['procedure_details'][:100]}...")
    
    return redirect(url_for('preview_consent'))

@app.route('/preview_consent')
def preview_consent():
    if 'username' not in session or 'current_consent' not in session:
        return redirect(url_for('dashboard'))
    
    return render_template('preview_consent.html',
                         consent_data=session['current_consent'],
                         now=datetime.now())

@app.route('/save_consent', methods=['POST'])
def save_consent():
    try:
        # Get form data
        patient_id = request.form.get('patient_id')
        consent_type = request.form.get('consent_type')
        signature_data = request.form.get('signature')
        
        # Get current user role from session
        current_role = session.get('role')
        user_id = session.get('user_id')
        
        # Update consent status based on who is signing
        consent = Consent.query.filter_by(patient_id=patient_id, consent_type=consent_type).first()
        
        if consent:
            if current_role == 'patient':
                consent.patient_signed = True
                consent.patient_signature = signature_data
                consent.patient_signed_at = datetime.utcnow()
            elif current_role == 'relative':
                consent.relative_signed = True
                consent.relative_signature = signature_data
                consent.relative_signed_at = datetime.utcnow()
            elif current_role == 'nurse':
                consent.nurse_signed = True
                consent.nurse_signature = signature_data
                consent.nurse_signed_at = datetime.utcnow()
            elif current_role == 'doctor':
                consent.doctor_signed = True
                consent.doctor_signature = signature_data
                consent.doctor_signed_at = datetime.utcnow()
                consent.status = 'completed'
            
            db.session.commit()
            
            flash('Consent signed successfully!', 'success')
            return redirect(url_for('dashboard'))  # Use the fallback dashboard
        
        flash('Error saving consent. Please try again.', 'error')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving consent: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
@app.route('/api/get_consent_template/<template_name>')
def get_consent_template(template_name):
    """API endpoint to get template data for a consent form"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    consent_types = get_consent_types()
    
    if template_name in consent_types:
        template_data = consent_types[template_name]
        return jsonify({
            'form_name': template_data['display_name'],
            'template_content': template_data['template_content']
        })
    else:
        return jsonify({'error': 'Template not found'}), 404

@app.route('/signature')
def signature_page():
    if 'username' not in session or 'current_consent' not in session:
        return redirect(url_for('dashboard'))
    
    return render_template('signature.html',
                         consent_data=session['current_consent'])

@app.route('/save_patient_signatures', methods=['POST'])
def save_patient_signatures():
    """Save both patient and relative signatures"""
    if 'username' not in session or 'current_consent' not in session:
        return redirect(url_for('dashboard'))
    
    patient_signature_data = request.form['patient_signature']
    relative_signature_data = request.form['relative_signature']
    consent_data = session['current_consent']
    
    try:
        # Save to database first
        conn = sqlite3.connect('consents.db')
        c = conn.cursor()
        c.execute('''INSERT INTO consents 
                     (patient_name, patient_age, patient_mrn, consent_type, patient_signature_data, relative_signature_data, counsellor_id, signatory_name, signatory_relation, signatory_mobile, consent_required_for, consent_required_for_ml, procedure_details, procedure_details_ml, doctor_name)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (consent_data['patient_name'], consent_data['patient_age'], 
                   consent_data['patient_mrn'], consent_data['consent_type'],
                   patient_signature_data, relative_signature_data, session['username'],
                   consent_data['signatory_name'], consent_data['signatory_relation'], 
                   consent_data['signatory_mobile'], consent_data['consent_required_for'],
                   consent_data['consent_required_for_ml'], consent_data['procedure_details'],
                   consent_data['procedure_details_ml'], consent_data['doctor']))
        conn.commit()
        consent_id = c.lastrowid
        
        # Generate PDF filename
        final_pdf_filename = f"MRN_{consent_data['patient_mrn']}_Consent_{consent_id}.pdf"
        
        # Update with final PDF path
        c.execute('UPDATE consents SET final_pdf = ? WHERE id = ?', 
                  (final_pdf_filename, consent_id))
        conn.commit()
        
        # Generate initial PDF with patient signatures only
        patient_info = {
            'name': consent_data['patient_name'],
            'age': consent_data['patient_age'],
            'mrn': consent_data['patient_mrn'],
            'consent_required_for': consent_data['consent_required_for'],
            'consent_required_for_ml': consent_data['consent_required_for_ml'],
            'procedure_details': consent_data['procedure_details'],
            'procedure_details_ml': consent_data['procedure_details_ml'],
            'counsellor': session['username'],
            'doctor': consent_data['doctor'],
            'signatory_name': consent_data['signatory_name'],
            'signatory_relation': consent_data['signatory_relation']
        }
        
        # Create PDF with patient signatures only (nurse and doctor pending)
        pdf_packet = create_complete_consent_pdf(patient_info, patient_signature_data, relative_signature_data, None, None, consent_id)
        
        # Save the PDF
        final_pdf_path = os.path.join(app.config['GENERATED_FOLDER'], final_pdf_filename)
        os.makedirs(os.path.dirname(final_pdf_path), exist_ok=True)
        
        with open(final_pdf_path, 'wb') as output_file:
            output_file.write(pdf_packet.getvalue())
            
        conn.close()
        
        # Clear session
        session.pop('current_consent', None)
        
        return redirect(url_for('patient_signature_success', consent_id=consent_id))
    
    except Exception as e:
        print(f"Error saving patient signatures: {e}")
        return f"""
        <h2>Error</h2>
        <p>There was an issue saving the signatures. Please try again.</p>
        <p>Error: {str(e)}</p>
        <a href="/dashboard">Back to Dashboard</a>
        """

@app.route('/patient_signature_success/<int:consent_id>')
def patient_signature_success(consent_id):
    """Show success page after patient and relative signatures"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get consent details from database
    conn = sqlite3.connect('consents.db')
    c = conn.cursor()
    c.execute('SELECT patient_name, final_pdf FROM consents WHERE id = ?', (consent_id,))
    consent = c.fetchone()
    conn.close()
    
    if not consent:
        return "Consent not found", 404
    
    return render_template('patient_signature_success.html',
                         consent_id=consent_id,
                         patient_name=consent[0],
                         final_pdf_filename=consent[1] if consent[1] else 'Pending')

@app.route('/nurse_signature/<int:consent_id>')
def nurse_signature_page(consent_id):
    """Page for nurse to provide signature"""
    if 'username' not in session or session.get('user_type') != 'nurse':
        return redirect(url_for('login'))
    
    # Get consent details from database
    conn = sqlite3.connect('consents.db')
    c = conn.cursor()
    c.execute('SELECT patient_name, patient_age, patient_mrn, consent_required_for, consent_required_for_ml, procedure_details, procedure_details_ml, doctor_name, signatory_name, signatory_relation FROM consents WHERE id = ?', (consent_id,))
    consent = c.fetchone()
    conn.close()
    
    if not consent:
        return "Consent not found", 404
    
    consent_data = {
        'patient_name': consent[0],
        'patient_age': consent[1],
        'patient_mrn': consent[2],
        'consent_required_for': consent[3],
        'consent_required_for_ml': consent[4],
        'procedure_details': consent[5],
        'procedure_details_ml': consent[6],
        'doctor': consent[7],
        'signatory_name': consent[8],
        'signatory_relation': consent[9]
    }
    
    return render_template('nurse_signature.html',
                         consent_data=consent_data,
                         consent_id=consent_id)

@app.route('/save_nurse_signature/<int:consent_id>', methods=['POST'])
def save_nurse_signature(consent_id):
    """Save nurse's signature"""
    if 'username' not in session or session.get('user_type') != 'nurse':
        return redirect(url_for('login'))
    
    nurse_signature_data = request.form.get('nurse_signature')
    
    if not nurse_signature_data:
        return "No signature data received", 400
    
    try:
        # Get consent details from database
        conn = sqlite3.connect('consents.db')
        c = conn.cursor()
        c.execute('''SELECT patient_name, patient_age, patient_mrn, consent_required_for, consent_required_for_ml, procedure_details, procedure_details_ml, doctor_name, signatory_name, signatory_relation, 
                            patient_signature_data, relative_signature_data, final_pdf 
                     FROM consents WHERE id = ?''', (consent_id,))
        consent = c.fetchone()
        
        if not consent:
            conn.close()
            return "Consent not found", 404
        
        print(f"Updating consent {consent_id} with nurse signature")
        
        # Update database with nurse signature and who signed it
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('UPDATE consents SET nurse_signature_data = ?, nurse_signed_by = ?, nurse_signed_at = ? WHERE id = ?', 
                  (nurse_signature_data, session['username'], current_time, consent_id))
        conn.commit()
        
        # Generate PDF with nurse signature added
        patient_info = {
            'name': consent[0],
            'age': consent[1],
            'mrn': consent[2],
            'consent_required_for': consent[3],
            'consent_required_for_ml': consent[4],
            'procedure_details': consent[5],
            'procedure_details_ml': consent[6],
            'counsellor': session['username'],
            'doctor': consent[7],
            'signatory_name': consent[8],
            'signatory_relation': consent[9]
        }
        
        print("Creating consent PDF with nurse signature...")
        
        # Create PDF with patient, relative, and nurse signatures (doctor pending)
        pdf_packet = create_complete_consent_pdf(patient_info, consent[10], consent[11], nurse_signature_data, None, consent_id, session['username'], None)
        
        # Save the PDF
        final_pdf_path = os.path.join(app.config['GENERATED_FOLDER'], consent[12])
        
        print(f"Saving PDF: {final_pdf_path}")
        
        # Ensure the generated_pdfs folder exists
        os.makedirs(os.path.dirname(final_pdf_path), exist_ok=True)
        
        # Write PDF to file
        with open(final_pdf_path, 'wb') as output_file:
            output_file.write(pdf_packet.getvalue())
            
        conn.close()
        
        print("PDF with nurse signature generated successfully")
        return render_template('nurse_signature_success.html',
                             consent_id=consent_id,
                             patient_name=consent[0],
                             final_pdf_filename=consent[12])
    
    except Exception as e:
        print(f"Error saving nurse signature: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return f"Error saving signature: {str(e)}", 500

@app.route('/doctor_signature/<int:consent_id>')
def doctor_signature_page(consent_id):
    """Page for doctor to provide signature"""
    if 'username' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('login'))
    
    # Get consent details from database
    conn = sqlite3.connect('consents.db')
    c = conn.cursor()
    c.execute('SELECT patient_name, patient_age, patient_mrn, consent_required_for, consent_required_for_ml, procedure_details, procedure_details_ml, doctor_name, signatory_name, signatory_relation FROM consents WHERE id = ?', (consent_id,))
    consent = c.fetchone()
    conn.close()
    
    if not consent:
        return "Consent not found", 404
    
    consent_data = {
        'patient_name': consent[0],
        'patient_age': consent[1],
        'patient_mrn': consent[2],
        'consent_required_for': consent[3],
        'consent_required_for_ml': consent[4],
        'procedure_details': consent[5],
        'procedure_details_ml': consent[6],
        'doctor': consent[7],
        'signatory_name': consent[8],
        'signatory_relation': consent[9]
    }
    
    return render_template('doctor_signature.html',
                         consent_data=consent_data,
                         consent_id=consent_id)

@app.route('/save_doctor_signature/<int:consent_id>', methods=['POST'])
def save_doctor_signature(consent_id):
    """Save doctor's signature and generate final PDF"""
    if 'username' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('login'))
    
    doctor_signature_data = request.form.get('doctor_signature')
    
    if not doctor_signature_data:
        return "No signature data received", 400
    
    try:
        # Get consent details from database
        conn = sqlite3.connect('consents.db')
        c = conn.cursor()
        c.execute('''SELECT patient_name, patient_age, patient_mrn, consent_required_for, consent_required_for_ml, procedure_details, procedure_details_ml, doctor_name, signatory_name, signatory_relation, 
                            patient_signature_data, relative_signature_data, nurse_signature_data, final_pdf 
                     FROM consents WHERE id = ?''', (consent_id,))
        consent = c.fetchone()
        
        if not consent:
            conn.close()
            return "Consent not found", 404
        
        print(f"Updating consent {consent_id} with doctor signature")
        
        # Update database with doctor signature and who signed it
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('UPDATE consents SET doctor_signature_data = ?, doctor_signed_by = ?, doctor_signed_at = ? WHERE id = ?', 
                  (doctor_signature_data, session['username'], current_time, consent_id))
        conn.commit()
        
        # Generate final PDF with ALL signatures
        patient_info = {
            'name': consent[0],
            'age': consent[1],
            'mrn': consent[2],
            'consent_required_for': consent[3],
            'consent_required_for_ml': consent[4],
            'procedure_details': consent[5],
            'procedure_details_ml': consent[6],
            'counsellor': session['username'],
            'doctor': consent[7],
            'signatory_name': consent[8],
            'signatory_relation': consent[9]
        }
        
        print("Creating complete consent PDF with ALL signatures...")
        
        # Create complete PDF with ALL signatures
        pdf_packet = create_complete_consent_pdf(patient_info, consent[10], consent[11], consent[12], doctor_signature_data, consent_id, None, session['username'])
        
        # Save the PDF
        final_pdf_path = os.path.join(app.config['GENERATED_FOLDER'], consent[13])
        
        print(f"Saving PDF: {final_pdf_path}")
        
        # Ensure the generated_pdfs folder exists
        os.makedirs(os.path.dirname(final_pdf_path), exist_ok=True)
        
        # Write PDF to file
        with open(final_pdf_path, 'wb') as output_file:
            output_file.write(pdf_packet.getvalue())
            
        conn.close()
        
        print("PDF with ALL signatures generated successfully")
        return render_template('final_success.html',
                             consent_id=consent_id,
                             patient_name=consent[0],
                             final_pdf_filename=consent[13])
    
    except Exception as e:
        print(f"Error saving doctor signature: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return f"Error saving signature: {str(e)}", 500

@app.route('/download_consent/<filename>')
def download_consent(filename):
    """Download the final signed PDF for HIS upload"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    file_path = os.path.join(app.config['GENERATED_FOLDER'], filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        return "File not found", 404

@app.route('/consents')
def view_consents():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('consents.db')
    c = conn.cursor()
    
    # First, let's check what columns actually exist in the table
    c.execute("PRAGMA table_info(consents)")
    columns = [column[1] for column in c.fetchall()]
    print(f"Available columns: {columns}")  # Debug info
    
    # Build query based on available columns
    select_columns = [
        'id', 'patient_name', 'patient_age', 'patient_mrn', 'consent_type'
    ]
    
    # Add optional columns if they exist
    optional_columns = [
        'consent_required_for', 'procedure_details', 'doctor_name',
        'signatory_name', 'signatory_relation', 'counsellor_id',
        'created_at', 'final_pdf', 'patient_signature_data', 'relative_signature_data',
        'nurse_signature_data', 'doctor_signature_data', 'nurse_signed_by', 'doctor_signed_by'
    ]
    
    for col in optional_columns:
        if col in columns:
            select_columns.append(col)
        else:
            print(f"⚠️ Column '{col}' not found, skipping")
    
    # Build the query
    query = f'''SELECT {', '.join(select_columns)} 
                FROM consents 
                ORDER BY created_at DESC'''
    
    print(f"Executing query: {query}")  # Debug info
    
    c.execute(query)
    consents = c.fetchall()
    conn.close()
    
    consent_types = get_consent_types()
    
    return render_template('consents_list.html', 
                         consents=consents, 
                         consent_types=consent_types,
                         username=session['username'])

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_type', None)
    session.pop('full_name', None)
    session.pop('current_consent', None)
    return redirect(url_for('login'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_message="Internal server error"), 500

if __name__ == '__main__':
    # Setup databases
    print("🔄 Initializing databases...")
    init_users_database()
    init_database()
    
    print("=" * 60)
    print("MES Medical College - Digital Consent System")
    print("✅ Database created with MULTI-SIGNATURE support")
    print("✅ ADDED: Nurse user type and dashboard")
    print("✅ IMPROVED: Multi-signature workflow")
    print("✅ FIXED: Logo loading in PDF")
    print("Server starting on http://0.0.0.0:5000")
    print("Available on network: http://[YOUR-IP]:5000")
    print("=" * 60)
    
    # Display available consent templates
    consent_types = get_consent_types()
    if consent_types:
        print(f"Found {len(consent_types)} consent templates:")
        for filename, template_data in consent_types.items():
            print(f"  - {template_data['display_name']}")
    else:
        print("No consent templates found. Please add .txt files to 'static/consent_forms/' folder.")
    
    print("\n🔐 DEFAULT LOGIN CREDENTIALS:")
    print(f"Admin: {DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}")
    print("Counsellors: counsellor1 / password123")
    print("Nurses: nurse1 / nurse123")
    print("Doctors: doctor1 / doctor123")
    print("\n💡 WORKFLOW:")
    print("1. Counsellor creates consent → Patient & Relative sign")
    print("2. Nurse signs the consent")
    print("3. Doctor provides final signature")
    print("4. PDF is ready for HIS upload")
    
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)