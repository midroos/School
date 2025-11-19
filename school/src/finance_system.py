import sqlite3
from datetime import datetime, timedelta

class FinanceSystem:
    def __init__(self, db_path):
        self.db_path = db_path

    # --- 1. دوال الإحصائيات (Dashboard Stats) ---
    def get_daily_stats(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        today_date = datetime.now().strftime("%Y-%m-%d")
        
        # 1. إجمالي إيراد اليوم
        cur.execute("SELECT SUM(amount) FROM transactions WHERE date LIKE ? || '%' AND type='payment'", (today_date,))
        daily_total = cur.fetchone()[0] or 0.0
        
        # 2. حركات اليوم (أحدث 10 حركات)
        cur.execute("""
            SELECT t.date, s.name, t.amount, t.payment_method
            FROM transactions t
            JOIN students s ON t.student_id = s.id
            WHERE t.date LIKE ? || '%'
            ORDER BY t.date DESC
            LIMIT 10
        """, (today_date,))
        daily_transactions = cur.fetchall()

        # 3. عدد الأقساط المتأخرة
        cur.execute("""
            SELECT COUNT(id) FROM installments 
            WHERE due_date < ? AND status = 'pending'
        """, (today_date,))
        overdue_count = cur.fetchone() or (0,)
        
        conn.close()
        return daily_total, daily_transactions, overdue_count

    # --- 2. دوال إدارة الأقساط والدفع ---

    def create_fee_plan(self, student_id, total_fees, installments_count, start_date_str):
        """ينشئ خطة تقسيط ويولد الأقساط"""
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            return False, "صيغة التاريخ غير صحيحة (YYYY-MM-DD)."
            
        if installments_count <= 0 or total_fees <= 0:
            return False, "العدد والمبلغ يجب أن يكونا أكبر من صفر."

        monthly_amount = total_fees / installments_count
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        try:
            for i in range(installments_count):
                due_date = (start_date + timedelta(days=30 * i)).strftime("%Y-%m-%d") 
                
                cur.execute("""INSERT INTO installments (student_id, sequence, amount, due_date, status)
                               VALUES (?, ?, ?, ?, 'pending')""", 
                               (student_id, i + 1, monthly_amount, due_date))
            
            conn.commit()
            return True, f"تم توليد {installments_count} قسطاً للطالب بنجاح."
            
        except Exception as e:
            conn.rollback()
            return False, f"خطأ في قاعدة البيانات أثناء توليد الأقساط: {str(e)}"
        finally:
            conn.close()


    def get_pending_installments(self):
        """جلب الأقساط غير المدفوعة مع اسم الطالب"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT i.id, s.name, i.sequence, i.due_date, i.amount, i.paid_amount
            FROM installments i
            JOIN students s ON i.student_id = s.id
            WHERE i.status = 'pending'
            ORDER BY i.due_date ASC
            LIMIT 50
        """)
        data = cur.fetchall()
        conn.close()
        return data

    def pay_installment(self, installment_id, amount, method, student_name):
        """تسجيل دفعة وتحديث حالة القسط"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT student_id, amount FROM installments WHERE id=?", (installment_id,))
            inst_data = cur.fetchone()
            if not inst_data:
                return False, "القسط غير موجود."
            
            student_id, required_amount = inst_data

            # 1. تحديث حالة القسط إلى 'paid'
            cur.execute("UPDATE installments SET status='paid', paid_amount=?, paid_date=? WHERE id=?", 
                        (amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), installment_id))
            
            # 2. تسجيل الحركة في جدول transactions
            cur.execute("""
                INSERT INTO transactions (student_id, date, amount, type, description, payment_method)
                VALUES (?, ?, ?, 'payment', ?, ?)
            """, (student_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), amount, 
                  f"قسط رقم {installment_id} للطالب {student_name}", method))
            
            conn.commit()
            return True, f"تم تسجيل الدفع بنجاح. المبلغ: {amount:,.2f}"
            
        except Exception as e:
            conn.rollback()
            return False, f"خطأ في التسديد: {str(e)}"
        finally:
            conn.close()

    # --- 3. دوال إدارة بيانات الطلاب ---

    def get_students(self):
        """جلب قائمة الطلاب الأساسية للقوائم المنسدلة"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, name, grade FROM students ORDER BY name ASC")
        data = cur.fetchall()
        conn.close()
        return data

    def add_new_student(self, name, grade, academic_year, parent_phone):
        """إضافة طالب جديد"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""INSERT INTO students (name, grade, academic_year, parent_phone, created_at)
                           VALUES (?, ?, ?, ?, ?)""", 
                           (name, grade, academic_year, parent_phone, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            return True, f"تم إضافة الطالب: {name} بنجاح."
        except Exception as e:
            conn.rollback()
            return False, f"خطأ في الإضافة: {str(e)}"
        finally:
            conn.close()

    def update_student_data(self, student_id, name, grade, academic_year, parent_phone):
        """تحديث بيانات طالب"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""UPDATE students SET name=?, grade=?, academic_year=?, parent_phone=? WHERE id=? """,
                        (name, grade, academic_year, parent_phone, student_id))
            conn.commit()
            return True, f"تم تحديث بيانات الطالب رقم {student_id} بنجاح."
        except Exception as e:
            conn.rollback()
            return False, f"خطأ في التحديث: {str(e)}"
        finally:
            conn.close()

    def get_student_details(self, student_id):
        """جلب تفاصيل طالب واحد"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, name, grade, academic_year, parent_phone FROM students WHERE id=?", (student_id,))
        data = cur.fetchone()
        conn.close()
        return data 

    def get_all_students_for_management(self):
        """جلب كل بيانات الطلاب لجدول الإدارة"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, name, grade, academic_year, parent_phone FROM students ORDER BY name ASC")
        data = cur.fetchall()
        conn.close()
        return data