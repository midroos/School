import sqlite3
import os

def init_db():
    # المسار الديناميكي لملف قاعدة البيانات ليكون بجوار هذا الملف
    db_path = os.path.join(os.path.dirname(__file__), 'school.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # --- دالة مساعدة لإضافة عمود جديد (لترحيل البيانات) ---
    def _add_academic_year_column_if_not_exists(cursor):
        cursor.execute("PRAGMA table_info(students)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'academic_year' not in columns:
            cursor.execute("ALTER TABLE students ADD COLUMN academic_year TEXT")
            print("Database Migration: Added 'academic_year' column to students table.")

    # 1. جدول الطلاب (students)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        grade TEXT NOT NULL,
        parent_phone TEXT,
        created_at TEXT,
        status TEXT DEFAULT 'active'
    )
    """)

    # تنفيذ دالة الترحيل
    _add_academic_year_column_if_not_exists(cur)

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
