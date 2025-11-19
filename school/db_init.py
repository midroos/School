import sqlite3
import os

def init_db():
    conn = sqlite3.connect('school.db')
    cur = conn.cursor()
    
    # 1. جدول الطلاب (students)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        grade TEXT NOT NULL,
        academic_year TEXT,     -- حقل العام الدراسي 
        parent_phone TEXT,
        created_at TEXT,
        status TEXT DEFAULT 'active'
    )
    """)

    # 2. جدول حركات الخزينة (transactions)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        amount REAL NOT NULL,
        type TEXT,              -- 'payment' أو 'expense'
        description TEXT,
        payment_method TEXT,
        FOREIGN KEY (student_id) REFERENCES students (id)
    )
    """)

    # 3. جدول الأقساط (installments)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS installments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        sequence INTEGER,       -- حقل رقم القسط 
        amount REAL NOT NULL,
        paid_amount REAL DEFAULT 0.0,
        due_date TEXT NOT NULL,
        paid_date TEXT,
        status TEXT DEFAULT 'pending', -- 'pending', 'paid'
        FOREIGN KEY (student_id) REFERENCES students (id)
    )
    """)
    
    conn.commit()
    conn.close()
    print("✔ تم تهيئة قاعدة البيانات بنجاح (Dynamic Database Ready)")

if __name__ == '__main__':
    init_db()