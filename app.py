from datetime import datetime
from flask import Flask, flash, jsonify, redirect, render_template, render_template_string, request, session, url_for
import os
import re
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = "pezang_fixed_duplicate_endpoint_2026"

# 設定你的 Supabase PostgreSQL 雲端資料庫連線字串 (Session Pooler)
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres.gutyrssxtpuxndflkceq:Erin83390454@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
)

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, password TEXT NOT NULL, role TEXT)")
        
        # 供應商資料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_code TEXT PRIMARY KEY, supplier_name TEXT NOT NULL, tax_id TEXT, 
                contact_info TEXT, phone TEXT, email TEXT, payment_terms TEXT, bank_info TEXT, address TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_code TEXT PRIMARY KEY, customer_name TEXT NOT NULL, tax_id TEXT, 
                contact_info TEXT, payment_terms TEXT, address TEXT
            )
        """)
        
        cursor.execute("CREATE TABLE IF NOT EXISTS warehouses (id SERIAL PRIMARY KEY, warehouse_name TEXT UNIQUE NOT NULL)")
        
        # 庫存項目資料表 (含 spec 規格與 color 顏色)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_items (
                sku TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT, 
                spec TEXT, color TEXT, cost REAL DEFAULT 0, price REAL DEFAULT 0, 
                stock INTEGER DEFAULT 0, safety_stock INTEGER DEFAULT 0, note TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                emp_id TEXT PRIMARY KEY, emp_name TEXT NOT NULL, department TEXT, title TEXT, 
                phone TEXT, hire_date TEXT, base_salary REAL DEFAULT 0, status TEXT DEFAULT '在職', 
                bank_name TEXT, bank_account TEXT, note TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payroll_records (
                id SERIAL PRIMARY KEY, emp_id TEXT, emp_name TEXT, pay_month TEXT,
                base_salary REAL DEFAULT 0, allowance REAL DEFAULT 0, overtime_pay REAL DEFAULT 0,
                leave_deduction REAL DEFAULT 0, emp_purchase_deduction REAL DEFAULT 0,
                insurance_deduction REAL DEFAULT 0, net_salary REAL DEFAULT 0, pay_date TEXT,
                status TEXT DEFAULT '已發放', note TEXT, created_at TEXT
            )
        """)

        # 採購單主檔
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                po_number TEXT PRIMARY KEY, purchaser TEXT, order_date TEXT, delivery_date TEXT,
                vendor_type TEXT, supplier_code TEXT, supplier_name TEXT,
                vendor_contact TEXT, currency TEXT, grand_total REAL, deposit_pct REAL,
                deposit_amount TEXT, balance_pct REAL, balance_amount TEXT,
                shipping_mark TEXT, packing TEXT, bank_info TEXT, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_items (
                id SERIAL PRIMARY KEY, po_number TEXT, model TEXT,
                product_name TEXT, specification TEXT, color TEXT, quantity INTEGER,
                unit_price REAL, subtotal REAL, remarks TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inbound_orders (
                inbound_no TEXT PRIMARY KEY, receiver_name TEXT, warehouse TEXT,
                po_number TEXT, inbound_date TEXT, month TEXT, supplier_code TEXT,
                supplier_name TEXT, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inbound_items (
                id SERIAL PRIMARY KEY, inbound_no TEXT, warehouse TEXT,
                model TEXT, product_name TEXT, specification TEXT, color TEXT,
                ordered_qty INTEGER, actual_qty INTEGER, unit_price REAL, subtotal REAL, remarks TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_orders (
                so_number TEXT PRIMARY KEY, sales_person TEXT, order_date TEXT,
                customer_code TEXT, customer_name TEXT, currency TEXT, grand_total REAL,
                deposit_paid REAL DEFAULT 0, pay_method TEXT DEFAULT '現金', balance_due REAL DEFAULT 0,
                remark TEXT, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_items (
                id SERIAL PRIMARY KEY, so_number TEXT, model TEXT,
                product_name TEXT, specification TEXT, color TEXT, quantity INTEGER,
                unit_price REAL, subtotal REAL, remarks TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_orders (
                do_number TEXT PRIMARY KEY, shipper_name TEXT, warehouse TEXT,
                so_number TEXT, delivery_date TEXT, customer_code TEXT, customer_name TEXT,
                driver TEXT, manual_freight REAL DEFAULT 0, grand_total REAL, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_items (
                id SERIAL PRIMARY KEY, do_number TEXT, warehouse TEXT,
                model TEXT, product_name TEXT, specification TEXT, color TEXT,
                shipped_qty INTEGER, unit_price REAL, subtotal REAL, remarks TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_no TEXT PRIMARY KEY, invoice_date TEXT, invoice_type TEXT,
                party_type TEXT DEFAULT '銷貨發票', entity_name TEXT, tax_id TEXT, sales_amount REAL, tax_amount REAL,
                total_amount REAL, status TEXT DEFAULT '正常', note TEXT, created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credit_card_txns (
                txn_id SERIAL PRIMARY KEY, order_id TEXT, customer_name TEXT,
                txn_type TEXT DEFAULT '刷卡收入', amount REAL, auth_code TEXT, card_last4 TEXT,
                txn_date TEXT, note TEXT, created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ap_invoices (
                inbound_no TEXT PRIMARY KEY, inbound_date TEXT, vendor_display TEXT,
                total_amount REAL, payment_term TEXT, due_date TEXT, status TEXT DEFAULT '未付'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ap_payments (
                pay_no TEXT PRIMARY KEY, pay_date TEXT, inbound_no TEXT,
                vendor_name TEXT, pay_amount REAL, pay_method TEXT, remarks TEXT, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ar_invoices (
                do_number TEXT PRIMARY KEY, delivery_date TEXT, customer_display TEXT,
                total_amount REAL, payment_term TEXT, due_date TEXT, status TEXT DEFAULT '未收'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ar_records (
                id SERIAL PRIMARY KEY,
                order_id TEXT, customer TEXT, sales_amount REAL, deposit REAL,
                receive_amount REAL, pay_type TEXT, check_no TEXT, check_due_date TEXT,
                receive_date TEXT, unpaid_amount REAL, driver TEXT, driver_area TEXT,
                freight REAL, old_item_fee REAL, keyin_user TEXT, note TEXT, created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id SERIAL PRIMARY KEY, trans_date TEXT, trans_type TEXT,
                order_id TEXT, customer_code TEXT, customer_name TEXT, sku TEXT,
                qty INTEGER, price REAL, total_amount REAL, cogs REAL,
                keyin_user TEXT, status TEXT, note TEXT, created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_performance (
                id SERIAL PRIMARY KEY,
                sales_person TEXT, order_id TEXT, order_date TEXT,
                customer_name TEXT, sales_amount REAL, expense_coefficient REAL DEFAULT 0.15,
                net_performance REAL, commission_rate REAL DEFAULT 0.05,
                commission_amount REAL, status TEXT DEFAULT '已結算',
                note TEXT, created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vouchers (
                voucher_no TEXT PRIMARY KEY, voucher_date TEXT, voucher_type TEXT,
                summary TEXT, preparer TEXT, total_amount REAL, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voucher_items (
                id SERIAL PRIMARY KEY, voucher_no TEXT,
                account_code TEXT, account_name TEXT, debit REAL DEFAULT 0, credit REAL DEFAULT 0
            )
        """)

        default_users = [
            ("EMP01", "黃詠甯", "0320", "會計主管"),
            ("EMP02", "江婉秀", "0510", "門市經辦"),
            ("admin", "系統管理員", "pezang888", "系統管理")
        ]
        for u in default_users:
            cursor.execute("""
                INSERT INTO users (id, name, password, role) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (id) DO UPDATE 
                SET password = EXCLUDED.password, name = EXCLUDED.name, role = EXCLUDED.role
            """, u)

        cursor.execute("SELECT COUNT(*) FROM warehouses")
        if cursor.fetchone()["count"] == 0:
            cursor.executemany("INSERT INTO warehouses (warehouse_name) VALUES (%s)",
                [("八里倉",), ("南倉",), ("土城門市倉",), ("外倉",)])

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Init DB Error: {e}")

init_db()

# ==================== 路由與 API ====================

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    is_accountant = session["user_id"] in ["EMP01", "EMP02", "admin"]
    return render_template("index.html", user_name=session["user_name"], user_id=session["user_id"], is_accountant=is_accountant)

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        uid, pwd = data.get("username") or data.get("user_id"), data.get("password")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s AND password = %s", (uid, pwd))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            session["user_id"], session["user_name"], session["user_role"] = user["id"], user["name"], user["role"]
            return jsonify({"success": True, "user": {"username": user["id"], "name": user["name"], "role": user["role"]}}) if request.is_json else redirect(url_for("index"))
        return jsonify({"success": False, "message": "❌ 帳號或密碼錯誤"}) if request.is_json else "登入失敗"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/api/warehouses")
def get_warehouses():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT warehouse_name FROM warehouses")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([r["warehouse_name"] for r in rows])

@app.route("/api/vendor/")
def get_vendor(v_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT supplier_name FROM suppliers WHERE supplier_code = %s", (v_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify({"found": True, "vendor_name": row["supplier_name"]} if row else {"found": False})

@app.route("/api/customer/")
def get_customer(c_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_name FROM customers WHERE customer_code = %s", (c_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify({"found": True, "customer_name": row["customer_name"]} if row else {"found": False})

# --- 客戶建立 CRUD API ---
@app.route("/api/customers/list")
def api_get_customers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers ORDER BY customer_code")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/customers/save", methods=["POST"])
def api_save_customer():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customers (customer_code, customer_name, tax_id, contact_info, payment_terms, address)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (customer_code) DO UPDATE 
            SET customer_name = EXCLUDED.customer_name, tax_id = EXCLUDED.tax_id, 
                contact_info = EXCLUDED.contact_info, payment_terms = EXCLUDED.payment_terms, address = EXCLUDED.address
        """, (data.get("customer_code"), data.get("customer_name"), data.get("tax_id"),
              data.get("contact_info"), data.get("payment_terms"), data.get("address")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 客戶資料存檔/修改成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/customers/delete/", methods=["POST"])
def api_delete_customer(c_code):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE customer_code = %s", (c_code,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 客戶刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

# --- 員工與薪資 CRUD API ---
@app.route("/api/employees/list")
def get_employees():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees ORDER BY emp_id")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/employees/save", methods=["POST"])
def save_employee():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO employees (emp_id, emp_name, department, title, phone, hire_date, base_salary, status, bank_name, bank_account, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (emp_id) DO UPDATE 
            SET emp_name = EXCLUDED.emp_name, department = EXCLUDED.department, title = EXCLUDED.title,
                phone = EXCLUDED.phone, hire_date = EXCLUDED.hire_date, base_salary = EXCLUDED.base_salary,
                status = EXCLUDED.status, bank_name = EXCLUDED.bank_name, bank_account = EXCLUDED.bank_account, note = EXCLUDED.note
        """, (data.get("emp_id"), data.get("emp_name"), data.get("department"), data.get("title"),
              data.get("phone"), data.get("hire_date"), data.get("base_salary"), data.get("status"), 
              data.get("bank_name"), data.get("bank_account"), data.get("note")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 員工資料存檔/修改成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/employees/delete/", methods=["POST"])
def delete_employee(emp_id):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM employees WHERE emp_id = %s", (emp_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 員工刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/payroll/list")
def get_payroll():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payroll_records ORDER BY pay_month DESC, emp_id ASC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/payroll/save", methods=["POST"])
def save_payroll():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        base = float(data.get("base_salary", 0))
        allow = float(data.get("allowance", 0))
        ot = float(data.get("overtime_pay", 0))
        leave_ded = float(data.get("leave_deduction", 0))
        pur_ded = float(data.get("emp_purchase_deduction", 0))
        ins_ded = float(data.get("insurance_deduction", 0))
        net = base + allow + ot - leave_ded - pur_ded - ins_ded
        p_id = data.get("payroll_id")
        if p_id:
            cursor.execute("""
                UPDATE payroll_records SET base_salary=%s, allowance=%s, overtime_pay=%s, leave_deduction=%s, 
                emp_purchase_deduction=%s, insurance_deduction=%s, net_salary=%s, pay_date=%s, status=%s, note=%s WHERE id=%s
            """, (base, allow, ot, leave_ded, pur_ded, ins_ded, net, data.get("pay_date"), data.get("status", "已發放"), data.get("note"), p_id))
        else:
            cursor.execute("""
                INSERT INTO payroll_records (emp_id, emp_name, pay_month, base_salary, allowance, overtime_pay, leave_deduction, emp_purchase_deduction, insurance_deduction, net_salary, pay_date, status, note, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (data.get("emp_id"), data.get("emp_name"), data.get("pay_month"), base, allow, ot, leave_ded, pur_ded, ins_ded, net,
                  data.get("pay_date"), data.get("status", "已發放"), data.get("note"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"✔ 薪資紀錄存檔成功！實發金額: ${net:,.2f}"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/payroll/delete/", methods=["POST"])
def delete_payroll(pay_id):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM payroll_records WHERE id = %s", (pay_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 薪資紀錄刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

# --- 採購與進貨 API ---
@app.route("/api/po/save", methods=["POST"])
def save_po():
    if "user_id" not in session: return jsonify({"status": "error", "message": "請先登入"})
    data = request.get_json()
    po_no = data.get("po_no")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM purchase_orders WHERE po_number = %s", (po_no,))
        cursor.execute("DELETE FROM purchase_items WHERE po_number = %s", (po_no,))
        
        grand_total = float(data.get("grand_total") or 0)
        dep_pct = float(data.get("dep_pct") or 0)
        bal_pct = float(data.get("bal_pct") or 100)

        def extract_number(val):
            if not val: return 0.0
            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", str(val))
            return float(numbers[0]) if numbers else 0.0

        dep_amount = extract_number(data.get("dep_amt"))
        bal_amount = extract_number(data.get("bal_amt"))

        cursor.execute("""
            INSERT INTO purchase_orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (po_no, data.get("buyer_name"), data.get("order_date"), data.get("delivery_date"),
              data.get("vendor_type"), data.get("vendor_id"), data.get("vendor_name"),
              data.get("vendor_contact"), data.get("currency"), grand_total, dep_pct,
              str(dep_amount), bal_pct, str(bal_amount),
              data.get("shipping_mark"), data.get("packing"), data.get("bank_info"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        for item in data.get("items", []):
            qty = int(item.get("qty") or 0)
            unit_price = float(item.get("unit_price") or 0)
            subtotal = qty * unit_price
            cursor.execute("""
                INSERT INTO purchase_items (po_number, model, product_name, specification, color, quantity, unit_price, subtotal, remarks) 
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (po_no, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                  qty, unit_price, subtotal, item.get("remarks")))
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: 
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/po/")
def get_po(po_no):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM purchase_orders WHERE po_number = %s", (po_no,))
    po = cursor.fetchone()
    if not po:
        cursor.close()
        conn.close()
        return jsonify({"found": False, "message": "找不到採購單"})
    cursor.execute("SELECT model, product_name as name, specification as size, color, quantity as qty, unit_price, subtotal as total, remarks FROM purchase_items WHERE po_number = %s", (po_no,))
    items = [dict(r) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify({"found": True, "header": dict(po), "items": items})
@app.route("/api/inbound/save", methods=["POST"])
def save_inbound():
    if "user_id" not in session: return jsonify({"status": "error", "message": "請先登入"})
    data = request.get_json()
    in_no = data.get("inbound_no")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inbound_orders WHERE inbound_no = %s", (in_no,))
        cursor.execute("DELETE FROM inbound_items WHERE inbound_no = %s", (in_no,))
        
        v_id = data.get("vendor_id", "") or ""
        v_name = data.get("vendor_name", "") or "未命名供應商"
        
        cursor.execute("INSERT INTO inbound_orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (in_no, data.get("receiver_name"), data.get("warehouse", "八里倉"), data.get("po_no"),
             data.get("inbound_date"), data.get("month"), v_id, v_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        total_amt = 0
        for item in data.get("items", []):
            actual_qty = float(item.get("actual_qty") or 0)
            unit_price = float(item.get("unit_price") or 0)
            sub = actual_qty * unit_price
            total_amt += sub
            wh = item.get("warehouse", "八里倉")
            
            cursor.execute("""
                INSERT INTO inbound_items (inbound_no, warehouse, model, product_name, specification, color, ordered_qty, actual_qty, unit_price, subtotal, remarks) 
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (in_no, wh, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                  item.get("ordered_qty"), actual_qty, unit_price, sub, item.get("remarks")))
            
            sku = item.get("model")
            cursor.execute("""
                INSERT INTO inventory_items (sku, name, category, spec, color, cost, price, stock, safety_stock, note)
                VALUES (%s, %s, '五金配件', %s, %s, %s, %s, %s, 10, '進貨入庫')
                ON CONFLICT (sku) DO UPDATE SET stock = inventory_items.stock + EXCLUDED.stock, spec = EXCLUDED.spec, color = EXCLUDED.color
            """, (sku, item.get("name"), item.get("size"), item.get("color"), unit_price, unit_price * 1.5, actual_qty))

        v_display = f"{v_id} {v_name}".strip() if v_id else v_name
        inbound_date = data.get("inbound_date")
        cursor.execute("""
            INSERT INTO ap_invoices (inbound_no, inbound_date, vendor_display, total_amount, payment_term, due_date, status) 
            VALUES (%s, %s, %s, %s, '月結30天', %s, '未付')
            ON CONFLICT (inbound_no) DO UPDATE 
            SET inbound_date = EXCLUDED.inbound_date, vendor_display = EXCLUDED.vendor_display, total_amount = EXCLUDED.total_amount, due_date = EXCLUDED.due_date
        """, (in_no, inbound_date, v_display, total_amt, inbound_date))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: 
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/inbound/<string:in_no>")
def get_inbound(in_no):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inbound_orders WHERE inbound_no = %s", (in_no,))
    order = cursor.fetchone()
    if not order:
        cursor.close()
        conn.close()
        return jsonify({"found": False, "message": "找不到進貨單"})
    cursor.execute("SELECT warehouse, model, product_name as name, specification as size, color, ordered_qty, actual_qty, unit_price, subtotal as total, remarks FROM inbound_items WHERE inbound_no = %s", (in_no,))
    items = [dict(r) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify({"found": True, "header": dict(order), "items": items})

@app.route("/api/so/save", methods=["POST"])
def save_so():
    if "user_id" not in session: return jsonify({"status": "error", "message": "請先登入"})
    data = request.get_json()
    so_no = data.get("so_no")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sales_orders WHERE so_number = %s", (so_no,))
        cursor.execute("DELETE FROM sales_items WHERE so_number = %s", (so_no,))
        
        grand_total = float(data.get("grand_total") or 0)
        deposit_paid = float(data.get("deposit_paid") or 0)
        balance_due = max(0, grand_total - deposit_paid)

        cursor.execute("""
            INSERT INTO sales_orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (so_no, data.get("sales_person"), data.get("order_date"), data.get("customer_code"),
              data.get("customer_name"), data.get("currency"), grand_total, deposit_paid,
              data.get("pay_method", "現金"), balance_due, data.get("remark"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        for item in data.get("items", []):
            qty = int(item.get("qty") or 0)
            unit_price = float(item.get("unit_price") or 0)
            subtotal = qty * unit_price
            cursor.execute("""
                INSERT INTO sales_items (so_number, model, product_name, specification, color, quantity, unit_price, subtotal, remarks) 
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (so_no, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                  qty, unit_price, subtotal, item.get("remarks")))
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/so/")
def get_so(so_no):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales_orders WHERE so_number = %s", (so_no,))
    so = cursor.fetchone()
    if not so:
        cursor.close()
        conn.close()
        return jsonify({"found": False, "message": "找不到客戶訂單"})
    cursor.execute("SELECT model, product_name as name, specification as size, color, quantity as qty, unit_price, subtotal as total, remarks FROM sales_items WHERE so_number = %s", (so_no,))
    items = [dict(r) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify({"found": True, "header": dict(so), "items": items})

@app.route("/api/delivery/save", methods=["POST"])
def save_delivery():
    if "user_id" not in session: return jsonify({"status": "error", "message": "請先登入"})
    data = request.get_json()
    do_no = data.get("do_number")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM delivery_orders WHERE do_number = %s", (do_no,))
        cursor.execute("DELETE FROM delivery_items WHERE do_number = %s", (do_no,))
        c_id = data.get("customer_code", "") or ""
        c_name = data.get("customer_name", "") or "未命名客戶"
        driver = data.get("driver", "大蔡")
        manual_freight = float(data.get("manual_freight", 0))

        cursor.execute("INSERT INTO delivery_orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (do_no, data.get("shipper_name"), data.get("warehouse", "八里倉"), data.get("so_no"),
             data.get("delivery_date"), c_id, c_name, driver, manual_freight, data.get("grand_total", 0), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        total_amt = 0
        for item in data.get("items", []):
            sub = item.get("shipped_qty", 0) * item.get("unit_price", 0)
            total_amt += sub
            wh = item.get("warehouse", "八里倉")
            cursor.execute("""
                INSERT INTO delivery_items (do_number, warehouse, model, product_name, specification, color, shipped_qty, unit_price, subtotal, remarks) 
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (do_no, wh, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                  item.get("shipped_qty"), item.get("unit_price"), sub, item.get("remarks")))
            sku = item.get("model")
            cursor.execute("UPDATE inventory_items SET stock = stock - %s WHERE sku = %s", (item.get("shipped_qty"), sku))
        c_display = f"{c_id} {c_name}".strip() if c_id else c_name
        cursor.execute("""
            INSERT INTO ar_invoices (do_number, delivery_date, customer_display, total_amount, payment_term, due_date, status) 
            VALUES (%s, %s, %s, %s, '月結30天', %s, '未收')
            ON CONFLICT (do_number) DO UPDATE 
            SET delivery_date = EXCLUDED.delivery_date, customer_display = EXCLUDED.customer_display, total_amount = EXCLUDED.total_amount, due_date = EXCLUDED.due_date
        """, (do_no, data.get("delivery_date"), c_display, total_amt, data.get("delivery_date")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route("/api/delivery/")
def get_delivery(do_no):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM delivery_orders WHERE do_number = %s", (do_no,))
    dOrder = cursor.fetchone()
    if not dOrder:
        cursor.close()
        conn.close()
        return jsonify({"found": False, "message": "找不到銷貨出貨單"})
    cursor.execute("SELECT warehouse, model, product_name as name, specification as size, color, shipped_qty, unit_price, subtotal as total, remarks FROM delivery_items WHERE do_number = %s", (do_no,))
    items = [dict(r) for r in cursor.fetchall()]
    res_data = dict(dOrder)
    cursor.close()
    conn.close()
    return jsonify({"found": True, "header": res_data, "items": items})

@app.route("/api/inventory/list")
def get_inventory():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT sku, name, category, spec, color, cost, price, stock, safety_stock, note FROM inventory_items ORDER BY sku")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/inventory/save", methods=["POST"])
def save_inventory():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventory_items (sku, name, category, spec, color, cost, price, stock, safety_stock, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (sku) DO UPDATE SET 
                name = EXCLUDED.name, category = EXCLUDED.category, spec = EXCLUDED.spec, color = EXCLUDED.color,
                cost = EXCLUDED.cost, price = EXCLUDED.price, stock = EXCLUDED.stock, safety_stock = EXCLUDED.safety_stock, note = EXCLUDED.note
        """, (data.get("sku"), data.get("name"), data.get("category"), data.get("spec"), data.get("color"),
              data.get("cost"), data.get("price"), data.get("stock"), data.get("safety_stock"), data.get("note")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 庫存規格資料存檔成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/inventory/delete/", methods=["POST"])
def delete_inventory(sku):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory_items WHERE sku = %s", (sku,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/inventory/transaction/save", methods=["POST"])
def save_inventory_transaction():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ttype = data.get("transType")
        sku = data.get("transSku")
        qty = int(data.get("transQty", 0))
        price = float(data.get("transPrice", 0))
        cursor.execute("SELECT * FROM inventory_items WHERE sku = %s", (sku,))
        item = cursor.fetchone()
        if not item: 
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "找不到商品"})
        cost = item["cost"]
        current_stock = item["stock"]
        if ttype == "進貨":
            cursor.execute("UPDATE inventory_items SET stock = stock + %s WHERE sku = %s", (qty, sku))
            cogs = 0
        elif ttype == "進貨退回":
            cursor.execute("UPDATE inventory_items SET stock = GREATEST(0, stock - %s) WHERE sku = %s", (qty, sku))
            cogs = 0
        elif ttype == "銷貨":
            if current_stock < qty: 
                cursor.close()
                conn.close()
                return jsonify({"success": False, "message": f"庫存不足，剩餘 {current_stock} 件"})
            cursor.execute("UPDATE inventory_items SET stock = stock - %s WHERE sku = %s", (qty, sku))
            cogs = qty * cost
        elif ttype == "銷貨退回":
            cursor.execute("UPDATE inventory_items SET stock = stock + %s WHERE sku = %s", (qty, sku))
            cogs = -(qty * cost)
        else:
            cogs = 0
        total_amt = qty * price
        cursor.execute("""
            INSERT INTO inventory_transactions (trans_date, trans_type, order_id, customer_code, customer_name, sku, qty, price, total_amount, cogs, keyin_user, status, note, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '已入帳', %s, %s)
        """, (data.get("transDate"), ttype, data.get("orderId"), data.get("customerCode"), data.get("customerName"),
              sku, qty, price, total_amt, cogs, data.get("keyinUser"), data.get("transNote"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"【{ttype}】單據登錄成功！結轉 COGS: ${cogs:,.0f}"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/sales/performance")
def get_sales_performance():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales_performance ORDER BY order_date DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/sales/performance/save", methods=["POST"])
def save_sales_performance():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sp_id = data.get("perf_id")
        sales_amt = float(data.get("sales_amount", 0))
        expense_coef = float(data.get("expense_coefficient", 0.15))
        rate = float(data.get("commission_rate", 0.05))
        
        net_perf = sales_amt * (1 - expense_coef)
        comm_amt = net_perf * rate

        if sp_id:
            cursor.execute("""
                UPDATE sales_performance SET sales_person=%s, order_id=%s, order_date=%s, customer_name=%s, 
                sales_amount=%s, expense_coefficient=%s, net_performance=%s, commission_rate=%s, commission_amount=%s, status=%s, note=%s WHERE id=%s
            """, (data.get("sales_person"), data.get("order_id"), data.get("order_date"), data.get("customer_name"),
                  sales_amt, expense_coef, net_perf, rate, comm_amt, data.get("status", "已結算"), data.get("note"), sp_id))
        else:
            cursor.execute("""
                INSERT INTO sales_performance (sales_person, order_id, order_date, customer_name, sales_amount, expense_coefficient, net_performance, commission_rate, commission_amount, status, note, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (data.get("sales_person"), data.get("order_id"), data.get("order_date"), data.get("customer_name"),
                  sales_amt, expense_coef, net_perf, rate, comm_amt, data.get("status", "已結算"), data.get("note"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"✔ 業務業績與管銷係數計算成功！淨業績: ${net_perf:,.2f}"})
        
    except Exception as e: 
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/sales/performance/delete/<int:sp_id>", methods=["POST"])
def delete_sales_performance(sp_id):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sales_performance WHERE id = %s", (sp_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 業績紀錄刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/vouchers/list")
def get_vouchers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vouchers ORDER BY voucher_date DESC")
    vouchers = cursor.fetchall()
    result = []
    for v in vouchers:
        cursor.execute("SELECT * FROM voucher_items WHERE voucher_no = %s", (v["voucher_no"],))
        items = cursor.fetchall()
        result.append({**dict(v), "items": [dict(i) for i in items]})
    cursor.close()
    conn.close()
    return jsonify(result)

@app.route("/api/vouchers/save", methods=["POST"])
def save_voucher():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        v_no = data.get("voucher_no")
        items = data.get("items", [])
        total_dr = sum(float(i.get("debit", 0)) for i in items)
        total_cr = sum(float(i.get("credit", 0)) for i in items)
        if abs(total_dr - total_cr) > 0.01:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": f"❌ 借貸不平衡！借方總計 (({total_dr:,.2f}) 與貸方總計 (){total_cr:,.2f}) 不符。"})
        
        cursor.execute("DELETE FROM vouchers WHERE voucher_no = %s", (v_no,))
        cursor.execute("DELETE FROM voucher_items WHERE voucher_no = %s", (v_no,))
        cursor.execute("INSERT INTO vouchers VALUES (%s, %s, %s, %s, %s, %s, %s)",
                       (v_no, data.get("voucher_date"), data.get("voucher_type"), data.get("summary"),
                        data.get("preparer"), total_dr, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        for it in items:
            cursor.execute("INSERT INTO voucher_items (voucher_no, account_code, account_name, debit, credit) VALUES (%s, %s, %s, %s, %s)",
                           (v_no, it.get("account_code"), it.get("account_name"), float(it.get("debit", 0)), float(it.get("credit", 0))))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 會計傳票存檔成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/vouchers/delete/<string:v_no>", methods=["POST"])
def delete_voucher(v_no):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vouchers WHERE voucher_no = %s", (v_no,))
        cursor.execute("DELETE FROM voucher_items WHERE voucher_no = %s", (v_no,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 傳票刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/finance/reports")
def get_finance_reports():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT account_code, account_name, SUM(debit) as dr, SUM(credit) as cr FROM voucher_items GROUP BY account_code")
    v_items = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"trial_balance": [dict(r) for r in v_items]})

@app.route("/api/creditcard/list")
def get_creditcard_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credit_card_txns ORDER BY txn_date DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/creditcard/save", methods=["POST"])
def save_creditcard_txn():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO credit_card_txns (order_id, customer_name, txn_type, amount, auth_code, card_last4, txn_date, note, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (data.get("order_id"), data.get("customer_name"), data.get("txn_type", "刷卡收入"),
              data.get("amount", 0), data.get("auth_code"), data.get("card_last4"),
              data.get("txn_date"), data.get("note"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 信用卡交易紀錄儲存成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/creditcard/delete/<int:txn_id>", methods=["POST"])
def delete_creditcard_txn(txn_id):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM credit_card_txns WHERE txn_id = %s", (txn_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/invoices/list")
def get_invoices_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices ORDER BY invoice_date DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/invoices/save", methods=["POST"])
def save_invoice():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO invoices (invoice_no, invoice_date, invoice_type, party_type, entity_name, tax_id, sales_amount, tax_amount, total_amount, status, note, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (invoice_no) DO UPDATE SET
                invoice_date = EXCLUDED.invoice_date, invoice_type = EXCLUDED.invoice_type, party_type = EXCLUDED.party_type,
                entity_name = EXCLUDED.entity_name, tax_id = EXCLUDED.tax_id, sales_amount = EXCLUDED.sales_amount,
                tax_amount = EXCLUDED.tax_amount, total_amount = EXCLUDED.total_amount, status = EXCLUDED.status, note = EXCLUDED.note
        """, (data.get("invoice_no"), data.get("invoice_date"), data.get("invoice_type"), data.get("party_type"),
              data.get("customer_name"), data.get("tax_id"), data.get("sales_amount", 0), data.get("tax_amount", 0),
              (data.get("sales_amount", 0) + data.get("tax_amount", 0)), data.get("status", "正常"), data.get("note"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 發票資料儲存成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/invoices/delete/<string:inv_no>", methods=["POST"])
def delete_invoice(inv_no):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoices WHERE invoice_no = %s", (inv_no,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 發票刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/ar/search/<string:order_id>")
def search_ar_record(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ar_records WHERE order_id = %s ORDER BY id ASC", (order_id.upper(),))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if not rows: return jsonify({"success": False, "message": "查無此訂單收款紀錄"})
    history = []
    total_col = 0
    base = dict(rows[0])
    for r in rows:
        amt = r["receive_amount"]
        total_col += amt
        history.append({
            "rowIndex": r["id"], "date": r["receive_date"], "payType": r["pay_type"],
            "amount": amt, "checkNo": r["check_no"], "checkDueDate": r["check_due_date"],
            "driver": r["driver"], "driverArea": r["driver_area"], "freight": r["freight"],
            "oldItemFee": r["old_item_fee"], "user": r["keyin_user"], "note": r["note"]
        })
    current_unpaid = max(0, base["sales_amount"] - base["deposit"] - total_col)
    return jsonify({
        "success": True,
        "data": {
            "orderId": base["order_id"], "customer": base["customer"],
            "salesAmount": base["sales_amount"], "deposit": base["deposit"],
            "totalCollected": total_col, "currentUnpaid": current_unpaid,
            "discrepancyStatus": "相符" if current_unpaid == 0 else "短收 (欠款)",
            "balanceNote": "✨ 此訂單已結清" if current_unpaid == 0 else f"🚨 尚欠 ${current_unpaid:,.0f}",
            "driver": base["driver"], "driverArea": base["driver_area"],
            "freight": base["freight"], "oldItemFee": base["old_item_fee"],
            "historyRecords": history
        }
    })

@app.route("/api/ar/save", methods=["POST"])
def save_ar_record():
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        is_edit = data.get("isEditSpecificRow")
        target_id = data.get("targetRowIndex")
        if is_edit and target_id:
            cursor.execute("""
                UPDATE ar_records SET receive_amount=%s, pay_type=%s, check_no=%s, check_due_date=%s, receive_date=%s, unpaid_amount=%s, driver=%s, driver_area=%s, freight=%s, old_item_fee=%s, note=%s WHERE id=%s
            """, (data.get("receiveAmount"), data.get("payType"), data.get("checkNo"), data.get("checkDueDate"),
                  data.get("receiveDate"), data.get("unpaidAmount"), data.get("driver"), data.get("driverArea"),
                  data.get("freight"), data.get("oldItemFee"), data.get("note"), target_id))
        else:
            cursor.execute("""
                INSERT INTO ar_records (order_id, customer, sales_amount, deposit, receive_amount, pay_type, check_no, check_due_date, receive_date, unpaid_amount, driver, driver_area, freight, old_item_fee, keyin_user, note, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (data.get("orderId"), data.get("customer"), data.get("salesAmount"), data.get("deposit"),
                  data.get("receiveAmount"), data.get("payType"), data.get("checkNo"), data.get("checkDueDate"),
                  data.get("receiveDate"), data.get("unpaidAmount"), data.get("driver"), data.get("driverArea"),
                  data.get("freight"), data.get("oldItemFee"), data.get("keyinUser"), data.get("note"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "🎉 收款紀錄儲存成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/print/data")
def get_print_data():
    start = request.args.get("startDate", "")
    end = request.args.get("endDate", "")
    driver = request.args.get("driver", "ALL")
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM ar_records WHERE receive_date BETWEEN %s AND %s"
    params = [start, end]
    if driver != "ALL":
        query += " AND driver = %s"
        params.append(driver)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    lst = []
    for r in rows:
        lst.append({
            "id": r["order_id"], "customer": r["customer"], "sales": r["sales_amount"],
            "deposit": r["deposit"], "received": r["receive_amount"], "payType": r["pay_type"],
            "checkNo": r["check_no"], "checkDueDate": r["check_due_date"], "date": r["receive_date"],
            "unpaid": r["unpaid_amount"], "driver": r["driver"], "driverArea": r["driver_area"],
            "freight": r["freight"], "oldFee": r["old_item_fee"], "user": r["keyin_user"], "note": r["note"]
        })
    return jsonify({"type": "AR", "list": lst})

@app.route("/api/ap/summary")
def get_ap_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ap_invoices")
    invoices = cursor.fetchall()
    data = []
    for inv in invoices:
        cursor.execute("SELECT SUM(pay_amount) as t FROM ap_payments WHERE inbound_no = %s", (inv["inbound_no"],))
        p_res = cursor.fetchone()
        paid = p_res["t"] if p_res and p_res["t"] else 0
        unpaid = inv["total_amount"] - paid
        status = "已結清" if unpaid <= 0 else ("部分付款" if paid > 0 else "未付")
        data.append({**dict(inv), "paid_amount": paid, "unpaid_amount": unpaid, "status": status})
    cursor.close()
    conn.close()
    return jsonify({"found": True, "data": data})

@app.route("/api/ap/pay", methods=["POST"])
def save_payment():
    data = request.get_json()
    pay_no = "PAY" + datetime.now().strftime("%Y%m%d%H%M%S")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ap_payments VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (pay_no, data.get("pay_date"), data.get("inbound_no"), data.get("vendor_name"),
             data.get("pay_amount"), data.get("pay_method"), data.get("remarks"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route("/api/ap/search/<string:inbound_no>")
def search_ap_record(inbound_no):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ap_invoices WHERE inbound_no = %s", (inbound_no.upper(),))
    inv = cursor.fetchone()
    if not inv:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "查無此進貨單號的應付帳款紀錄"})
    
    cursor.execute("SELECT * FROM ap_payments WHERE inbound_no = %s ORDER BY pay_date ASC", (inbound_no.upper(),))
    payments = cursor.fetchall()
    total_paid = sum(p["pay_amount"] for p in payments)
    unpaid = max(0, inv["total_amount"] - total_paid)
    
    history = []
    for p in payments:
        history.append({
            "payNo": p["pay_no"], "payDate": p["pay_date"], "vendorName": p["vendor_name"],
            "payAmount": p["pay_amount"], "payMethod": p["pay_method"], "remarks": p["remarks"]
        })
    cursor.close()
    conn.close()
    return jsonify({
        "success": True,
        "data": {
            "inboundNo": inv["inbound_no"], "inboundDate": inv["inbound_date"],
            "vendorDisplay": inv["vendor_display"], "totalAmount": inv["total_amount"],
            "totalPaid": total_paid, "currentUnpaid": unpaid,
            "status": "已結清" if unpaid <= 0 else ("部分付款" if total_paid > 0 else "未付"),
            "historyRecords": history
        }
    })

@app.route("/api/ar/summary")
def get_ar_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ar_invoices")
    invoices = cursor.fetchall()
    data = []
    for inv in invoices:
        cursor.execute("SELECT SUM(receive_amount) as t FROM ar_records WHERE order_id = %s", (inv["do_number"],))
        ar_res = cursor.fetchone()
        collected = ar_res["t"] if ar_res and ar_res["t"] else 0
        uncollected = inv["total_amount"] - collected
        status = "已收清" if uncollected <= 0 else ("部分收款" if collected > 0 else "未收")
        data.append({
            "do_number": inv["do_number"], "delivery_date": inv["delivery_date"], "customer_display": inv["customer_display"],
            "total_amount": inv["total_amount"], "payment_term": inv["payment_term"], "due_date": inv["due_date"],
            "collected_amount": collected, "uncollected_amount": uncollected, "status": status
        })
    cursor.close()
    conn.close()
    return jsonify({"found": True, "data": data})

@app.route("/api/finance/summary")
def get_finance_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total_amount) FROM ap_invoices")
    total_ap = cursor.fetchone()["sum"] or 0
    cursor.execute("SELECT SUM(pay_amount) FROM ap_payments")
    paid_ap = cursor.fetchone()["sum"] or 0
    cursor.execute("SELECT SUM(total_amount) FROM ar_invoices")
    total_ar = cursor.fetchone()["sum"] or 0
    cursor.execute("SELECT SUM(receive_amount) FROM ar_records")
    collected_ar = cursor.fetchone()["sum"] or 0
    cursor.close()
    conn.close()
    return jsonify({
        "total_ap": total_ap, "paid_ap": paid_ap, "unpaid_ap": total_ap - paid_ap,
        "total_ar": total_ar, "collected_ar": collected_ar, "uncollected_ar": total_ar - collected_ar
    })

# --- 供應商管理頁面 ---
@app.route("/suppliers")
def suppliers_page():
    if "user_id" not in session: return redirect(url_for("login_page"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers ORDER BY supplier_code")
    suppliers_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template_string(SUPPLIERS_HTML, suppliers=suppliers_list, user_name=session.get("user_name"))

@app.route("/suppliers/add", methods=["POST"])
def add_supplier():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO suppliers (supplier_code, supplier_name, tax_id, contact_info, phone, email, payment_terms, bank_info, address) 
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (request.form["supplier_code"], request.form["supplier_name"], request.form.get("tax_id"),
              request.form.get("contact_info"), request.form.get("phone"), request.form.get("email"),
              request.form.get("payment_terms"), request.form.get("bank_info"), request.form.get("address")))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e: 
        print(e)
    return redirect(url_for("suppliers_page"))# --- 供應商管理 API ---
@app.route("/api/suppliers/list")
def api_get_suppliers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers ORDER BY supplier_code")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/suppliers/save", methods=["POST"])
def api_save_supplier():
    if "user_id" not in session: 
        return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO suppliers (supplier_code, supplier_name, tax_id, phone, payment_terms, address)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (supplier_code) DO UPDATE 
            SET supplier_name = EXCLUDED.supplier_name, tax_id = EXCLUDED.tax_id, 
                phone = EXCLUDED.phone, payment_terms = EXCLUDED.payment_terms, address = EXCLUDED.address
        """, (data.get("supplier_code"), data.get("supplier_name"), data.get("tax_id"),
              data.get("phone"), data.get("payment_terms"), data.get("address")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 供應商資料存檔/修改成功！"})
    except Exception as e: 
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/suppliers/delete/", methods=["POST"])
def api_delete_supplier(code):
    if "user_id" not in session: 
        return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM suppliers WHERE supplier_code = %s", (code,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 供應商刪除成功！"})
    except Exception as e: 
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/inbound/delete/", methods=["POST"])
def delete_inbound(in_no):
    if "user_id" not in session: 
        return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 先刪除關聯的應付帳款付款紀錄與應付發票，避免資料庫衝突
        cursor.execute("DELETE FROM ap_payments WHERE inbound_no = %s", (in_no,))
        cursor.execute("DELETE FROM ap_invoices WHERE inbound_no = %s", (in_no,))
        # 刪除進貨明細與主檔
        cursor.execute("DELETE FROM inbound_items WHERE inbound_no = %s", (in_no,))
        cursor.execute("DELETE FROM inbound_orders WHERE inbound_no = %s", (in_no,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "✔ 進貨單刪除成功！"})
    except Exception as e: 
        return jsonify({"success": False, "message": str(e)})

@app.route("/suppliers/edit/<string:code>", methods=["POST"])
def edit_supplier(code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE suppliers SET supplier_name=%s, tax_id=%s, contact_info=%s, phone=%s, email=%s, payment_terms=%s, bank_info=%s, address=%s 
            WHERE supplier_code=%s
        """, (request.form["supplier_name"], request.form.get("tax_id"), request.form.get("contact_info"),
              request.form.get("phone"), request.form.get("email"), request.form.get("payment_terms"),
              request.form.get("bank_info"), request.form.get("address"), code))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e: print(e)
    return redirect(url_for("suppliers_page"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ==================== 前端樣板 (HTML) ====================
MAIN_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>珮藏居傢俱有限公司 - 企業全方位管理系統</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    :root { --primary: #0f172a; --brand: #c59b27; --border: #cbd5e1; --text: #1e293b; --bg-main: #f8fafc; }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft JhengHei", sans-serif; }
    body { background-color: var(--bg-main); color: var(--text); padding: 15px 15px 85px 15px; display: flex; justify-content: center; font-size: 13px; }
    .container { width: 100%; max-width: 1280px; background: #ffffff; border-radius: 10px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05); border: 1px solid var(--border); overflow: hidden; }
    .nav-header-wrapper { background: #0f172a; border-bottom: 3px solid var(--brand); padding: 10px 20px; }
    .nav-group-row { display: flex; gap: 15px; align-items: center; flex-wrap: wrap; padding: 6px 0; border-bottom: 1px dashed rgba(255,255,255,0.1); }
    .nav-group-row:last-child { border-bottom: none; }
    .nav-group-title { color: #f59e0b; font-size: 11.5px; font-weight: 700; min-width: 120px; display: inline-flex; align-items: center; gap: 4px; }
    .nav-group-buttons { display: flex; gap: 5px; flex-wrap: wrap; flex: 1; }
    .tab-btn { background: #1e293b; color: #cbd5e1; border: none; padding: 5px 10px; font-size: 11.5px; font-weight: 600; border-radius: 5px; cursor: pointer; transition: all 0.2s ease; }
    .tab-btn:hover { background: #334155; color: #fff; }
    .tab-btn.active { background: var(--brand); color: #fff; box-shadow: 0 2px 8px rgba(197, 155, 39, 0.4); }
    .btn-supplier-link { background: #0284c7; color: #fff; text-decoration: none; padding: 5px 10px; font-size: 11.5px; font-weight: 600; border-radius: 5px; display: inline-flex; align-items: center; gap: 4px; }
    .btn-supplier-link:hover { background: #0369a1; color: #fff; }
    .po-header { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #fff; padding: 22px 30px; display: flex; justify-content: space-between; align-items: center; border-bottom: 4px solid var(--brand); }
    .po-title h1 { font-size: 20px; font-weight: 700; letter-spacing: 0.5px; } 
    .po-title div { font-size: 11.5px; color: #94a3b8; margin-top: 3px; }
    .po-company-info { text-align: right; font-size: 12px; color: #cbd5e1; line-height: 1.5; }
    .company-name-top { font-size: 14px; font-weight: 700; color: #f59e0b; margin-bottom: 3px; }
    .company-mid-row { display: flex; justify-content: flex-end; gap: 15px; margin-bottom: 3px; }
    .company-address { font-size: 11px; color: #94a3b8; }
    form { padding: 25px 35px 45px 35px; }
    .section-block { margin-bottom: 18px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
    .section-title { font-size: 14px; font-weight: 700; color: var(--primary); margin-bottom: 14px; padding-bottom: 6px; border-bottom: 2px solid #f1f5f9; display: flex; align-items: center; gap: 6px; }
    .section-title::before { content: ""; width: 4px; height: 13px; background: var(--brand); border-radius: 2px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
    .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
    .form-group { display: flex; flex-direction: column; gap: 5px; }
    label { font-size: 12px; font-weight: 600; color: #475569; }
    .required::after { content: " *"; color: #dc2626; }
    input, select, textarea { padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: #fff; color: var(--text); outline: none; width: 100%; transition: border-color 0.2s, box-shadow 0.2s; }
    input:focus, select:focus, textarea:focus { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(197, 155, 39, 0.15); }
    .readonly { background: #f8fafc; color: #475569; font-weight: 600; }
    .items-table { width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 8px; border-radius: 6px; overflow: hidden; border: 1px solid var(--border); }
    .items-table th { background: #f8fafc; color: #334155; font-size: 12px; padding: 10px; border-bottom: 1px solid var(--border); text-align: left; font-weight: 600; }
    .items-table td { padding: 8px 10px; border-bottom: 1px solid #f1f5f9; border-right: 1px solid #f1f5f9; vertical-align: middle; font-size: 12.5px; background: #fff; }
    .items-table tr:last-child td { border-bottom: none; }
    .input-qty { text-align: center; } .input-price { text-align: right; } .input-total { text-align: right; }
    .btn-add-item { background: #0f172a; color: #fff; border: none; padding: 6px 12px; font-size: 12px; font-weight: 600; border-radius: 6px; cursor: pointer; }
    .btn-del-item { background: #fee2e2; color: #dc2626; border: 1px solid #fecaca; padding: 3px 7px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600; }
    .btn-query { background: #0f172a; color: #fff; border: none; padding: 8px 12px; font-size: 12px; font-weight: 600; border-radius: 6px; cursor: pointer; }
    .floating-action-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(255, 255, 255, 0.92); backdrop-filter: blur(8px); border-top: 1px solid var(--border); padding: 12px 24px; display: flex; justify-content: center; gap: 10px; z-index: 1000; box-shadow: 0 -4px 20px rgba(0,0,0,0.06); }
    .btn-submit { background: linear-gradient(135deg, var(--brand) 0%, #a68120 100%); color: #fff; font-size: 13px; font-weight: 700; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; box-shadow: 0 2px 6px rgba(197,155,39,0.3); }
    .btn-print { background: #475569; color: #fff; font-size: 13px; font-weight: 600; border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; }
    .btn-reset { background: #64748b; color: #fff; font-size: 13px; font-weight: 600; border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; }
    .btn-logout { background: #dc2626; color: #fff; font-size: 13px; font-weight: 600; border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; }
    .app-view { display: none; } .app-view.active { display: block; }
    @media print { 
      .nav-header-wrapper, .floating-action-bar, .btn-query, .btn-add-item, .btn-del-item, .no-print { display: none !important; } 
      body { background-color: #fff; padding: 0; } 
      .container { box-shadow: none; border: none; width: 100%; max-width: 100%; } 
      form { padding: 10px; } 
    }
  </style>
</head>
<body>
<div class="container" id="appContainer">
  <div class="po-header">
    <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>ENTERPRISE MANAGEMENT SYSTEM (當前使用者: {{ user_name }})</div></div>
    <div class="po-company-info">
      <div class="company-name-top">珮藏居傢俱有限公司</div>
      <div class="company-mid-row"><span>統編：83390454</span><span>電話：02-22691071</span></div>
      <div class="company-address">地址：新北市土城區中央路3段130-6號</div>
    </div>
  </div>

  <div class="nav-header-wrapper">
    <div class="nav-group-row">
      <span class="nav-group-title"><i class="fa-solid fa-address-book"></i> 基礎主檔管理：</span>
      <div class="nav-group-buttons">
        <button type="button" class="tab-btn" id="btnTabCustomer" onclick="switchTab('customer')">📇 客戶建立</button>
        <a href="{{ url_for('suppliers_page') }}" class="btn-supplier-link"><i class="fa-solid fa-truck-field"></i> 供應商管理</a>
      </div>
    </div>
    <div class="nav-group-row">
      <span class="nav-group-title"><i class="fa-solid fa-boxes-stacked"></i> 採購與進貨：</span>
      <div class="nav-group-buttons">
        <button type="button" class="tab-btn active" id="btnTabPurchase" onclick="switchTab('purchase')">📄 採購單</button>
        <button type="button" class="tab-btn" id="btnTabInbound" onclick="switchTab('inbound')">📦 進貨驗收</button>
      </div>
    </div>
    <div class="nav-group-row">
      <span class="nav-group-title"><i class="fa-solid fa-cart-shopping"></i> 訂單與銷貨：</span>
      <div class="nav-group-buttons">
        <button type="button" class="tab-btn" id="btnTabSo" onclick="switchTab('so')">🛒 客戶訂單</button>
        <button type="button" class="tab-btn" id="btnTabDelivery" onclick="switchTab('delivery')">🚚 銷貨出貨</button>
        <button type="button" class="tab-btn" id="btnTabSalesPerf" onclick="switchTab('salesPerf')">🏆 業務業績與管銷</button>
      </div>
    </div>
  </div>

  <!-- 1. 採購單系統 -->
  <div id="purchaseView" class="app-view active">
    <form id="purchaseForm" onsubmit="handlePoSubmit(event)">
      <div class="section-block">
        <div class="section-title">一、 採購基本資料與查詢修改</div>
        <div class="grid-3">
          <div class="form-group"><label class="required">採購人員</label><input type="text" id="po_buyer_name" value="{{ user_name }}" required></div>
          <div class="form-group"><label class="required">採購編號</label><div style="display:flex; gap:6px;"><input type="text" id="po_no" required style="flex:1;"><button type="button" class="btn-query" onclick="queryPoRecord()">🔍 查詢</button></div></div>
          <div class="form-group"><label class="required">訂購日期</label><input type="date" id="po_order_date" required></div>
        </div>
        <div class="grid-2" style="margin-top:12px;">
          <div class="form-group"><label class="required">交貨日期</label><input type="date" id="po_delivery_date" required></div>
          <div class="form-group"><label class="required">廠商類別</label><select id="po_vendor_type" required><option value="" disabled selected hidden>請選擇</option><option value="國外廠商">國外廠商</option><option value="國內廠商">國內廠商</option></select></div>
        </div>
        <div class="grid-3" style="margin-top:12px; border-top:1px dashed #cbd5e1; padding-top:12px;">
          <div class="form-group"><label>供應商編號</label><input type="text" id="po_vendor_id" onblur="lookupVendorName('po')"></div>
          <div class="form-group"><label class="required">供應商名稱</label><input type="text" id="po_vendor_name" required></div>
          <div class="form-group"><label>供應商聯絡人</label><input type="text" id="po_vendor_contact"></div>
        </div>
      </div>
      <div class="section-block">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <div class="section-title" style="margin-bottom:0; border:none; padding:0;">二、 採購品項明細</div>
          <button type="button" class="btn-add-item" onclick="addPoItemRow()">＋ 新增品項</button>
        </div>
        <table class="items-table">
          <thead><tr><th style="width:14%;">型號</th><th style="width:18%;">品名</th><th style="width:12%;">規格</th><th style="width:12%;">顏色</th><th style="width:7%;">數量</th><th style="width:11%;">單價</th><th style="width:13%;">金額</th><th style="width:7%;" class="no-print">操作</th></tr></thead>
          <tbody id="poItemsBody"></tbody>
          <tfoot><tr><td colspan="6" style="text-align:right; font-weight:bold;">總金額：</td><td colspan="2" style="font-weight:bold;"><span id="poGrandTotalText">0.00</span> <span id="poCurrencyLabel">NTD</span></td></tr></tfoot>
        </table>
      </div>
    </form>
  </div>

  <!-- 2. 進貨驗收系統 (已修正：供應商編號與名稱獨立並排) -->
  <div id="inboundView" class="app-view">
    <form id="inboundForm" onsubmit="handleInboundSubmit(event)">
      <div class="section-block">
        <div class="section-title">一、 進貨基本資料與採購單轉入</div>
        <div class="grid-3">
          <div class="form-group"><label class="required">收貨人員</label><input type="text" id="in_receiver_name" value="{{ user_name }}" required></div>
          <div class="form-group"><label class="required">進貨單號</label><div style="display:flex; gap:6px;"><input type="text" id="in_no" required style="flex:1;"><button type="button" class="btn-query" onclick="queryInboundRecord()">🔍 查詢</button></div></div>
          <div class="form-group"><label class="required">進貨日期</label><input type="date" id="in_date" required onchange="autoFillMonth()"></div>
        </div>
        <div class="grid-2" style="margin-top:12px;">
          <div class="form-group"><label class="required">歸屬月份</label><input type="text" id="in_month" required></div>
          <div class="form-group"><label class="required">採購編號</label><div style="display:flex; gap:6px;"><input type="text" id="in_po_no" required style="flex:1;"><button type="button" class="btn-query" onclick="importFromPo()">📥 轉入PO</button></div></div>
        </div>
        <!-- 供應商編號與供應商名稱獨立並排 -->
        <div class="grid-2" style="margin-top:12px; border-top:1px dashed #cbd5e1; padding-top:12px;">
          <div class="form-group">
            <label class="required">供應商編號</label>
            <input type="text" id="in_vendor_id" onblur="lookupVendorName('in')" placeholder="輸入代號按離開" required>
          </div>
          <div class="form-group">
            <label class="required">供應商名稱</label>
            <input type="text" id="in_vendor_name" class="readonly" readonly required placeholder="自動帶出名稱">
          </div>
        </div>
      </div>
      <div class="section-block">
        <div class="section-title">二、 進貨驗收明細與入庫倉庫</div>
        <table class="items-table">
          <thead><tr><th style="width:12%;">型號</th><th style="width:16%;">品名</th><th style="width:11%;">規格</th><th style="width:11%;">顏色</th><th style="width:12%;">入庫倉庫</th><th style="width:6%;">訂購</th><th style="width:7%;">實際</th><th style="width:11%;">單價</th><th style="width:12%;">金額</th></tr></thead>
          <tbody id="inItemsBody"></tbody>
          <tfoot><tr><td colspan="8" style="text-align:right; font-weight:bold;">總進貨金額：</td><td style="font-weight:bold;"><span id="inGrandTotalText">0.00</span></td></tr></tfoot>
        </table>
      </div>
    </form>
  </div>
</div>

<div class="floating-action-bar" id="floatingBar">
  <button type="button" class="btn-submit" onclick="submitCurrentForm()">💾 儲存當前頁面</button>
  <button type="button" class="btn-print" onclick="window.print()">🖨️ 列印單據</button>
  <button type="button" class="btn-reset" onclick="resetCurrentForm()">🔄 清空重設</button>
  <button type="button" class="btn-logout" onclick="window.location.href='/logout'">🚪 登出</button>
</div>

<script>
  let currentTab = 'purchase';
  window.addEventListener('DOMContentLoaded', () => {
    ['po_order_date', 'po_delivery_date', 'in_date'].forEach(id => {
      const el = document.getElementById(id); if (el) el.valueAsDate = new Date();
    });
    const mEl = document.getElementById('in_month'); if (mEl) mEl.value = new Date().toISOString().slice(0, 7);
    for (let i = 0; i < 4; i++) { addPoItemRow(); }
  });
  function switchTab(tab) {
    currentTab = tab;
    ['purchase', 'inbound', 'so', 'delivery', 'inventory', 'customer', 'supplier', 'trans', 'salesPerf', 'creditCard', 'invoice', 'hr', 'payroll', 'apPro', 'arPro', 'printCenter', 'ap', 'ar', 'finance'].forEach(t => {
      const btn = document.getElementById('btnTab' + t.charAt(0).toUpperCase() + t.slice(1));
      const view = document.getElementById(t + 'View');
      if(btn) btn.className = (t === tab) ? 'tab-btn active' : 'tab-btn';
      if(view) view.className = (t === tab) ? 'app-view active' : 'app-view';
    });

  }
  function lookupVendorName(type) {
    const vIdInputId = (type === 'po') ? 'po_vendor_id' : 'in_vendor_id';
    const vNameInputId = (type === 'po') ? 'po_vendor_name' : 'in_vendor_name';
    
    const vId = document.getElementById(vIdInputId).value.trim();
    if (!vId) return;

    fetch(`/api/vendor/${vId}`)
      .then(r => r.json())
      .then(res => {
        if (res.found) {
          document.getElementById(vNameInputId).value = res.vendor_name;
        } else {
          alert("⚠️ 查無此供應商代號！請先至「供應商建立」頁面建檔。");
          document.getElementById(vNameInputId).value = '';
        }
      })
      .catch(err => {
        console.error("查詢供應商發生錯誤:", err);
      });
  }

  function addPoItemRow() {
    const tbody = document.getElementById('poItemsBody');
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><input type="text" class="po-model" placeholder="型號"></td><td><input type="text" class="po-name" placeholder="品名"></td><td><input type="text" class="po-size" placeholder="規格"></td><td><input type="text" class="po-color" placeholder="顏色"></td><td><input type="number" class="po-qty input-qty" min="0" oninput="calculatePoTotals()"></td><td><input type="number" class="po-price input-price" step="0.01" min="0" oninput="calculatePoTotals()"></td><td><input type="text" class="po-total readonly input-total" readonly></td><td class="no-print" style="text-align:center;"><button type="button" class="btn-del-item" onclick="this.closest('tr').remove(); calculatePoTotals();">刪除</button></td>`;
    tbody.appendChild(tr);
  }
  function calculatePoTotals() {
    let gt = 0;
    document.querySelectorAll('#poItemsBody tr').forEach(row => {
      const q = parseFloat(row.querySelector('.po-qty').value) || 0;
      const p = parseFloat(row.querySelector('.po-price').value) || 0;
      const t = q * p;
      row.querySelector('.po-total').value = t ? t.toLocaleString('zh-TW', {minimumFractionDigits:2}) : '';
      gt += t;
    });
    document.getElementById('poGrandTotalText').innerText = gt.toLocaleString('zh-TW', {minimumFractionDigits:2});
  }
  function queryInboundRecord() {
    const no = document.getElementById('in_no').value.trim();
    if (!no) return alert("請輸入進貨單號");
    fetch(`/api/inbound/${no}`).then(r => r.json()).then(res => {
      if (res.found) {
        const h = res.header;
        document.getElementById('in_receiver_name').value = h.receiver_name;
        document.getElementById('in_date').value = h.inbound_date;
        document.getElementById('in_month').value = h.month;
        document.getElementById('in_po_no').value = h.po_number;
        document.getElementById('in_vendor_id').value = h.supplier_code || h.vendor_id || '';
        document.getElementById('in_vendor_name').value = h.supplier_name || h.vendor_name || '';
        alert("✔ 進貨單載入成功！");
      } else alert(res.message);
    });
  }
</script>
</body>
</html>
"""

SUPPLIERS_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><title>供應商管理 - 珮藏居系統</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <nav class="navbar navbar-dark bg-dark shadow-sm mb-4">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('index') }}">珮藏居採購系統</a>
            <a href="{{ url_for('index') }}" class="btn btn-outline-light btn-sm">返回首頁</a>
        </div>
    </nav>
    <div class="container-fluid px-4">
        <h4 class="text-secondary mb-3">供應商清單管理</h4>
    </div>
</body>
</html>
"""