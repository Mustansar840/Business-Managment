import customtkinter as ctk
import database
from tkinter import messagebox, filedialog
from datetime import date, datetime
from fpdf import FPDF
import csv
import os
import subprocess
import sys
import webbrowser
import urllib.parse

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ================== APP SETUP (Only Dark Mode) ==================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LedgerProApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LedgerPro - Business Management")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # Single admin PIN (default)
        self.admin_pin = "1234"

        # Login screen
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(fill="both", expand=True)
        self.build_login_ui()

    # ================= IMPROVED LOGIN UI =================
    def build_login_ui(self):
        for widget in self.login_frame.winfo_children():
            widget.destroy()

        # Main card
        login_card = ctk.CTkFrame(self.login_frame, width=420, height=440, corner_radius=20,
                                  fg_color="#1e1e1e")
        login_card.place(relx=0.5, rely=0.45, anchor="center")

        # Logo / Icon
        ctk.CTkLabel(login_card, text="🔐", font=ctk.CTkFont(size=48)).pack(pady=(30, 10))
        ctk.CTkLabel(login_card, text="LedgerPro", font=ctk.CTkFont(size=28, weight="bold")).pack()
        ctk.CTkLabel(login_card, text="Business at a Glance", font=ctk.CTkFont(size=14)).pack(pady=(0, 25))

        # PIN entry
        self.pin_entry = ctk.CTkEntry(login_card, placeholder_text="Admin PIN", show="*",
                                      width=200, height=45, font=ctk.CTkFont(size=18),
                                      justify="center")
        self.pin_entry.pack(pady=15)
        self.pin_entry.bind("<Return>", lambda e: self.check_pin())

        # Error message
        self.login_error = ctk.CTkLabel(login_card, text="", text_color="red", font=ctk.CTkFont(size=12))
        self.login_error.pack(pady=(0, 10))

        # Login button
        ctk.CTkButton(login_card, text="Login", width=200, height=45,
                      font=ctk.CTkFont(size=16, weight="bold"),
                      command=self.check_pin).pack(pady=5)

        # Change PIN button
        ctk.CTkButton(login_card, text="Change PIN", width=200, height=35,
                      fg_color="gray", command=self.change_pin_dialog).pack(pady=10)

    def check_pin(self):
        entered = self.pin_entry.get()
        if entered == self.admin_pin:
            self.login_frame.destroy()
            self.initialize_main_ui()
        else:
            self.login_error.configure(text="❌ Incorrect PIN!")
            self.pin_entry.delete(0, 'end')

    def change_pin_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Change Admin PIN")
        dialog.geometry("300x250")
        dialog.grab_set()
        dialog.configure(fg_color="#1e1e1e")

        ctk.CTkLabel(dialog, text="Change Admin PIN", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)

        ctk.CTkLabel(dialog, text="Old PIN").pack(pady=5)
        old_pin = ctk.CTkEntry(dialog, show="*", width=180)
        old_pin.pack()

        ctk.CTkLabel(dialog, text="New PIN").pack(pady=5)
        new_pin = ctk.CTkEntry(dialog, show="*", width=180)
        new_pin.pack()

        error_lbl = ctk.CTkLabel(dialog, text="", text_color="red")
        error_lbl.pack(pady=5)

        def save_new_pin():
            if old_pin.get() != self.admin_pin:
                error_lbl.configure(text="Old PIN incorrect!")
                return
            if not new_pin.get():
                error_lbl.configure(text="New PIN cannot be empty!")
                return
            self.admin_pin = new_pin.get()
            dialog.destroy()
            messagebox.showinfo("Success", "Admin PIN changed successfully!")

        ctk.CTkButton(dialog, text="Save", command=save_new_pin).pack(pady=10)

    # ================= MAIN UI (Admin Full Access) =================
    def initialize_main_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="LedgerPro",
                                       font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.pack(pady=30, padx=20)

        nav_buttons = [
            ("📊 Dashboard", self.show_dashboard),
            ("👥 Staff & Salary", self.show_employees),
            ("📋 Daily Attendance", self.show_attendance),
            ("💰 Salary Report", self.show_salary_report),
            ("📒 Ledger / Hisab", self.show_ledger),
        ]
        for text, cmd in nav_buttons:
            ctk.CTkButton(self.sidebar, text=text, height=42, command=cmd).pack(pady=6, padx=20)

        # Daily Report & Admin Tools
        ctk.CTkButton(self.sidebar, text="📤 Send Daily Report", height=36, fg_color="#25D366",
                      command=self.send_daily_report).pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="☁️ Sync to Cloud", height=36, fg_color="#2E8B57",
                      command=self.cloud_upload).pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="⬇️ Download from Cloud", height=36, fg_color="#8B4513",
                      command=self.cloud_download).pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="💾 Backup DB", height=36, fg_color="#444",
                      command=self.backup_db).pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="📥 Restore DB", height=36, fg_color="#444",
                      command=self.restore_db).pack(pady=5, padx=20)

        # Main container
        self.main_container = ctk.CTkFrame(self, corner_radius=10)
        self.main_container.pack(side="right", fill="both", expand=True, padx=15, pady=15)

        self.show_dashboard()

    # ================= Admin Utility Methods =================
    def send_daily_report(self):
        total_in, total_out = database.get_dashboard_summary()
        balance = total_in - total_out
        today_str = date.today().strftime("%d-%b-%Y")
        missing = database.get_missing_attendance_today()
        missing_str = ", ".join(missing) if missing else "None"

        msg = f"*📋 Daily Report - {today_str}*\n\n"
        msg += f"💰 Income: Rs {total_in:,.0f}\n"
        msg += f"📤 Expense: Rs {total_out:,.0f}\n"
        msg += f"🏦 Balance: Rs {balance:,.0f}\n"
        msg += f"⚠️ Missing Attendance: {missing_str}\n"

        boss_phone = "+920000000000"   # <-- yahan apna real number daalein
        url = f"https://wa.me/{boss_phone}?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)

    def backup_db(self):
        path = database.backup_database()
        messagebox.showinfo("Backup", f"Database backed up to:\n{path}")

    def restore_db(self):
        file_path = filedialog.askopenfilename(title="Select Backup File",
                                               filetypes=[("Database files", "*.db")])
        if file_path:
            if messagebox.askyesno("Confirm Restore", "This will replace current data. Proceed?"):
                database.restore_database(file_path)
                messagebox.showinfo("Restore", "Database restored. Restart app to see changes.")

    def cloud_upload(self):
        result = database.cloud_upload()
        messagebox.showinfo("Cloud Sync", result)

    def cloud_download(self):
        result = database.cloud_download()
        messagebox.showinfo("Cloud Sync", result)

    def clear_screen(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

    # ================= DASHBOARD (Full Admin – No restrictions) =================
    def show_dashboard(self):
        self.current_screen = self.show_dashboard
        self.clear_screen()

        ctk.CTkLabel(self.main_container, text="Dashboard", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=10)

        total_in, total_out = database.get_dashboard_summary()
        balance = total_in - total_out
        liabilities = database.get_total_liabilities()
        top_cat, top_amt = database.get_top_expense_category_this_month()
        emp_count = database.get_employee_count()

        today = date.today()
        current_month = today.month
        current_year = today.year
        prev_month = current_month - 1 if current_month > 1 else 12
        prev_year = current_year if current_month > 1 else current_year - 1
        prev_in, prev_out = database.get_monthly_summary(prev_year, prev_month)

        def change_arrow(current, previous):
            if previous == 0:
                return "↗️ N/A"
            diff = ((current - previous) / previous) * 100
            return f"↑ {diff:.1f}%" if diff > 0 else f"↓ {abs(diff):.1f}%"

        # KPI Cards
        kpi_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        kpi_frame.pack(pady=10, padx=10, fill="x")
        kpi_frame.columnconfigure((0,1,2,3,4), weight=1)

        def make_kpi(parent, title, value, trend, bg_color, row, col):
            card = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=15)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10,5))
            ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=22, weight="bold")).pack()
            ctk.CTkLabel(card, text=trend, font=ctk.CTkFont(size=12),
                         text_color="lightgray").pack(pady=(5,10))

        make_kpi(kpi_frame, "💰 Total Income", f"Rs {total_in:,.0f}", change_arrow(total_in, prev_in), "#2E8B57", 0, 0)
        make_kpi(kpi_frame, "📤 Total Expense", f"Rs {total_out:,.0f}", change_arrow(total_out, prev_out), "#B22222", 0, 1)
        make_kpi(kpi_frame, "🏦 Cash Balance", f"Rs {balance:,.0f}", "Balance", "#4682B4", 0, 2)
        make_kpi(kpi_frame, "🧾 Liabilities", f"Rs {liabilities:,.0f}", "Unpaid Salary", "#8B4513", 0, 3)
        make_kpi(kpi_frame, "👥 Active Staff", f"{emp_count}", f"Top: {top_cat}" if top_cat!="None" else "N/A", "#5e2c5e", 0, 4)

        # Charts (always visible)
        chart_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        chart_frame.pack(pady=10, padx=10, fill="both", expand=True)

        left_chart = ctk.CTkFrame(chart_frame, corner_radius=15)
        left_chart.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(left_chart, text="📈 Monthly Income vs Expense", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        right_chart = ctk.CTkFrame(chart_frame, corner_radius=15)
        right_chart.pack(side="right", fill="both", expand=True, padx=5)
        ctk.CTkLabel(right_chart, text="🥧 Expense Breakdown (This Month)", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        # Matplotlib theme (dark)
        facecolor = '#1e1e1e'
        textcolor = 'white'

        # Bar chart
        fig1 = Figure(figsize=(4, 3), dpi=100)
        ax1 = fig1.add_subplot(111)
        months = []
        incomes = []
        expenses = []
        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            inc, exp = database.get_monthly_summary(y, m)
            months.append(date(y, m, 1).strftime('%b'))
            incomes.append(inc)
            expenses.append(exp)
        x = range(len(months))
        ax1.bar([i-0.15 for i in x], incomes, width=0.3, color='#2E8B57', label='Income')
        ax1.bar([i+0.15 for i in x], expenses, width=0.3, color='#B22222', label='Expense')
        ax1.set_xticks(x)
        ax1.set_xticklabels(months)
        ax1.legend()
        ax1.tick_params(colors=textcolor)
        ax1.set_facecolor(facecolor)
        fig1.patch.set_facecolor(facecolor)
        for spine in ax1.spines.values():
            spine.set_color(textcolor)
        canvas1 = FigureCanvasTkAgg(fig1, master=left_chart)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True)

        # Pie chart
        conn = database.sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        month_str = today.strftime("%Y-%m")
        cursor.execute("SELECT category, SUM(amount) FROM ledger WHERE category IN ('Expense', 'Hand Cash', 'Cash to Boss') AND date LIKE ? GROUP BY category", (month_str+'%',))
        rows = cursor.fetchall()
        conn.close()
        labels = [r[0] for r in rows]
        sizes = [r[1] for r in rows]
        fig2 = Figure(figsize=(4, 3), dpi=100)
        ax2 = fig2.add_subplot(111)
        if sizes:
            ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['#ff6347','#ffa500','#4682b4'])
            ax2.axis('equal')
        else:
            ax2.text(0.5,0.5,'No expenses', ha='center', va='center', color=textcolor)
        ax2.set_facecolor(facecolor)
        fig2.patch.set_facecolor(facecolor)
        canvas2 = FigureCanvasTkAgg(fig2, master=right_chart)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True)

        # Alerts panel
        alerts_frame = ctk.CTkFrame(self.main_container, corner_radius=10)
        alerts_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(alerts_frame, text="⚠️ Alerts & Warnings", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=5)
        over_adv = database.get_over_advance_employees()
        if over_adv:
            for name, adv, est in over_adv:
                ctk.CTkLabel(alerts_frame, text=f"🚨 {name} ka advance Rs {adv:,.0f} unki monthly salary ke 50% se zyada hai!",
                             text_color="red").pack(anchor="w", padx=20)
        missing = database.get_missing_attendance_today()
        if missing:
            names = ", ".join(missing)
            ctk.CTkLabel(alerts_frame, text=f"📋 Aaj in employees ki hazri baaki hai: {names}",
                         text_color="orange").pack(anchor="w", padx=20)
        if balance < 5000:
            ctk.CTkLabel(alerts_frame, text=f"💸 Low Cash Warning! Current Balance: Rs {balance:,.0f}",
                         text_color="yellow").pack(anchor="w", padx=20)
        if not over_adv and not missing and balance >= 5000:
            ctk.CTkLabel(alerts_frame, text="✅ Sab kuch theek hai! Koi warnings nahi.", text_color="green").pack(anchor="w", padx=20)

        # Recent Activity
        feed_frame = ctk.CTkFrame(self.main_container, corner_radius=10)
        feed_frame.pack(pady=10, padx=10, fill="both", expand=False)
        ctk.CTkLabel(feed_frame, text="🕒 Recent Activity", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=5)
        activities = database.get_recent_activities(5)
        for ts, desc in activities:
            ctk.CTkLabel(feed_frame, text=f"{ts} - {desc}", font=ctk.CTkFont(size=12), anchor="w").pack(anchor="w", padx=20, pady=2)

    # ================= STAFF MANAGEMENT (unchanged) =================
    def show_employees(self):
        self.current_screen = self.show_employees
        self.clear_screen()
        ctk.CTkLabel(self.main_container, text="Staff & Per Day Salary Management",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)

        form_frame = ctk.CTkFrame(self.main_container)
        form_frame.pack(pady=10, padx=20, fill="x")

        self.emp_name = ctk.CTkEntry(form_frame, placeholder_text="Naam", width=180)
        self.emp_name.pack(side="left", padx=5, pady=10)
        self.emp_phone = ctk.CTkEntry(form_frame, placeholder_text="Phone", width=130)
        self.emp_phone.pack(side="left", padx=5, pady=10)
        self.emp_salary = ctk.CTkEntry(form_frame, placeholder_text="Per Day Salary (Rs)", width=150)
        self.emp_salary.pack(side="left", padx=5, pady=10)

        ctk.CTkButton(form_frame, text="Save Data", width=100, fg_color="green", command=self.save_employee).pack(side="left", padx=5)
        ctk.CTkButton(form_frame, text="Clear", width=70, fg_color="gray", command=self.clear_emp_form).pack(side="left", padx=5)

        ctk.CTkLabel(self.main_container, text="Mojooda Staff:", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        self.emp_list_frame = ctk.CTkScrollableFrame(self.main_container, width=800, height=300)
        self.emp_list_frame.pack(pady=10, padx=20, fill="both", expand=True)
        self.load_employees_list()

    def clear_emp_form(self):
        self.emp_name.delete(0, 'end')
        self.emp_phone.delete(0, 'end')
        self.emp_salary.delete(0, 'end')

    def load_employees_list(self):
        for widget in self.emp_list_frame.winfo_children(): widget.destroy()
        headers = ["Naam", "Phone", "Per Day Salary", "Action"]
        for col, txt in enumerate(headers):
            ctk.CTkLabel(self.emp_list_frame, text=txt, font=ctk.CTkFont(weight="bold"), width=180, anchor="w").grid(row=0, column=col, padx=10, pady=5)
        for idx, emp in enumerate(database.get_all_employees()):
            emp_id, name, phone, salary = emp
            ctk.CTkLabel(self.emp_list_frame, text=name, width=180).grid(row=idx+1, column=0, padx=10, pady=5)
            ctk.CTkLabel(self.emp_list_frame, text=phone, width=180).grid(row=idx+1, column=1, padx=10, pady=5)
            ctk.CTkLabel(self.emp_list_frame, text=f"Rs {salary}", width=180).grid(row=idx+1, column=2, padx=10, pady=5)
            ctk.CTkButton(self.emp_list_frame, text="Delete", width=70, fg_color="#B22222",
                          command=lambda e_id=emp_id: self.delete_emp(e_id)).grid(row=idx+1, column=3, padx=10, pady=5)

    def save_employee(self):
        name, phone, salary = self.emp_name.get(), self.emp_phone.get(), self.emp_salary.get()
        if not name or not salary:
            messagebox.showerror("Error", "Naam aur Per Day Salary likhna zaroori hai!")
            return
        try:
            per_day = float(salary)
        except ValueError:
            messagebox.showerror("Error", "Salary mein sirf number daalein")
            return
        database.insert_employee(name, phone, per_day)
        self.clear_emp_form()
        self.load_employees_list()

    def delete_emp(self, emp_id):
        if messagebox.askyesno("Confirm", "Delete employee?"):
            database.delete_employee(emp_id)
            self.load_employees_list()

    # ================= ATTENDANCE (unchanged) =================
    def show_attendance(self):
        self.current_screen = self.show_attendance
        self.clear_screen()
        ctk.CTkLabel(self.main_container, text="Daily Attendance & Advance", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)

        form_frame = ctk.CTkFrame(self.main_container)
        form_frame.pack(pady=10, padx=20, fill="x")

        self.att_date_var = ctk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.att_date_var.trace_add("write", self.update_att_dropdown)

        self.att_date = ctk.CTkEntry(form_frame, textvariable=self.att_date_var, width=110)
        self.att_date.pack(side="left", padx=5)

        self.att_employee = ctk.CTkOptionMenu(form_frame, values=["Loading..."], width=150)
        self.att_employee.pack(side="left", padx=5)
        self.update_att_dropdown()

        self.att_status = ctk.CTkOptionMenu(form_frame, values=["Present (P)", "Half Day (H)", "Absent (A)"], width=130)
        self.att_status.pack(side="left", padx=5)

        self.att_advance = ctk.CTkEntry(form_frame, placeholder_text="Advance Rs", width=120)
        self.att_advance.insert(0, "0")
        self.att_advance.pack(side="left", padx=5)

        ctk.CTkButton(form_frame, text="Mark Hazri", width=100, fg_color="purple", command=self.save_attendance).pack(side="left", padx=5)

        filter_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        filter_frame.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(filter_frame, text="Filter By Name:").pack(side="left", padx=5)
        all_names = ["All"] + database.get_employee_names()
        self.filter_emp_var = ctk.StringVar(value="All")
        self.filter_emp_menu = ctk.CTkOptionMenu(filter_frame, values=all_names, variable=self.filter_emp_var,
                                                 command=self.load_attendance_list)
        self.filter_emp_menu.pack(side="left", padx=5)

        ctk.CTkLabel(filter_frame, text="Filter By Date:").pack(side="left", padx=5)
        self.filter_date_var = ctk.StringVar(value="")
        self.filter_date_entry = ctk.CTkEntry(filter_frame, textvariable=self.filter_date_var, placeholder_text="e.g. 2026-06-05", width=120)
        self.filter_date_entry.pack(side="left", padx=5)
        ctk.CTkButton(filter_frame, text="Search Date", width=80, command=self.load_attendance_list).pack(side="left", padx=5)
        ctk.CTkButton(filter_frame, text="Clear Filters", width=80, fg_color="gray", command=self.clear_att_filters).pack(side="left", padx=5)

        ctk.CTkButton(filter_frame, text="📅 Calendar View", width=100, fg_color="#2a5c8a", command=self.show_calendar).pack(side="left", padx=10)

        self.att_total_lbl = ctk.CTkLabel(filter_frame, text="Total Advance: Rs 0", font=ctk.CTkFont(size=16, weight="bold"), text_color="orange")
        self.att_total_lbl.pack(side="right", padx=10)

        self.att_list_frame = ctk.CTkScrollableFrame(self.main_container, width=850, height=350)
        self.att_list_frame.pack(pady=10, padx=20, fill="both", expand=True)
        self.load_attendance_list()

    def update_att_dropdown(self, *args):
        current_date = self.att_date_var.get()
        unmarked = database.get_unmarked_employees(current_date)
        if unmarked:
            self.att_employee.configure(values=unmarked)
            self.att_employee.set(unmarked[0])
        else:
            self.att_employee.configure(values=["Sab Ki Hazri Lag Gayi"])
            self.att_employee.set("Sab Ki Hazri Lag Gayi")

    def clear_att_filters(self):
        self.filter_emp_var.set("All")
        self.filter_date_var.set("")
        self.load_attendance_list()

    def save_attendance(self):
        date_val = self.att_date_var.get()
        emp_name = self.att_employee.get()
        status = self.att_status.get().split()[0]
        advance = self.att_advance.get()

        if emp_name == "Sab Ki Hazri Lag Gayi" or not emp_name:
            messagebox.showerror("Error", "Koi employee nahi bacha!")
            return
        try:
            advance_float = float(advance)
        except ValueError:
            messagebox.showerror("Error", "Advance mein number daalein!")
            return

        database.insert_attendance(emp_name, date_val, status, advance_float)
        self.att_advance.delete(0, 'end'); self.att_advance.insert(0, "0")
        self.update_att_dropdown()
        self.load_attendance_list()

    def load_attendance_list(self, *args):
        for widget in self.att_list_frame.winfo_children(): widget.destroy()

        headers = ["Date", "Employee", "Status", "Advance", "Action"]
        for col, txt in enumerate(headers):
            ctk.CTkLabel(self.att_list_frame, text=txt, font=ctk.CTkFont(weight="bold"), width=120, anchor="w").grid(row=0, column=col, padx=5, pady=5)

        emp_filter = self.filter_emp_var.get()
        date_filter = self.filter_date_var.get()
        records = database.get_attendance_records(emp_filter, date_filter)

        total_adv = 0
        for idx, rec in enumerate(records):
            att_id, date_val, name, status, adv = rec
            total_adv += adv
            ctk.CTkLabel(self.att_list_frame, text=date_val, width=120).grid(row=idx+1, column=0, padx=5, pady=5)
            ctk.CTkLabel(self.att_list_frame, text=name, width=150).grid(row=idx+1, column=1, padx=5, pady=5)
            ctk.CTkLabel(self.att_list_frame, text=status, width=120).grid(row=idx+1, column=2, padx=5, pady=5)
            ctk.CTkLabel(self.att_list_frame, text=f"Rs {adv}", width=120).grid(row=idx+1, column=3, padx=5, pady=5)
            ctk.CTkButton(self.att_list_frame, text="Delete", width=70, fg_color="#B22222",
                          command=lambda a_id=att_id: self.delete_att(a_id)).grid(row=idx+1, column=4, padx=5, pady=5)

        if emp_filter != "All":
            details = database.get_employee_salary_details(emp_filter)
            if details:
                net_pay = details['net_payable']
                self.att_total_lbl.configure(text=f"Total Advance: Rs {total_adv:,.0f} | Net Salary Banti: Rs {net_pay:,.0f}")
            else:
                self.att_total_lbl.configure(text=f"Total Advance: Rs {total_adv:,.0f}")
        else:
            self.att_total_lbl.configure(text=f"Total Advance: Rs {total_adv:,.0f}")

    def delete_att(self, att_id):
        if messagebox.askyesno("Confirm", "Hazri delete karni hai?"):
            database.delete_attendance(att_id)
            self.update_att_dropdown()
            self.load_attendance_list()

    def show_calendar(self):
        emp_name = self.filter_emp_var.get()
        if emp_name == "All":
            messagebox.showinfo("Select Employee", "Calendar view ke liye pehle kisi ek employee ko filter karein.")
            return
        cal_win = ctk.CTkToplevel(self)
        cal_win.title(f"Attendance Calendar - {emp_name}")
        cal_win.geometry("400x400")
        cal_win.grab_set()
        today = date.today()
        year, month = today.year, today.month
        att_dict = database.get_month_attendance(emp_name, year, month)

        cal_frame = ctk.CTkFrame(cal_win)
        cal_frame.pack(pady=20, padx=20, fill="both", expand=True)

        month_lbl = ctk.CTkLabel(cal_frame, text=f"{date(year, month, 1).strftime('%B %Y')}", font=ctk.CTkFont(size=18, weight="bold"))
        month_lbl.grid(row=0, column=0, columnspan=7, pady=10)

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(days):
            ctk.CTkLabel(cal_frame, text=day, width=40).grid(row=1, column=i)

        first_day = date(year, month, 1)
        start_weekday = first_day.weekday()
        if month == 12:
            num_days = 31
        else:
            next_month = date(year, month+1, 1)
            num_days = (next_month - first_day).days

        row = 2
        col = start_weekday
        for d in range(1, num_days+1):
            day_str = f"{year}-{month:02d}-{d:02d}"
            status = att_dict.get(day_str, "")
            color = "#333"
            if status == "Present":
                color = "#2E8B57"
            elif status == "Half":
                color = "#DAA520"
            elif status == "Absent":
                color = "#B22222"
            elif d > today.day:
                color = "#555"
            box = ctk.CTkLabel(cal_frame, text=str(d), width=40, height=30, fg_color=color, corner_radius=5)
            box.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col > 6:
                col = 0
                row += 1

        legend_frame = ctk.CTkFrame(cal_win)
        legend_frame.pack(pady=10)
        ctk.CTkLabel(legend_frame, text="Present", fg_color="#2E8B57", corner_radius=4, width=80).pack(side="left", padx=5)
        ctk.CTkLabel(legend_frame, text="Half", fg_color="#DAA520", corner_radius=4, width=60).pack(side="left", padx=5)
        ctk.CTkLabel(legend_frame, text="Absent", fg_color="#B22222", corner_radius=4, width=80).pack(side="left", padx=5)

    # ================= SALARY REPORT =================
    def show_salary_report(self):
        self.current_screen = self.show_salary_report
        self.clear_screen()
        ctk.CTkLabel(self.main_container, text="Salary Report & Clearance", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)

        ctrl_frame = ctk.CTkFrame(self.main_container)
        ctrl_frame.pack(pady=10, padx=20, fill="x")

        staff_names = database.get_employee_names()
        if not staff_names: staff_names = ["No Staff Available"]
        self.sal_emp_combo = ctk.CTkOptionMenu(ctrl_frame, values=staff_names, width=200)
        self.sal_emp_combo.pack(side="left", padx=10)

        ctk.CTkButton(ctrl_frame, text="Generate Receipt", command=self.generate_receipt).pack(side="left", padx=10)

        self.receipt_frame = ctk.CTkFrame(self.main_container, width=500, height=500, fg_color="#1E1E1E")
        self.receipt_frame.pack(pady=20)
        self.receipt_frame.pack_propagate(False)

    def generate_receipt(self):
        emp_name = self.sal_emp_combo.get()
        if emp_name == "No Staff Available":
            messagebox.showerror("Error", "Pehle staff add karein!")
            return

        details = database.get_employee_salary_details(emp_name)
        if not details: return

        for widget in self.receipt_frame.winfo_children(): widget.destroy()

        ctk.CTkLabel(self.receipt_frame, text=f"Salary Slip: {emp_name}", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#FFD700").pack(pady=(20,10))
        ctk.CTkLabel(self.receipt_frame, text=f"Per Day Salary: Rs {details['per_day']}", font=ctk.CTkFont(size=14)).pack(pady=2)
        ctk.CTkLabel(self.receipt_frame, text=f"Total Presents: {details['presents']} Din", font=ctk.CTkFont(size=14)).pack(pady=2)
        ctk.CTkLabel(self.receipt_frame, text=f"Half Days: {details['half_days']} Din", font=ctk.CTkFont(size=14)).pack(pady=2)
        ctk.CTkLabel(self.receipt_frame, text=f"Total Earned: Rs {details['earned']}",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color="lightgreen").pack(pady=10)
        ctk.CTkLabel(self.receipt_frame, text=f"Advance Taken: - Rs {details['advance']}",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color="#FF6347").pack(pady=2)
        ctk.CTkLabel(self.receipt_frame, text="----------------------------").pack(pady=5)
        ctk.CTkLabel(self.receipt_frame, text=f"Net Payable: Rs {details['net_payable']}",
                     font=ctk.CTkFont(size=24, weight="bold"), text_color="#00FFFF").pack(pady=10)

        btn_row = ctk.CTkFrame(self.receipt_frame)
        btn_row.pack(pady=10)
        if details['net_payable'] > 0:
            ctk.CTkButton(btn_row, text="Pay & Clear", fg_color="green",
                          command=lambda: self.pay_salary(emp_name, details['net_payable'])).pack(side="left", padx=5)
        elif details['net_payable'] == 0:
            ctk.CTkLabel(self.receipt_frame, text="Sab Hisab Clear Hai!", font=ctk.CTkFont(size=16, weight="bold"),
                         text_color="gray").pack(pady=15)
        else:
            ctk.CTkLabel(self.receipt_frame, text="Advance zyada liya hua hai!", font=ctk.CTkFont(size=16, weight="bold"),
                         text_color="red").pack(pady=15)

        ctk.CTkButton(btn_row, text="📥 PDF", fg_color="#2a5c8a",
                      command=lambda: self.export_salary_pdf(emp_name, details)).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="📄 CSV", fg_color="#2a5c8a",
                      command=lambda: self.export_salary_csv(emp_name, details)).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="📱 WhatsApp", fg_color="#25D366",
                      command=lambda: self.send_whatsapp_salary(emp_name, details)).pack(side="left", padx=5)

        hist_frame = ctk.CTkFrame(self.receipt_frame)
        hist_frame.pack(pady=10, fill="x")
        ctk.CTkLabel(hist_frame, text="Payment History", font=ctk.CTkFont(weight="bold")).pack()
        history = database.get_payment_history(emp_name)
        if history:
            for h in history[:5]:
                ctk.CTkLabel(hist_frame, text=f"{h[0]}  -  Rs {h[1]}", font=ctk.CTkFont(size=12)).pack(anchor="w")
        else:
            ctk.CTkLabel(hist_frame, text="No previous payments").pack()

    def send_whatsapp_salary(self, emp_name, details):
        conn = database.sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT phone FROM employees WHERE name=?", (emp_name,))
        row = cursor.fetchone()
        conn.close()
        phone = row[0] if row and row[0] else ""
        if not phone:
            messagebox.showerror("Error", "Employee ka phone number nahi hai!")
            return
        msg = f"*Salary Slip - {emp_name}*\n"
        msg += f"Per Day: Rs {details['per_day']}\n"
        msg += f"Presents: {details['presents']}, Half: {details['half_days']}\n"
        msg += f"Earned: Rs {details['earned']}\n"
        msg += f"Advance: Rs {details['advance']}\n"
        msg += f"Net Payable: Rs {details['net_payable']}"
        url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)

    def pay_salary(self, emp_name, amount):
        if messagebox.askyesno("Confirm Payment", f"{emp_name} ko Rs {amount} de kar clear karna hai?"):
            database.pay_and_clear_salary(emp_name, amount)
            self.generate_receipt()

    def export_salary_pdf(self, emp_name, details):
        filename = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                filetypes=[("PDF files", "*.pdf")],
                                                initialfile=f"Salary_Receipt_{emp_name}.pdf")
        if not filename: return
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=16, style='B')
            pdf.cell(200, 10, txt=f"Salary Receipt - {emp_name}", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Helvetica", size=12)
            pdf.cell(200, 10, txt=f"Per Day Salary: Rs {details['per_day']}", ln=True)
            pdf.cell(200, 10, txt=f"Total Presents: {details['presents']} Din", ln=True)
            pdf.cell(200, 10, txt=f"Half Days: {details['half_days']} Din", ln=True)
            pdf.cell(200, 10, txt=f"Total Earned: Rs {details['earned']}", ln=True)
            pdf.cell(200, 10, txt=f"Advance Taken: Rs {details['advance']}", ln=True)
            pdf.ln(5)
            pdf.set_font("Helvetica", size=14, style='B')
            pdf.cell(200, 10, txt=f"Net Payable: Rs {details['net_payable']}", ln=True)
            pdf.output(filename)
            messagebox.showinfo("Success", "PDF saved!")
        except Exception as e:
            messagebox.showerror("Error", f"PDF creation failed: {e}")

    def export_salary_csv(self, emp_name, details):
        filename = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv")],
                                                initialfile=f"Salary_Receipt_{emp_name}.csv")
        if not filename: return
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Field", "Value"])
                writer.writerow(["Employee", emp_name])
                writer.writerow(["Per Day Salary", details['per_day']])
                writer.writerow(["Presents", details['presents']])
                writer.writerow(["Half Days", details['half_days']])
                writer.writerow(["Total Earned", details['earned']])
                writer.writerow(["Advance", details['advance']])
                writer.writerow(["Net Payable", details['net_payable']])
            messagebox.showinfo("Success", "CSV saved!")
        except Exception as e:
            messagebox.showerror("Error", f"CSV creation failed: {e}")

    # ================= LEDGER (unchanged) =================
    def show_ledger(self):
        self.current_screen = self.show_ledger
        self.clear_screen()
        ctk.CTkLabel(self.main_container, text="Hisab Kitab / Ledger", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)

        form_frame = ctk.CTkFrame(self.main_container)
        form_frame.pack(pady=10, padx=20, fill="x")

        self.trans_date = ctk.CTkEntry(form_frame, placeholder_text="Date", width=110)
        self.trans_date.insert(0, date.today().strftime("%Y-%m-%d"))
        self.trans_date.pack(side="left", padx=5)

        self.trans_category = ctk.CTkOptionMenu(form_frame, values=["Boss Investment", "Customer Payment",
                                                                   "Expense", "Hand Cash", "Cash to Boss"], width=150)
        self.trans_category.pack(side="left", padx=5)

        self.trans_amount = ctk.CTkEntry(form_frame, placeholder_text="Amount (Rs)", width=100)
        self.trans_amount.pack(side="left", padx=5)

        self.trans_desc = ctk.CTkEntry(form_frame, placeholder_text="Tafseel", width=150)
        self.trans_desc.pack(side="left", padx=5)

        self.attached_image_path = None
        self.attach_label = ctk.CTkLabel(form_frame, text="No file", text_color="gray", width=100)
        self.attach_label.pack(side="left", padx=5)

        ctk.CTkButton(form_frame, text="📎 Attach", width=70, command=self.attach_image).pack(side="left", padx=5)
        ctk.CTkButton(form_frame, text="Add Record", width=90, fg_color="blue", command=self.save_transaction).pack(side="left", padx=5)
        ctk.CTkButton(form_frame, text="Clear", width=60, fg_color="gray", command=self.clear_ledger_form).pack(side="left", padx=5)

        filter_frame1 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        filter_frame1.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(filter_frame1, text="Date:").pack(side="left", padx=5)
        self.filter_var = ctk.StringVar(value="All Time")
        ctk.CTkOptionMenu(filter_frame1, values=["All Time", "Current Month"], variable=self.filter_var,
                          command=self.load_ledger_list).pack(side="left", padx=5)
        ctk.CTkLabel(filter_frame1, text="Category:").pack(side="left", padx=5)
        self.filter_cat_var = ctk.StringVar(value="All Categories")
        ctk.CTkOptionMenu(filter_frame1, values=["All Categories", "Boss Investment", "Customer Payment",
                                                 "Expense", "Hand Cash", "Cash to Boss"],
                          variable=self.filter_cat_var, command=self.load_ledger_list).pack(side="left", padx=5)

        filter_frame2 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        filter_frame2.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(filter_frame2, text="Search:").pack(side="left", padx=5)
        self.search_keyword = ctk.CTkEntry(filter_frame2, placeholder_text="Description", width=130)
        self.search_keyword.pack(side="left", padx=5)
        ctk.CTkLabel(filter_frame2, text="Min Rs").pack(side="left", padx=5)
        self.min_amt = ctk.CTkEntry(filter_frame2, placeholder_text="Min", width=80)
        self.min_amt.pack(side="left", padx=5)
        ctk.CTkLabel(filter_frame2, text="Max Rs").pack(side="left", padx=5)
        self.max_amt = ctk.CTkEntry(filter_frame2, placeholder_text="Max", width=80)
        self.max_amt.pack(side="left", padx=5)
        ctk.CTkButton(filter_frame2, text="Search", width=60, command=self.load_ledger_list).pack(side="left", padx=10)
        ctk.CTkButton(filter_frame2, text="Clear", width=60, fg_color="gray", command=self.clear_ledger_search).pack(side="left", padx=5)

        tot_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        tot_frame.pack(pady=5, padx=20, fill="x")
        self.ledger_total_lbl = ctk.CTkLabel(tot_frame, text="Total: Rs 0", font=ctk.CTkFont(size=16, weight="bold"))
        self.ledger_total_lbl.pack(side="left", padx=10)
        ctk.CTkButton(tot_frame, text="📥 PDF", fg_color="#2a5c8a", command=self.export_ledger_pdf).pack(side="right", padx=5)
        ctk.CTkButton(tot_frame, text="📄 CSV", fg_color="#2a5c8a", command=self.export_ledger_csv).pack(side="right", padx=5)
        ctk.CTkButton(tot_frame, text="📤 Send to Boss", fg_color="#25D366", command=self.send_ledger_whatsapp).pack(side="right", padx=5)

        self.ledger_list_frame = ctk.CTkScrollableFrame(self.main_container, width=900, height=350)
        self.ledger_list_frame.pack(pady=10, padx=20, fill="both", expand=True)
        self.load_ledger_list()

    def attach_image(self):
        file_path = filedialog.askopenfilename(title="Select Screenshot/Receipt",
                                               filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if file_path:
            self.attached_image_path = file_path
            self.attach_label.configure(text=os.path.basename(file_path), text_color="lightgreen")
        else:
            self.attached_image_path = None
            self.attach_label.configure(text="No file", text_color="gray")

    def clear_ledger_form(self):
        self.trans_amount.delete(0, 'end')
        self.trans_desc.delete(0, 'end')
        self.attached_image_path = None
        self.attach_label.configure(text="No file", text_color="gray")

    def clear_ledger_search(self):
        self.search_keyword.delete(0, 'end')
        self.min_amt.delete(0, 'end')
        self.max_amt.delete(0, 'end')
        self.load_ledger_list()

    def save_transaction(self):
        date_val = self.trans_date.get()
        category = self.trans_category.get()
        amount = self.trans_amount.get()
        desc = self.trans_desc.get()

        if not amount or not desc:
            messagebox.showerror("Error", "Amount aur Tafseel likhna zaroori hai!")
            return
        try:
            amount_float = float(amount)
        except ValueError:
            messagebox.showerror("Error", "Amount sirf numbers!")
            return

        saved_path = None
        if self.attached_image_path:
            saved_path = database.save_attachment(self.attached_image_path)

        database.insert_transaction(date_val, category, amount_float, desc, saved_path)
        self.clear_ledger_form()
        self.load_ledger_list()

    def load_ledger_list(self, *args):
        for widget in self.ledger_list_frame.winfo_children(): widget.destroy()

        headers = ["Date", "Category", "Amount", "Description", "Proof", "Action"]
        widths = [100, 150, 100, 200, 80, 80]
        for col, (txt, w) in enumerate(zip(headers, widths)):
            ctk.CTkLabel(self.ledger_list_frame, text=txt, font=ctk.CTkFont(weight="bold"), width=w, anchor="w").grid(row=0, column=col, padx=5, pady=5)

        selected_date = self.filter_var.get()
        selected_cat = self.filter_cat_var.get()
        month_filter = date.today().strftime("%Y-%m") if selected_date == "Current Month" else None

        keyword = self.search_keyword.get()
        min_amt = self.min_amt.get()
        max_amt = self.max_amt.get()

        transactions = database.get_all_transactions(month_filter, selected_cat,
                                                     keyword=keyword,
                                                     min_amt=min_amt if min_amt else None,
                                                     max_amt=max_amt if max_amt else None)
        total_income = 0
        total_expense = 0

        for idx, t in enumerate(transactions):
            t_id, date_val, cat, amt, desc, img_path = t
            if cat in ["Expense", "Hand Cash", "Cash to Boss"]:
                color = "red"
                total_expense += amt
            else:
                color = "lightgreen"
                total_income += amt

            ctk.CTkLabel(self.ledger_list_frame, text=date_val, width=100).grid(row=idx+1, column=0, padx=5, pady=3)
            ctk.CTkLabel(self.ledger_list_frame, text=cat, width=150, text_color=color).grid(row=idx+1, column=1, padx=5, pady=3)
            ctk.CTkLabel(self.ledger_list_frame, text=f"Rs {amt}", width=100, text_color=color).grid(row=idx+1, column=2, padx=5, pady=3)
            ctk.CTkLabel(self.ledger_list_frame, text=desc, width=200, anchor="w").grid(row=idx+1, column=3, padx=5, pady=3)

            if img_path and os.path.exists(img_path):
                ctk.CTkButton(self.ledger_list_frame, text="View", width=60, fg_color="#444",
                              command=lambda p=img_path: self.open_image(p)).grid(row=idx+1, column=4, padx=5, pady=3)
            else:
                ctk.CTkLabel(self.ledger_list_frame, text="N/A", width=80).grid(row=idx+1, column=4, padx=5, pady=3)

            ctk.CTkButton(self.ledger_list_frame, text="Del", width=60, fg_color="#B22222",
                          command=lambda tr_id=t_id: self.delete_trans(tr_id)).grid(row=idx+1, column=5, padx=5, pady=3)

        if selected_cat == "All Categories":
            self.ledger_total_lbl.configure(text=f"In: Rs {total_income:,.0f} | Out: Rs {total_expense:,.0f}",
                                            text_color="#FFD700")
        elif selected_cat in ["Expense", "Hand Cash", "Cash to Boss"]:
            self.ledger_total_lbl.configure(text=f"Filtered Total: Rs {total_expense:,.0f}", text_color="#FF6347")
        else:
            self.ledger_total_lbl.configure(text=f"Filtered Total: Rs {total_income:,.0f}", text_color="lightgreen")

    def open_image(self, path):
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", path])
            elif sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open: {e}")

    def delete_trans(self, trans_id):
        if messagebox.askyesno("Confirm", "Delete this entry?"):
            database.delete_transaction(trans_id)
            self.load_ledger_list()

    def send_ledger_whatsapp(self):
        boss_phone = "+920000000000"  # <<< yahan apna real number daalein
        total_in, total_out = database.get_dashboard_summary()
        balance = total_in - total_out
        msg = f"*Daily Closing ({date.today().strftime('%d-%b-%Y')})*\n"
        msg += f"Income: Rs {total_in:,.0f}\n"
        msg += f"Expense: Rs {total_out:,.0f}\n"
        msg += f"Cash Balance: Rs {balance:,.0f}"
        url = f"https://wa.me/{boss_phone}?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)

    def export_ledger_pdf(self):
        selected_date = self.filter_var.get()
        selected_cat = self.filter_cat_var.get()
        month_filter = date.today().strftime("%Y-%m") if selected_date == "Current Month" else None
        transactions = database.get_all_transactions(month_filter, selected_cat,
                                                     keyword=self.search_keyword.get(),
                                                     min_amt=self.min_amt.get() if self.min_amt.get() else None,
                                                     max_amt=self.max_amt.get() if self.max_amt.get() else None)
        if not transactions:
            messagebox.showinfo("Info", "No data.")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                filetypes=[("PDF files", "*.pdf")],
                                                initialfile="Ledger_Report.pdf")
        if not filename: return
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=16, style='B')
            pdf.cell(200, 10, txt="Ledger Report", ln=True, align='C')
            pdf.ln(8)
            pdf.set_font("Helvetica", size=10, style='B')
            pdf.cell(30, 8, "Date", border=1)
            pdf.cell(50, 8, "Category", border=1)
            pdf.cell(30, 8, "Amount", border=1)
            pdf.cell(70, 8, "Description", border=1)
            pdf.ln()
            total_in = 0
            total_out = 0
            pdf.set_font("Helvetica", size=9)
            for t in transactions:
                t_id, date_val, cat, amt, desc, _ = t
                if cat in ["Expense", "Hand Cash", "Cash to Boss"]:
                    total_out += amt
                    color = (220,20,60)
                else:
                    total_in += amt
                    color = (0,100,0)
                pdf.set_text_color(*color)
                pdf.cell(30, 7, date_val, border=1)
                pdf.cell(50, 7, cat[:25], border=1)
                pdf.cell(30, 7, f"Rs {amt}", border=1)
                pdf.cell(70, 7, desc[:40], border=1)
                pdf.ln()
                pdf.set_text_color(0,0,0)
            pdf.ln(5)
            pdf.set_font("Helvetica", size=11, style='B')
            pdf.cell(200, 8, txt=f"Total Income: Rs {total_in:,.0f}", ln=True)
            pdf.cell(200, 8, txt=f"Total Expense: Rs {total_out:,.0f}", ln=True)
            pdf.output(filename)
            messagebox.showinfo("Success", "PDF saved!")
        except Exception as e:
            messagebox.showerror("Error", f"PDF failed: {e}")

    def export_ledger_csv(self):
        selected_date = self.filter_var.get()
        selected_cat = self.filter_cat_var.get()
        month_filter = date.today().strftime("%Y-%m") if selected_date == "Current Month" else None
        transactions = database.get_all_transactions(month_filter, selected_cat,
                                                     keyword=self.search_keyword.get(),
                                                     min_amt=self.min_amt.get() if self.min_amt.get() else None,
                                                     max_amt=self.max_amt.get() if self.max_amt.get() else None)
        if not transactions:
            messagebox.showinfo("Info", "No data.")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv")],
                                                initialfile="Ledger_Report.csv")
        if not filename: return
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Category", "Amount", "Description"])
                for t in transactions:
                    _, date_val, cat, amt, desc, _ = t
                    writer.writerow([date_val, cat, amt, desc])
            messagebox.showinfo("Success", "CSV saved!")
        except Exception as e:
            messagebox.showerror("Error", f"CSV failed: {e}")

if __name__ == "__main__":
    database.create_tables()
    app = LedgerProApp()
    app.mainloop()