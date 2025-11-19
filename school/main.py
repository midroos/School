import flet as ft
from src.finance_system import FinanceSystem
from src.db_init import init_db
import sqlite3
import traceback
import sys

# --- الإعدادات والمتغيرات الأساسية ---
DB_PATH = "data/school.db"

# متغير عالمي لتخزين قائمة الطلاب الحالية المعروضة في جدول الإدارة (للبحث)
current_managed_students_data = []

# 1. تهيئة قاعدة البيانات والنظام المالي
init_db(DB_PATH)
system = FinanceSystem(DB_PATH)

def main(page: ft.Page):
    try:
        # 2. إعدادات الصفحة الرئيسية
        page.title = "نظام UDMM لإدارة المدارس - المالية"
        page.rtl = True
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window.width = 1200
        page.window.height = 800
        page.padding = 20
        page.scroll = ft.ScrollMode.ADAPTIVE

        print("✅ التطبيق بدأ التشغيل...")  # رسالة تأكيد في الكونسول

        # --- وظيفة مساعدة لعرض الرسائل (Snack Bar) ---
        def show_snackbar(message, page, error=False):
            """يعرض رسالة سريعة في أسفل الشاشة"""
            page.snack_bar = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.RED if error else ft.Colors.GREEN_400,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()

        # --- المتغيرات والعناصر الرسومية الرئيسية (UI Elements) ---

        # نصوص الإجماليات
        txt_daily_total = ft.Text("0.00", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        txt_overdue_count = ft.Text("0", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)

        # الجداول
        daily_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("الوقت")),
                ft.DataColumn(ft.Text("الطالب")),
                ft.DataColumn(ft.Text("المبلغ")),
                ft.DataColumn(ft.Text("الطريقة"))
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.GREY_300)
        )

        pending_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("الطالب")),
                ft.DataColumn(ft.Text("رقم القسط")),
                ft.DataColumn(ft.Text("تاريخ الاستحقاق")),
                ft.DataColumn(ft.Text("المبلغ المتبقي")),
                ft.DataColumn(ft.Text("إجراء"))
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.GREY_300)
        )

        student_management_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("الرقم")),
                ft.DataColumn(ft.Text("اسم الطالب")),
                ft.DataColumn(ft.Text("الصف الدراسي")),
                ft.DataColumn(ft.Text("العام الدراسي")),
                ft.DataColumn(ft.Text("هاتف الولي")),
                ft.DataColumn(ft.Text("تعديل"))
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.GREY_300)
        )

        # حقول الإدخال للخطة المالية
        dd_students = ft.Dropdown(label="اختر الطالب", width=300)
        tf_total = ft.TextField(label="إجمالي الرسوم السنوية", width=200, keyboard_type=ft.KeyboardType.NUMBER)
        tf_count = ft.TextField(label="عدد الأقساط", width=150, value="10", keyboard_type=ft.KeyboardType.NUMBER)
        tf_start = ft.TextField(label="تاريخ بداية الأقساط (YYYY-MM-DD)", width=250, value="2025-09-01")

        # تعريف حقول إدخال الطالب
        dlg_std_name = ft.TextField(label="اسم الطالب")
        dlg_std_grade = ft.TextField(label="الصف/المرحلة الدراسية")
        dlg_std_academic_year = ft.TextField(label="العام الدراسي (مثال: 2025-2026)")
        dlg_std_phone = ft.TextField(label="هاتف ولي الأمر (اختياري)")

        # --- دوال تحميل وتحديث البيانات ---

        def load_students_dropdowns():
            try:
                students_list = system.get_students()
                options = [ft.dropdown.Option(key=str(s[0]), text=f"{s[1]} ({s[2]})") for s in students_list]
                dd_students.options = options
                page.update()
                print(f"✅ تم تحميل {len(students_list)} طالب في القائمة المنسدلة")
            except Exception as e:
                print(f"❌ خطأ في تحميل الطلاب: {e}")

        def filter_and_load_student_management_table(query=""):
            global current_managed_students_data

            try:
                if not current_managed_students_data:
                    current_managed_students_data = system.get_all_students_for_management()

                student_management_table.rows.clear()

                filtered_students = []
                if query:
                    q = query.strip().lower()
                    for s in current_managed_students_data:
                        if q in s[1].lower() or (s[4] and q in s[4].lower()):
                            filtered_students.append(s)
                else:
                    filtered_students = current_managed_students_data

                for s in filtered_students:
                    s_id, name, grade, academic_year, phone = s
                    edit_btn = ft.IconButton(
                        icon=ft.Icons.EDIT,
                        icon_color=ft.Colors.AMBER,
                        tooltip="تعديل بيانات الطالب",
                        data=s_id,
                        on_click=lambda e: open_student_form(e, action="edit")
                    )
                    student_management_table.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(str(s_id))),
                            ft.DataCell(ft.Text(name)),
                            ft.DataCell(ft.Text(grade)),
                            ft.DataCell(ft.Text(academic_year or "-")),
                            ft.DataCell(ft.Text(phone or "-")),
                            ft.DataCell(edit_btn),
                        ])
                    )
                page.update()
                print(f"✅ تم تحميل {len(filtered_students)} طالب في جدول الإدارة")
            except Exception as e:
                print(f"❌ خطأ في تحميل جدول الطلاب: {e}")

        def load_pending_installments():
            try:
                pending_table.rows.clear()
                data = system.get_pending_installments()

                for row in data:
                    inst_id, s_name, seq, date, amount, paid_amount = row
                    remaining = amount - paid_amount
                    pay_btn = ft.IconButton(
                        icon=ft.Icons.PAYMENT,
                        icon_color=ft.Colors.BLUE,
                        tooltip="تسديد الآن",
                        data={"id": inst_id, "amount": remaining, "name": s_name},
                        on_click=open_payment_dialog
                    )
                    pending_table.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(s_name)),
                            ft.DataCell(ft.Text(str(seq))),
                            ft.DataCell(ft.Text(date)),
                            ft.DataCell(ft.Text(f"{remaining:,.2f}")),
                            ft.DataCell(pay_btn),
                        ])
                    )
                page.update()
                print(f"✅ تم تحميل {len(data)} قسط معلق")
            except Exception as e:
                print(f"❌ خطأ في تحميل الأقساط: {e}")

        def refresh_dashboard():
            try:
                total, trans, overdue = system.get_daily_stats()
                txt_daily_total.value = f"{total:,.2f} ج.م"
                txt_overdue_count.value = f"{overdue[0]} أقساط"

                daily_table.rows.clear()
                for t in trans:
                    daily_table.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(t[0].split(' ')[1] if ' ' in t[0] else t[0])),
                            ft.DataCell(ft.Text(t[1])),
                            ft.DataCell(ft.Text(f"{t[2]:,.2f}", color=ft.Colors.GREEN)),
                            ft.DataCell(ft.Text(t[3])),
                        ])
                    )

                load_pending_installments()
                load_students_dropdowns()
                page.update()
                print("✅ تم تحديث اللوحة الرئيسية")
            except Exception as e:
                print(f"❌ خطأ في تحديث اللوحة: {e}")

        # --- دوال العمليات (Events Handlers) ---

        def search_students_change(e):
            filter_and_load_student_management_table(e.control.value)

        def handle_print_student_report(e):
            data_to_print = []
            for row in student_management_table.rows:
                data_to_print.append([cell.content.value for cell in row.cells[:-1]])

            msg = f"تم محاكاة طباعة تقرير ({len(data_to_print)} طالب). يجب تطوير وظيفة التصدير لـ PDF."
            show_snackbar(msg, page)

        # --- دوال نوافذ الإدخال المنبثقة ---

        def close_dialog(e):
            dlg_payment.open = False
            student_form_dlg.open = False
            page.update()

        # --- A. نافذة الدفع ---
        def open_payment_dialog(e):
            data = e.control.data
            dlg_amount.value = str(data['amount'])
            dlg_student_pay.value = data['name']
            dlg_payment.data = data['id']
            page.dialog = dlg_payment
            dlg_payment.open = True
            page.update()

        def confirm_payment(e):
            try:
                inst_id = dlg_payment.data
                amt = float(dlg_amount.value)
                method = dlg_method.value
                s_name = dlg_student_pay.value

                success, msg = system.pay_installment(inst_id, amt, method, s_name)

                dlg_payment.open = False
                show_snackbar(msg, page, error=not success)
                refresh_dashboard()

            except ValueError:
                show_snackbar("الرجاء التأكد من المبلغ المدخل.", page, error=True)
                page.update()

        # --- B. نافذة إدارة الطلاب (إضافة / تعديل) ---

        def open_student_form(e, action="add"):
            student_form_dlg.data = {"action": action, "id": None}
            # مسح الحقول عند الفتح
            dlg_std_name.value = ""
            dlg_std_grade.value = ""
            dlg_std_academic_year.value = ""
            dlg_std_phone.value = ""
            student_form_dlg.title.value = "إضافة طالب جديد"

            if action == "edit":
                student_id = e.control.data
                details = system.get_student_details(student_id)
                if details:
                    s_id, name, grade, academic_year, phone = details
                    dlg_std_name.value = name
                    dlg_std_grade.value = grade
                    dlg_std_academic_year.value = academic_year
                    dlg_std_phone.value = phone
                    student_form_dlg.data = {"action": "edit", "id": s_id}
                    student_form_dlg.title.value = f"تعديل بيانات الطالب ({name})"

            page.dialog = student_form_dlg
            student_form_dlg.open = True
            page.update()

        def save_student_data(e):
            """يحفظ بيانات الطالب الجديد أو يعدلها"""
            action = student_form_dlg.data.get("action")
            s_id = student_form_dlg.data.get("id")

            # التقاط القيم من الحقول
            name = dlg_std_name.value.strip()
            grade = dlg_std_grade.value.strip()
            academic_year = dlg_std_academic_year.value.strip()
            phone = dlg_std_phone.value.strip() if dlg_std_phone.value else ""

            if not name or not grade or not academic_year:
                show_snackbar("الاسم، الصف، والعام الدراسي مطلوبة!", page, error=True)
                return

            try:
                if action == "add":
                    success, msg = system.add_new_student(name, grade, academic_year, phone)
                elif action == "edit" and s_id:
                    success, msg = system.update_student_data(s_id, name, grade, academic_year, phone)
                else:
                    success, msg = False, "خطأ غير معروف في العملية."

                student_form_dlg.open = False

                # إعادة تعيين البيانات للتحديث
                global current_managed_students_data
                current_managed_students_data = []

                show_snackbar(msg, page, error=not success)

                # تحديث جميع الجداول والقوائم
                filter_and_load_student_management_table()
                load_students_dropdowns()
                refresh_dashboard()
                page.update()

            except Exception as ex:
                show_snackbar(f"خطأ في الحفظ: {str(ex)}", page, error=True)

        # --- C. دالة حفظ الخطة المالية ---
        def add_plan_click(e):
            """زر حفظ الخطة المالية"""
            student_id = dd_students.value
            total_fees_str = tf_total.value
            count_str = tf_count.value
            start_date = tf_start.value

            if not student_id or not total_fees_str or not count_str or not start_date:
                show_snackbar("الرجاء ملء جميع بيانات الخطة.", page, error=True)
                return

            try:
                total_fees = float(total_fees_str)
                installments_count = int(count_str)

                ok, msg = system.create_fee_plan(
                    int(student_id),
                    total_fees,
                    installments_count,
                    start_date
                )

                if ok:
                    tf_total.value = ""
                    tf_count.value = "10"
                    tf_start.value = "2025-09-01"
                    dd_students.value = None

                show_snackbar(msg, page, error=not ok)
                refresh_dashboard()

            except ValueError as ve:
                show_snackbar(f"خطأ في البيانات: {str(ve)}", page, error=True)
            except Exception as ex:
                show_snackbar(f"خطأ غير متوقع: {str(ex)}", page, error=True)
            page.update()

        # --- تعريف نوافذ الإدخال (Dialogs Definition) ---

        # نافذة الدفع
        dlg_student_pay = ft.TextField(label="الطالب", read_only=True, border_color=ft.Colors.BLUE)
        dlg_amount = ft.TextField(label="المبلغ المدفوع", text_align=ft.TextAlign.RIGHT)
        dlg_method = ft.Dropdown(
            label="طريقة الدفع",
            options=[
                ft.dropdown.Option("Cash"),
                ft.dropdown.Option("Bank Transfer"),
                ft.dropdown.Option("Cheque")
            ],
            value="Cash"
        )

        dlg_payment = ft.AlertDialog(
            title=ft.Text("تسديد قسط وإصدار سند"),
            content=ft.Column([dlg_student_pay, dlg_amount, dlg_method], height=200, tight=True),
            actions=[
                ft.TextButton("إلغاء", on_click=close_dialog),
                ft.ElevatedButton("تأكيد وطباعة", on_click=confirm_payment, bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE),
            ],
        )

        # نافذة إدارة الطلاب (إضافة/تعديل)
        student_form_dlg = ft.AlertDialog(
            title=ft.Text("إدارة بيانات الطالب"),
            content=ft.Column([dlg_std_name, dlg_std_grade, dlg_std_academic_year, dlg_std_phone], height=320, tight=True),
            actions=[
                ft.TextButton("إلغاء", on_click=close_dialog),
                ft.ElevatedButton("حفظ البيانات", on_click=save_student_data, icon=ft.Icons.SAVE),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # --- تصميم الهيكل العام (Layout Structure) ---

        # الكروت العلوية (KPIs)
        card_revenue = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.MONETIZATION_ON, color=ft.Colors.WHITE, size=30),
                ft.Text("إيراد الخزينة اليوم", color=ft.Colors.WHITE70),
                txt_daily_total
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.TEAL,
            padding=20,
            border_radius=15,
            expand=True
        )

        card_overdue = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.WHITE, size=30),
                ft.Text("المتأخرات الحرجة", color=ft.Colors.WHITE70),
                txt_overdue_count
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.RED_400,
            padding=20,
            border_radius=15,
            expand=True
        )

        # التبويبات الرئيسية
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="لوحة التحصيل",
                    icon=ft.Icons.DASHBOARD,
                    content=ft.Container(
                        padding=10,
                        content=ft.Column([
                            ft.Row([card_revenue, card_overdue]),
                            ft.Divider(height=20),
                            ft.Text("الأقساط المستحقة", size=18, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=pending_table,
                                height=300,
                                border=ft.border.all(1, ft.Colors.GREY_300)
                            ),
                            ft.Divider(height=20),
                            ft.Text("سجل الحركات اليومية", size=18, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=daily_table,
                                height=200,
                                bgcolor=ft.Colors.GREY_50,
                                border_radius=10,
                                padding=10
                            )
                        ], scroll=ft.ScrollMode.ADAPTIVE)
                    )
                ),
                ft.Tab(
                    text="الخطط المالية",
                    icon=ft.Icons.RECEIPT_LONG,
                    content=ft.Container(
                        padding=30,
                        content=ft.Column([
                            ft.Text("إنشاء خطة تقسيط جديدة", size=24, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            dd_students,
                            ft.Row([tf_total, tf_count]),
                            tf_start,
                            ft.ElevatedButton(
                                "حفظ الخطة وتوليد الأقساط",
                                on_click=add_plan_click,
                                icon=ft.Icons.SAVE,
                                style=ft.ButtonStyle(padding=20)
                            )
                        ])
                    )
                ),
                ft.Tab(
                    text="إدارة الطلاب",
                    icon=ft.Icons.PEOPLE,
                    content=ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Row([
                                ft.TextField(
                                    label="ابحث بالاسم أو الهاتف",
                                    width=350,
                                    on_change=search_students_change,
                                    prefix_icon=ft.Icons.SEARCH
                                ),
                                ft.ElevatedButton(
                                    "طباعة التقرير",
                                    on_click=handle_print_student_report,
                                    icon=ft.Icons.PRINT
                                ),
                                ft.ElevatedButton(
                                    "إضافة طالب جديد",
                                    on_click=lambda e: open_student_form(e, action="add"),
                                    icon=ft.Icons.PERSON_ADD
                                )
                            ]),
                            ft.Divider(),
                            ft.Container(
                                content=student_management_table,
                                height=500,
                                border=ft.border.all(1, ft.Colors.GREY_300)
                            )
                        ])
                    )
                ),
            ],
            expand=True,
        )

        page.add(tabs)

        # تهيئة وتحميل البيانات الأولية
        print("🔄 جاري تحميل البيانات الأولية...")
        refresh_dashboard()
        filter_and_load_student_management_table()
        print("✅ التطبيق جاهز للاستخدام!")
    except Exception as e:
        print(f"❌ Error in main: {e}")
        traceback.print_exc()

        # Show error in UI
        page.add(ft.Text(f"Error: {str(e)}", color="red"))
        page.update()

# تشغيل التطبيق
if __name__ == "__main__":
    try:
        ft.app(target=main, view=ft.WEB_BROWSER, port=8550)
    except Exception as e:
        print(f"❌ Failed to start app: {e}")
        sys.exit(1)
