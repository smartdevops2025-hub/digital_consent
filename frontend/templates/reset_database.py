import os
import sqlite3
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def reset_database():
    # Remove existing database files
    if os.path.exists('users.db'):
        os.remove('users.db')
        print("🗑️ Removed old users.db")
    
    if os.path.exists('consents.db'):
        os.remove('consents.db')
        print("🗑️ Removed old consents.db")
    
    # Create new users database
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password_hash TEXT,
                  user_type TEXT,
                  full_name TEXT,
                  department TEXT,
                  is_active INTEGER DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  last_login TIMESTAMP)''')
    
    # Create default users
    default_users = [
        ('admin', 'admin123', 'admin', 'System Administrator', 'IT', 1),
        ('counsellor1', 'password123', 'counsellor', 'Counsellor One', 'Counselling', 1),
        ('counsellor2', 'password123', 'counsellor', 'Counsellor Two', 'Counselling', 1),
        ('doctor1', 'doctor123', 'doctor', 'Dr. Sajid', 'Surgery', 1),
        ('doctor2', 'doctor123', 'doctor', 'Dr. Rahman', 'Medicine', 1)
    ]
    
    for username, password, user_type, full_name, department, is_active in default_users:
        password_hash = hash_password(password)
        c.execute('INSERT INTO users (username, password_hash, user_type, full_name, department, is_active) VALUES (?, ?, ?, ?, ?, ?)',
                  (username, password_hash, user_type, full_name, department, is_active))
        print(f"✅ Created user: {username}")
    
    conn.commit()
    
    # Verify the users were created
    c.execute('SELECT username, user_type, is_active FROM users')
    users = c.fetchall()
    print("\n📋 VERIFICATION - Users in database:")
    for user in users:
        print(f"  - {user[0]} ({user[1]}) - Active: {user[2]}")
    
    conn.close()
    
    print("\n✅ Database reset complete!")
    print("🔐 You can now login with:")
    print("   Admin: admin / admin123")
    print("   Counsellor: counsellor1 / password123")
    print("   Doctor: doctor1 / doctor123")

if __name__ == '__main__':
    reset_database()