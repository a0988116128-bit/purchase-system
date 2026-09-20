from datetime import datetime
from flask import Flask, flash, jsonify, redirect, render_template_string, request, session, url_for
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "pezang_ultimate_enterprise_v4_2026"

DB_PATH = (
    "/tmp/database.db"
    if os.environ.get("RENDER")
    else "database.db"
)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, password TEXT NOT NULL, role TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS suppliers (supplier_code TEXT PRIMARY KEY, supplier_name TEXT NOT NULL, tax_id TEXT, contact_info TEXT, payment_terms TEXT, bank_info TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS customers (customer_code TEXT PRIMARY KEY, customer_name TEXT NOT NULL, tax_id TEXT, contact_info TEXT, payment_terms TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS warehouses (id INTEGER PRIMARY KEY AUTOINCREMENT, warehouse_name TEXT UNIQUE NOT NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS inventory_items (sku TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT, cost REAL DEFAULT 0, price REAL DEFAULT 0, stock INTEGER DEFAULT 0, safety_stock INTEGER DEFAULT 0, note TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS employees (emp_id TEXT PRIMARY KEY, emp_name TEXT NOT NULL, department TEXT, title TEXT, phone TEXT, hire_date TEXT, base_salary REAL DEFAULT 0, status TEXT DEFAULT '在職', note TEXT)")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payroll_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT, emp_id TEXT, emp_name TEXT, pay_month TEXT,
                base_salary REAL DEFAULT 0, allowance REAL DEFAULT 0, overtime_pay REAL DEFAULT 0,
                leave_deduction REAL DEFAULT 0, emp_purchase_deduction REAL DEFAULT 0,
                insurance_deduction REAL DEFAULT 0, net_salary REAL DEFAULT 0, pay_date TEXT,
                status TEXT DEFAULT '已發放', note TEXT, created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                po_number TEXT PRIMARY KEY, purchaser TEXT, order_date TEXT, delivery_date TEXT,
                price_term TEXT, vendor_type TEXT, supplier_code TEXT, supplier_name TEXT,
                vendor_contact TEXT, currency TEXT, grand_total REAL, deposit_pct REAL,
                deposit_amount REAL, balance_pct REAL, balance_amount REAL,
                shipping_mark TEXT, packing TEXT, bank_info TEXT, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, po_number TEXT, model TEXT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT, inbound_no TEXT, warehouse TEXT,
                model TEXT, product_name TEXT, specification TEXT, color TEXT,
                ordered_qty INTEGER, actual_qty INTEGER, unit_price REAL, subtotal REAL, remarks TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_orders (
                so_number TEXT PRIMARY KEY, sales_person TEXT, order_date TEXT,
                customer_code TEXT, customer_name TEXT, currency TEXT, grand_total REAL,
                remark TEXT, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, so_number TEXT, model TEXT,
                product_name TEXT, specification TEXT, color TEXT, quantity INTEGER,
                unit_price REAL, subtotal REAL, remarks TEXT
            )
        """)

        # 銷貨出貨單 (新增 driver 與 manual_freight 欄位)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_orders (
                do_number TEXT PRIMARY KEY, shipper_name TEXT, warehouse TEXT,
                so_number TEXT, delivery_date TEXT, customer_code TEXT, customer_name TEXT,
                driver TEXT, manual_freight REAL DEFAULT 0, grand_total REAL, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, do_number TEXT, warehouse TEXT,
                model TEXT, product_name TEXT, specification TEXT, color TEXT,
                shipped_qty INTEGER, unit_price REAL, subtotal REAL, remarks TEXT
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
            CREATE TABLE IF NOT EXISTS ar_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT, customer TEXT, sales_amount REAL, deposit REAL,
                receive_amount REAL, pay_type TEXT, check_no TEXT, check_due_date TEXT,
                receive_date TEXT, unpaid_amount REAL, driver TEXT, driver_area TEXT,
                freight REAL, old_item_fee REAL, keyin_user TEXT, note TEXT, created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, trans_date TEXT, trans_type TEXT,
                order_id TEXT, customer_code TEXT, customer_name TEXT, sku TEXT,
                qty INTEGER, price REAL, total_amount REAL, cogs REAL,
                keyin_user TEXT, status TEXT, note TEXT, created_at TEXT
            )
        """)

        # 業務業績表 (支援手動輸入或銷貨連動)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sales_person TEXT, order_id TEXT, order_date TEXT,
                customer_name TEXT, sales_amount REAL, commission_rate REAL DEFAULT 0.05,
                commission_amount REAL, status TEXT DEFAULT '已結算',
                note TEXT, created_at TEXT
            )
        """)

        # 會計傳票主檔與明細
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vouchers (
                voucher_no TEXT PRIMARY KEY, voucher_date TEXT, voucher_type TEXT,
                summary TEXT, preparer TEXT, total_amount REAL, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voucher_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_no TEXT,
                account_code TEXT, account_name TEXT, debit REAL DEFAULT 0, credit REAL DEFAULT 0
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO users (id, name, password, role) VALUES (?, ?, ?, ?)",
                [("01", "黃詠甯", "0320", "系統管理"), ("02", "經辦人員", "1234", "門市經辦"), ("admin", "系統管理員", "pezang888", "系統管理")])

        cursor.execute("SELECT COUNT(*) FROM warehouses")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO warehouses (warehouse_name) VALUES (?)",
                [("八里倉",), ("南倉",), ("土城門市倉",), ("外倉",)])

        cursor.execute("SELECT COUNT(*) FROM employees")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
                ("EMP01", "黃詠甯", "管理部", "會計及特助", "0912-345678", "2024-01-01", 45000, "在職", "核心管理"),
                ("EMP02", "江婉秀", "門市部", "門市經辦", "0922-888999", "2024-06-01", 35000, "在職", "門市業務")
            ])

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Init DB Error: {e}")

init_db()


# ==================== 路由與 API ====================

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template_string(MAIN_HTML, user_name=session["user_name"], user_role=session.get("user_role", "經辦人"))

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        uid, pwd = data.get("username") or data.get("user_id"), data.get("password")
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE id = ? AND password = ?", (uid, pwd)).fetchone()
        conn.close()
        if user:
            session["user_id"], session["user_name"], session["user_role"] = user["id"], user["name"], user["role"]
            return jsonify({"success": True, "user": {"username": user["id"], "name": user["name"], "role": user["role"]}}) if request.is_json else redirect(url_for("index"))
        return jsonify({"success": False, "message": "❌ 帳號或密碼錯誤"}) if request.is_json else "登入失敗"
    return render_template_string(LOGIN_HTML)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/api/warehouses")
def get_warehouses():
    conn = get_db_connection()
    rows = conn.execute("SELECT warehouse_name FROM warehouses").fetchall()
    conn.close()
    return jsonify([r["warehouse_name"] for r in rows])

@app.route("/api/vendor/<string:v_id>")
def get_vendor(v_id):
    conn = get_db_connection()
    row = conn.execute("SELECT supplier_name FROM suppliers WHERE supplier_code = ?", (v_id,)).fetchone()
    conn.close()
    return jsonify({"found": True, "vendor_name": row["supplier_name"]} if row else {"found": False})

@app.route("/api/customer/<string:c_id>")
def get_customer(c_id):
    conn = get_db_connection()
    row = conn.execute("SELECT customer_name FROM customers WHERE customer_code = ?", (c_id,)).fetchone()
    conn.close()
    return jsonify({"found": True, "customer_name": row["customer_name"]} if row else {"found": False})


# --- 員工與薪資 CRUD API ---
@app.route("/api/employees/list")
def get_employees():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM employees ORDER BY emp_id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/employees/save", methods=["POST"])
def save_employee():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        conn.execute("""INSERT INTO employees (emp_id, emp_name, department, title, phone, hire_date, base_salary, status, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(emp_id) DO UPDATE SET emp_name=?, department=?, title=?, phone=?, hire_date=?, base_salary=?, status=?, note=?""",
                     (data.get("emp_id"), data.get("emp_name"), data.get("department"), data.get("title"),
                      data.get("phone"), data.get("hire_date"), data.get("base_salary"), data.get("status"), data.get("note"),
                      data.get("emp_name"), data.get("department"), data.get("title"), data.get("phone"),
                      data.get("hire_date"), data.get("base_salary"), data.get("status"), data.get("note")))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "✔ 員工資料存檔/修改成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/employees/delete/<string:emp_id>", methods=["POST"])
def delete_employee(emp_id):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM employees WHERE emp_id = ?", (emp_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "✔ 員工刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/payroll/list")
def get_payroll():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM payroll_records ORDER BY pay_month DESC, emp_id ASC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/payroll/save", methods=["POST"])
def save_payroll():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        base = float(data.get("base_salary", 0))
        allow = float(data.get("allowance", 0))
        ot = float(data.get("overtime_pay", 0))
        leave_ded = float(data.get("leave_deduction", 0))
        pur_ded = float(data.get("emp_purchase_deduction", 0))
        ins_ded = float(data.get("insurance_deduction", 0))
        net = base + allow + ot - leave_ded - pur_ded - ins_ded
        
        p_id = data.get("payroll_id")
        if p_id:
            conn.execute("""UPDATE payroll_records SET base_salary=?, allowance=?, overtime_pay=?, leave_deduction=?, emp_purchase_deduction=?, insurance_deduction=?, net_salary=?, pay_date=?, status=?, note=? WHERE id=?""",
                         (base, allow, ot, leave_ded, pur_ded, ins_ded, net, data.get("pay_date"), data.get("status", "已發放"), data.get("note"), p_id))
        else:
            conn.execute("""INSERT INTO payroll_records (emp_id, emp_name, pay_month, base_salary, allowance, overtime_pay, leave_deduction, emp_purchase_deduction, insurance_deduction, net_salary, pay_date, status, note, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                         (data.get("emp_id"), data.get("emp_name"), data.get("pay_month"), base, allow, ot, leave_ded, pur_ded, ins_ded, net,
                          data.get("pay_date"), data.get("status", "已發放"), data.get("note"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"✔ 薪資紀錄存檔成功！實發金額: ${net:,.2f}"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/payroll/delete/<int:pay_id>", methods=["POST"])
def delete_payroll(pay_id):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM payroll_records WHERE id = ?", (pay_id,))
        conn.commit()
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
        conn.execute("DELETE FROM purchase_orders WHERE po_number = ?", (po_no,))
        conn.execute("DELETE FROM purchase_items WHERE po_number = ?", (po_no,))
        conn.execute("""INSERT INTO purchase_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (po_no, data.get("buyer_name"), data.get("order_date"), data.get("delivery_date"),
             data.get("price_term"), data.get("vendor_type"), data.get("vendor_id"), data.get("vendor_name"),
             data.get("vendor_contact"), data.get("currency"), data.get("grand_total", 0), data.get("dep_pct", 0),
             data.get("dep_amt", ""), data.get("bal_pct", 100), data.get("bal_amt", ""),
             data.get("shipping_mark"), data.get("packing"), data.get("bank_info"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        for item in data.get("items", []):
            conn.execute("INSERT INTO purchase_items (po_number, model, product_name, specification, color, quantity, unit_price, subtotal, remarks) VALUES (?,?,?,?,?,?,?,?,?)",
                (po_no, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                 item.get("qty"), item.get("unit_price"), item.get("total"), item.get("remarks")))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route("/api/po/<string:po_no>")
def get_po(po_no):
    conn = get_db_connection()
    po = conn.execute("SELECT * FROM purchase_orders WHERE po_number = ?", (po_no,)).fetchone()
    if not po:
        conn.close()
        return jsonify({"found": False, "message": "找不到採購單"})
    items = [dict(r) for r in conn.execute("SELECT model, product_name as name, specification as size, color, quantity as qty, unit_price, subtotal as total, remarks FROM purchase_items WHERE po_number = ?", (po_no,)).fetchall()]
    conn.close()
    return jsonify({"found": True, "header": dict(po), "items": items})

@app.route("/api/inbound/save", methods=["POST"])
def save_inbound():
    if "user_id" not in session: return jsonify({"status": "error", "message": "請先登入"})
    data = request.get_json()
    in_no = data.get("inbound_no")
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM inbound_orders WHERE inbound_no = ?", (in_no,))
        conn.execute("DELETE FROM inbound_items WHERE inbound_no = ?", (in_no,))
        
        v_id = data.get("vendor_id", "") or ""
        v_name = data.get("vendor_name", "") or "未命名供應商"

        conn.execute("INSERT INTO inbound_orders VALUES (?,?,?,?,?,?,?,?,?)",
            (in_no, data.get("receiver_name"), data.get("warehouse", "八里倉"), data.get("po_no"),
             data.get("inbound_date"), data.get("month"), v_id, v_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        total_amt = 0
        for item in data.get("items", []):
            sub = item.get("actual_qty", 0) * item.get("unit_price", 0)
            total_amt += sub
            wh = item.get("warehouse", "八里倉")
            conn.execute("INSERT INTO inbound_items (inbound_no, warehouse, model, product_name, specification, color, ordered_qty, actual_qty, unit_price, subtotal, remarks) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (in_no, wh, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                 item.get("ordered_qty"), item.get("actual_qty"), item.get("unit_price"), sub, item.get("remarks")))
            
            sku = item.get("model")
            conn.execute("""INSERT INTO inventory_items (sku, name, category, cost, price, stock, safety_stock, note)
                            VALUES (?, ?, '五金配件', ?, ?, ?, 10, '進貨入庫')
                            ON CONFLICT(sku) DO UPDATE SET stock = stock + ?""",
                         (sku, item.get("name"), item.get("unit_price"), item.get("unit_price") * 1.5, item.get("actual_qty"), item.get("actual_qty")))

        v_display = f"{v_id} {v_name}".strip() if v_id else v_name
        conn.execute("INSERT OR REPLACE INTO ap_invoices VALUES (?,?,?,?, '月結30天', ?, '未付')",
            (in_no, data.get("inbound_date"), v_display, total_amt, data.get("inbound_date")))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route("/api/inbound/<string:in_no>")
def get_inbound(in_no):
    conn = get_db_connection()
    order = conn.execute("SELECT * FROM inbound_orders WHERE inbound_no = ?", (in_no,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"found": False, "message": "找不到進貨單"})
    items = [dict(r) for r in conn.execute("SELECT warehouse, model, product_name as name, specification as size, color, ordered_qty, actual_qty, unit_price, subtotal as total, remarks FROM inbound_items WHERE inbound_no = ?", (in_no,)).fetchall()]
    conn.close()
    return jsonify({"found": True, "header": dict(order), "items": items})


# --- 訂單與銷貨 API ---
@app.route("/api/so/save", methods=["POST"])
def save_so():
    if "user_id" not in session: return jsonify({"status": "error", "message": "請先登入"})
    data = request.get_json()
    so_no = data.get("so_no")
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM sales_orders WHERE so_number = ?", (so_no,))
        conn.execute("DELETE FROM sales_items WHERE so_number = ?", (so_no,))
        conn.execute("INSERT INTO sales_orders VALUES (?,?,?,?,?,?,?,?,?)",
            (so_no, data.get("sales_person"), data.get("order_date"), data.get("customer_code"),
             data.get("customer_name"), data.get("currency"), data.get("grand_total", 0), data.get("remark"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        for item in data.get("items", []):
            conn.execute("INSERT INTO sales_items (so_number, model, product_name, specification, color, quantity, unit_price, subtotal, remarks) VALUES (?,?,?,?,?,?,?,?,?)",
                (so_no, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                 item.get("qty"), item.get("unit_price"), item.get("total"), item.get("remarks")))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route("/api/so/<string:so_no>")
def get_so(so_no):
    conn = get_db_connection()
    so = conn.execute("SELECT * FROM sales_orders WHERE so_number = ?", (so_no,)).fetchone()
    if not so:
        conn.close()
        return jsonify({"found": False, "message": "找不到客戶訂單"})
    items = [dict(r) for r in conn.execute("SELECT model, product_name as name, specification as size, color, quantity as qty, unit_price, subtotal as total, remarks FROM sales_items WHERE so_number = ?", (so_no,)).fetchall()]
    conn.close()
    return jsonify({"found": True, "header": dict(so), "items": items})

@app.route("/api/delivery/save", methods=["POST"])
def save_delivery():
    if "user_id" not in session: return jsonify({"status": "error", "message": "請先登入"})
    data = request.get_json()
    do_no = data.get("do_number")
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM delivery_orders WHERE do_number = ?", (do_no,))
        conn.execute("DELETE FROM delivery_items WHERE do_number = ?", (do_no,))
        
        c_id = data.get("customer_code", "") or ""
        c_name = data.get("customer_name", "") or "未命名客戶"
        driver = data.get("driver", "大蔡")
        manual_freight = float(data.get("manual_freight", 0))

        conn.execute("INSERT INTO delivery_orders VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (do_no, data.get("shipper_name"), data.get("warehouse", "八里倉"), data.get("so_no"),
             data.get("delivery_date"), c_id, c_name, driver, manual_freight, data.get("grand_total", 0), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        total_amt = 0
        for item in data.get("items", []):
            sub = item.get("shipped_qty", 0) * item.get("unit_price", 0)
            total_amt += sub
            wh = item.get("warehouse", "八里倉")
            conn.execute("INSERT INTO delivery_items (do_number, warehouse, model, product_name, specification, color, shipped_qty, unit_price, subtotal, remarks) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (do_no, wh, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                 item.get("shipped_qty"), item.get("unit_price"), sub, item.get("remarks")))
            
            sku = item.get("model")
            conn.execute("UPDATE inventory_items SET stock = stock - ? WHERE sku = ?", (item.get("shipped_qty"), sku))

        c_display = f"{c_id} {c_name}".strip() if c_id else c_name
        conn.execute("INSERT OR REPLACE INTO ar_invoices VALUES (?,?,?,?, '月結30天', ?, '未收')",
            (do_no, data.get("delivery_date"), c_display, total_amt, data.get("delivery_date")))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route("/api/delivery/<string:do_no>")
def get_delivery(do_no):
    conn = get_db_connection()
    dOrder = conn.execute("SELECT * FROM delivery_orders WHERE do_number = ?", (do_no,)).fetchone()
    if not dOrder:
        conn.close()
        return jsonify({"found": False, "message": "找不到銷貨出貨單"})
    items = [dict(r) for r in conn.execute("SELECT warehouse, model, product_name as name, specification as size, color, shipped_qty, unit_price, subtotal as total, remarks FROM delivery_items WHERE do_number = ?", (do_no,)).fetchall()]
    res_data = dict(dOrder)
    conn.close()
    return jsonify({"found": True, "header": res_data, "items": items})


# --- 庫存 CRUD 與進銷存 API ---
@app.route("/api/inventory/list")
def get_inventory():
    conn = get_db_connection()
    rows = conn.execute("SELECT sku, name, category, cost, price, stock, safety_stock, note FROM inventory_items ORDER BY sku").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/inventory/save", methods=["POST"])
def save_inventory_item():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        conn.execute("""INSERT INTO inventory_items (sku, name, category, cost, price, stock, safety_stock, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(sku) DO UPDATE SET name=?, category=?, cost=?, price=?, stock=?, safety_stock=?, note=?""",
                     (data.get("sku"), data.get("name"), data.get("category"), data.get("cost"), data.get("price"),
                      data.get("stock"), data.get("safety_stock"), data.get("note"),
                      data.get("name"), data.get("category"), data.get("cost"), data.get("price"),
                      data.get("stock"), data.get("safety_stock"), data.get("note")))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "✔ 商品存檔/修改成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/inventory/delete/<string:sku>", methods=["POST"])
def delete_inventory_item(sku):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM inventory_items WHERE sku = ?", (sku,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "✔ 商品刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/inventory/transaction/save", methods=["POST"])
def save_inventory_transaction():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        ttype = data.get("transType")
        sku = data.get("transSku")
        qty = int(data.get("transQty", 0))
        price = float(data.get("transPrice", 0))
        
        item = conn.execute("SELECT * FROM inventory_items WHERE sku = ?", (sku,)).fetchone()
        if not item: return jsonify({"success": False, "message": "找不到商品"})
        
        cost = item["cost"]
        current_stock = item["stock"]
        
        if ttype == "進貨":
            conn.execute("UPDATE inventory_items SET stock = stock + ? WHERE sku = ?", (qty, sku))
            cogs = 0
        elif ttype == "進貨退回":
            conn.execute("UPDATE inventory_items SET stock = MAX(0, stock - ?) WHERE sku = ?", (qty, sku))
            cogs = 0
        elif ttype == "銷貨":
            if current_stock < qty: return jsonify({"success": False, "message": f"庫存不足，剩餘 {current_stock} 件"})
            conn.execute("UPDATE inventory_items SET stock = stock - ? WHERE sku = ?", (qty, sku))
            cogs = qty * cost
        elif ttype == "銷貨退回":
            conn.execute("UPDATE inventory_items SET stock = stock + ? WHERE sku = ?", (qty, sku))
            cogs = -(qty * cost)
        else:
            cogs = 0

        total_amt = qty * price
        conn.execute("""INSERT INTO inventory_transactions (trans_date, trans_type, order_id, customer_code, customer_name, sku, qty, price, total_amount, cogs, keyin_user, status, note, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '已入帳', ?, ?)""",
                     (data.get("transDate"), ttype, data.get("orderId"), data.get("customerCode"), data.get("customerName"),
                      sku, qty, price, total_amt, cogs, data.get("keyinUser"), data.get("transNote"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"【{ttype}】單據登錄成功！結轉 COGS: ${cogs:,.0f}"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

# --- 業務業績 API (支援手動輸入、查詢、修改、刪除) ---
@app.route("/api/sales/performance")
def get_sales_performance():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM sales_performance ORDER BY order_date DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/sales/performance/save", methods=["POST"])
def save_sales_performance():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        sp_id = data.get("perf_id")
        sales_amt = float(data.get("sales_amount", 0))
        rate = float(data.get("commission_rate", 0.05))
        comm_amt = sales_amt * rate

        if sp_id:
            conn.execute("""UPDATE sales_performance SET sales_person=?, order_id=?, order_date=?, customer_name=?, sales_amount=?, commission_rate=?, commission_amount=?, status=?, note=? WHERE id=?""",
                         (data.get("sales_person"), data.get("order_id"), data.get("order_date"), data.get("customer_name"),
                          sales_amt, rate, comm_amt, data.get("status", "已結算"), data.get("note"), sp_id))
        else:
            conn.execute("""INSERT INTO sales_performance (sales_person, order_id, order_date, customer_name, sales_amount, commission_rate, commission_amount, status, note, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                         (data.get("sales_person"), data.get("order_id"), data.get("order_date"), data.get("customer_name"),
                          sales_amt, rate, comm_amt, data.get("status", "已結算"), data.get("note"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "✔ 業務業績紀錄存檔成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/sales/performance/delete/<int:sp_id>", methods=["POST"])
def delete_sales_performance(sp_id):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM sales_performance WHERE id = ?", (sp_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "✔ 業務業績紀錄刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})


# --- 會計傳票 API ---
@app.route("/api/vouchers/list")
def get_vouchers():
    conn = get_db_connection()
    vouchers = conn.execute("SELECT * FROM vouchers ORDER BY voucher_date DESC").fetchall()
    result = []
    for v in vouchers:
        items = conn.execute("SELECT * FROM voucher_items WHERE voucher_no = ?", (v["voucher_no"],)).fetchall()
        result.append({**dict(v), "items": [dict(i) for i in items]})
    conn.close()
    return jsonify(result)

@app.route("/api/vouchers/save", methods=["POST"])
def save_voucher():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        v_no = data.get("voucher_no")
        items = data.get("items", [])
        
        total_dr = sum(float(i.get("debit", 0)) for i in items)
        total_cr = sum(float(i.get("credit", 0)) for i in items)
        if abs(total_dr - total_cr) > 0.01:
            return jsonify({"success": False, "message": f"❌ 借貸不平衡！借方總計 (${total_dr:,.2f}) 與貸方總計 (${total_cr:,.2f}) 不符。"})

        conn.execute("DELETE FROM vouchers WHERE voucher_no = ?", (v_no,))
        conn.execute("DELETE FROM voucher_items WHERE voucher_no = ?", (v_no,))

        conn.execute("INSERT INTO vouchers VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (v_no, data.get("voucher_date"), data.get("voucher_type"), data.get("summary"),
                      data.get("preparer"), total_dr, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        for it in items:
            conn.execute("INSERT INTO voucher_items (voucher_no, account_code, account_name, debit, credit) VALUES (?, ?, ?, ?, ?)",
                         (v_no, it.get("account_code"), it.get("account_name"), float(it.get("debit", 0)), float(it.get("credit", 0))))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "✔ 會計傳票存檔成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/vouchers/delete/<string:v_no>", methods=["POST"])
def delete_voucher(v_no):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM vouchers WHERE voucher_no = ?", (v_no,))
        conn.execute("DELETE FROM voucher_items WHERE voucher_no = ?", (v_no,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "✔ 傳票刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})


# --- 四大財務報表 API ---
@app.route("/api/finance/reports")
def get_finance_reports():
    conn = get_db_connection()
    # 範例計算：試算表與綜合損益表
    v_items = conn.execute("SELECT account_code, account_name, SUM(debit) as dr, SUM(credit) as cr FROM voucher_items GROUP BY account_code").fetchall()
    conn.close()
    return jsonify({"trial_balance": [dict(r) for r in v_items]})


# --- 應收 / 應付與其他 API ---
@app.route("/api/ar/search/<string:order_id>")
def search_ar_record(order_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM ar_records WHERE order_id = ? ORDER BY id ASC", (order_id.upper(),)).fetchall()
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
        is_edit = data.get("isEditSpecificRow")
        target_id = data.get("targetRowIndex")
        
        if is_edit and target_id:
            conn.execute("""UPDATE ar_records SET receive_amount=?, pay_type=?, check_no=?, check_due_date=?, receive_date=?, unpaid_amount=?, driver=?, driver_area=?, freight=?, old_item_fee=?, note=? WHERE id=?""",
                         (data.get("receiveAmount"), data.get("payType"), data.get("checkNo"), data.get("checkDueDate"),
                          data.get("receiveDate"), data.get("unpaidAmount"), data.get("driver"), data.get("driverArea"),
                          data.get("freight"), data.get("oldItemFee"), data.get("note"), target_id))
        else:
            conn.execute("""INSERT INTO ar_records (order_id, customer, sales_amount, deposit, receive_amount, pay_type, check_no, check_due_date, receive_date, unpaid_amount, driver, driver_area, freight, old_item_fee, keyin_user, note, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                         (data.get("orderId"), data.get("customer"), data.get("salesAmount"), data.get("deposit"),
                          data.get("receiveAmount"), data.get("payType"), data.get("checkNo"), data.get("checkDueDate"),
                          data.get("receiveDate"), data.get("unpaidAmount"), data.get("driver"), data.get("driverArea"),
                          data.get("freight"), data.get("oldItemFee"), data.get("keyinUser"), data.get("note"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "🎉 收款紀錄儲存成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/print/data")
def get_print_data():
    start = request.args.get("startDate", "")
    end = request.args.get("endDate", "")
    driver = request.args.get("driver", "ALL")
    conn = get_db_connection()
    
    query = "SELECT * FROM ar_records WHERE receive_date BETWEEN ? AND ?"
    params = [start, end]
    if driver != "ALL":
        query += " AND driver = ?"
        params.append(driver)
        
    rows = conn.execute(query, params).fetchall()
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
    invoices = conn.execute("SELECT * FROM ap_invoices").fetchall()
    data = []
    for inv in invoices:
        paid = conn.execute("SELECT SUM(pay_amount) as t FROM ap_payments WHERE inbound_no = ?", (inv["inbound_no"],)).fetchone()["t"] or 0
        unpaid = inv["total_amount"] - paid
        status = "已結清" if unpaid <= 0 else ("部分付款" if paid > 0 else "未付")
        data.append({**dict(inv), "paid_amount": paid, "unpaid_amount": unpaid, "status": status})
    conn.close()
    return jsonify({"found": True, "data": data})

@app.route("/api/ap/pay", methods=["POST"])
def save_payment():
    data = request.get_json()
    pay_no = "PAY" + datetime.now().strftime("%Y%m%d%H%M%S")
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO ap_payments VALUES (?,?,?,?,?,?,?,?)",
            (pay_no, data.get("pay_date"), data.get("inbound_no"), data.get("vendor_name"),
             data.get("pay_amount"), data.get("pay_method"), data.get("remarks"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route("/api/ar/summary")
def get_ar_summary():
    conn = get_db_connection()
    invoices = conn.execute("SELECT * FROM ar_invoices").fetchall()
    data = []
    for inv in invoices:
        collected = conn.execute("SELECT SUM(receive_amount) as t FROM ar_records WHERE order_id = ?", (inv["do_number"],)).fetchone()["t"] or 0
        uncollected = inv["total_amount"] - collected
        status = "已收清" if uncollected <= 0 else ("部分收款" if collected > 0 else "未收")
        data.append({
            "do_number": inv["do_number"], "delivery_date": inv["delivery_date"], "customer_display": inv["customer_display"],
            "total_amount": inv["total_amount"], "payment_term": inv["payment_term"], "due_date": inv["due_date"],
            "collected_amount": collected, "uncollected_amount": uncollected, "status": status
        })
    conn.close()
    return jsonify({"found": True, "data": data})

@app.route("/api/finance/summary")
def get_finance_summary():
    conn = get_db_connection()
    total_ap = conn.execute("SELECT SUM(total_amount) FROM ap_invoices").fetchone()[0] or 0
    paid_ap = conn.execute("SELECT SUM(pay_amount) FROM ap_payments").fetchone()[0] or 0
    total_ar = conn.execute("SELECT SUM(total_amount) FROM ar_invoices").fetchone()[0] or 0
    collected_ar = conn.execute("SELECT SUM(receive_amount) FROM ar_records").fetchone()[0] or 0
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
    suppliers_list = conn.execute("SELECT * FROM suppliers ORDER BY supplier_code").fetchall()
    conn.close()
    return render_template_string(SUPPLIERS_HTML, suppliers=suppliers_list, user_name=session.get("user_name"))

@app.route("/suppliers/add", methods=["POST"])
def add_supplier():
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO suppliers VALUES (?,?,?,?,?,?)",
            (request.form["supplier_code"], request.form["supplier_name"], request.form["tax_id"],
             request.form["contact_info"], request.form["payment_terms"], request.form["bank_info"]))
        conn.commit()
        conn.close()
    except: pass
    return redirect(url_for("suppliers_page"))

@app.route("/suppliers/edit/<string:code>", methods=["POST"])
def edit_supplier(code):
    try:
        conn = get_db_connection()
        conn.execute("UPDATE suppliers SET supplier_name=?, tax_id=?, contact_info=?, payment_terms=?, bank_info=? WHERE supplier_code=?",
            (request.form["supplier_name"], request.form["tax_id"], request.form["contact_info"],
             request.form["payment_terms"], request.form["bank_info"], code))
        conn.commit()
        conn.close()
    except: pass
    return redirect(url_for("suppliers_page"))


# ==================== 前端樣板 (HTML) ====================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <title>系統登入 - 珮藏居傢俱管理系統</title>
  <style>
    body { background: #0f172a; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: sans-serif; margin: 0; }
    .card { background: #fff; padding: 40px; border-radius: 12px; width: 100%; max-width: 400px; box-shadow: 0 20px 25px rgba(0,0,0,0.3); border-top: 4px solid #c59b27; }
    h2 { color: #0f172a; margin-bottom: 6px; font-size: 20px; }
    p { color: #64748b; font-size: 13px; margin-bottom: 24px; }
    .form-group { margin-bottom: 16px; display: flex; flex-direction: column; gap: 4px; }
    label { font-size: 12.5px; font-weight: 600; color: #334155; }
    input { padding: 8px 12px; border: 1px solid #94a3b8; border-radius: 4px; font-size: 14px; outline: none; }
    button { background: #c59b27; color: #fff; border: none; padding: 10px; width: 100%; font-weight: 700; border-radius: 6px; cursor: pointer; font-size: 14px; margin-top: 10px; }
  </style>
</head>
<body>
  <div class="card">
    <h2>珮藏居傢俱管理系統</h2>
    <p>請輸入授權帳號與密碼進行登入</p>
    <form method="POST">
      <div class="form-group"><label>帳號</label><input type="text" name="username" required></div>
      <div class="form-group"><label>密碼</label><input type="password" name="password" required></div>
      <button type="submit">登入系統</button>
    </form>
  </div>
</body>
</html>
"""

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
    :root { --primary: #0f172a; --brand: #c59b27; --border: #94a3b8; --text: #1e293b; }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background-color: #f1f5f9; color: var(--text); padding: 20px 20px 90px 20px; display: flex; justify-content: center; font-size: 13px; }
    .container { width: 100%; max-width: 1200px; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid var(--border); overflow: hidden; }
    .nav-tabs { background: #1e293b; padding: 10px 20px; display: flex; gap: 6px; border-bottom: 2px solid var(--brand); justify-content: space-between; align-items: center; flex-wrap: wrap; }
    .nav-tabs-left { display: flex; gap: 6px; flex-wrap: wrap; }
    .tab-btn { background: #334155; color: #cbd5e1; border: none; padding: 8px 12px; font-size: 13px; font-weight: 600; border-radius: 6px; cursor: pointer; transition: all 0.2s; }
    .tab-btn:hover { background: #475569; color: #fff; }
    .tab-btn.active { background: var(--brand); color: #fff; box-shadow: 0 2px 8px rgba(197, 155, 39, 0.4); }
    .btn-supplier-link { background: #0284c7; color: #fff; text-decoration: none; padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px; }
    .po-header { background: #0f172a; color: #fff; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; border-bottom: 4px solid var(--brand); }
    .po-title h1 { font-size: 22px; font-weight: 700; } .po-title div { font-size: 12px; color: #cbd5e1; margin-top: 2px; }
    .po-company-info { text-align: right; font-size: 12px; color: #e2e8f0; line-height: 1.5; }
    form { padding: 20px 30px 40px 30px; }
    .section-block { margin-bottom: 14px; }
    .section-title { font-size: 13.5px; font-weight: 700; color: var(--primary); margin-bottom: 8px; padding-bottom: 4px; border-bottom: 2px solid #cbd5e1; display: flex; align-items: center; gap: 6px; }
    .section-title::before { content: ""; width: 4px; height: 12px; background: var(--brand); border-radius: 2px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .form-group { display: flex; flex-direction: column; gap: 2px; }
    label { font-size: 12px; font-weight: 600; color: #334155; }
    .required::after { content: " *"; color: #dc2626; }
    input, select, textarea { padding: 6px 8px; font-size: 13px; border: 1px solid var(--border); border-radius: 4px; background: #fff; color: var(--text); outline: none; width: 100%; }
    .readonly { background: #f8fafc; color: #475569; font-weight: 600; }
    .items-table { width: 100%; border-collapse: collapse; margin-top: 4px; }
    .items-table th { background: #f1f5f9; color: #334155; font-size: 12px; padding: 6px; border: 1px solid var(--border); text-align: left; }
    .items-table td { padding: 5px 6px; border: 1px solid var(--border); vertical-align: middle; font-size: 12.5px; }
    .input-qty { text-align: center; } .input-price { text-align: right; } .input-total { text-align: right; }
    .item-remarks { border: none !important; background: transparent !important; font-size: 11.5px; color: #475569; padding: 2px !important; }
    .btn-add-item { background: #0f172a; color: #fff; border: none; padding: 5px 10px; font-size: 12px; font-weight: 600; border-radius: 4px; cursor: pointer; }
    .btn-del-item { background: #fee2e2; color: #dc2626; border: 1px solid #fecaca; padding: 2px 5px; border-radius: 4px; cursor: pointer; font-size: 11px; }
    .btn-query { background: #0f172a; color: #fff; border: none; padding: 6px 8px; font-size: 12px; font-weight: 600; border-radius: 4px; cursor: pointer; }
    .floating-action-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(255,255,255,0.95); backdrop-filter: blur(6px); border-top: 1px solid var(--border); padding: 10px 20px; display: flex; justify-content: center; gap: 8px; z-index: 1000; box-shadow: 0 -4px 20px rgba(0,0,0,0.1); }
    .btn-submit { background: linear-gradient(135deg, var(--brand) 0%, #a68120 100%); color: #fff; font-size: 13px; font-weight: 700; border: none; padding: 9px 14px; border-radius: 6px; cursor: pointer; }
    .btn-print { background: #475569; color: #fff; font-size: 13px; font-weight: 600; border: none; padding: 9px 12px; border-radius: 6px; cursor: pointer; }
    .btn-reset { background: #64748b; color: #fff; font-size: 13px; font-weight: 600; border: none; padding: 9px 12px; border-radius: 6px; cursor: pointer; }
    .btn-logout { background: #dc2626; color: #fff; font-size: 13px; font-weight: 600; border: none; padding: 9px 12px; border-radius: 6px; cursor: pointer; }
    .finance-group { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px; margin-bottom: 10px; }
    .inventory-group { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; margin-bottom: 10px; }
    .check-box { background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 8px; margin-top: 6px; }
    .unpaid-alert-card { background: #fff1f2; border: 1px solid #fda4af; border-radius: 8px; padding: 10px; margin-bottom: 10px; }
    .history-card { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; margin-top: 14px; }
    .driver-cash-summary { background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1.5px solid #10b981; border-radius: 8px; padding: 12px; margin-bottom: 14px; }
    .app-view { display: none; } .app-view.active { display: block; }
    @media print { .nav-tabs, .floating-action-bar, .btn-query, .btn-add-item, .btn-del-item, .no-print { display: none !important; } body { background-color: #fff; padding: 0; } .container { box-shadow: none; border: none; width: 100%; } form { padding: 10px; } }
  </style>
</head>
<body>

<div class="container" id="appContainer">
  <div class="nav-tabs">
    <div class="nav-tabs-left">
      <button type="button" class="tab-btn active" id="btnTabPurchase" onclick="switchTab('purchase')">📄 採購單</button>
      <button type="button" class="tab-btn" id="btnTabInbound" onclick="switchTab('inbound')">📦 進貨驗收</button>
      <button type="button" class="tab-btn" id="btnTabSo" onclick="switchTab('so')">🛒 客戶訂單</button>
      <button type="button" class="tab-btn" id="btnTabDelivery" onclick="switchTab('delivery')">🚚 銷貨出貨</button>
      <button type="button" class="tab-btn" id="btnTabInventory" onclick="switchTab('inventory')">📊 庫存管理</button>
      <button type="button" class="tab-btn" id="btnTabTrans" onclick="switchTab('trans')">📑 進退/銷退</button>
      <button type="button" class="tab-btn" id="btnTabSalesPerf" onclick="switchTab('salesPerf')">🏆 業務業績</button>
      <button type="button" class="tab-btn" id="btnTabHr" onclick="switchTab('hr')">👥 人事名冊</button>
      <button type="button" class="tab-btn" id="btnTabPayroll" onclick="switchTab('payroll')">💵 薪資系統</button>
      <button type="button" class="tab-btn" id="btnTabArPro" onclick="switchTab('arPro')">📥 專業應收</button>
      <button type="button" class="tab-btn" id="btnTabPrintCenter" onclick="switchTab('printCenter')">🖨️ 司機運費對帳</button>
      <button type="button" class="tab-btn" id="btnTabAp" onclick="switchTab('ap')">💰 應付帳款</button>
      <button type="button" class="tab-btn" id="btnTabAr" onclick="switchTab('ar')">💳 應收帳款</button>
      <button type="button" class="tab-btn" id="btnTabFinance" onclick="switchTab('finance')">📈 財務系統</button>
    </div>
    <div><a href="{{ url_for('suppliers_page') }}" class="btn-supplier-link"><i class="fa-solid fa-address-book"></i> 供應商管理</a></div>
  </div>

  <!-- 1. 採購單系統 -->
  <div id="purchaseView" class="app-view active">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>PURCHASE ORDER (採購訂單)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <form id="purchaseForm" onsubmit="handlePoSubmit(event)">
      <div class="section-block">
        <div class="section-title">一、 採購基本資料與查詢修改</div>
        <div class="grid-3">
          <div class="form-group"><label class="required">採購人員</label><input type="text" id="po_buyer_name" value="{{ user_name }}" required></div>
          <div class="form-group"><label class="required">採購編號</label><div style="display:flex; gap:4px;"><input type="text" id="po_no" required style="flex:1;"><button type="button" class="btn-query" onclick="queryPoRecord()">🔍 查詢</button></div></div>
          <div class="form-group"><label class="required">訂購日期</label><input type="date" id="po_order_date" required></div>
        </div>
        <div class="grid-2" style="margin-top:8px;">
          <div class="form-group"><label class="required">交貨日期</label><input type="date" id="po_delivery_date" required></div>
          <div class="form-group"><label class="required">Price Term</label><input type="text" id="po_price_term" required></div>
        </div>
        <div class="grid-3" style="margin-top:8px; border-top:1px dashed #cbd5e1; padding-top:8px;">
          <div class="form-group"><label class="required">廠商類別</label><select id="po_vendor_type" required><option value="" disabled selected hidden>請選擇</option><option value="國外廠商">國外廠商</option><option value="國內廠商">國內廠商</option></select></div>
          <div class="form-group"><label>廠商編號</label><input type="text" id="po_vendor_id" onblur="lookupVendorName('po')"></div>
          <div class="form-group"><label class="required">供應商名稱</label><input type="text" id="po_vendor_name" required></div>
        </div>
        <div class="grid-2" style="margin-top:8px;">
          <div class="form-group"><label class="required">幣別</label><select id="po_currency" required onchange="calculatePoTotals()"><option value="" disabled selected hidden>請選擇</option><option value="USD">USD</option><option value="NTD">NTD</option><option value="EUR">EUR</option><option value="RMB">RMB</option><option value="JPY">JPY</option></select></div>
          <div class="form-group"><label>供應商聯絡人</label><input type="text" id="po_vendor_contact"></div>
        </div>
      </div>
      <div class="section-block">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <div class="section-title" style="margin-bottom:0; border:none; padding:0;">二、 採購品項明細</div>
          <button type="button" class="btn-add-item" onclick="addPoItemRow()">＋ 新增品項</button>
        </div>
        <table class="items-table">
          <thead><tr><th style="width:16%;">型號</th><th style="width:20%;">品名</th><th style="width:14%;">規格</th><th style="width:12%;">顏色</th><th style="width:7%;">數量</th><th style="width:11%;">單價</th><th style="width:13%;">金額</th><th style="width:7%;" class="no-print">操作</th></tr></thead>
          <tbody id="poItemsBody"></tbody>
          <tfoot><tr><td colspan="6" style="text-align:right; font-weight:bold;">總金額：</td><td colspan="2" style="font-weight:bold;"><span id="poGrandTotalText">0.00</span> <span id="poCurrencyLabel"></span></td></tr></tfoot>
        </table>
      </div>
      <div class="section-block">
        <div class="section-title">三、 付款與裝運設定</div>
        <div class="grid-2">
          <div class="form-group"><label>訂金比例 (%) / 金額</label><div style="display:flex; gap:4px;"><input type="number" id="po_dep_pct" style="width:70px;" oninput="calculatePoTotals()"><input type="text" id="po_dep_amt" class="readonly" readonly style="flex:1;"></div></div>
          <div class="form-group"><label>尾款比例 (%) / 金額</label><div style="display:flex; gap:4px;"><input type="number" id="po_bal_pct" class="readonly" style="width:70px;" readonly><input type="text" id="po_bal_amt" class="readonly" readonly style="flex:1;"></div></div>
        </div>
        <div class="grid-2" style="margin-top:8px;">
          <div class="form-group"><label>Shipping Mark</label><input type="text" id="po_shipping_mark"></div>
          <div class="form-group"><label>Packing</label><input type="text" id="po_packing"></div>
        </div>
        <div class="form-group" style="margin-top:8px;"><label class="required">Bank Information</label><textarea id="po_bank_info" rows="2" required></textarea></div>
      </div>
    </form>
  </div>

  <!-- 2. 進貨驗收系統 -->
  <div id="inboundView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>GOODS RECEIPT (進貨驗收單)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <form id="inboundForm" onsubmit="handleInboundSubmit(event)">
      <div class="section-block">
        <div class="section-title">一、 進貨基本資料與採購單轉入</div>
        <div class="grid-3">
          <div class="form-group"><label class="required">收貨人員</label><input type="text" id="in_receiver_name" value="{{ user_name }}" required></div>
          <div class="form-group"><label class="required">進貨單號</label><div style="display:flex; gap:4px;"><input type="text" id="in_no" required style="flex:1;"><button type="button" class="btn-query" onclick="queryInboundRecord()">🔍 查詢</button></div></div>
          <div class="form-group"><label class="required">進貨日期</label><input type="date" id="in_date" required onchange="autoFillMonth()"></div>
        </div>
        <div class="grid-3" style="margin-top:8px;">
          <div class="form-group"><label class="required">歸屬月份</label><input type="text" id="in_month" required></div>
          <div class="form-group"><label class="required">採購編號</label><input type="text" id="in_po_no" required></div>
          <div class="form-group"><label>廠商編號</label><div style="display:flex; gap:4px;"><input type="text" id="in_vendor_id" onblur="lookupVendorName('in')" style="flex:1;"><button type="button" class="btn-query" onclick="importFromPo()">📥 轉入PO</button></div></div>
        </div>
        <div class="grid-2" style="margin-top:8px;"><div class="form-group"><label class="required">供應商名稱</label><input type="text" id="in_vendor_name" class="readonly" readonly required></div></div>
      </div>
      <div class="section-block">
        <div class="section-title">二、 進貨驗收明細與入庫倉庫</div>
        <table class="items-table">
          <thead><tr><th style="width:13%;">型號</th><th style="width:17%;">品名</th><th style="width:12%;">規格</th><th style="width:10%;">顏色</th><th style="width:12%;">入庫倉庫</th><th style="width:6%;">訂購</th><th style="width:7%;">實際</th><th style="width:11%;">單價</th><th style="width:12%;">金額</th></tr></thead>
          <tbody id="inItemsBody"></tbody>
          <tfoot><tr><td colspan="8" style="text-align:right; font-weight:bold;">總進貨金額：</td><td style="font-weight:bold;"><span id="inGrandTotalText">0.00</span></td></tr></tfoot>
        </table>
      </div>
    </form>
  </div>

  <!-- 3. 客戶訂單系統 -->
  <div id="soView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>SALES ORDER (客戶訂單)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <form id="soForm" onsubmit="handleSoSubmit(event)">
      <div class="section-block">
        <div class="section-title">一、 客戶訂單基本資料</div>
        <div class="grid-3">
          <div class="form-group"><label class="required">業務人員</label><input type="text" id="so_sales_person" value="{{ user_name }}" required></div>
          <div class="form-group"><label class="required">訂單編號</label><div style="display:flex; gap:4px;"><input type="text" id="so_no" required style="flex:1;"><button type="button" class="btn-query" onclick="querySoRecord()">🔍 查詢</button></div></div>
          <div class="form-group"><label class="required">訂單日期</label><input type="date" id="so_order_date" required></div>
        </div>
        <div class="grid-3" style="margin-top:8px;">
          <div class="form-group"><label>客戶編號</label><input type="text" id="so_customer_code" onblur="lookupCustomerName()"></div>
          <div class="form-group"><label class="required">客戶名稱</label><input type="text" id="so_customer_name" required></div>
          <div class="form-group"><label class="required">幣別</label><select id="so_currency" required><option value="NTD" selected>NTD</option><option value="USD">USD</option></select></div>
        </div>
      </div>
      <div class="section-block">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <div class="section-title" style="margin-bottom:0; border:none; padding:0;">二、 訂單品項明細</div>
          <button type="button" class="btn-add-item" onclick="addSoItemRow()">＋ 新增品項</button>
        </div>
        <table class="items-table">
          <thead><tr><th style="width:16%;">型號</th><th style="width:20%;">品名</th><th style="width:14%;">規格</th><th style="width:12%;">顏色</th><th style="width:7%;">數量</th><th style="width:11%;">單價</th><th style="width:13%;">金額</th><th style="width:7%;" class="no-print">操作</th></tr></thead>
          <tbody id="soItemsBody"></tbody>
          <tfoot><tr><td colspan="6" style="text-align:right; font-weight:bold;">總訂單金額：</td><td colspan="2" style="font-weight:bold;"><span id="soGrandTotalText">0.00</span></td></tr></tfoot>
        </table>
      </div>
      <div class="section-block"><div class="form-group"><label>備註說明</label><textarea id="so_remark" rows="2"></textarea></div></div>
    </form>
  </div>

  <!-- 4. 銷貨出貨系統 (含送貨司機與自訂運費欄位) -->
  <div id="deliveryView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>DELIVERY ORDER (銷貨出貨單)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <form id="deliveryForm" onsubmit="handleDeliverySubmit(event)">
      <div class="section-block">
        <div class="section-title">一、 出貨基本資料與訂單轉入</div>
        <div class="grid-3">
          <div class="form-group"><label class="required">出貨人員</label><input type="text" id="do_shipper_name" value="{{ user_name }}" required></div>
          <div class="form-group"><label class="required">出貨單號</label><div style="display:flex; gap:4px;"><input type="text" id="do_number" required style="flex:1;"><button type="button" class="btn-query" onclick="queryDeliveryRecord()">🔍 查詢</button></div></div>
          <div class="form-group"><label class="required">出貨日期</label><input type="date" id="do_date" required></div>
        </div>
        <div class="grid-3" style="margin-top:8px;">
          <div class="form-group"><label class="required">客戶訂單編號 (SO)</label><div style="display:flex; gap:4px;"><input type="text" id="do_so_no" required style="flex:1;"><button type="button" class="btn-query" onclick="importFromSo()">📥 轉入SO</button></div></div>
          <div class="form-group"><label>客戶編號</label><input type="text" id="do_customer_code"></div>
          <div class="form-group"><label class="required">客戶名稱</label><input type="text" id="do_customer_name" class="readonly" readonly required></div>
        </div>
        <div class="grid-2" style="margin-top:8px;">
          <div class="form-group">
            <label class="required">送貨司機 / 倉別</label>
            <select id="do_driver" class="form-select form-select-sm" required>
              <option value="大蔡" selected>大蔡</option>
              <option value="大生">大生</option>
              <option value="南倉">南倉</option>
            </select>
          </div>
          <div class="form-group">
            <label class="required">運費金額 ($)</label>
            <input type="number" id="do_manual_freight" class="form-control form-control-sm" value="0" min="0" required>
          </div>
        </div>
      </div>
      <div class="section-block">
        <div class="section-title">二、 出貨明細與出貨倉庫扣庫存</div>
        <table class="items-table">
          <thead><tr><th style="width:15%;">型號</th><th style="width:20%;">品名</th><th style="width:13%;">規格</th><th style="width:11%;">顏色</th><th style="width:13%;">出貨倉庫</th><th style="width:7%;">數量</th><th style="width:10%;">單價</th><th style="width:11%;">金額</th></tr></thead>
          <tbody id="doItemsBody"></tbody>
          <tfoot><tr><td colspan="7" style="text-align:right; font-weight:bold;">總出貨金額：</td><td style="font-weight:bold;"><span id="doGrandTotalText">0.00</span></td></tr></tfoot>
        </table>
      </div>
    </form>
  </div>

  <!-- 5. 庫存管理系統 -->
  <div id="inventoryView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>INVENTORY MANAGEMENT (庫存主檔與維護)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <div style="padding:20px 30px;">
      <div class="card p-3 mb-4 bg-light border">
        <h6 class="fw-bold text-primary mb-2">📦 商品建檔與維護（新增或修改）</h6>
        <form id="inventoryForm" onsubmit="handleInventorySave(event)">
          <div class="row g-2">
            <div class="col-3"><label class="form-label">商品型號 (SKU) *</label><input type="text" id="invSku" class="form-control form-control-sm" placeholder="例: P001" required></div>
            <div class="col-3"><label class="form-label">商品名稱 *</label><input type="text" id="invName" class="form-control form-control-sm" placeholder="商品名稱" required></div>
            <div class="col-3"><label class="form-label">分類</label><input type="text" id="invCategory" class="form-control form-control-sm" placeholder="類別"></div>
            <div class="col-3"><label class="form-label">進貨成本 ($)</label><input type="number" id="invCost" class="form-control form-control-sm" value="0" step="0.01"></div>
          </div>
          <div class="row g-2 mt-2">
            <div class="col-3"><label class="form-label">建議售價 ($)</label><input type="number" id="invPrice" class="form-control form-control-sm" value="0" step="0.01"></div>
            <div class="col-3"><label class="form-label">現有庫存量</label><input type="number" id="invStock" class="form-control form-control-sm" value="0"></div>
            <div class="col-3"><label class="form-label">安全庫存</label><input type="number" id="invSafety" class="form-control form-control-sm" value="10"></div>
            <div class="col-3 d-flex align-items-end gap-1">
              <button type="submit" class="btn btn-success btn-sm w-100 fw-bold">💾 儲存商品</button>
              <button type="button" class="btn btn-secondary btn-sm" onclick="resetInvForm()">重設</button>
            </div>
          </div>
        </form>
      </div>

      <div class="d-flex justify-content-between align-items-center mb-2">
        <h6 class="fw-bold text-dark mb-0">📊 現有商品與庫存清單</h6>
        <div class="d-flex gap-2">
          <input type="text" id="invSearchBox" class="form-control form-control-sm" placeholder="搜尋型號或名稱..." oninput="filterInventory()">
          <button type="button" class="btn-query btn-sm" onclick="loadInventory()">🔄 重新整理</button>
        </div>
      </div>
      <table class="items-table">
        <thead><tr><th>型號/SKU</th><th>商品名稱</th><th>分類</th><th>成本</th><th>售價</th><th>庫存量</th><th>安全庫存</th><th class="no-print text-center">操作</th></tr></thead>
        <tbody id="inventoryTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 6. 進退/銷退單據系統 -->
  <div id="transView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>INVENTORY TRANSACTION (進退/銷退單據)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <form id="transForm" onsubmit="event.preventDefault(); submitTransaction();" style="padding:20px 30px;">
      <div class="inventory-group">
        <span class="fw-bold text-success d-block mb-2">📑 建立進銷存交易單據 (含訂單編號與客戶資訊)：</span>
        <div class="row g-2 mb-2">
          <div class="col-6">
            <label class="form-label">單據類型 *</label>
            <select id="transType" class="form-select form-select-sm fw-bold text-primary">
              <option value="銷貨" selected>📦 銷貨 (自動扣庫存 & 結轉銷貨成本)</option>
              <option value="進貨">📥 進貨 (增加庫存)</option>
              <option value="銷貨退回">↩️ 銷貨退回 (商品加回庫存)</option>
              <option value="進貨退回">🔙 進貨退回 (減少庫存)</option>
            </select>
          </div>
          <div class="col-6"><label class="form-label">單據日期 *</label><input type="date" id="transDate" class="form-control form-control-sm" required></div>
        </div>
        <div class="row g-2 mb-2">
          <div class="col-4"><label class="form-label">訂單編號</label><input type="text" id="transOrderId" class="form-control form-control-sm" placeholder="例: 4110213"></div>
          <div class="col-4"><label class="form-label">客戶代號</label><input type="text" id="transCustCode" class="form-control form-control-sm" placeholder="例: C001"></div>
          <div class="col-4"><label class="form-label">客戶名稱 *</label><input type="text" id="transCustName" class="form-control form-control-sm" placeholder="客戶抬頭" required></div>
        </div>
        <div class="row g-2 mb-2">
          <div class="col-6"><label class="form-label">選擇商品 (SKU) *</label><select id="transSkuSelect" class="form-select form-select-sm" onchange="onSkuSelected()"></select></div>
          <div class="col-6"><label class="form-label">商品型號 (SKU碼)</label><input type="text" id="transSku" class="form-control form-control-sm bg-white" readonly required></div>
        </div>
        <div class="row g-2 mb-2">
          <div class="col-4"><label class="form-label">交易數量 *</label><input type="number" id="transQty" class="form-control form-control-sm fw-bold" value="1" min="1" required></div>
          <div class="col-4"><label class="form-label">單價 ($) *</label><input type="number" id="transPrice" class="form-control form-control-sm fw-bold" value="0" required></div>
          <div class="col-4"><label class="form-label">KEY IN 人員</label><input type="text" id="transKeyin" class="form-control form-control-sm bg-white" value="{{ user_name }}" readonly></div>
        </div>
      </div>
      <button type="submit" class="btn btn-success btn-sm w-100 fw-bold py-2">💾 確認並送出單據</button>
    </form>
  </div>

  <!-- 7. 業務業績統計系統 (支援輸入、查詢、區間列印) -->
  <div id="salesPerfView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>SALES PERFORMANCE (業務人員業績與獎金統計)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <div style="padding:20px 30px;">
      <div class="card p-3 mb-4 bg-light border no-print">
        <h6 class="fw-bold text-primary mb-2">🏆 手動登錄或維護業務業績</h6>
        <form id="salesPerfForm" onsubmit="handleSalesPerfSave(event)">
          <input type="hidden" id="perfRecordId">
          <div class="row g-2">
            <div class="col-3"><label class="form-label">業務人員 *</label><input type="text" id="perfSalesPerson" class="form-control form-control-sm" placeholder="業務姓名" required></div>
            <div class="col-3"><label class="form-label">訂單編號</label><input type="text" id="perfOrderId" class="form-control form-control-sm" placeholder="訂單編號"></div>
            <div class="col-3"><label class="form-label">成交日期 *</label><input type="date" id="perfOrderDate" class="form-control form-control-sm" required></div>
            <div class="col-3"><label class="form-label">客戶名稱 *</label><input type="text" id="perfCustomer" class="form-control form-control-sm" placeholder="客戶名稱" required></div>
          </div>
          <div class="row g-2 mt-2">
            <div class="col-4"><label class="form-label">業績金額 ($) *</label><input type="number" id="perfSalesAmount" class="form-control form-control-sm" value="0" step="0.01" required></div>
            <div class="col-4"><label class="form-label">抽成比例 (例如 0.05)</label><input type="number" id="perfRate" class="form-control form-control-sm" value="0.05" step="0.01"></div>
            <div class="col-4 d-flex align-items-end gap-1">
              <button type="submit" id="perfSubmitBtn" class="btn btn-success btn-sm w-100 fw-bold">💾 儲存業績</button>
              <button type="button" class="btn btn-secondary btn-sm" onclick="resetSalesPerfForm()">重設</button>
            </div>
          </div>
        </form>
      </div>

      <div class="section-block no-print" style="background:#f8fafc; padding:15px; border-radius:6px; border:1px solid var(--border); margin-bottom:15px;">
        <div class="grid-3" style="align-items:end;">
          <div class="form-group"><label>依業務人員篩選</label><input type="text" id="perfFilterPerson" class="form-control form-control-sm" placeholder="留空代表全部"></div>
          <div class="form-group"><label>區間 (起)</label><input type="date" id="perfFilterStart" class="form-control form-control-sm"></div>
          <div class="form-group"><label>區間 (迄)</label><input type="date" id="perfFilterEnd" class="form-control form-control-sm"></div>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:10px;">
          <button type="button" class="btn-reset" onclick="loadSalesPerformance()" style="padding:5px 10px; font-size:12px;">查詢篩選</button>
          <button type="button" class="btn-print" onclick="window.print()" style="padding:5px 12px; font-size:12px;">🖨️ 列印業績報表</button>
        </div>
      </div>

      <table class="items-table">
        <thead><tr><th>業務人員</th><th>訂單編號</th><th>成交日期</th><th>客戶名稱</th><th>業績金額</th><th>抽成比例</th><th>預估抽成獎金</th><th>狀態</th><th class="no-print text-center">操作</th></tr></thead>
        <tbody id="salesPerfTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 8. 新進人員/人事名冊管理系統 (HR) -->
  <div id="hrView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>HR MANAGEMENT (員工與新進人員名冊)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <div style="padding:20px 30px;">
      <div class="card p-3 mb-4 bg-light border">
        <h6 class="fw-bold text-primary mb-2">👤 員工建檔與維護（新增或修改）</h6>
        <form id="hrForm" onsubmit="handleEmpSave(event)">
          <div class="row g-2">
            <div class="col-3"><label class="form-label">員工編號 *</label><input type="text" id="empId" class="form-control form-control-sm" placeholder="例: EMP03" required></div>
            <div class="col-3"><label class="form-label">員工姓名 *</label><input type="text" id="empName" class="form-control form-control-sm" placeholder="姓名" required></div>
            <div class="col-3"><label class="form-label">部門</label><input type="text" id="empDept" class="form-control form-control-sm" placeholder="部門"></div>
            <div class="col-3"><label class="form-label">職稱</label><input type="text" id="empTitle" class="form-control form-control-sm" placeholder="職稱"></div>
          </div>
          <div class="row g-2 mt-2">
            <div class="col-3"><label class="form-label">聯絡電話</label><input type="text" id="empPhone" class="form-control form-control-sm" placeholder="電話"></div>
            <div class="col-3"><label class="form-label">到職日</label><input type="date" id="empHireDate" class="form-control form-control-sm"></div>
            <div class="col-3"><label class="form-label">基本底薪 ($)</label><input type="number" id="empSalary" class="form-control form-control-sm" value="35000" step="100"></div>
            <div class="col-3"><label class="form-label">狀態</label><select id="empStatus" class="form-select form-select-sm"><option value="在職" selected>在職</option><option value="離職">離職</option></select></div>
          </div>
          <div class="mt-2 d-flex justify-content-end gap-1">
            <button type="submit" class="btn btn-success btn-sm fw-bold px-4">💾 儲存員工</button>
            <button type="button" class="btn btn-secondary btn-sm" onclick="resetEmpForm()">重設</button>
          </div>
        </form>
      </div>

      <div class="d-flex justify-content-between align-items-center mb-2">
        <h6 class="fw-bold text-dark mb-0">📋 員工名冊清單</h6>
        <button class="btn-query btn-sm" onclick="loadEmployees()">🔄 重新整理</button>
      </div>
      <table class="items-table">
        <thead><tr><th>員工編號</th><th>姓名</th><th>部門</th><th>職稱</th><th>電話</th><th>到職日</th><th>底薪</th><th>狀態</th><th class="no-print text-center">操作</th></tr></thead>
        <tbody id="empTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 9. 薪資發放系統 (Payroll) -->
  <div id="payrollView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>PAYROLL SYSTEM (員工薪資與發放管理)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <div style="padding:20px 30px;">
      <div class="card p-3 mb-4 bg-light border">
        <h6 class="fw-bold text-primary mb-2">💵 薪資登錄與發放維護</h6>
        <form id="payrollForm" onsubmit="handlePayrollSave(event)">
          <input type="hidden" id="payrollRecordId">
          <div class="row g-2">
            <div class="col-4">
              <label class="form-label">選擇員工 *</label>
              <select id="payEmpSelect" class="form-select form-select-sm" onchange="onEmpSelectedForPay()" required></select>
            </div>
            <div class="col-4"><label class="form-label">員工編號</label><input type="text" id="payEmpId" class="form-control form-control-sm bg-white" readonly></div>
            <div class="col-4"><label class="form-label">薪資月份 (YYYY-MM) *</label><input type="month" id="payMonth" class="form-control form-control-sm" required></div>
          </div>
          
          <div class="row g-2 mt-2">
            <div class="col-4"><label class="form-label">基本底薪 ($)</label><input type="number" id="payBase" class="form-control form-control-sm" value="0" oninput="calcPayrollNet()"></div>
            <div class="col-4"><label class="form-label text-success">職務/全勤津貼 ($)</label><input type="number" id="payAllowance" class="form-control form-control-sm" value="0" oninput="calcPayrollNet()"></div>
            <div class="col-4"><label class="form-label text-success">加班費 ($)</label><input type="number" id="payOvertime" class="form-control form-control-sm" value="0" oninput="calcPayrollNet()"></div>
          </div>

          <div class="row g-2 mt-2">
            <div class="col-4"><label class="form-label text-danger">請假/缺勤扣款 ($)</label><input type="number" id="payLeaveDed" class="form-control form-control-sm text-danger" value="0" oninput="calcPayrollNet()"></div>
            <div class="col-4"><label class="form-label text-danger">員購扣款 ($)</label><input type="number" id="payPurDed" class="form-control form-control-sm text-danger" value="0" oninput="calcPayrollNet()"></div>
            <div class="col-4"><label class="form-label text-danger">勞健保自付額 ($)</label><input type="number" id="payInsDed" class="form-control form-control-sm text-danger" value="0" oninput="calcPayrollNet()"></div>
          </div>

          <div class="row g-2 mt-2 align-items-center bg-white p-2 border rounded">
            <div class="col-6"><label class="form-label text-primary fw-bold fs-6">💰 實際發放金額 ($)：</label></div>
            <div class="col-6"><input type="number" id="payNet" class="form-control form-control-sm fw-bold text-success fs-5 bg-light" readonly></div>
          </div>

          <div class="row g-2 mt-2">
            <div class="col-4"><label class="form-label">發放日期 *</label><input type="date" id="payDate" class="form-control form-control-sm" required></div>
            <div class="col-8"><label class="form-label">備註說明</label><input type="text" id="payNote" class="form-control form-control-sm" placeholder="備註..."></div>
          </div>
          <div class="mt-2 d-flex justify-content-end gap-1">
            <button type="submit" id="payrollSubmitBtn" class="btn btn-success btn-sm fw-bold px-4">💾 儲存薪資紀錄</button>
            <button type="button" class="btn btn-secondary btn-sm" onclick="resetPayrollForm()">重設</button>
          </div>
        </form>
      </div>

      <div class="d-flex justify-content-between align-items-center mb-2">
        <h6 class="fw-bold text-dark mb-0">📜 歷年薪資發放紀錄查詢與維護</h6>
        <button class="btn-query btn-sm" onclick="loadPayroll()">🔄 重新整理</button>
      </div>
      <table class="items-table">
        <thead><tr><th>月份</th><th>編號</th><th>姓名</th><th>底薪</th><th>津貼</th><th>加班</th><th>請假扣款</th><th>員購扣</th><th>勞健保</th><th>實發金額</th><th>發放日</th><th class="no-print text-center">操作</th></tr></thead>
        <tbody id="payrollTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 10. 專業應收帳款管理 (AR Pro) -->
  <div id="arProView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>ACCOUNTS RECEIVABLE PRO (出納收款與對帳)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <div style="padding:20px 30px;">
      <div class="input-group input-group-sm mb-3">
        <input type="text" id="arSearchId" class="form-control" placeholder="輸入訂單編號查歷史明細或新增再次收款（如 4110213）">
        <button class="btn btn-outline-primary fw-bold" type="button" onclick="searchAR()">🔍 查詢單據歷史</button>
      </div>

      <div id="arUnpaidBanner" class="unpaid-alert-card" style="display:none;"></div>

      <form id="arForm" onsubmit="event.preventDefault(); submitAR();" style="padding:0;">
        <div class="row g-2 mb-2">
          <div class="col-6"><label class="form-label">訂單編號 *</label><input type="text" id="arOrderId" class="form-control form-control-sm" required></div>
          <div class="col-6"><label class="form-label">客戶名稱 *</label><input type="text" id="arCustomer" class="form-control form-control-sm" required></div>
        </div>

        <div class="finance-group">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <span class="fw-bold text-success">💰 本次收款資訊：</span>
            <span class="text-muted small">累計已收總額：<strong id="dispTotalCollectedText" class="text-dark">$0</strong></span>
          </div>
          <div class="row g-2">
            <div class="col-3"><label class="form-label">總金額 ($)</label><input type="number" id="arSalesAmount" class="form-control form-control-sm" value="0" oninput="calcAR()"></div>
            <div class="col-3"><label class="form-label">已收訂金 ($)</label><input type="number" id="arDeposit" class="form-control form-control-sm" value="0" oninput="calcAR()"></div>
            <div class="col-3"><label class="form-label text-primary fw-bold">本次收款 ($) *</label><input type="number" id="arReceiveAmount" class="form-control form-control-sm border-primary" value="0" oninput="calcAR()" required></div>
            <div class="col-3"><label class="form-label text-danger fw-bold">剩餘未收 ($)</label><input type="number" id="arUnpaidAmount" class="form-control form-control-sm bg-light text-danger fw-bold" value="0" readonly></div>
          </div>

          <div class="row g-2 mt-2">
            <div class="col-6">
              <label class="form-label">收款方式 *</label>
              <select id="arPayType" class="form-select form-select-sm" onchange="toggleARCheckFields()">
                <option value="現金" selected>💵 現金 (司機代收)</option><option value="匯款">🏦 匯款</option><option value="刷卡">💳 刷卡</option><option value="應收票據">📑 應收票據</option>
              </select>
            </div>
            <div class="col-6"><label class="form-label">收款日期 *</label><input type="date" id="arReceiveDate" class="form-control form-control-sm" required></div>
          </div>

          <div id="boxARCheck" class="check-box mt-2" style="display:none;">
            <div class="row g-2">
              <div class="col-6"><label class="form-label text-danger">支票號碼 *</label><input type="text" id="arCheckNo" class="form-control form-control-sm"></div>
              <div class="col-6"><label class="form-label text-danger">到期日 *</label><input type="date" id="arCheckDueDate" class="form-control form-control-sm"></div>
            </div>
          </div>
        </div>

        <div class="p-2 border rounded bg-light mb-2">
          <div class="row g-2">
            <div class="col-4">
              <label class="form-label">運送人員/倉別</label>
              <select id="arDriver" class="form-select form-select-sm" onchange="updateDriverLogic()">
                <option value="大蔡">大蔡</option><option value="大生">大生</option><option value="南倉">南倉</option>
              </select>
            </div>
            <div class="col-4"><label class="form-label">送貨地區</label><select id="arDriverArea" class="form-select form-select-sm" onchange="calcFreight()"></select></div>
            <div class="col-4"><label class="form-label text-danger">運費 ($)</label><input type="number" id="arFreight" class="form-control form-control-sm" value="0"></div>
          </div>
          <div class="row g-2 mt-1">
            <div class="col-6"><label class="form-label">舊貨回收費 ($)</label><input type="number" id="arOldItemFee" class="form-control form-control-sm" value="0"></div>
            <div class="col-6"><label class="form-label">KEY IN 人員</label><input type="text" id="arKeyinUser" class="form-control form-control-sm bg-white" value="{{ user_name }}" readonly></div>
          </div>
        </div>

        <div class="mb-3"><label class="form-label">備註說明</label><input type="text" id="arNote" class="form-control form-control-sm"></div>

        <div id="arHistoryBox" class="history-card" style="display:none;">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <h6 class="fw-bold text-dark mb-0">📜 該訂單歷史獨立收款清單：</h6><span class="badge bg-secondary" id="arHistoryCountBadge">0 筆</span>
          </div>
          <div class="table-responsive bg-white rounded border">
            <table class="table table-sm table-hover text-center align-middle mb-0" style="font-size:11.5px;">
              <thead class="table-light"><tr><th>收款日期</th><th>方式</th><th>金額</th><th>票號/到期日</th><th>經辦</th><th>備註</th><th>操作</th></tr></thead>
              <tbody id="arHistoryListBody"></tbody>
            </table>
          </div>
        </div>

        <div class="mt-3">
          <button type="submit" id="arSaveBtn" class="btn btn-success btn-sm w-100 fw-bold py-2">💾 儲存並新增一筆收款紀錄</button>
          <button type="button" id="arCancelEditBtn" class="btn btn-outline-secondary btn-sm w-100 mt-1" style="display:none;" onclick="cancelRowEdit()">❌ 取消修改</button>
        </div>
      </form>
    </div>
  </div>

  <!-- 11. 司機運費對帳系統 (原出納對帳單) -->
  <div id="printCenterView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>DRIVER FREIGHT RECONCILIATION (司機運費對帳系統)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <div style="padding:20px 30px;">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3 no-print">
        <div class="d-flex align-items-center gap-2 flex-wrap">
          <select id="printDriverFilter" class="form-select form-select-sm" style="width: 150px;">
            <option value="ALL">🚚 全部司機/倉別</option><option value="大蔡">大蔡</option><option value="大生">大生</option><option value="南倉">南倉</option>
          </select>
          <div class="d-flex align-items-center gap-1">
            <input type="date" id="printStartDate" class="form-control form-control-sm" style="width: 130px;">
            <span>~</span>
            <input type="date" id="printEndDate" class="form-control form-control-sm" style="width: 130px;">
          </div>
          <button class="btn btn-primary btn-sm fw-bold px-3" onclick="loadPrintData()">載入對帳單</button>
        </div>
        <button class="btn btn-outline-dark btn-sm fw-bold" onclick="window.print()">🖨️ 列印 / 存為 PDF</button>
      </div>
      <div id="printContainer" class="p-3 border rounded bg-white" style="min-height: 250px;">
        <div class="text-muted text-center py-5">請選取起迄日期並點擊「載入對帳單」以預覽並列印</div>
      </div>
    </div>
  </div>

  <!-- 12. 應付帳款系統 (支援單家廠商、月份、區間查詢與列印) -->
  <div id="apView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>ACCOUNTS PAYABLE (應付帳款管理)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <div style="padding:20px 30px;">
      <div class="section-block no-print" style="background:#f8fafc; padding:15px; border-radius:6px; border:1px solid var(--border); margin-bottom:15px;">
        <div class="grid-3" style="align-items:end;">
          <div class="form-group"><label>依單家廠商名稱或代號篩選</label><input type="text" id="ap_filter_vendor" class="form-control form-control-sm" placeholder="輸入廠商名稱/代號..." oninput="loadAP()"></div>
          <div class="form-group"><label>依歸屬月份 (YYYY-MM)</label><input type="month" id="ap_filter_month" oninput="loadAP()"></div>
          <div class="form-group"><label>日期區間 (起 ~ 迄)</label><div style="display:flex; gap:4px;"><input type="date" id="ap_filter_start" onchange="loadAP()"><span>~</span><input type="date" id="ap_filter_end" onchange="loadAP()"></div></div>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:10px;">
          <button type="button" class="btn-reset" onclick="resetApFilter()" style="padding:5px 10px; font-size:12px;">清除篩選</button>
          <button type="button" class="btn-print" onclick="window.print()" style="padding:5px 12px; font-size:12px;">🖨️ 列印應付報表</button>
        </div>
      </div>
      <table class="items-table">
        <thead><tr><th>進貨單號</th><th>進貨日期</th><th>供應商</th><th>應付總額</th><th>付款條件</th><th>預計付款日</th><th>已付金額</th><th>未付餘額</th><th>狀態</th><th class="no-print">操作</th></tr></thead>
        <tbody id="apTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 13. 應收帳款系統 (支援單家客戶、月份、區間查詢與列印) -->
  <div id="arView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>ACCOUNTS RECEIVABLE (應收帳款管理)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <div style="padding:20px 30px;">
      <div class="section-block no-print" style="background:#f8fafc; padding:15px; border-radius:6px; border:1px solid var(--border); margin-bottom:15px;">
        <div class="grid-3" style="align-items:end;">
          <div class="form-group"><label>依單家客戶名稱或代號篩選</label><input type="text" id="ar_filter_customer" class="form-control form-control-sm" placeholder="輸入客戶名稱/代號..." oninput="loadAR()"></div>
          <div class="form-group"><label>依歸屬月份 (YYYY-MM)</label><input type="month" id="ar_filter_month" oninput="loadAR()"></div>
          <div class="form-group"><label>日期區間 (起 ~ 迄)</label><div style="display:flex; gap:4px;"><input type="date" id="ar_filter_start" onchange="loadAR()"><span>~</span><input type="date" id="ar_filter_end" onchange="loadAR()"></div></div>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:10px;">
          <button type="button" class="btn-reset" onclick="resetArFilter()" style="padding:5px 10px; font-size:12px;">清除篩選</button>
          <button type="button" class="btn-print" onclick="window.print()" style="padding:5px 12px; font-size:12px;">🖨️ 列印應收報表</button>
        </div>
      </div>
      <table class="items-table">
        <thead><tr><th>出貨單號</th><th>出貨日期</th><th>客戶名稱</th><th>應收總額</th><th>付款條件</th><th>預計收款日</th><th>已收金額</th><th>未收餘額</th><th>狀態</th></tr></thead>
        <tbody id="arTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 14. 財務系統 (含傳票與4大財務報表) -->
  <div id="financeView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>FINANCIAL DASHBOARD & VOUCHERS (會計傳票與四大財務報表)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div><div>地址：新北市土城區中央路3段130-6號</div><div>電話：02-22691071</div></div>
    </div>
    <div style="padding:25px 30px;">
      <div class="card p-3 mb-4 bg-light border no-print">
        <h6 class="fw-bold text-primary mb-2">📑 會計傳票登錄（應收票據、應付票據、現金/銀行收支傳票）</h6>
        <form id="voucherForm" onsubmit="handleVoucherSave(event)">
          <div class="row g-2">
            <div class="col-3"><label class="form-label">傳票編號 *</label><input type="text" id="vNo" class="form-control form-control-sm" placeholder="例: V20260901" required></div>
            <div class="col-3"><label class="form-label">傳票日期 *</label><input type="date" id="vDate" class="form-control form-control-sm" required></div>
            <div class="col-3">
              <label class="form-label">傳票類型 *</label>
              <select id="vType" class="form-select form-select-sm">
                <option value="現金收入傳票">現金收入傳票</option>
                <option value="現金支出傳票">現金支出傳票</option>
                <option value="銀行收支傳票">銀行收支傳票</option>
                <option value="轉帳傳票" selected>轉帳傳票 (含票據)</option>
              </select>
            </div>
            <div class="col-3"><label class="form-label">製表人</label><input type="text" id="vPreparer" class="form-control form-control-sm bg-white" value="{{ user_name }}" readonly></div>
          </div>
          <div class="row g-2 mt-2">
            <div class="col-12"><label class="form-label">摘要說明 *</label><input type="text" id="vSummary" class="form-control form-control-sm" placeholder="例如：收回應收票據 / 支付租金..." required></div>
          </div>

          <div class="mt-3">
            <label class="fw-bold text-dark mb-1">傳票會計分錄明細（借貸平衡）：</label>
            <table class="table table-sm table-bordered bg-white" id="voucherItemsTable">
              <thead><tr><th>會計科目代號</th><th>會計科目名稱</th><th>借方金額 ($)</th><th>貸方金額 ($)</th><th class="text-center">操作</th></tr></thead>
              <tbody id="vItemsBody">
                <tr>
                  <td><input type="text" class="form-control form-control-sm v-code" value="1101" placeholder="代號"></td>
                  <td><input type="text" class="form-control form-control-sm v-name" value="現金/銀行存款" placeholder="名稱"></td>
                  <td><input type="number" class="form-control form-control-sm v-dr" value="0" step="0.01" oninput="calcVoucherTotals()"></td>
                  <td><input type="number" class="form-control form-control-sm v-cr" value="0" step="0.01" oninput="calcVoucherTotals()"></td>
                  <td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger py-0" onclick="this.closest('tr').remove(); calcVoucherTotals();">刪除</button></td>
                </tr>
                <tr>
                  <td><input type="text" class="form-control form-control-sm v-code" value="1141" placeholder="代號"></td>
                  <td><input type="text" class="form-control form-control-sm v-name" value="應收票據/應收帳款" placeholder="名稱"></td>
                  <td><input type="number" class="form-control form-control-sm v-dr" value="0" step="0.01" oninput="calcVoucherTotals()"></td>
                  <td><input type="number" class="form-control form-control-sm v-cr" value="0" step="0.01" oninput="calcVoucherTotals()"></td>
                  <td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger py-0" onclick="this.closest('tr').remove(); calcVoucherTotals();">刪除</button></td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td colspan="2" class="text-end fw-bold">合計：</td>
                  <td class="fw-bold text-primary" id="vTotalDr">0.00</td>
                  <td class="fw-bold text-success" id="vTotalCr">0.00</td>
                  <td class="text-center"><button type="button" class="btn btn-sm btn-dark" onclick="addVoucherItemRow()">＋ 增加分錄</button></td>
                </tr>
              </tfoot>
            </table>
          </div>
          <div class="text-end mt-2"><button type="submit" class="btn btn-success btn-sm fw-bold px-4">💾 儲存會計傳票</button></div>
        </form>
      </div>

      <div class="row g-3 mb-4">
        <div class="col-md-6">
          <div style="background:#f8fafc; border:1px solid var(--border); padding:20px; border-radius:8px;">
            <h4 style="color:#0f172a; margin-bottom:12px; border-bottom:2px solid var(--brand); padding-bottom:6px;">📈 四大財務報表與試算表摘要</h4>
            <button class="btn btn-outline-primary btn-sm fw-bold mb-2" onclick="loadFinancialReports()">📊 產生/重新整理報表</button>
            <div id="finReportsContainer" style="max-height:220px; overflow-y:auto;">
              <p class="text-muted small">點擊上方按鈕以載入會計科目試算表與損益狀況</p>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div style="background:#f8fafc; border:1px solid var(--border); padding:20px; border-radius:8px;">
            <h4 style="color:#0f172a; margin-bottom:12px; border-bottom:2px solid var(--brand); padding-bottom:6px;">📑 已建檔會計傳票清單</h4>
            <div class="table-responsive" style="max-height:220px; overflow-y:auto;">
              <table class="table table-sm table-hover bg-white mb-0" style="font-size:11.5px;">
                <thead><tr><th>傳票號碼</th><th>日期</th><th>類型</th><th>摘要</th><th>金額</th><th class="text-center">操作</th></tr></thead>
                <tbody id="voucherTableBody"></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- 互動付款 Modal -->
<div id="actionModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:2000; justify-content:center; align-items:center;">
  <div style="background:#fff; padding:25px; border-radius:8px; width:380px;">
    <h3 id="modalTitle" style="margin-bottom:12px; font-size:16px; color:#0f172a;">登記付款</h3>
    <form onsubmit="handleModalSubmit(event)" style="padding:0;">
      <input type="hidden" id="modalNo"><input type="hidden" id="modalType">
      <div class="form-group" style="margin-bottom:8px;"><label>供應商名稱</label><input type="text" id="modalName" class="readonly" readonly></div>
      <div class="form-group" style="margin-bottom:8px;"><label class="required">付款日期</label><input type="date" id="modalDate" required></div>
      <div class="form-group" style="margin-bottom:8px;"><label class="required">付款金額</label><input type="number" id="modalAmount" step="0.01" required></div>
      <div class="form-group" style="margin-bottom:8px;"><label class="required">付款方式</label><select id="modalMethod"><option value="銀行匯款">銀行匯款</option><option value="現金">現金</option><option value="支票">支票</option></select></div>
      <div class="form-group" style="margin-bottom:15px;"><label>備註</label><input type="text" id="modalRemarks"></div>
      <div style="display:flex; justify-content:flex-end; gap:6px;">
        <button type="button" class="btn-reset" onclick="closeModal()" style="padding:6px 10px;">取消</button>
        <button type="submit" class="btn-submit" style="padding:6px 14px;">確認付款</button>
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
  let warehouseOptionsList = ['八里倉', '南倉', '土城門市倉', '外倉'];
  let cachedInventory = [];
  let cachedEmployees = [];
  let arBaseOrder = null;
  let arEditTargetRow = 0;

  window.addEventListener('DOMContentLoaded', () => {
    ['po_order_date', 'po_delivery_date', 'in_date', 'so_order_date', 'do_date', 'arReceiveDate', 'transDate', 'empHireDate', 'payDate', 'perfOrderDate', 'vDate'].forEach(id => {
      const el = document.getElementById(id); if (el) el.valueAsDate = new Date();
    });
    const mEl = document.getElementById('in_month'); if (mEl) mEl.value = new Date().toISOString().slice(0, 7);
    const payMEl = document.getElementById('payMonth'); if (payMEl) payMEl.value = new Date().toISOString().slice(0, 7);

    const today = new Date();
    const firstDayStr = today.getFullYear() + "-" + String(today.getMonth() + 1).padStart(2, '0') + "-01";
    const todayStr = today.toISOString().split("T")[0];
    const pStart = document.getElementById('printStartDate'); if (pStart) pStart.value = firstDayStr;
    const pEnd = document.getElementById('printEndDate'); if (pEnd) pEnd.value = todayStr;

    for (let i = 0; i < 4; i++) { addPoItemRow(); addSoItemRow(); }
    fetch('/api/warehouses').then(r => r.json()).then(d => { if (d && d.length) warehouseOptionsList = d; });
    loadInventory();
    loadEmployees();
    loadPayroll();
    loadSalesPerformance();
    loadVouchers();
    updateDriverLogic();
    toggleARCheckFields();
  });

  function switchTab(tab) {
    currentTab = tab;
    ['purchase', 'inbound', 'so', 'delivery', 'inventory', 'trans', 'salesPerf', 'hr', 'payroll', 'arPro', 'printCenter', 'ap', 'ar', 'finance'].forEach(t => {
      const btn = document.getElementById('btnTab' + t.charAt(0).toUpperCase() + t.slice(1));
      const view = document.getElementById(t + 'View');
      if(btn) btn.className = (t === tab) ? 'tab-btn active' : 'tab-btn';
      if(view) view.className = (t === tab) ? 'app-view active' : 'app-view';
    });
    if (tab === 'inventory') loadInventory();
    else if (tab === 'trans') prepareTransForm();
    else if (tab === 'salesPerf') loadSalesPerformance();
    else if (tab === 'hr') loadEmployees();
    else if (tab === 'payroll') loadPayroll();
    else if (tab === 'ap') loadAP();
    else if (tab === 'ar') loadAR();
    else if (tab === 'finance') { loadFinancialReports(); loadVouchers(); }
  }

  function autoFillMonth() { const d = document.getElementById('in_date').value; if (d) document.getElementById('in_month').value = d.slice(0, 7); }

  function lookupVendorName(type) {
    const vId = document.getElementById(type === 'po' ? 'po_vendor_id' : 'in_vendor_id').value.trim();
    if (!vId) return;
    fetch(`/api/vendor/${vId}`).then(r => r.json()).then(res => {
      if (res.found) document.getElementById(type === 'po' ? 'po_vendor_name' : 'in_vendor_name').value = res.vendor_name;
    });
  }

  function lookupCustomerName() {
    const cId = document.getElementById('so_customer_code').value.trim();
    if (!cId) return;
    fetch(`/api/customer/${cId}`).then(r => r.json()).then(res => {
      if (res.found) document.getElementById('so_customer_name').value = res.customer_name;
    });
  }

  function submitCurrentForm() {
    if (currentTab === 'purchase') document.getElementById('purchaseForm').requestSubmit();
    else if (currentTab === 'inbound') document.getElementById('inboundForm').requestSubmit();
    else if (currentTab === 'so') document.getElementById('soForm').requestSubmit();
    else if (currentTab === 'delivery') document.getElementById('deliveryForm').requestSubmit();
    else if (currentTab === 'trans') document.getElementById('transForm').requestSubmit();
    else if (currentTab === 'arPro') document.getElementById('arForm').requestSubmit();
    else if (currentTab === 'inventory') document.getElementById('inventoryForm').requestSubmit();
    else if (currentTab === 'salesPerf') document.getElementById('salesPerfForm').requestSubmit();
    else if (currentTab === 'hr') document.getElementById('hrForm').requestSubmit();
    else if (currentTab === 'payroll') document.getElementById('payrollForm').requestSubmit();
    else if (currentTab === 'finance') document.getElementById('voucherForm').requestSubmit();
  }

  function resetCurrentForm() {
    if (currentTab === 'purchase' && confirm("清空採購單？")) { document.getElementById('purchaseForm').reset(); document.getElementById('poItemsBody').innerHTML = ''; for(let i=0;i<4;i++) addPoItemRow(); calculatePoTotals(); }
    else if (currentTab === 'so' && confirm("清空客戶訂單？")) { document.getElementById('soForm').reset(); document.getElementById('soItemsBody').innerHTML = ''; for(let i=0;i<4;i++) addSoItemRow(); calculateSoTotals(); }
  }

  function generateWarehouseSelectOptions(selWh) {
    let opts = '<option value="" disabled selected hidden>倉庫</option>';
    warehouseOptionsList.forEach(w => { opts += `<option value="${w}" ${w === selWh ? 'selected' : ''}>${w}</option>`; });
    return opts;
  }

  // 採購單明細
  function addPoItemRow() {
    const tbody = document.getElementById('poItemsBody');
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><input type="text" class="po-model" placeholder="型號"></td><td><input type="text" class="po-name" placeholder="品名"></td><td><input type="text" class="po-size" placeholder="規格"></td><td><input type="text" class="po-color" placeholder="顏色"></td><td><input type="number" class="po-qty input-qty" min="0" oninput="calculatePoTotals()"></td><td><input type="number" class="po-price input-price" step="0.01" min="0" oninput="calculatePoTotals()"></td><td><input type="text" class="po-total readonly input-total" readonly></td><td class="no-print" style="text-align:center;"><button type="button" class="btn-del-item" onclick="this.closest('tr').nextElementSibling.remove(); this.closest('tr').remove(); calculatePoTotals();">刪除</button></td>`;
    tbody.appendChild(tr);
    const rTr = document.createElement('tr');
    rTr.innerHTML = `<td colspan="8" style="padding:2px 4px; background:#fafafa;"><input type="text" class="item-remarks" placeholder="備註..."></td>`;
    tbody.appendChild(rTr);
    calculatePoTotals();
  }

  function calculatePoTotals() {
    const curr = document.getElementById('po_currency').value;
    document.getElementById('poCurrencyLabel').innerText = curr;
    let gt = 0;
    document.querySelectorAll('#poItemsBody tr:not(:nth-child(even))').forEach(row => {
      const q = parseFloat(row.querySelector('.po-qty').value) || 0;
      const p = parseFloat(row.querySelector('.po-price').value) || 0;
      const t = q * p;
      row.querySelector('.po-total').value = t ? t.toLocaleString('zh-TW', {minimumFractionDigits:2}) : '';
      gt += t;
    });
    document.getElementById('poGrandTotalText').innerText = gt.toLocaleString('zh-TW', {minimumFractionDigits:2});
    const dep = parseFloat(document.getElementById('po_dep_pct').value) || 0;
    const bal = 100 - dep;
    document.getElementById('po_bal_pct').value = bal;
    document.getElementById('po_dep_amt').value = curr ? `${curr} ${(gt * dep / 100).toLocaleString('zh-TW', {minimumFractionDigits:2})}` : '';
    document.getElementById('po_bal_amt').value = curr ? `${curr} ${(gt * bal / 100).toLocaleString('zh-TW', {minimumFractionDigits:2})}` : '';
  }

  function queryPoRecord() {
    const poNo = document.getElementById('po_no').value.trim();
    if (!poNo) return alert("請輸入採購編號");
    fetch(`/api/po/${poNo}`).then(r => r.json()).then(res => {
      if (res.found) {
        const h = res.header;
        document.getElementById('po_buyer_name').value = h.purchaser;
        document.getElementById('po_order_date').value = h.order_date;
        document.getElementById('po_delivery_date').value = h.delivery_date;
        document.getElementById('po_price_term').value = h.price_term;
        document.getElementById('po_vendor_type').value = h.vendor_type;
        document.getElementById('po_vendor_id').value = h.supplier_code;
        document.getElementById('po_vendor_name').value = h.supplier_name;
        document.getElementById('po_vendor_contact').value = h.vendor_contact;
        document.getElementById('po_currency').value = h.currency;
        document.getElementById('po_dep_pct').value = h.deposit_pct;
        document.getElementById('po_shipping_mark').value = h.shipping_mark;
        document.getElementById('po_packing').value = h.packing;
        document.getElementById('po_bank_info').value = h.bank_info;
        const tbody = document.getElementById('poItemsBody'); tbody.innerHTML = '';
        res.items.forEach(it => {
          tbody.innerHTML += `<tr><td><input type="text" class="po-model" value="${it.model||''}"></td><td><input type="text" class="po-name" value="${it.name||''}"></td><td><input type="text" class="po-size" value="${it.size||''}"></td><td><input type="text" class="po-color" value="${it.color||''}"></td><td><input type="number" class="po-qty input-qty" value="${it.qty||''}" oninput="calculatePoTotals()"></td><td><input type="number" class="po-price input-price" value="${it.unit_price||''}" oninput="calculatePoTotals()"></td><td><input type="text" class="po-total readonly input-total" readonly></td><td class="no-print" style="text-align:center;"><button type="button" class="btn-del-item" onclick="this.closest('tr').nextElementSibling.remove(); this.closest('tr').remove(); calculatePoTotals();">刪除</button></td></tr><tr><td colspan="8" style="padding:2px 4px; background:#fafafa;"><input type="text" class="item-remarks" value="${it.remarks||''}"></td></tr>`;
        });
        calculatePoTotals();
        alert("✔ 採購單載入成功！");
      } else alert(res.message);
    });
  }

  function handlePoSubmit(e) {
    e.preventDefault();
    let items = [], gt = 0;
    document.querySelectorAll('#poItemsBody tr:not(:nth-child(even))').forEach(r => {
      const q = parseFloat(r.querySelector('.po-qty').value) || 0;
      const p = parseFloat(r.querySelector('.po-price').value) || 0;
      const t = q * p; gt += t;
      items.push({
        model: r.querySelector('.po-model').value, name: r.querySelector('.po-name').value,
        size: r.querySelector('.po-size').value, color: r.querySelector('.po-color').value,
        qty: q, unit_price: p, total: t, remarks: r.nextElementSibling.querySelector('.item-remarks').value
      });
    });
    const payload = {
      buyer_name: document.getElementById('po_buyer_name').value, po_no: document.getElementById('po_no').value,
      order_date: document.getElementById('po_order_date').value, delivery_date: document.getElementById('po_delivery_date').value,
      price_term: document.getElementById('po_price_term').value, vendor_type: document.getElementById('po_vendor_type').value,
      vendor_id: document.getElementById('po_vendor_id').value, vendor_name: document.getElementById('po_vendor_name').value,
      vendor_contact: document.getElementById('po_vendor_contact').value, currency: document.getElementById('po_currency').value,
      items: items, grand_total: gt, dep_pct: document.getElementById('po_dep_pct').value,
      dep_amt: document.getElementById('po_dep_amt').value, bal_pct: document.getElementById('po_bal_pct').value,
      bal_amt: document.getElementById('po_bal_amt').value, shipping_mark: document.getElementById('po_shipping_mark').value,
      packing: document.getElementById('po_packing').value, bank_info: document.getElementById('po_bank_info').value
    };
    fetch('/api/po/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => alert(res.status === 'success' ? '✔ 採購單儲存成功！' : '✖ 失敗：' + res.message));
  }

  // 進貨驗收
  function importFromPo() {
    const poNo = document.getElementById('in_po_no').value.trim();
    if (!poNo) return alert("請輸入採購編號");
    fetch(`/api/po/${poNo}`).then(r => r.json()).then(res => {
      if (res.found) {
        document.getElementById('in_vendor_id').value = res.header.supplier_code;
        document.getElementById('in_vendor_name').value = res.header.supplier_name;
        const tbody = document.getElementById('inItemsBody'); tbody.innerHTML = '';
        res.items.forEach(it => {
          tbody.innerHTML += `<tr><td><input type="text" class="in-model readonly" value="${it.model}" readonly></td><td><input type="text" class="in-name readonly" value="${it.name}" readonly></td><td><input type="text" class="in-size readonly" value="${it.size}" readonly></td><td><input type="text" class="in-color readonly" value="${it.color}" readonly></td><td><select class="in-wh">${generateWarehouseSelectOptions('八里倉')}</select></td><td><input type="text" class="in-ordered readonly" value="${it.qty}" readonly style="text-align:center;"></td><td><input type="number" class="in-actual input-qty" value="${it.qty}" min="0" oninput="calculateInTotals()" required></td><td><input type="text" class="in-price readonly input-price" value="${it.unit_price}" readonly></td><td><input type="text" class="in-total readonly input-total" readonly></td></tr><tr><td colspan="9" style="padding:2px 4px; background:#fafafa;"><input type="text" class="item-remarks" value="${it.remarks||''}"></td></tr>`;
        });
        calculateInTotals();
        alert("✔ PO 轉入成功！");
      } else alert("找不到採購單");
    });
  }

  function calculateInTotals() {
    let gt = 0;
    document.querySelectorAll('#inItemsBody tr:not(:nth-child(even))').forEach(r => {
      const q = parseFloat(r.querySelector('.in-actual').value) || 0;
      const p = parseFloat(r.querySelector('.in-price').value) || 0;
      const t = q * p; r.querySelector('.in-total').value = t.toLocaleString('zh-TW', {minimumFractionDigits:2}); gt += t;
    });
    document.getElementById('inGrandTotalText').innerText = gt.toLocaleString('zh-TW', {minimumFractionDigits:2});
  }

  function handleInboundSubmit(e) {
    e.preventDefault();
    let items = [];
    document.querySelectorAll('#inItemsBody tr:not(:nth-child(even))').forEach(r => {
      items.push({
        warehouse: r.querySelector('.in-wh').value, model: r.querySelector('.in-model').value,
        name: r.querySelector('.in-name').value, size: r.querySelector('.in-size').value,
        color: r.querySelector('.in-color').value, ordered_qty: parseFloat(r.querySelector('.in-ordered').value)||0,
        actual_qty: parseFloat(r.querySelector('.in-actual').value)||0, unit_price: parseFloat(r.querySelector('.in-price').value)||0,
        remarks: r.nextElementSibling.querySelector('.item-remarks').value
      });
    });
    const payload = {
      receiver_name: document.getElementById('in_receiver_name').value, inbound_no: document.getElementById('in_no').value,
      po_no: document.getElementById('in_po_no').value, inbound_date: document.getElementById('in_date').value,
      month: document.getElementById('in_month').value, vendor_id: document.getElementById('in_vendor_id').value,
      vendor_name: document.getElementById('in_vendor_name').value, items: items
    };
    fetch('/api/inbound/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => alert(res.status === 'success' ? '✔ 進貨驗收存檔成功並已入庫！' : '✖ 失敗'));
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
        document.getElementById('in_vendor_id').value = h.supplier_code;
        document.getElementById('in_vendor_name').value = h.supplier_name;
        const tbody = document.getElementById('inItemsBody'); tbody.innerHTML = '';
        res.items.forEach(it => {
          tbody.innerHTML += `<tr><td><input type="text" class="in-model readonly" value="${it.model}" readonly></td><td><input type="text" class="in-name readonly" value="${it.name}" readonly></td><td><input type="text" class="in-size readonly" value="${it.size}" readonly></td><td><input type="text" class="in-color readonly" value="${it.color}" readonly></td><td><select class="in-wh">${generateWarehouseSelectOptions(it.warehouse)}</select></td><td><input type="text" class="in-ordered readonly" value="${it.ordered_qty}" readonly style="text-align:center;"></td><td><input type="number" class="in-actual input-qty" value="${it.actual_qty}" min="0" oninput="calculateInTotals()" required></td><td><input type="text" class="in-price readonly input-price" value="${it.unit_price}" readonly></td><td><input type="text" class="in-total readonly input-total" readonly></td></tr><tr><td colspan="9" style="padding:2px 4px; background:#fafafa;"><input type="text" class="item-remarks" value="${it.remarks||''}"></td></tr>`;
        });
        calculateInTotals();
        alert("✔ 進貨單載入成功！");
      } else alert(res.message);
    });
  }

  // 客戶訂單
  function addSoItemRow() {
    const tbody = document.getElementById('soItemsBody');
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><input type="text" class="so-model" placeholder="型號"></td><td><input type="text" class="so-name" placeholder="品名"></td><td><input type="text" class="so-size" placeholder="規格"></td><td><input type="text" class="so-color" placeholder="顏色"></td><td><input type="number" class="so-qty input-qty" min="0" oninput="calculateSoTotals()"></td><td><input type="number" class="so-price input-price" step="0.01" min="0" oninput="calculateSoTotals()"></td><td><input type="text" class="so-total readonly input-total" readonly></td><td class="no-print" style="text-align:center;"><button type="button" class="btn-del-item" onclick="this.closest('tr').nextElementSibling.remove(); this.closest('tr').remove(); calculateSoTotals();">刪除</button></td>`;
    tbody.appendChild(tr);
    const rTr = document.createElement('tr');
    rTr.innerHTML = `<td colspan="8" style="padding:2px 4px; background:#fafafa;"><input type="text" class="item-remarks" placeholder="備註..."></td>`;
    tbody.appendChild(rTr);
    calculateSoTotals();
  }

  function calculateSoTotals() {
    let gt = 0;
    document.querySelectorAll('#soItemsBody tr:not(:nth-child(even))').forEach(row => {
      const q = parseFloat(row.querySelector('.so-qty').value) || 0;
      const p = parseFloat(row.querySelector('.so-price').value) || 0;
      const t = q * p; row.querySelector('.so-total').value = t ? t.toLocaleString('zh-TW', {minimumFractionDigits:2}) : ''; gt += t;
    });
    document.getElementById('soGrandTotalText').innerText = gt.toLocaleString('zh-TW', {minimumFractionDigits:2});
  }

  function handleSoSubmit(e) {
    e.preventDefault();
    let items = [], gt = 0;
    document.querySelectorAll('#soItemsBody tr:not(:nth-child(even))').forEach(r => {
      const q = parseFloat(r.querySelector('.so-qty').value) || 0;
      const p = parseFloat(r.querySelector('.so-price').value) || 0;
      const t = q * p; gt += t;
      items.push({
        model: r.querySelector('.so-model').value, name: r.querySelector('.so-name').value,
        size: r.querySelector('.so-size').value, color: r.querySelector('.so-color').value,
        qty: q, unit_price: p, total: t, remarks: r.nextElementSibling.querySelector('.item-remarks').value
      });
    });
    const payload = {
      sales_person: document.getElementById('so_sales_person').value, so_no: document.getElementById('so_no').value,
      order_date: document.getElementById('so_order_date').value, customer_code: document.getElementById('so_customer_code').value,
      customer_name: document.getElementById('so_customer_name').value, currency: document.getElementById('so_currency').value,
      grand_total: gt, remark: document.getElementById('so_remark').value, items: items
    };
    fetch('/api/so/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => alert(res.status === 'success' ? '✔ 客戶訂單儲存成功！' : '✖ 失敗'));
  }

  function querySoRecord() {
    const soNo = document.getElementById('so_no').value.trim();
    if (!soNo) return alert("請輸入訂單編號");
    fetch(`/api/so/${soNo}`).then(r => r.json()).then(res => {
      if (res.found) {
        const h = res.header;
        document.getElementById('so_sales_person').value = h.sales_person;
        document.getElementById('so_order_date').value = h.order_date;
        document.getElementById('so_customer_code').value = h.customer_code;
        document.getElementById('so_customer_name').value = h.customer_name;
        document.getElementById('so_currency').value = h.currency;
        document.getElementById('so_remark').value = h.remark;
        const tbody = document.getElementById('soItemsBody'); tbody.innerHTML = '';
        res.items.forEach(it => {
          tbody.innerHTML += `<tr><td><input type="text" class="so-model" value="${it.model||''}"></td><td><input type="text" class="so-name" value="${it.name||''}"></td><td><input type="text" class="so-size" value="${it.size||''}"></td><td><input type="text" class="so-color" value="${it.color||''}"></td><td><input type="number" class="so-qty input-qty" value="${it.qty||''}" oninput="calculateSoTotals()"></td><td><input type="number" class="so-price input-price" value="${it.unit_price||''}" oninput="calculateSoTotals()"></td><td><input type="text" class="so-total readonly input-total" readonly></td><td class="no-print" style="text-align:center;"><button type="button" class="btn-del-item" onclick="this.closest('tr').nextElementSibling.remove(); this.closest('tr').remove(); calculateSoTotals();">刪除</button></td></tr><tr><td colspan="8" style="padding:2px 4px; background:#fafafa;"><input type="text" class="item-remarks" value="${it.remarks||''}"></td></tr>`;
        });
        calculateSoTotals();
        alert("✔ 訂單載入成功！");
      } else alert(res.message);
    });
  }

  // 銷貨出貨 (含司機與自訂運費)
  function importFromSo() {
    const soNo = document.getElementById('do_so_no').value.trim();
    if (!soNo) return alert("請輸入客戶訂單編號 (SO)");
    fetch(`/api/so/${soNo}`).then(r => r.json()).then(res => {
      if (res.found) {
        document.getElementById('do_customer_code').value = res.header.customer_code;
        document.getElementById('do_customer_name').value = res.header.customer_name;
        const tbody = document.getElementById('doItemsBody'); tbody.innerHTML = '';
        res.items.forEach(it => {
          tbody.innerHTML += `<tr><td><input type="text" class="do-model readonly" value="${it.model}" readonly></td><td><input type="text" class="do-name readonly" value="${it.name}" readonly></td><td><input type="text" class="do-size readonly" value="${it.size}" readonly></td><td><input type="text" class="do-color readonly" value="${it.color}" readonly></td><td><select class="do-wh">${generateWarehouseSelectOptions('八里倉')}</select></td><td><input type="number" class="do-qty input-qty" value="${it.qty}" min="0" oninput="calculateDoTotals()" required></td><td><input type="text" class="do-price readonly input-price" value="${it.unit_price}" readonly></td><td><input type="text" class="do-total readonly input-total" readonly></td></tr><tr><td colspan="8" style="padding:2px 4px; background:#fafafa;"><input type="text" class="item-remarks" value="${it.remarks||''}"></td></tr>`;
        });
        calculateDoTotals();
        alert("✔ SO 訂單轉入成功！");
      } else alert("找不到客戶訂單");
    });
  }

  function calculateDoTotals() {
    let gt = 0;
    document.querySelectorAll('#doItemsBody tr:not(:nth-child(even))').forEach(r => {
      const q = parseFloat(r.querySelector('.do-qty').value) || 0;
      const p = parseFloat(r.querySelector('.do-price').value) || 0;
      const t = q * p; r.querySelector('.do-total').value = t.toLocaleString('zh-TW', {minimumFractionDigits:2}); gt += t;
    });
    document.getElementById('doGrandTotalText').innerText = gt.toLocaleString('zh-TW', {minimumFractionDigits:2});
  }

  function handleDeliverySubmit(e) {
    e.preventDefault();
    let items = [];
    document.querySelectorAll('#doItemsBody tr:not(:nth-child(even))').forEach(r => {
      items.push({
        warehouse: r.querySelector('.do-wh').value, model: r.querySelector('.do-model').value,
        name: r.querySelector('.do-name').value, size: r.querySelector('.do-size').value,
        color: r.querySelector('.do-color').value, shipped_qty: parseFloat(r.querySelector('.do-qty').value)||0,
        unit_price: parseFloat(r.querySelector('.do-price').value)||0, remarks: r.nextElementSibling.querySelector('.item-remarks').value
      });
    });
    const payload = {
      shipper_name: document.getElementById('do_shipper_name').value, do_number: document.getElementById('do_number').value,
      so_no: document.getElementById('do_so_no').value, delivery_date: document.getElementById('do_date').value,
      customer_code: document.getElementById('do_customer_code').value, customer_name: document.getElementById('do_customer_name').value,
      driver: document.getElementById('do_driver').value,
      manual_freight: parseFloat(document.getElementById('do_manual_freight').value) || 0,
      grand_total: parseFloat(document.getElementById('doGrandTotalText').innerText.replace(/,/g,''))||0, items: items
    };
    fetch('/api/delivery/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => alert(res.status === 'success' ? '✔ 銷貨出貨單儲存成功並已記錄司機與運費！' : '✖ 失敗'));
  }

  function queryDeliveryRecord() {
    const no = document.getElementById('do_number').value.trim();
    if (!no) return alert("請輸入出貨單號");
    fetch(`/api/delivery/${no}`).then(r => r.json()).then(res => {
      if (res.found) {
        const h = res.header;
        document.getElementById('do_shipper_name').value = h.shipper_name;
        document.getElementById('do_date').value = h.delivery_date;
        document.getElementById('do_so_no').value = h.so_number;
        document.getElementById('do_customer_code').value = h.customer_code;
        document.getElementById('do_customer_name').value = h.customer_name;
        if (h.driver) document.getElementById('do_driver').value = h.driver;
        if (h.manual_freight !== undefined) document.getElementById('do_manual_freight').value = h.manual_freight;
        const tbody = document.getElementById('doItemsBody'); tbody.innerHTML = '';
        res.items.forEach(it => {
          tbody.innerHTML += `<tr><td><input type="text" class="do-model readonly" value="${it.model}" readonly></td><td><input type="text" class="do-name readonly" value="${it.name}" readonly></td><td><input type="text" class="do-size readonly" value="${it.size}" readonly></td><td><input type="text" class="do-color readonly" value="${it.color}" readonly></td><td><select class="do-wh">${generateWarehouseSelectOptions(it.warehouse)}</select></td><td><input type="number" class="do-qty input-qty" value="${it.shipped_qty}" min="0" oninput="calculateDoTotals()" required></td><td><input type="text" class="do-price readonly input-price" value="${it.unit_price}" readonly></td><td><input type="text" class="do-total readonly input-total" readonly></td></tr><tr><td colspan="8" style="padding:2px 4px; background:#fafafa;"><input type="text" class="item-remarks" value="${it.remarks||''}"></td></tr>`;
        });
        calculateDoTotals();
        alert("✔ 銷貨單載入成功！");
      } else alert(res.message);
    });
  }

  // 庫存 CRUD 管理
  function loadInventory() {
    fetch('/api/inventory/list').then(r => r.json()).then(data => {
      cachedInventory = data || [];
      renderInventoryTable(cachedInventory);
    });
  }

  function renderInventoryTable(items) {
    const tb = document.getElementById('inventoryTableBody'); tb.innerHTML = '';
    if (!items.length) { tb.innerHTML = `<tr><td colspan="8" class="text-center py-3 text-muted">尚無商品與庫存資料，請於上方新增</td></tr>`; return; }
    items.forEach(item => {
      tb.innerHTML += `<tr>
        <td><strong>${item.sku}</strong></td>
        <td class="text-start">${item.name}</td>
        <td>${item.category||'-'}</td>
        <td class="text-end">$${item.cost.toLocaleString()}</td>
        <td class="text-end">$${item.price.toLocaleString()}</td>
        <td class="text-end fw-bold text-success">${item.stock.toLocaleString()} 件</td>
        <td class="text-end">${item.safety_stock}</td>
        <td class="text-center no-print">
          <button class="btn btn-sm btn-outline-primary py-0 px-2" onclick='editInventoryItem(${JSON.stringify(item)})'>✏️ 修改</button>
          <button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="deleteInventoryItem('${item.sku}')">🗑️ 刪除</button>
        </td>
      </tr>`;
    });
  }

  function filterInventory() {
    const keyword = document.getElementById('invSearchBox').value.toLowerCase();
    const filtered = cachedInventory.filter(item => item.sku.toLowerCase().includes(keyword) || item.name.toLowerCase().includes(keyword));
    renderInventoryTable(filtered);
  }

  function handleInventorySave(e) {
    e.preventDefault();
    const payload = {
      sku: document.getElementById('invSku').value.trim(),
      name: document.getElementById('invName').value.trim(),
      category: document.getElementById('invCategory').value.trim(),
      cost: parseFloat(document.getElementById('invCost').value) || 0,
      price: parseFloat(document.getElementById('invPrice').value) || 0,
      stock: parseInt(document.getElementById('invStock').value) || 0,
      safety_stock: parseInt(document.getElementById('invSafety').value) || 10,
      note: ''
    };
    fetch('/api/inventory/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => {
        alert(res.message);
        if(res.success) { resetInvForm(); loadInventory(); }
      });
  }

  function editInventoryItem(item) {
    document.getElementById('invSku').value = item.sku;
    document.getElementById('invSku').readOnly = true;
    document.getElementById('invName').value = item.name;
    document.getElementById('invCategory').value = item.category || '';
    document.getElementById('invCost').value = item.cost;
    document.getElementById('invPrice').value = item.price;
    document.getElementById('invStock').value = item.stock;
    document.getElementById('invSafety').value = item.safety_stock;
    window.scrollTo({top: 0, behavior: 'smooth'});
  }

  function deleteInventoryItem(sku) {
    if (confirm(`確定要刪除商品【${sku}】嗎？`)) {
      fetch(`/api/inventory/delete/${sku}`, {method:'POST'}).then(r => r.json()).then(res => {
        alert(res.message);
        if(res.success) loadInventory();
      });
    }
  }

  function resetInvForm() {
    document.getElementById('inventoryForm').reset();
    document.getElementById('invSku').readOnly = false;
  }

  function prepareTransForm() {
    const sel = document.getElementById('transSkuSelect');
    sel.innerHTML = '<option value="">-- 請選擇商品 --</option>';
    cachedInventory.forEach((item, idx) => {
      sel.innerHTML += `<option value="${idx}">【${item.sku}】${item.name} (庫存:${item.stock})</option>`;
    });
  }

  function onSkuSelected() {
    const idx = document.getElementById('transSkuSelect').value;
    if (idx === "" || !cachedInventory[idx]) return;
    const item = cachedInventory[idx];
    document.getElementById('transSku').value = item.sku;
    document.getElementById('transPrice').value = item.price;
  }

  function submitTransaction() {
    const payload = {
      transType: document.getElementById('transType').value,
      orderId: document.getElementById('transOrderId').value,
      customerCode: document.getElementById('transCustCode').value,
      customerName: document.getElementById('transCustName').value,
      transSku: document.getElementById('transSku').value,
      transQty: document.getElementById('transQty').value,
      transPrice: document.getElementById('transPrice').value,
      transDate: document.getElementById('transDate').value,
      transNote: document.getElementById('transNote').value,
      keyinUser: document.getElementById('transKeyin').value
    };
    fetch('/api/inventory/transaction/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => {
        alert(res.message);
        if (res.success) { document.getElementById('transForm').reset(); document.getElementById('transDate').value = new Date().toISOString().split("T")[0]; loadInventory(); }
      });
  }

  // 業務業績 (支援輸入、修改、刪除、查詢區間列印)
  function loadSalesPerformance() {
    const pPerson = document.getElementById('perfFilterPerson').value.trim().toLowerCase();
    const pStart = document.getElementById('perfFilterStart').value;
    const pEnd = document.getElementById('perfFilterEnd').value;

    fetch('/api/sales/performance').then(r => r.json()).then(data => {
      const tb = document.getElementById('salesPerfTableBody'); tb.innerHTML = '';
      let filtered = data.filter(d => {
        if (pPerson && !d.sales_person.toLowerCase().includes(pPerson)) return false;
        if (pStart && d.order_date < pStart) return false;
        if (pEnd && d.order_date > pEnd) return false;
        return true;
      });

      if (!filtered.length) { tb.innerHTML = `<tr><td colspan="9" class="text-center py-3 text-muted">尚無符合條件的業務業績紀錄</td></tr>`; return; }
      filtered.forEach(d => {
        tb.innerHTML += `<tr>
          <td><strong>${d.sales_person}</strong></td>
          <td>${d.order_id||'-'}</td>
          <td>${d.order_date}</td>
          <td>${d.customer_name}</td>
          <td class="text-end">$${d.sales_amount.toLocaleString()}</td>
          <td class="text-center">${(d.commission_rate*100)}%</td>
          <td class="text-end fw-bold text-success">$${d.commission_amount.toLocaleString()}</td>
          <td class="text-center"><span class="badge bg-success">${d.status}</span></td>
          <td class="text-center no-print">
            <button class="btn btn-sm btn-outline-primary py-0 px-2" onclick='editSalesPerf(${JSON.stringify(d)})'>✏️</button>
            <button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="deleteSalesPerf(${d.id})">🗑️</button>
          </td>
        </tr>`;
      });
    });
  }

  function handleSalesPerfSave(e) {
    e.preventDefault();
    const payload = {
      perf_id: document.getElementById('perfRecordId').value || null,
      sales_person: document.getElementById('perfSalesPerson').value.trim(),
      order_id: document.getElementById('perfOrderId').value.trim(),
      order_date: document.getElementById('perfOrderDate').value,
      customer_name: document.getElementById('perfCustomer').value.trim(),
      sales_amount: parseFloat(document.getElementById('perfSalesAmount').value) || 0,
      commission_rate: parseFloat(document.getElementById('perfRate').value) || 0.05,
      status: '已結算',
      note: ''
    };
    fetch('/api/sales/performance/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => {
        alert(res.message);
        if(res.success) { resetSalesPerfForm(); loadSalesPerformance(); }
      });
  }

  function editSalesPerf(d) {
    document.getElementById('perfRecordId').value = d.id;
    document.getElementById('perfSalesPerson').value = d.sales_person;
    document.getElementById('perfOrderId').value = d.order_id || '';
    document.getElementById('perfOrderDate').value = d.order_date;
    document.getElementById('perfCustomer').value = d.customer_name;
    document.getElementById('perfSalesAmount').value = d.sales_amount;
    document.getElementById('perfRate').value = d.commission_rate;
    document.getElementById('perfSubmitBtn').innerText = "✏️ 覆寫修改業績";
    window.scrollTo({top: 0, behavior: 'smooth'});
  }

  function deleteSalesPerf(id) {
    if (confirm("確定要刪除這筆業務業績紀錄嗎？")) {
      fetch(`/api/sales/performance/delete/${id}`, {method:'POST'}).then(r => r.json()).then(res => {
        alert(res.message);
        if(res.success) loadSalesPerformance();
      });
    }
  }

  function resetSalesPerfForm() {
    document.getElementById('salesPerfForm').reset();
    document.getElementById('perfRecordId').value = '';
    document.getElementById('perfOrderDate').valueAsDate = new Date();
    document.getElementById('perfSubmitBtn').innerText = "💾 儲存業績";
  }

  // 人事名冊 (HR CRUD)
  function loadEmployees() {
    fetch('/api/employees/list').then(r => r.json()).then(data => {
      cachedEmployees = data || [];
      const tb = document.getElementById('empTableBody'); tb.innerHTML = '';
      if (!cachedEmployees.length) { tb.innerHTML = `<tr><td colspan="9" class="text-center py-3 text-muted">尚無員工資料</td></tr>`; return; }
      cachedEmployees.forEach(e => {
        tb.innerHTML += `<tr>
          <td><strong>${e.emp_id}</strong></td>
          <td>${e.emp_name}</td>
          <td>${e.department||'-'}</td>
          <td>${e.title||'-'}</td>
          <td>${e.phone||'-'}</td>
          <td>${e.hire_date||'-'}</td>
          <td class="text-end">$${e.base_salary.toLocaleString()}</td>
          <td class="text-center"><span class="badge ${e.status==='在職'?'bg-success':'bg-secondary'}">${e.status}</span></td>
          <td class="text-center no-print">
            <button class="btn btn-sm btn-outline-primary py-0 px-2" onclick='editEmployee(${JSON.stringify(e)})'>✏️ 修改</button>
            <button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="deleteEmployee('${e.emp_id}')">🗑️ 刪除</button>
          </td>
        </tr>`;
      });
      preparePayrollEmpSelect();
    });
  }

  function handleEmpSave(e) {
    e.preventDefault();
    const payload = {
      emp_id: document.getElementById('empId').value.trim(),
      emp_name: document.getElementById('empName').value.trim(),
      department: document.getElementById('empDept').value.trim(),
      title: document.getElementById('empTitle').value.trim(),
      phone: document.getElementById('empPhone').value.trim(),
      hire_date: document.getElementById('empHireDate').value,
      base_salary: parseFloat(document.getElementById('empSalary').value) || 0,
      status: document.getElementById('empStatus').value,
      note: ''
    };
    fetch('/api/employees/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => {
        alert(res.message);
        if(res.success) { resetEmpForm(); loadEmployees(); }
      });
  }

  function editEmployee(e) {
    document.getElementById('empId').value = e.emp_id;
    document.getElementById('empId').readOnly = true;
    document.getElementById('empName').value = e.emp_name;
    document.getElementById('empDept').value = e.department || '';
    document.getElementById('empTitle').value = e.title || '';
    document.getElementById('empPhone').value = e.phone || '';
    document.getElementById('empHireDate').value = e.hire_date || '';
    document.getElementById('empSalary').value = e.base_salary;
    document.getElementById('empStatus').value = e.status || '在職';
    window.scrollTo({top: 0, behavior: 'smooth'});
  }

  function deleteEmployee(empId) {
    if (confirm(`確定要刪除員工【${empId}】嗎？`)) {
      fetch(`/api/employees/delete/${empId}`, {method:'POST'}).then(r => r.json()).then(res => {
        alert(res.message);
        if(res.success) loadEmployees();
      });
    }
  }

  function resetEmpForm() {
    document.getElementById('hrForm').reset();
    document.getElementById('empId').readOnly = false;
  }

  // 薪資系統
  function preparePayrollEmpSelect() {
    const sel = document.getElementById('payEmpSelect');
    sel.innerHTML = '<option value="">-- 請選擇員工 --</option>';
    cachedEmployees.forEach(e => {
      sel.innerHTML += `<option value="${e.emp_id}">${e.emp_name} (${e.emp_id}) - ${e.title||'職員'}</option>`;
    });
  }

  function onEmpSelectedForPay() {
    const empId = document.getElementById('payEmpSelect').value;
    const emp = cachedEmployees.find(x => x.emp_id === empId);
    if (emp) {
      document.getElementById('payEmpId').value = emp.emp_id;
      document.getElementById('payBase').value = emp.base_salary;
      calcPayrollNet();
    } else {
      document.getElementById('payEmpId').value = '';
      document.getElementById('payBase').value = 0;
      calcPayrollNet();
    }
  }

  function calcPayrollNet() {
    const base = parseFloat(document.getElementById('payBase').value) || 0;
    const allow = parseFloat(document.getElementById('payAllowance').value) || 0;
    const ot = parseFloat(document.getElementById('payOvertime').value) || 0;
    const leaveDed = parseFloat(document.getElementById('payLeaveDed').value) || 0;
    const purDed = parseFloat(document.getElementById('payPurDed').value) || 0;
    const insDed = parseFloat(document.getElementById('payInsDed').value) || 0;
    
    const net = base + allow + ot - leaveDed - purDed - insDed;
    document.getElementById('payNet').value = net.toFixed(2);
  }

  function handlePayrollSave(e) {
    e.preventDefault();
    const empId = document.getElementById('payEmpId').value;
    const emp = cachedEmployees.find(x => x.emp_id === empId);
    if (!emp) return alert("請先選擇員工！");

    const payload = {
      payroll_id: document.getElementById('payrollRecordId').value || null,
      emp_id: empId,
      emp_name: emp.emp_name,
      pay_month: document.getElementById('payMonth').value,
      base_salary: parseFloat(document.getElementById('payBase').value) || 0,
      allowance: parseFloat(document.getElementById('payAllowance').value) || 0,
      overtime_pay: parseFloat(document.getElementById('payOvertime').value) || 0,
      leave_deduction: parseFloat(document.getElementById('payLeaveDed').value) || 0,
      emp_purchase_deduction: parseFloat(document.getElementById('payPurDed').value) || 0,
      insurance_deduction: parseFloat(document.getElementById('payInsDed').value) || 0,
      pay_date: document.getElementById('payDate').value,
      status: '已發放',
      note: document.getElementById('payNote').value.trim()
    };
    fetch('/api/payroll/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => {
        alert(res.message);
        if(res.success) { resetPayrollForm(); loadPayroll(); }
      });
  }

  function editPayrollRecord(p) {
    document.getElementById('payrollRecordId').value = p.id;
    document.getElementById('payEmpSelect').value = p.emp_id;
    document.getElementById('payEmpId').value = p.emp_id;
    document.getElementById('payMonth').value = p.pay_month;
    document.getElementById('payBase').value = p.base_salary;
    document.getElementById('payAllowance').value = p.allowance;
    document.getElementById('payOvertime').value = p.overtime_pay;
    document.getElementById('payLeaveDed').value = p.leave_deduction;
    document.getElementById('payPurDed').value = p.emp_purchase_deduction;
    document.getElementById('payInsDed').value = p.insurance_deduction;
    document.getElementById('payDate').value = p.pay_date;
    document.getElementById('payNote').value = p.note || '';
    document.getElementById('payrollSubmitBtn').innerText = "✏️ 覆寫修改薪資";
    calcPayrollNet();
    window.scrollTo({top: 0, behavior: 'smooth'});
  }

  function resetPayrollForm() {
    document.getElementById('payrollForm').reset();
    document.getElementById('payrollRecordId').value = '';
    document.getElementById('payMonth').value = new Date().toISOString().slice(0, 7);
    document.getElementById('payDate').valueAsDate = new Date();
    document.getElementById('payrollSubmitBtn').innerText = "💾 儲存薪資紀錄";
  }

  function loadPayroll() {
    fetch('/api/payroll/list').then(r => r.json()).then(data => {
      const tb = document.getElementById('payrollTableBody'); tb.innerHTML = '';
      if (!data.length) { tb.innerHTML = `<tr><td colspan="12" class="text-center py-3 text-muted">尚無薪資發放紀錄</td></tr>`; return; }
      data.forEach(p => {
        tb.innerHTML += `<tr>
          <td><strong>${p.pay_month}</strong></td>
          <td>${p.emp_id}</td>
          <td>${p.emp_name}</td>
          <td class="text-end">$${p.base_salary.toLocaleString()}</td>
          <td class="text-end text-success">+$${p.allowance.toLocaleString()}</td>
          <td class="text-end text-success">+$${p.overtime_pay.toLocaleString()}</td>
          <td class="text-end text-danger">-$${p.leave_deduction.toLocaleString()}</td>
          <td class="text-end text-danger">-$${p.emp_purchase_deduction.toLocaleString()}</td>
          <td class="text-end text-danger">-$${p.insurance_deduction.toLocaleString()}</td>
          <td class="text-end fw-bold text-success">$${p.net_salary.toLocaleString()}</td>
          <td>${p.pay_date}</td>
          <td class="text-center no-print">
            <button class="btn btn-sm btn-outline-primary py-0 px-2" onclick='editPayrollRecord(${JSON.stringify(p)})'>✏️</button>
            <button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="deletePayroll(${p.id})">🗑️</button>
          </td>
        </tr>`;
      });
    });
  }

  function deletePayroll(id) {
    if (confirm("確定要刪除這筆薪資發放紀錄嗎？")) {
      fetch(`/api/payroll/delete/${id}`, {method:'POST'}).then(r => r.json()).then(res => {
        alert(res.message);
        if(res.success) loadPayroll();
      });
    }
  }

  // 專業應收帳款 (AR Pro)
  function toggleARCheckFields() {
    const type = document.getElementById("arPayType").value;
    document.getElementById("boxARCheck").style.display = (type === "應收票據") ? "block" : "none";
  }

  function searchAR() {
    const id = document.getElementById("arSearchId").value.trim().toUpperCase();
    if (!id) return alert("請輸入訂單編號！");
    fetch(`/api/ar/search/${id}`).then(r => r.json()).then(res => {
      if (res.success) {
        arBaseOrder = res.data;
        arEditTargetRow = 0;
        document.getElementById("arOrderId").value = arBaseOrder.orderId;
        document.getElementById("arCustomer").value = arBaseOrder.customer;
        document.getElementById("arSalesAmount").value = arBaseOrder.salesAmount;
        document.getElementById("arDeposit").value = arBaseOrder.deposit;
        document.getElementById("dispTotalCollectedText").innerText = "$" + (arBaseOrder.deposit + arBaseOrder.totalCollected).toLocaleString();
        document.getElementById("arReceiveAmount").value = arBaseOrder.currentUnpaid;
        document.getElementById("arUnpaidAmount").value = 0;
        
        const banner = document.getElementById("arUnpaidBanner");
        banner.style.display = "block";
        banner.innerHTML = `<div class="d-flex justify-content-between align-items-center"><div><span class="badge bg-danger">${arBaseOrder.discrepancyStatus}</span> 銷售總額: $${arBaseOrder.salesAmount.toLocaleString()}，已收: $${(arBaseOrder.deposit + arBaseOrder.totalCollected).toLocaleString()}</div><div>尚欠餘額：<strong class="text-danger fs-5">$${arBaseOrder.currentUnpaid.toLocaleString()}</strong></div></div>`;
        
        document.getElementById("arDriver").value = arBaseOrder.driver || '大蔡';
        updateDriverLogic();
        document.getElementById("arFreight").value = arBaseOrder.freight || 0;
        document.getElementById("arOldItemFee").value = arBaseOrder.oldItemFee || 0;
        document.getElementById("arNote").value = arBaseOrder.balanceNote || '';
        
        document.getElementById("arOrderId").readOnly = true;
        document.getElementById("arSalesAmount").readOnly = true;
        document.getElementById("arDeposit").readOnly = true;
        renderARHistoryTable(arBaseOrder.historyRecords);
      } else alert(res.message);
    });
  }

  function renderARHistoryTable(records) {
    const box = document.getElementById("arHistoryBox");
    const tbody = document.getElementById("arHistoryListBody");
    const badge = document.getElementById("arHistoryCountBadge");
    tbody.innerHTML = "";
    if (!records || records.length === 0) { box.style.display = "none"; return; }
    badge.innerText = records.length + " 筆";
    records.forEach(r => {
      const checkInfo = (r.payType === "應收票據" && r.checkNo) ? `${r.checkNo} (到期:${r.checkDueDate})` : "-";
      tbody.innerHTML += `<tr><td><strong>${r.date}</strong></td><td><span class="badge bg-secondary">${r.payType}</span></td><td class="text-end fw-bold text-primary">$${r.amount.toLocaleString()}</td><td>${checkInfo}</td><td>${r.user}</td><td class="text-start">${r.note||''}</td><td><button type="button" class="btn btn-outline-primary btn-sm py-0 px-2" style="font-size:11px;" onclick='loadSpecificRowForEdit(${JSON.stringify(r)})'>✏️ 修改</button></td></tr>`;
    });
    box.style.display = "block";
  }

  function loadSpecificRowForEdit(r) {
    arEditTargetRow = r.rowIndex;
    document.getElementById("arReceiveDate").value = r.date;
    document.getElementById("arPayType").value = r.payType;
    toggleARCheckFields();
    document.getElementById("arCheckNo").value = r.checkNo || "";
    document.getElementById("arCheckDueDate").value = r.checkDueDate || "";
    document.getElementById("arReceiveAmount").value = r.amount;
    document.getElementById("arNote").value = r.note || "";
    document.getElementById("arSaveBtn").innerText = `✏️ 覆寫儲存【第 ${r.rowIndex} 筆】`;
    document.getElementById("arCancelEditBtn").style.display = "block";
    calcAR();
  }

  function cancelRowEdit() {
    arEditTargetRow = 0;
    if(arBaseOrder) document.getElementById("arReceiveAmount").value = arBaseOrder.currentUnpaid;
    document.getElementById("arSaveBtn").innerText = "💾 儲存並新增一筆收款紀錄";
    document.getElementById("arCancelEditBtn").style.display = "none";
    calcAR();
  }

  function calcAR() {
    const sales = parseFloat(document.getElementById("arSalesAmount").value) || 0;
    const deposit = parseFloat(document.getElementById("arDeposit").value) || 0;
    const thisRec = parseFloat(document.getElementById("arReceiveAmount").value) || 0;
    const remain = arBaseOrder ? (arEditTargetRow > 0 ? (sales - deposit - thisRec) : (arBaseOrder.currentUnpaid - thisRec)) : (sales - deposit - thisRec);
    document.getElementById("arUnpaidAmount").value = Math.max(0, remain);
    calcFreight();
  }

  function updateDriverLogic() {
    const driver = document.getElementById("arDriver").value;
    const areaSelect = document.getElementById("arDriverArea");
    areaSelect.innerHTML = "";
    if (driver === "大蔡") {
      areaSelect.innerHTML = '<option value="NORTH_4">新竹以北 (4%)</option><option value="SOUTH_5">苗栗以南 (5%)</option><option value="HUALIEN_7">花蓮 (7%)</option><option value="CUSTOM">手動自訂</option>';
    } else if (driver === "南倉") {
      areaSelect.innerHTML = '<option value="TAINAN_5">台南 (5%)</option><option value="OTHER_6">其餘 (6%)</option><option value="CUSTOM">手動自訂</option>';
    } else {
      areaSelect.innerHTML = '<option value="CUSTOM">自行輸入運費</option>';
    }
    calcFreight();
  }

  function calcFreight() {
    const driver = document.getElementById("arDriver").value;
    const area = document.getElementById("arDriverArea").value;
    const sales = parseFloat(document.getElementById("arSalesAmount").value) || 0;
    if (area === "CUSTOM" || driver === "大生") return;
    const rate = (driver === "大蔡") ? (area === "NORTH_4" ? 0.04 : area === "SOUTH_5" ? 0.05 : 0.07) : (area === "TAINAN_5" ? 0.05 : 0.06);
    document.getElementById("arFreight").value = Math.round(sales * rate);
  }

  function submitAR() {
    const payType = document.getElementById("arPayType").value;
    if (payType === "應收票據" && (!document.getElementById("arCheckNo").value.trim() || !document.getElementById("arCheckDueDate").value)) {
      return alert("⚠️ 請填寫完整的票號與到期日！");
    }
    const payload = {
      orderId: document.getElementById("arOrderId").value.trim(),
      customer: document.getElementById("arCustomer").value.trim(),
      salesAmount: parseFloat(document.getElementById("arSalesAmount").value) || 0,
      deposit: parseFloat(document.getElementById("arDeposit").value) || 0,
      receiveAmount: parseFloat(document.getElementById("arReceiveAmount").value) || 0,
      unpaidAmount: parseFloat(document.getElementById("arUnpaidAmount").value) || 0,
      payType: payType, checkNo: document.getElementById("arCheckNo").value.trim(),
      checkDueDate: document.getElementById("arCheckDueDate").value,
      receiveDate: document.getElementById("arReceiveDate").value,
      driver: document.getElementById("arDriver").value,
      driverArea: document.getElementById("arDriverArea").selectedOptions[0]?.text || "",
      freight: parseFloat(document.getElementById("arFreight").value) || 0,
      oldItemFee: parseFloat(document.getElementById("arOldItemFee").value) || 0,
      keyinUser: document.getElementById("arKeyinUser").value,
      note: document.getElementById("arNote").value.trim(),
      isEditSpecificRow: (arEditTargetRow > 0), targetRowIndex: arEditTargetRow
    };
    fetch('/api/ar/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => {
        alert(res.message);
        if (res.success) {
          document.getElementById("arForm").reset();
          document.getElementById("arUnpaidBanner").style.display = "none";
          document.getElementById("arHistoryBox").style.display = "none";
          document.getElementById("arOrderId").readOnly = false;
          document.getElementById("arSalesAmount").readOnly = false;
          document.getElementById("arDeposit").readOnly = false;
          arBaseOrder = null; arEditTargetRow = 0;
        }
      });
  }

  // 司機運費對帳系統 (原出納對帳單)
  function loadPrintData() {
    const start = document.getElementById("printStartDate").value;
    const end = document.getElementById("printEndDate").value;
    const driverFilter = document.getElementById("printDriverFilter").value;
    const container = document.getElementById("printContainer");
    if (!start || !end) return alert("⚠️ 請選取起迄日期！");
    container.innerHTML = '<div class="text-center py-4 text-muted">載入對帳單中...</div>';

    fetch(`/api/print/data?startDate=${start}&endDate=${end}&driver=${driverFilter}`).then(r => r.json()).then(res => {
      let list = res.list || [];
      if (!list.length) { container.innerHTML = '<div class="text-center py-4 text-muted">此區段內無收款紀錄</div>'; return; }

      let sumCash = 0, sumFreight = 0, sumOld = 0;
      list.forEach(r => {
        sumFreight += Number(r.freight) || 0;
        sumOld += Number(r.oldFee) || 0;
        if (r.payType === "現金") sumCash += Number(r.received) || 0;
      });
      const netCash = sumCash - sumFreight - sumOld;
      const title = driverFilter === "ALL" ? "全門市" : `司機【${driverFilter}】`;

      let html = `<div class="driver-cash-summary shadow-sm mb-3">
        <div class="row g-2 text-center align-items-center mb-2">
          <div class="col-3 border-end"><div>💵 代收現金</div><strong class="fs-6 text-dark">$${sumCash.toLocaleString()}</strong></div>
          <div class="col-3 border-end"><div>🚚 扣除運費</div><strong class="fs-6 text-danger">-$${sumFreight.toLocaleString()}</strong></div>
          <div class="col-3 border-end"><div>📦 扣除舊貨</div><strong class="fs-6 text-danger">-$${sumOld.toLocaleString()}</strong></div>
          <div class="col-3 bg-white p-2 rounded border border-success"><div>💰 本期應繳現金</div><strong class="fs-6 text-success">$${netCash.toLocaleString()}</strong></div>
        </div>
      </div>
      <table class="table table-bordered table-sm text-center align-middle" style="font-size:11px;">
        <thead class="table-light">
          <tr><th colspan="11" class="bg-dark text-white py-2" style="font-size:11pt;">🚚 珮藏居 - ${title} 司機運費與代收對帳單 (${start} ~ ${end})</th></tr>
          <tr><th>單號</th><th>客戶</th><th>收款日</th><th>方式</th><th>實收金額</th><th>司機/倉別</th><th>運費</th><th>舊貨費</th><th>未收餘額</th><th>經辦</th><th>備註</th></tr>
        </thead><tbody>`;
      list.forEach(r => {
        html += `<tr><td>${r.id}</td><td>${r.customer}</td><td>${r.date}</td><td><span class="badge bg-success">${r.payType}</span></td><td class="text-end text-success fw-bold">$${Number(r.received).toLocaleString()}</td><td>${r.driver}<br><small>${r.driverArea}</small></td><td class="text-end text-danger">$${Number(r.freight).toLocaleString()}</td><td class="text-end text-danger">$${Number(r.oldFee).toLocaleString()}</td><td class="text-end text-danger">$${Number(r.unpaid).toLocaleString()}</td><td>${r.user}</td><td class="text-start">${r.note||''}</td></tr>`;
      });
      html += `</tbody></table>`;
      container.innerHTML = html;
    });
  }

  // AP, AR, 財務載入
  function loadAP() {
    const fVendor = document.getElementById('ap_filter_vendor').value.trim().toLowerCase();
    const fMonth = document.getElementById('ap_filter_month').value;
    const fStart = document.getElementById('ap_filter_start').value;
    const fEnd = document.getElementById('ap_filter_end').value;
    fetch('/api/ap/summary').then(r => r.json()).then(res => {
      const tb = document.getElementById('apTableBody'); tb.innerHTML = '';
      if (!res.data.length) { tb.innerHTML = `<tr><td colspan="10" class="text-center py-3 text-muted">無應付帳款資料</td></tr>`; return; }
      let filtered = res.data.filter(d => {
        let dt = d.inbound_date;
        let vName = d.vendor_name.toLowerCase();
        if (fVendor && !vName.includes(fVendor)) return false;
        if (fMonth && dt && dt.slice(0, 7) !== fMonth) return false;
        if (fStart && dt && dt < fStart) return false;
        if (fEnd && dt && dt > fEnd) return false;
        return true;
      });
      if (!filtered.length) { tb.innerHTML = `<tr><td colspan="10" class="text-center py-3 text-muted">查無符合條件的應付帳款</td></tr>`; return; }
      filtered.forEach(d => {
        tb.innerHTML += `<tr><td>${d.inbound_no}</td><td>${d.inbound_date}</td><td>${d.vendor_name}</td><td class="text-end">$${d.total_amount.toLocaleString()}</td><td>${d.payment_term}</td><td>${d.due_date}</td><td class="text-end text-success">$${d.paid_amount.toLocaleString()}</td><td class="text-end text-danger fw-bold">$${d.unpaid_amount.toLocaleString()}</td><td class="text-center"><span class="badge ${d.status==='已結清'?'bg-success':'bg-danger'}">${d.status}</span></td><td class="no-print text-center"><button class="btn btn-query btn-sm py-0 px-2" onclick="openModal('ap','${d.inbound_no}','${d.vendor_name}',${d.unpaid_amount})">登記付款</button></td></tr>`;
      });
    });
  }
  function resetApFilter() { document.getElementById('ap_filter_vendor').value = ''; document.getElementById('ap_filter_month').value = ''; document.getElementById('ap_filter_start').value = ''; document.getElementById('ap_filter_end').value = ''; loadAP(); }

  function loadAR() {
    const fCust = document.getElementById('ar_filter_customer').value.trim().toLowerCase();
    const fMonth = document.getElementById('ar_filter_month').value;
    const fStart = document.getElementById('ar_filter_start').value;
    const fEnd = document.getElementById('ar_filter_end').value;
    fetch('/api/ar/summary').then(r => r.json()).then(res => {
      const tb = document.getElementById('arTableBody'); tb.innerHTML = '';
      if (!res.data.length) { tb.innerHTML = `<tr><td colspan="9" class="text-center py-3 text-muted">無應收帳款資料</td></tr>`; return; }
      let filtered = res.data.filter(d => {
        let dt = d.delivery_date;
        let cName = d.customer_display.toLowerCase();
        if (fCust && !cName.includes(fCust)) return false;
        if (fMonth && dt && dt.slice(0, 7) !== fMonth) return false;
        if (fStart && dt && dt < fStart) return false;
        if (fEnd && dt && dt > fEnd) return false;
        return true;
      });
      if (!filtered.length) { tb.innerHTML = `<tr><td colspan="9" class="text-center py-3 text-muted">查無符合條件的應收帳款</td></tr>`; return; }
      filtered.forEach(d => {
        tb.innerHTML += `<tr><td>${d.do_number}</td><td>${d.delivery_date}</td><td>${d.customer_display}</td><td class="text-end">$${d.total_amount.toLocaleString()}</td><td>${d.payment_term}</td><td>${d.due_date}</td><td class="text-end text-success">$${d.collected_amount.toLocaleString()}</td><td class="text-end text-danger fw-bold">$${d.uncollected_amount.toLocaleString()}</td><td class="text-center"><span class="badge ${d.status==='已收清'?'bg-success':'bg-danger'}">${d.status}</span></td></tr>`;
      });
    });
  }
  function resetArFilter() { document.getElementById('ar_filter_customer').value = ''; document.getElementById('ar_filter_month').value = ''; document.getElementById('ar_filter_start').value = ''; document.getElementById('ar_filter_end').value = ''; loadAR(); }

  function loadFinance() {
    fetch('/api/finance/summary').then(r => r.json()).then(d => {
      document.getElementById('finTotalAp').innerText = d.total_ap.toLocaleString();
      document.getElementById('finPaidAp').innerText = d.paid_ap.toLocaleString();
      document.getElementById('finUnpaidAp').innerText = d.unpaid_ap.toLocaleString();
      document.getElementById('finTotalAr').innerText = d.total_ar.toLocaleString();
      document.getElementById('finCollectedAr').innerText = d.collected_ar.toLocaleString();
      document.getElementById('finUncollectedAr').innerText = d.uncollected_ar.toLocaleString();
    });
  }

  // 傳票與財務報表管理
  function addVoucherItemRow() {
    const tbody = document.getElementById('vItemsBody');
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><input type="text" class="form-control form-control-sm v-code" placeholder="代號"></td><td><input type="text" class="form-control form-control-sm v-name" placeholder="名稱"></td><td><input type="number" class="form-control form-control-sm v-dr" value="0" step="0.01" oninput="calcVoucherTotals()"></td><td><input type="number" class="form-control form-control-sm v-cr" value="0" step="0.01" oninput="calcVoucherTotals()"></td><td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger py-0" onclick="this.closest('tr').remove(); calcVoucherTotals();">刪除</button></td>`;
    tbody.appendChild(tr);
  }

  function calcVoucherTotals() {
    let dr = 0, cr = 0;
    document.querySelectorAll('.v-dr').forEach(el => { dr += parseFloat(el.value) || 0; });
    document.querySelectorAll('.v-cr').forEach(el => { cr += parseFloat(el.value) || 0; });
    document.getElementById('vTotalDr').innerText = dr.toFixed(2);
    document.getElementById('vTotalCr').innerText = cr.toFixed(2);
  }

  function handleVoucherSave(e) {
    e.preventDefault();
    let items = [];
    let dr = 0, cr = 0;
    document.querySelectorAll('#vItemsBody tr').forEach(tr => {
      const dVal = parseFloat(tr.querySelector('.v-dr').value) || 0;
      const cVal = parseFloat(tr.querySelector('.v-cr').value) || 0;
      dr += dVal; cr += cVal;
      items.push({
        account_code: tr.querySelector('.v-code').value.trim(),
        account_name: tr.querySelector('.v-name').value.trim(),
        debit: dVal, credit: cVal
      });
    });

    if (Math.abs(dr - cr) > 0.01) return alert(`⚠️ 借貸不平衡！借方總計 ($${dr.toFixed(2)}) 與貸方總計 ($${cr.toFixed(2)}) 不符。`);

    const payload = {
      voucher_no: document.getElementById('vNo').value.trim(),
      voucher_date: document.getElementById('vDate').value,
      voucher_type: document.getElementById('vType').value,
      summary: document.getElementById('vSummary').value.trim(),
      preparer: document.getElementById('vPreparer').value,
      items: items
    };

    fetch('/api/vouchers/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => {
        alert(res.message);
        if (res.success) { document.getElementById('voucherForm').reset(); document.getElementById('vDate').valueAsDate = new Date(); loadVouchers(); loadFinancialReports(); }
      });
  }

  function loadVouchers() {
    fetch('/api/vouchers/list').then(r => r.json()).then(data => {
      const tb = document.getElementById('voucherTableBody'); tb.innerHTML = '';
      if (!data.length) { tb.innerHTML = `<tr><td colspan="6" class="text-center py-2 text-muted">尚無傳票紀錄</td></tr>`; return; }
      data.forEach(v => {
        tb.innerHTML += `<tr><td><strong>${v.voucher_no}</strong></td><td>${v.voucher_date}</td><td>${v.voucher_type}</td><td>${v.summary}</td><td class="text-end">$${v.total_amount.toLocaleString()}</td><td class="text-center"><button class="btn btn-sm btn-outline-danger py-0" onclick="deleteVoucher('${v.voucher_no}')">刪除</button></td></tr>`;
      });
    });
  }

  function deleteVoucher(vNo) {
    if (confirm(`確定要刪除傳票【${vNo}】嗎？`)) {
      fetch(`/api/vouchers/delete/${vNo}`, {method:'POST'}).then(r => r.json()).then(res => {
        alert(res.message);
        if (res.success) { loadVouchers(); loadFinancialReports(); }
      });
    }
  }

  function loadFinancialReports() {
    fetch('/api/finance/reports').then(r => r.json()).then(res => {
      const box = document.getElementById('finReportsContainer');
      let html = '<h6 class="fw-bold text-success mb-2">⚖️ 會計科目試算表餘額：</h6><ul class="list-unstyled mb-0" style="font-size:12px;">';
      if (!res.trial_balance.length) { html += '<li class="text-muted">尚無分錄資料</li>'; }
      res.trial_balance.forEach(tb => {
        let diff = tb.dr - tb.cr;
        html += `<li class="d-flex justify-content-between border-bottom py-1"><span>【${tb.account_code}】${tb.account_name}</span><strong>借:${tb.dr.toLocaleString()} / 貸:${tb.cr.toLocaleString()}</strong></li>`;
      });
      html += '</ul>';
      box.innerHTML = html;
    });
  }

  function openModal(type, no, name, amt) {
    document.getElementById('modalType').value = type;
    document.getElementById('modalNo').value = no;
    document.getElementById('modalName').value = name;
    document.getElementById('modalAmount').value = amt > 0 ? amt : '';
    document.getElementById('modalDate').valueAsDate = new Date();
    document.getElementById('modalRemarks').value = '';
    document.getElementById('actionModal').style.display = 'flex';
  }
  function closeModal() { document.getElementById('actionModal').style.display = 'none'; }

  function handleModalSubmit(e) {
    e.preventDefault();
    const payload = {
      pay_date: document.getElementById('modalDate').value, inbound_no: document.getElementById('modalNo').value,
      vendor_name: document.getElementById('modalName').value, pay_amount: parseFloat(document.getElementById('modalAmount').value)||0,
      pay_method: document.getElementById('modalMethod').value, remarks: document.getElementById('modalRemarks').value
    };
    fetch('/api/ap/pay', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => {
        if(res.status === 'success') { alert("✔ 付款登記成功！"); closeModal(); loadAP(); }
        else alert("失敗");
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
    <style>body { background-color: #f8f9fa; } @media print { .no-print, .col-md-4 { display: none !important; } .col-md-8 { width: 100% !important; } }</style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark shadow-sm mb-4 no-print">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('index') }}"><i class="fa-solid fa-boxes-stacked me-2"></i>珮藏居採購系統</a>
            <a href="{{ url_for('index') }}" class="btn btn-outline-light btn-sm"><i class="fa-solid fa-arrow-left me-1"></i>返回首頁</a>
        </div>
    </nav>
    <div class="container-fluid px-4">
        <div class="row">
            <div class="col-md-4 mb-4">
                <div class="card shadow-sm p-4">
                    <h4 class="mb-3 text-primary"><i class="fa-solid fa-user-plus me-2"></i>新增供應商</h4>
                    <form action="{{ url_for('add_supplier') }}" method="POST">
                        <div class="mb-2"><label class="form-label">供應商代號</label><input type="text" class="form-control" name="supplier_code" required></div>
                        <div class="mb-2"><label class="form-label">供應商名稱</label><input type="text" class="form-control" name="supplier_name" required></div>
                        <div class="mb-2"><label class="form-label">統一編號</label><input type="text" class="form-control" name="tax_id"></div>
                        <div class="mb-2"><label class="form-label">聯絡人</label><input type="text" class="form-control" name="contact_info"></div>
                        <div class="mb-2"><label class="form-label">付款條件</label><input type="text" class="form-control" name="payment_terms" value="月結30天"></div>
                        <div class="mb-3"><label class="form-label">銀行資訊</label><input type="text" class="form-control" name="bank_info"></div>
                        <button type="submit" class="btn btn-dark w-100">儲存供應商</button>
                    </form>
                </div>
            </div>
            <div class="col-md-8">
                <div class="card shadow-sm p-4">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h4 class="text-secondary mb-0">供應商清單</h4>
                        <button onclick="window.print()" class="btn btn-outline-secondary btn-sm no-print">列印清單</button>
                    </div>
                    <table class="table table-hover align-middle">
                        <thead class="table-dark"><tr><th>代號</th><th>名稱</th><th>統編</th><th>聯絡人</th><th>付款條件</th><th class="text-center no-print">操作</th></tr></thead>
                        <tbody>
                            {% for s in suppliers %}
                            <tr>
                                <td>{{ s.supplier_code }}</td><td><strong>{{ s.supplier_name }}</strong></td><td>{{ s.tax_id or '-' }}</td><td>{{ s.contact_info or '-' }}</td><td>{{ s.payment_terms or '-' }}</td>
                                <td class="text-center no-print"><button class="btn btn-sm btn-outline-primary" data-bs-toggle="modal" data-bs-target="#editModal{{ s.supplier_code }}"><i class="fa-solid fa-pen-to-square"></i></button></td>
                            </tr>
                            <div class="modal fade" id="editModal{{ s.supplier_code }}" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header bg-dark text-white"><h5 class="modal-title">修改供應商</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div>
                            <form action="{{ url_for('edit_supplier', code=s.supplier_code) }}" method="POST"><div class="modal-body">
                                <div class="mb-2"><label>代號 (不可改)</label><input type="text" class="form-control" value="{{ s.supplier_code }}" disabled></div>
                                <div class="mb-2"><label>名稱</label><input type="text" class="form-control" name="supplier_name" value="{{ s.supplier_name }}" required></div>
                                <div class="mb-2"><label>統編</label><input type="text" class="form-control" name="tax_id" value="{{ s.tax_id or '' }}"></div>
                                <div class="mb-2"><label>聯絡人</label><input type="text" class="form-control" name="contact_info" value="{{ s.contact_info or '' }}"></div>
                                <div class="mb-2"><label>付款條件</label><input type="text" class="form-control" name="payment_terms" value="{{ s.payment_terms or '' }}"></div>
                                <div class="mb-2"><label>銀行</label><input type="text" class="form-control" name="bank_info" value="{{ s.bank_info or '' }}"></div>
                            </div><div class="modal-footer"><button type="submit" class="btn btn-primary btn-sm">儲存變更</button></div></form></div></div></div>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# API 路由補充：庫存、員工與薪資 CRUD
@app.route("/api/inventory/save", methods=["POST"])
def api_save_inventory():
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    data = request.get_json()
    try:
        conn = get_db_connection()
        conn.execute("""INSERT INTO inventory_items (sku, name, category, cost, price, stock, safety_stock, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(sku) DO UPDATE SET name=?, category=?, cost=?, price=?, stock=?, safety_stock=?, note=?""",
                     (data.get("sku"), data.get("name"), data.get("category"), data.get("cost"), data.get("price"),
                      data.get("stock"), data.get("safety_stock"), data.get("note"),
                      data.get("name"), data.get("category"), data.get("cost"), data.get("price"),
                      data.get("stock"), data.get("safety_stock"), data.get("note")))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "✔ 商品存檔/修改成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@app.route("/api/inventory/delete/<string:sku>", methods=["POST"])
def api_delete_inventory(sku):
    if "user_id" not in session: return jsonify({"success": False, "message": "請先登入"})
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM inventory_items WHERE sku = ?", (sku,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "✔ 商品刪除成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)