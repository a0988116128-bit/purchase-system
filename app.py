from datetime import datetime
from flask import Flask, flash, jsonify, redirect, render_template_string, request, session, url_for
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "pezang_perfect_system_2026_v2"

# 自動判斷資料庫路徑：Render 雲端使用 /tmp/database.db，本地使用 database.db
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

        # 1. 系統使用者
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                password TEXT NOT NULL
            )
        """)

        # 2. 供應商主檔
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_code TEXT PRIMARY KEY,
                supplier_name TEXT NOT NULL,
                tax_id TEXT,
                contact_info TEXT,
                payment_terms TEXT,
                bank_info TEXT
            )
        """)

        # 3. 客戶主檔
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_code TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                tax_id TEXT,
                contact_info TEXT,
                payment_terms TEXT
            )
        """)

        # 4. 倉庫清單
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS warehouses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                warehouse_name TEXT UNIQUE NOT NULL
            )
        """)

        # 5. 採購單主檔與明細
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

        # 6. 進貨驗收主檔與明細
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

        # 7. 庫存帳
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT, warehouse TEXT, model TEXT,
                product_name TEXT, specification TEXT, color TEXT, stock_qty INTEGER DEFAULT 0,
                updated_at TEXT, UNIQUE(warehouse, model, color)
            )
        """)

        # 8. 客戶訂單主檔與明細
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

        # 9. 銷貨出貨單主檔與明細
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_orders (
                do_number TEXT PRIMARY KEY, shipper_name TEXT, warehouse TEXT,
                so_number TEXT, delivery_date TEXT, customer_code TEXT, customer_name TEXT,
                grand_total REAL, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, do_number TEXT, warehouse TEXT,
                model TEXT, product_name TEXT, specification TEXT, color TEXT,
                shipped_qty INTEGER, unit_price REAL, subtotal REAL, remarks TEXT
            )
        """)

        # 10. 應付帳款與付款
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

        # 11. 應收帳款與收款
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ar_invoices (
                do_number TEXT PRIMARY KEY, delivery_date TEXT, customer_display TEXT,
                total_amount REAL, payment_term TEXT, due_date TEXT, status TEXT DEFAULT '未收'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ar_collections (
                col_no TEXT PRIMARY KEY, col_date TEXT, do_number TEXT,
                customer_name TEXT, col_amount REAL, col_method TEXT, remarks TEXT, created_at TEXT
            )
        """)

        # 預設資料初始化
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO users (id, name, password) VALUES (?, ?, ?)",
                [("01", "黃詠甯", "0320"), ("02", "江婉秀", "1234"), ("admin", "系統管理員", "pezang888")])

        cursor.execute("SELECT COUNT(*) FROM suppliers")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO suppliers VALUES (?, ?, ?, ?, ?, ?)",
                [("328", "席德瑞思", "24567891", "王經理", "月結30天", "台新銀行 1234"),
                 ("427", "興隆", "87654321", "陳小姐", "現金付款", "合作金庫 5678")])

        cursor.execute("SELECT COUNT(*) FROM customers")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
                [("C01", "特力屋內湖店", "11223344", "林主任", "月結30天"),
                 ("C02", "詩肯柚木", "55667788", "張經理", "月結60天")])

        cursor.execute("SELECT COUNT(*) FROM warehouses")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO warehouses (warehouse_name) VALUES (?)",
                [("八里倉",), ("南倉",), ("土城門市倉",), ("外倉",)])

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
    return render_template_string(MAIN_HTML, user_name=session["user_name"])

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        uid, pwd = data.get("username") or data.get("user_id"), data.get("password")
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE id = ? AND password = ?", (uid, pwd)).fetchone()
        conn.close()
        if user:
            session["user_id"], session["user_name"] = user["id"], user["name"]
            return jsonify({"success": True, "name": user["name"]}) if request.is_json else redirect(url_for("index"))
        return jsonify({"success": False, "message": "帳號或密碼錯誤"}) if request.is_json else "登入失敗"
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
        conn.execute("INSERT INTO inbound_orders VALUES (?,?,?,?,?,?,?,?,?)",
            (in_no, data.get("receiver_name"), data.get("warehouse", "八里倉"), data.get("po_no"),
             data.get("inbound_date"), data.get("month"), data.get("vendor_id"), data.get("vendor_name"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        total_amt = 0
        for item in data.get("items", []):
            sub = item.get("actual_qty", 0) * item.get("unit_price", 0)
            total_amt += sub
            wh = item.get("warehouse", "八里倉")
            conn.execute("INSERT INTO inbound_items (inbound_no, warehouse, model, product_name, specification, color, ordered_qty, actual_qty, unit_price, subtotal, remarks) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (in_no, wh, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                 item.get("ordered_qty"), item.get("actual_qty"), item.get("unit_price"), sub, item.get("remarks")))
            
            conn.execute("""INSERT INTO inventory (warehouse, model, product_name, specification, color, stock_qty, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(warehouse, model, color) 
                            DO UPDATE SET stock_qty = stock_qty + ?, updated_at = ?""",
                         (wh, item.get("model"), item.get("name"), item.get("size"), item.get("color"), item.get("actual_qty"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          item.get("actual_qty"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        v_display = (data.get("vendor_id", "") + " " if data.get("vendor_id") else "") + (data.get("vendor_name") or "")
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
        conn.execute("INSERT INTO delivery_orders VALUES (?,?,?,?,?,?,?,?,?)",
            (do_no, data.get("shipper_name"), data.get("warehouse", "八里倉"), data.get("so_no"),
             data.get("delivery_date"), data.get("customer_code"), data.get("customer_name"), data.get("grand_total", 0), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        total_amt = 0
        for item in data.get("items", []):
            sub = item.get("shipped_qty", 0) * item.get("unit_price", 0)
            total_amt += sub
            wh = item.get("warehouse", "八里倉")
            conn.execute("INSERT INTO delivery_items (do_number, warehouse, model, product_name, specification, color, shipped_qty, unit_price, subtotal, remarks) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (do_no, wh, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                 item.get("shipped_qty"), item.get("unit_price"), sub, item.get("remarks")))
            
            conn.execute("""UPDATE inventory SET stock_qty = stock_qty - ?, updated_at = ? 
                            WHERE warehouse = ? AND model = ? AND color = ?""",
                         (item.get("shipped_qty"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), wh, item.get("model"), item.get("color")))

        c_display = (data.get("customer_code", "") + " " if data.get("customer_code") else "") + (data.get("customer_name") or "")
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
    conn.close()
    return jsonify({"found": True, "header": dict(dOrder), "items": items})


# --- 庫存、財務與會計 API ---
@app.route("/api/inventory/list")
def get_inventory():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM inventory ORDER BY warehouse, model").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

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
        collected = conn.execute("SELECT SUM(col_amount) as t FROM ar_collections WHERE do_number = ?", (inv["do_number"],)).fetchone()["t"] or 0
        uncollected = inv["total_amount"] - collected
        status = "已收清" if uncollected <= 0 else ("部分收款" if collected > 0 else "未收")
        data.append({**dict(inv), "collected_amount": collected, "uncollected_amount": uncollected, "status": status})
    conn.close()
    return jsonify({"found": True, "data": data})

@app.route("/api/ar/collect", methods=["POST"])
def save_collection():
    data = request.get_json()
    col_no = "COL" + datetime.now().strftime("%Y%m%d%H%M%S")
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO ar_collections VALUES (?,?,?,?,?,?,?,?)",
            (col_no, data.get("col_date"), data.get("do_number"), data.get("customer_name"),
             data.get("col_amount"), data.get("col_method"), data.get("remarks"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route("/api/finance/summary")
def get_finance_summary():
    conn = get_db_connection()
    total_ap = conn.execute("SELECT SUM(total_amount) FROM ap_invoices").fetchone()[0] or 0
    paid_ap = conn.execute("SELECT SUM(pay_amount) FROM ap_payments").fetchone()[0] or 0
    total_ar = conn.execute("SELECT SUM(total_amount) FROM ar_invoices").fetchone()[0] or 0
    collected_ar = conn.execute("SELECT SUM(col_amount) FROM ar_collections").fetchone()[0] or 0
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
  <style>
    :root { --primary: #0f172a; --brand: #c59b27; --border: #94a3b8; --text: #1e293b; }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background-color: #f1f5f9; color: var(--text); padding: 20px 20px 90px 20px; display: flex; justify-content: center; }
    .container { width: 100%; max-width: 1100px; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid var(--border); overflow: hidden; }
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
    .msgBox { display: none; margin-top: 8px; padding: 6px; border-radius: 4px; font-size: 12px; text-align: center; font-weight: 600; }
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
      <button type="button" class="tab-btn" id="btnTabInventory" onclick="switchTab('inventory')">📊 庫存查詢</button>
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
      <div class="po-company-info"><div>統一編號：83390454</div><div>電話：02-22691071</div></div>
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
      <div class="po-company-info"><div>統一編號：83390454</div></div>
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
      <div class="po-company-info"><div>統一編號：83390454</div></div>
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

  <!-- 4. 銷貨出貨系統 -->
  <div id="deliveryView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>DELIVERY ORDER (銷貨出貨單)</div></div>
      <div class="po-company-info"><div>統一編號：83390454</div></div>
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

  <!-- 5. 庫存查詢系統 -->
  <div id="inventoryView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>INVENTORY REPORT (即時庫存總覽)</div></div>
      <div class="po-company-info"><div>各倉存貨即時連動</div></div>
    </div>
    <div style="padding:20px 30px;">
      <div style="display:flex; justify-content:flex-end; margin-bottom:10px;"><button type="button" class="btn-query" onclick="loadInventory()">🔄 重新整理庫存</button></div>
      <table class="items-table">
        <thead><tr><th>倉庫別</th><th>產品型號</th><th>產品名稱</th><th>規格</th><th>顏色</th><th>現有庫存量</th><th>最後更新時間</th></tr></thead>
        <tbody id="inventoryTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 6. 應付帳款系統 -->
  <div id="apView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>ACCOUNTS PAYABLE (應付帳款與付款)</div></div>
      <div class="po-company-info"><div>進貨自動拋轉應付帳款</div></div>
    </div>
    <div style="padding:20px 30px;">
      <table class="items-table">
        <thead><tr><th>進貨單號</th><th>進貨日期</th><th>供應商</th><th>應付總額</th><th>付款條件</th><th>預計付款日</th><th>已付金額</th><th>未付餘額</th><th>狀態</th><th class="no-print">操作</th></tr></thead>
        <tbody id="apTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 7. 應收帳款系統 -->
  <div id="arView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>ACCOUNTS RECEIVABLE (應收帳款與收款)</div></div>
      <div class="po-company-info"><div>銷貨自動拋轉應收帳款</div></div>
    </div>
    <div style="padding:20px 30px;">
      <table class="items-table">
        <thead><tr><th>出貨單號</th><th>出貨日期</th><th>客戶名稱</th><th>應收總額</th><th>付款條件</th><th>預計收款日</th><th>已收金額</th><th>未收餘額</th><th>狀態</th><th class="no-print">操作</th></tr></thead>
        <tbody id="arTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 8. 財務系統 -->
  <div id="financeView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>FINANCIAL DASHBOARD (財務報表總覽)</div></div>
      <div class="po-company-info"><div>企業資產與收支流向</div></div>
    </div>
    <div style="padding:25px 30px;">
      <div class="grid-2" style="gap:20px;">
        <div style="background:#f8fafc; border:1px solid var(--border); padding:20px; border-radius:8px;">
          <h3 style="color:#0f172a; margin-bottom:12px; border-bottom:2px solid var(--brand); padding-bottom:6px;">💰 應付帳款摘要 (AP)</h3>
          <p style="margin:8px 0; font-size:14px;">應付總額：<strong id="finTotalAp" style="float:right;">0.00</strong></p>
          <p style="margin:8px 0; font-size:14px; color:#15803d;">已付總額：<strong id="finPaidAp" style="float:right;">0.00</strong></p>
          <p style="margin:8px 0; font-size:14px; color:#dc2626;">未付餘額 (負債)：<strong id="finUnpaidAp" style="float:right;">0.00</strong></p>
        </div>
        <div style="background:#f8fafc; border:1px solid var(--border); padding:20px; border-radius:8px;">
          <h3 style="color:#0f172a; margin-bottom:12px; border-bottom:2px solid var(--brand); padding-bottom:6px;">💳 應收帳款摘要 (AR)</h3>
          <p style="margin:8px 0; font-size:14px;">應收總額：<strong id="finTotalAr" style="float:right;">0.00</strong></p>
          <p style="margin:8px 0; font-size:14px; color:#15803d;">已收總額：<strong id="finCollectedAr" style="float:right;">0.00</strong></p>
          <p style="margin:8px 0; font-size:14px; color:#dc2626;">未收餘額 (資產)：<strong id="finUncollectedAr" style="float:right;">0.00</strong></p>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- 互動付款/收款 Modal -->
<div id="actionModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:2000; justify-content:center; align-items:center;">
  <div style="background:#fff; padding:25px; border-radius:8px; width:380px;">
    <h3 id="modalTitle" style="margin-bottom:12px; font-size:16px; color:#0f172a;">登記作業</h3>
    <form onsubmit="handleModalSubmit(event)" style="padding:0;">
      <input type="hidden" id="modalNo"><input type="hidden" id="modalType">
      <div class="form-group" style="margin-bottom:8px;"><label>對象名稱</label><input type="text" id="modalName" class="readonly" readonly></div>
      <div class="form-group" style="margin-bottom:8px;"><label class="required">日期</label><input type="date" id="modalDate" required></div>
      <div class="form-group" style="margin-bottom:8px;"><label class="required">金額</label><input type="number" id="modalAmount" step="0.01" required></div>
      <div class="form-group" style="margin-bottom:8px;"><label class="required">方式</label><select id="modalMethod"><option value="銀行匯款">銀行匯款</option><option value="現金">現金</option><option value="支票">支票</option></select></div>
      <div class="form-group" style="margin-bottom:15px;"><label>備註</label><input type="text" id="modalRemarks"></div>
      <div style="display:flex; justify-content:flex-end; gap:6px;">
        <button type="button" class="btn-reset" onclick="closeModal()" style="padding:6px 10px;">取消</button>
        <button type="submit" class="btn-submit" style="padding:6px 14px;">確認送出</button>
      </div>
    </form>
  </div>
</div>

<div class="floating-action-bar" id="floatingBar">
  <button type="button" class="btn-submit" onclick="submitCurrentForm()">💾 儲存單據</button>
  <button type="button" class="btn-print" onclick="window.print()">🖨️ 列印單據</button>
  <button type="button" class="btn-reset" onclick="resetCurrentForm()">🔄 清空重設</button>
  <button type="button" class="btn-logout" onclick="window.location.href='/logout'">🚪 登出</button>
</div>

<script>
  let currentTab = 'purchase';
  let warehouseOptionsList = ['八里倉', '南倉', '土城門市倉', '外倉'];

  window.addEventListener('DOMContentLoaded', () => {
    ['po_order_date', 'po_delivery_date', 'in_date', 'so_order_date', 'do_date'].forEach(id => {
      const el = document.getElementById(id); if (el) el.valueAsDate = new Date();
    });
    const mEl = document.getElementById('in_month'); if (mEl) mEl.value = new Date().toISOString().slice(0, 7);
    for (let i = 0; i < 4; i++) { addPoItemRow(); addSoItemRow(); }
    fetch('/api/warehouses').then(r => r.json()).then(d => { if (d && d.length) warehouseOptionsList = d; });
  });

  function switchTab(tab) {
    currentTab = tab;
    ['purchase', 'inbound', 'so', 'delivery', 'inventory', 'ap', 'ar', 'finance'].forEach(t => {
      document.getElementById('btnTab' + t.charAt(0).toUpperCase() + t.slice(1)).className = (t === tab) ? 'tab-btn active' : 'tab-btn';
      document.getElementById(t + 'View').className = (t === tab) ? 'app-view active' : 'app-view';
    });
    if (tab === 'inventory') loadInventory();
    else if (tab === 'ap') loadAP();
    else if (tab === 'ar') loadAR();
    else if (tab === 'finance') loadFinance();
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

  // 銷貨出貨
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
      grand_total: parseFloat(document.getElementById('doGrandTotalText').innerText.replace(/,/g,''))||0, items: items
    };
    fetch('/api/delivery/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => alert(res.status === 'success' ? '✔ 銷貨出貨單儲存成功並已扣減庫存！' : '✖ 失敗'));
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
        const tbody = document.getElementById('doItemsBody'); tbody.innerHTML = '';
        res.items.forEach(it => {
          tbody.innerHTML += `<tr><td><input type="text" class="do-model readonly" value="${it.model}" readonly></td><td><input type="text" class="do-name readonly" value="${it.name}" readonly></td><td><input type="text" class="do-size readonly" value="${it.size}" readonly></td><td><input type="text" class="do-color readonly" value="${it.color}" readonly></td><td><select class="do-wh">${generateWarehouseSelectOptions(it.warehouse)}</select></td><td><input type="number" class="do-qty input-qty" value="${it.shipped_qty}" min="0" oninput="calculateDoTotals()" required></td><td><input type="text" class="do-price readonly input-price" value="${it.unit_price}" readonly></td><td><input type="text" class="do-total readonly input-total" readonly></td></tr><tr><td colspan="8" style="padding:2px 4px; background:#fafafa;"><input type="text" class="item-remarks" value="${it.remarks||''}"></td></tr>`;
        });
        calculateDoTotals();
        alert("✔ 銷貨單載入成功！");
      } else alert(res.message);
    });
  }

  // 庫存、AP、AR、財務載入
  function loadInventory() {
    fetch('/api/inventory/list').then(r => r.json()).then(data => {
      const tb = document.getElementById('inventoryTableBody'); tb.innerHTML = '';
      if (!data.length) { tb.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:15px; color:#64748b;">目前無庫存記錄</td></tr>`; return; }
      data.forEach(d => {
        tb.innerHTML += `<tr><td>${d.warehouse}</td><td><strong>${d.model}</strong></td><td>${d.product_name}</td><td>${d.specification||'-'}</td><td>${d.color||'-'}</td><td style="text-align:center; font-weight:bold; color:${d.stock_qty>0?'#15803d':'#dc2626'};">${d.stock_qty}</td><td style="font-size:11px; color:#64748b;">${d.updated_at}</td></tr>`;
      });
    });
  }

  function loadAP() {
    fetch('/api/ap/summary').then(r => r.json()).then(res => {
      const tb = document.getElementById('apTableBody'); tb.innerHTML = '';
      if (!res.data.length) { tb.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:15px; color:#64748b;">無應付帳款資料</td></tr>`; return; }
      res.data.forEach(d => {
        tb.innerHTML += `<tr><td>${d.inbound_no}</td><td>${d.inbound_date}</td><td>${d.vendor_name}</td><td style="text-align:right;">${d.total_amount.toLocaleString()}</td><td>${d.payment_term}</td><td>${d.due_date}</td><td style="text-align:right; color:#15803d;">${d.paid_amount.toLocaleString()}</td><td style="text-align:right; color:#dc2626; font-weight:bold;">${d.unpaid_amount.toLocaleString()}</td><td style="text-align:center;"><span style="padding:2px 6px; border-radius:4px; font-size:11px; background:${d.status==='已結清'?'#dcfce7; color:#15803d;':'#fee2e2; color:#dc2626;'}">${d.status}</span></td><td class="no-print" style="text-align:center;"><button type="button" class="btn-query" style="padding:2px 6px; font-size:11px;" onclick="openModal('ap', '${d.inbound_no}', '${d.vendor_name}', ${d.unpaid_amount})">登記付款</button></td></tr>`;
      });
    });
  }

  function loadAR() {
    fetch('/api/ar/summary').then(r => r.json()).then(res => {
      const tb = document.getElementById('arTableBody'); tb.innerHTML = '';
      if (!res.data.length) { tb.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:15px; color:#64748b;">無應收帳款資料</td></tr>`; return; }
      res.data.forEach(d => {
        tb.innerHTML += `<tr><td>${d.do_number}</td><td>${d.delivery_date}</td><td>${d.customer_display}</td><td style="text-align:right;">${d.total_amount.toLocaleString()}</td><td>${d.payment_term}</td><td>${d.due_date}</td><td style="text-align:right; color:#15803d;">${d.collected_amount.toLocaleString()}</td><td style="text-align:right; color:#dc2626; font-weight:bold;">${d.uncollected_amount.toLocaleString()}</td><td style="text-align:center;"><span style="padding:2px 6px; border-radius:4px; font-size:11px; background:${d.status==='已收清'?'#dcfce7; color:#15803d;':'#fee2e2; color:#dc2626;'}">${d.status}</span></td><td class="no-print" style="text-align:center;"><button type="button" class="btn-query" style="padding:2px 6px; font-size:11px;" onclick="openModal('ar', '${d.do_number}', '${d.customer_display}', ${d.uncollected_amount})">登記收款</button></td></tr>`;
      });
    });
  }

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

  function openModal(type, no, name, amt) {
    document.getElementById('modalType').value = type;
    document.getElementById('modalNo').value = no;
    document.getElementById('modalName').value = name;
    document.getElementById('modalAmount').value = amt > 0 ? amt : '';
    document.getElementById('modalDate').valueAsDate = new Date();
    document.getElementById('modalRemarks').value = '';
    document.getElementById('modalTitle').innerText = type === 'ap' ? '登記應付帳款付款' : '登記應收帳款收款';
    document.getElementById('actionModal').style.display = 'flex';
  }
  function closeModal() { document.getElementById('actionModal').style.display = 'none'; }

  function handleModalSubmit(e) {
    e.preventDefault();
    const type = document.getElementById('modalType').value;
    const payload = {
      pay_date: document.getElementById('modalDate').value, col_date: document.getElementById('modalDate').value,
      inbound_no: document.getElementById('modalNo').value, do_number: document.getElementById('modalNo').value,
      vendor_name: document.getElementById('modalName').value, customer_name: document.getElementById('modalName').value,
      pay_amount: parseFloat(document.getElementById('modalAmount').value)||0, col_amount: parseFloat(document.getElementById('modalAmount').value)||0,
      pay_method: document.getElementById('modalMethod').value, col_method: document.getElementById('modalMethod').value,
      remarks: document.getElementById('modalRemarks').value
    };
    const endpoint = type === 'ap' ? '/api/ap/pay' : '/api/ar/collect';
    fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(r => r.json()).then(res => {
        if(res.status === 'success') { alert("✔ 登記成功！"); closeModal(); if(type==='ap') loadAP(); else loadAR(); }
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)