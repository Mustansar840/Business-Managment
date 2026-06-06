import sqlite3
from datetime import date, datetime, timedelta
import os
import shutil

DB_NAME = 'hisab_kitab.db'
ATTACHMENTS_DIR = 'attachments'
BACKUP_DIR = 'backups'

if not os.path.exists(ATTACHMENTS_DIR):
    os.makedirs(ATTACHMENTS_DIR)
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            per_day_salary REAL DEFAULT 0, 
            joining_date TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id INTEGER,
            date TEXT,
            status TEXT,
            advance_taken REAL DEFAULT 0,
            is_paid INTEGER DEFAULT 0,
            FOREIGN KEY(emp_id) REFERENCES employees(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            amount REAL,
            description TEXT,
            proof_image_path TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now','localtime')),
            description TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            purchase_price REAL DEFAULT 0,
            sale_price REAL DEFAULT 0,
            current_stock INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            date TEXT,
            type TEXT,
            quantity INTEGER,
            unit_price REAL,
            FOREIGN KEY(item_id) REFERENCES inventory_items(id)
        )
    ''')

    try: cursor.execute("ALTER TABLE attendance ADD COLUMN is_paid INTEGER DEFAULT 0")
    except: pass

    conn.commit()
    conn.close()

# ========= ACTIVITY LOG =========
def log_activity(description):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO activity_log (description) VALUES (?)", (description,))
    conn.commit()
    conn.close()

def get_recent_activities(limit=5):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, description FROM activity_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ========= EMPLOYEE FUNCTIONS =========
def insert_employee(name, phone, per_day_salary):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    cursor.execute('''
        INSERT INTO employees (name, phone, per_day_salary, joining_date)
        VALUES (?, ?, ?, ?)
    ''', (name, phone, per_day_salary, today))
    conn.commit()
    conn.close()
    log_activity(f"New staff '{name}' added.")

def get_all_employees():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone, per_day_salary FROM employees")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_employee_names():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM employees")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def delete_employee(emp_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
    conn.commit()
    conn.close()

# ========= LEDGER FUNCTIONS =========
def save_attachment(source_path):
    if not source_path or not os.path.exists(source_path):
        return None
    filename = os.path.basename(source_path)
    dest_path = os.path.join(ATTACHMENTS_DIR, filename)
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(ATTACHMENTS_DIR, f"{base}_{counter}{ext}")
        counter += 1
    shutil.copy2(source_path, dest_path)
    return dest_path

def insert_transaction(date_val, category, amount, description, proof_image_path=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ledger (date, category, amount, description, proof_image_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (date_val, category, amount, description, proof_image_path))
    conn.commit()
    conn.close()
    log_activity(f"{category}: Rs {amount} - {description}")

def get_all_transactions(month_filter=None, category_filter="All Categories",
                         keyword="", min_amt=None, max_amt=None,
                         date_from=None, date_to=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    query = "SELECT id, date, category, amount, description, proof_image_path FROM ledger WHERE 1=1"
    params = []
    if month_filter:
        query += " AND date LIKE ?"
        params.append(f"{month_filter}%")
    if category_filter != "All Categories":
        query += " AND category = ?"
        params.append(category_filter)
    if keyword:
        query += " AND description LIKE ?"
        params.append(f"%{keyword}%")
    if min_amt is not None:
        query += " AND amount >= ?"
        params.append(float(min_amt))
    if max_amt is not None:
        query += " AND amount <= ?"
        params.append(float(max_amt))
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)
    query += " ORDER BY date DESC, id DESC"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_transaction(trans_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ledger WHERE id=?", (trans_id,))
    conn.commit()
    conn.close()
    log_activity(f"Transaction ID {trans_id} deleted.")

def get_dashboard_summary():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM ledger WHERE category IN ('Boss Investment', 'Customer Payment')")
    total_in = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(amount) FROM ledger WHERE category IN ('Expense', 'Hand Cash', 'Cash to Boss')")
    total_out = cursor.fetchone()[0] or 0.0
    conn.close()
    return total_in, total_out

def get_monthly_summary(year, month):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year+1}-01-01"
    else:
        end = f"{year}-{month+1:02d}-01"
    cursor.execute("SELECT SUM(amount) FROM ledger WHERE category IN ('Boss Investment', 'Customer Payment') AND date >= ? AND date < ?", (start, end))
    income = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(amount) FROM ledger WHERE category IN ('Expense', 'Hand Cash', 'Cash to Boss') AND date >= ? AND date < ?", (start, end))
    expense = cursor.fetchone()[0] or 0.0
    conn.close()
    return income, expense

def get_top_expense_category_this_month():
    today = date.today()
    month = today.strftime("%Y-%m")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT category, SUM(amount) FROM ledger WHERE category IN ('Expense', 'Hand Cash', 'Cash to Boss') AND date LIKE ? GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1", (month+'%',))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    return "None", 0

def get_total_liabilities():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM employees")
    employees = cursor.fetchall()
    total = 0.0
    for (name,) in employees:
        details = get_employee_salary_details(name)
        if details and details['net_payable'] > 0:
            total += details['net_payable']
    conn.close()
    return total

def get_employee_count():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM employees")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_over_advance_employees():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, per_day_salary FROM employees")
    employees = cursor.fetchall()
    over_adv = []
    for name, per_day in employees:
        monthly_est = per_day * 30
        cursor.execute("SELECT SUM(advance_taken) FROM attendance a JOIN employees e ON a.emp_id=e.id WHERE e.name=? AND a.is_paid=0", (name,))
        adv = cursor.fetchone()[0] or 0.0
        if adv > 0.5 * monthly_est:
            over_adv.append((name, adv, monthly_est))
    conn.close()
    return over_adv

def get_missing_attendance_today():
    today = date.today().strftime("%Y-%m-%d")
    return get_unmarked_employees(today)

# ========= ATTENDANCE FUNCTIONS =========
def get_unmarked_employees(date_val):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name FROM employees 
        WHERE id NOT IN (SELECT emp_id FROM attendance WHERE date = ?)
    ''', (date_val,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def insert_attendance(emp_name, date_val, status, advance_taken):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM employees WHERE name=?", (emp_name,))
    result = cursor.fetchone()
    if result:
        emp_id = result[0]
        cursor.execute('''
            INSERT INTO attendance (emp_id, date, status, advance_taken, is_paid)
            VALUES (?, ?, ?, ?, 0)
        ''', (emp_id, date_val, status, advance_taken))
        conn.commit()
    conn.close()
    log_activity(f"Attendance: {emp_name} marked {status} on {date_val} (Advance: Rs {advance_taken})")

def get_attendance_records(filter_name="All", filter_date=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    query = '''
        SELECT a.id, a.date, e.name, a.status, a.advance_taken 
        FROM attendance a JOIN employees e ON a.emp_id = e.id WHERE 1=1
    '''
    params = []
    if filter_name != "All":
        query += " AND e.name = ?"
        params.append(filter_name)
    if filter_date != "":
        query += " AND a.date = ?"
        params.append(filter_date)
    query += " ORDER BY a.date DESC, a.id DESC LIMIT 100"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_attendance(att_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance WHERE id=?", (att_id,))
    conn.commit()
    conn.close()
    log_activity(f"Attendance ID {att_id} deleted.")

# ========= SALARY CALCULATION (Per Day) =========
def get_employee_salary_details(emp_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, per_day_salary FROM employees WHERE name=?", (emp_name,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        return None
    emp_id, per_day = emp
    per_day = round(float(per_day), 2)
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE emp_id=? AND status='Present' AND is_paid=0", (emp_id,))
    presents = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE emp_id=? AND status='Half' AND is_paid=0", (emp_id,))
    half_days = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(advance_taken) FROM attendance WHERE emp_id=? AND is_paid=0", (emp_id,))
    advance = cursor.fetchone()[0] or 0.0
    conn.close()
    earned = (presents + (half_days * 0.5)) * per_day
    net_payable = earned - advance
    return {
        "per_day": per_day,
        "presents": presents,
        "half_days": half_days,
        "earned": round(earned, 2),
        "advance": advance,
        "net_payable": round(net_payable, 2)
    }

def pay_and_clear_salary(emp_name, net_payable):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM employees WHERE name=?", (emp_name,))
    emp_id = cursor.fetchone()[0]
    cursor.execute("UPDATE attendance SET is_paid=1 WHERE emp_id=? AND is_paid=0", (emp_id,))
    today = date.today().strftime("%Y-%m-%d")
    desc = f"Salary Paid to {emp_name} (Cleared)"
    cursor.execute('''
        INSERT INTO ledger (date, category, amount, description)
        VALUES (?, 'Expense', ?, ?)
    ''', (today, net_payable, desc))
    conn.commit()
    conn.close()
    log_activity(f"Salary cleared for {emp_name}: Rs {net_payable}")

def get_payment_history(emp_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, amount FROM ledger 
        WHERE category='Expense' AND description LIKE ?
        ORDER BY date DESC
    ''', (f"Salary Paid to {emp_name} (Cleared)",))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ========= INVENTORY FUNCTIONS =========
def insert_inventory_item(name, purchase_price, sale_price, initial_qty):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO inventory_items (name, purchase_price, sale_price, current_stock)
        VALUES (?, ?, ?, ?)
    ''', (name, purchase_price, sale_price, initial_qty))
    conn.commit()
    conn.close()
    log_activity(f"New item added: {name} (Stock: {initial_qty})")

def get_all_inventory_items():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, purchase_price, sale_price, current_stock FROM inventory_items ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_stock(item_id, quantity, unit_price=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if unit_price is None:
        cursor.execute("SELECT purchase_price FROM inventory_items WHERE id=?", (item_id,))
        unit_price = cursor.fetchone()[0]
    cursor.execute('''
        INSERT INTO inventory_transactions (item_id, date, type, quantity, unit_price)
        VALUES (?, date('now'), 'IN', ?, ?)
    ''', (item_id, quantity, unit_price))
    cursor.execute("UPDATE inventory_items SET current_stock = current_stock + ? WHERE id=?", (quantity, item_id))
    conn.commit()
    conn.close()
    log_activity(f"Stock IN: Item ID {item_id}, Qty {quantity}")

def remove_stock(item_id, quantity, sale_price=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if sale_price is None:
        cursor.execute("SELECT sale_price FROM inventory_items WHERE id=?", (item_id,))
        sale_price = cursor.fetchone()[0]
    cursor.execute('''
        INSERT INTO inventory_transactions (item_id, date, type, quantity, unit_price)
        VALUES (?, date('now'), 'OUT', ?, ?)
    ''', (item_id, quantity, sale_price))
    cursor.execute("UPDATE inventory_items SET current_stock = current_stock - ? WHERE id=?", (quantity, item_id))
    conn.commit()
    conn.close()
    log_activity(f"Stock OUT: Item ID {item_id}, Qty {quantity}")

# ========= CLOUD SYNC (Firebase) =========
def cloud_upload():
    try:
        import pyrebase
    except ImportError:
        return "pyrebase not installed. Run: pip install pyrebase4"
    config_path = "firebase_config.json"
    if not os.path.exists(config_path):
        return "firebase_config.json not found."
    with open(config_path) as f:
        import json
        config = json.load(f)
    firebase = pyrebase.initialize_app(config)
    db = firebase.database()

    employees = get_all_employees()
    db.child("employees").set([{"id": e[0], "name": e[1], "phone": e[2], "per_day_salary": e[3]} for e in employees])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, category, amount, description FROM ledger")
    ledger_rows = cursor.fetchall()
    conn.close()
    db.child("ledger").set([{"id": r[0], "date": r[1], "category": r[2], "amount": r[3], "description": r[4]} for r in ledger_rows])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT a.id, a.date, e.name, a.status, a.advance_taken, a.is_paid FROM attendance a JOIN employees e ON a.emp_id=e.id")
    att_rows = cursor.fetchall()
    conn.close()
    db.child("attendance").set([{"id": r[0], "date": r[1], "employee": r[2], "status": r[3], "advance": r[4], "is_paid": r[5]} for r in att_rows])

    items = get_all_inventory_items()
    db.child("inventory_items").set([{"id": i[0], "name": i[1], "purchase_price": i[2], "sale_price": i[3], "current_stock": i[4]} for i in items])
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, item_id, date, type, quantity, unit_price FROM inventory_transactions")
    inv_trans = cursor.fetchall()
    conn.close()
    db.child("inventory_transactions").set([{"id": t[0], "item_id": t[1], "date": t[2], "type": t[3], "quantity": t[4], "unit_price": t[5]} for t in inv_trans])

    log_activity("Data uploaded to Firebase cloud.")
    return "Upload successful!"

def cloud_download():
    try:
        import pyrebase
    except ImportError:
        return "pyrebase not installed."
    config_path = "firebase_config.json"
    if not os.path.exists(config_path):
        return "firebase_config.json not found."
    with open(config_path) as f:
        import json
        config = json.load(f)
    firebase = pyrebase.initialize_app(config)
    db = firebase.database()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employees")
    cursor.execute("DELETE FROM attendance")
    cursor.execute("DELETE FROM ledger")
    cursor.execute("DELETE FROM inventory_items")
    cursor.execute("DELETE FROM inventory_transactions")
    conn.commit()

    employees_data = db.child("employees").get().val()
    if employees_data:
        for emp in employees_data:
            conn.execute("INSERT INTO employees (id, name, phone, per_day_salary) VALUES (?, ?, ?, ?)",
                         (emp['id'], emp['name'], emp.get('phone',''), emp['per_day_salary']))

    ledger_data = db.child("ledger").get().val()
    if ledger_data:
        for t in ledger_data:
            conn.execute("INSERT INTO ledger (id, date, category, amount, description) VALUES (?, ?, ?, ?, ?)",
                         (t['id'], t['date'], t['category'], t['amount'], t['description']))

    att_data = db.child("attendance").get().val()
    if att_data:
        for a in att_data:
            cursor.execute("SELECT id FROM employees WHERE name=?", (a['employee'],))
            emp_id = cursor.fetchone()
            if emp_id:
                conn.execute("INSERT INTO attendance (id, emp_id, date, status, advance_taken, is_paid) VALUES (?, ?, ?, ?, ?, ?)",
                             (a['id'], emp_id[0], a['date'], a['status'], a['advance'], a['is_paid']))

    inv_items = db.child("inventory_items").get().val()
    if inv_items:
        for i in inv_items:
            conn.execute("INSERT INTO inventory_items (id, name, purchase_price, sale_price, current_stock) VALUES (?, ?, ?, ?, ?)",
                         (i['id'], i['name'], i['purchase_price'], i['sale_price'], i['current_stock']))

    inv_trans = db.child("inventory_transactions").get().val()
    if inv_trans:
        for t in inv_trans:
            conn.execute("INSERT INTO inventory_transactions (id, item_id, date, type, quantity, unit_price) VALUES (?, ?, ?, ?, ?, ?)",
                         (t['id'], t['item_id'], t['date'], t['type'], t['quantity'], t['unit_price']))

    conn.commit()
    conn.close()
    log_activity("Data downloaded from Firebase cloud.")
    return "Download successful!"

# ========= BACKUP / RESTORE =========
def backup_database():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    shutil.copy2(DB_NAME, backup_path)
    log_activity(f"Database backup created: {backup_name}")
    return backup_path

def restore_database(backup_path):
    if not os.path.exists(backup_path):
        return False
    shutil.copy2(backup_path, DB_NAME)
    log_activity(f"Database restored from: {backup_path}")
    return True

if __name__ == '__main__':
    create_tables()
    print("Database ready!")