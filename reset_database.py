import sqlite3
import os

def reset_database():
    # Delete existing database
    if os.path.exists('consents.db'):
        os.remove('consents.db')
        print("Old database deleted")
    
    # Create new database with correct schema
    conn = sqlite3.connect('consents.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE consents
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  patient_name TEXT,
                  patient_age INTEGER,
                  patient_mrn TEXT,
                  consent_type TEXT,
                  original_pdf TEXT,
                  final_pdf TEXT,
                  signature_data TEXT,
                  counsellor_id TEXT,
                  signatory_name TEXT,
                  signatory_relation TEXT,
                  signatory_mobile TEXT,
                  procedure_name TEXT,
                  doctor_signature TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    print("New database created with all columns:")
    print("✓ patient_name")
    print("✓ patient_age") 
    print("✓ patient_mrn")
    print("✓ consent_type")
    print("✓ original_pdf")
    print("✓ final_pdf")
    print("✓ signature_data")
    print("✓ counsellor_id")
    print("✓ signatory_name")
    print("✓ signatory_relation")
    print("✓ signatory_mobile")
    print("✓ procedure_name")
    print("✓ doctor_signature")
    print("✓ created_at")
    
    conn.commit()
    conn.close()
    print("\nDatabase reset complete!")

if __name__ == '__main__':
    reset_database()