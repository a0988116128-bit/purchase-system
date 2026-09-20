from datetime import datetime
from flask import Flask, flash, jsonify, redirect, render_template_string, request, session, url_for
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "pezang_ultimate_enterprise_2026"

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
                password TEXT NOT NULL,
                role TEXT
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

        # 5. 商品與庫存主檔
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_items (
                sku TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                cost REAL DEFAULT 0,
                price REAL DEFAULT 0,
                stock INTEGER DEFAULT 0,
                safety_stock INTEGER DEFAULT 0,
                note TEXT
            )
        """)

        # 6. 採購單主檔與明細
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

        # 7. 進貨驗收主檔與明細
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

        # 10. 應付帳款與付款記錄
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

        # 11. 應收帳款明細表 (支援分次收款、司機、運費、舊貨費等)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ar_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                customer TEXT,
                sales_amount REAL,
                deposit REAL,
                receive_amount REAL,
                pay_type TEXT,
                check_no TEXT,
                check_due_date TEXT,
                receive_date TEXT,
                unpaid_amount REAL,
                driver TEXT,
                driver_area TEXT,
                freight REAL,
                old_item_fee REAL,
                keyin_user TEXT,
                note TEXT,
                created_at TEXT
            )
        """)

        # 12. 進銷存交易流水帳
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trans_date TEXT,
                trans_type TEXT,
                order_id TEXT,
                customer_code TEXT,
                customer_name TEXT,
                sku TEXT,
                qty INTEGER,
                price REAL,
                total_amount REAL,
                cogs REAL,
                keyin_user TEXT,
                status TEXT,
                note TEXT,
                created_at TEXT
            )
        """)

        # 預設資料初始化
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO users (id, name, password, role) VALUES (?, ?, ?, ?)",
                [("01", "黃詠甯", "0320", "系統管理"), ("02", "經辦人員", "1234", "門市經辦"), ("admin", "系統管理員", "pezang888", "系統管理")])

        cursor.execute("SELECT COUNT(*) FROM suppliers")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO suppliers VALUES (?, ?, ?, ?, ?, ?)",
                [("328", "席德瑞思", "24567891", "王經理", "月結30天", "台新銀行 1234"),
                 ("427", "興隆", "87654321", "陳小姐", "現金付款", "合作金庫 5678")])

        cursor.execute("SELECT COUNT(*) FROM customers")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
                [("C001", "王小明", "0912-345678", "台北市中正區忠孝東路一段1號", "VIP客戶"),
                 ("C002", "林美華", "0922-888999", "新北市中和區中原街95號", "櫃體設計案"),
                 ("C003", "張大山", "0933-123123", "台中市西屯區台灣大道三段", "老客戶介紹")])

        cursor.execute("SELECT COUNT(*) FROM warehouses")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO warehouses (warehouse_name) VALUES (?)",
                [("八里倉",), ("南倉",), ("土城門市倉",), ("外倉",)])

        cursor.execute("SELECT COUNT(*) FROM inventory_items")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO inventory_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
                ("706004S", "悍高智慧收納五金", "五金配件", 1200, 2500, 50, 10, "熱銷款"),
                ("101055", "頂級緩衝抽屜組", "櫥櫃五金", 800, 1800, 30, 5, "標準配備"),
                ("BED-01", "天然乳膠獨立筒床墊 (標準)", "床墊系列", 6000, 15000, 15, 3, "暢銷床墊"),
                ("FUR-99", "北歐風實木餐邊櫃", "傢俱系列", 8500, 18000, 8, 2, "展示品")
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
            
            # 同步更新庫存
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

        conn.execute("INSERT INTO delivery_orders VALUES (?,?,?,?,?,?,?,?,?)",
            (do_no, data.get("shipper_name"), data.get("warehouse", "八里倉"), data.get("so_no"),
             data.get("delivery_date"), c_id, c_name, data.get("grand_total", 0), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        total_amt = 0
        for item in data.get("items", []):
            sub = item.get("shipped_qty", 0) * item.get("unit_price", 0)
            total_amt += sub
            wh = item.get("warehouse", "八里倉")
            conn.execute("INSERT INTO delivery_items (do_number, warehouse, model, product_name, specification, color, shipped_qty, unit_price, subtotal, remarks) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (do_no, wh, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                 item.get("shipped_qty"), item.get("unit_price"), sub, item.get("remarks")))
            
            # 扣庫存
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
    conn.close()
    return jsonify({"found": True, "header": dict(dOrder), "items": items})


# --- 庫存、進銷存流水帳、應收/應付 API ---
@app.route("/api/inventory/list")
def get_inventory():
    conn = get_db_connection()
    rows = conn.execute("SELECT sku, name, category, cost, price, stock FROM inventory_items ORDER BY sku").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

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
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM ar_records WHERE receive_date BETWEEN ? AND ? ORDER BY receive_date ASC", (start, end)).fetchall()
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
      <button type="button" class="tab-btn" id="btnTabInventory" onclick="switchTab('inventory')">📊 庫存總覽</button>
      <button type="button" class="tab-btn" id="btnTabTrans" onclick="switchTab('trans')">📑 進退/銷退</button>
      <button type="button" class="tab-btn" id="btnTabArPro" onclick="switchTab('arPro')">📥 專業應收帳款</button>
      <button type="button" class="tab-btn" id="btnTabPrintCenter" onclick="switchTab('printCenter')">🖨️ 出納對帳單</button>
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
        <thead><tr><th>商品型號/SKU</th><th>商品名稱</th><th>分類</th><th>進貨成本</th><th>建議售價</th><th>目前庫存數量</th></tr></thead>
        <tbody id="inventoryTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 6. 進退/銷退單據系統 -->
  <div id="transView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>INVENTORY TRANSACTION (進退/銷退單據)</div></div>
      <div class="po-company-info"><div>即時結轉 COGS 與庫存</div></div>
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

  <!-- 7. 專業應收帳款管理 (AR Pro) -->
  <div id="arProView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>ACCOUNTS RECEIVABLE PRO (出納收款與對帳)</div></div>
      <div class="po-company-info"><div>每筆收款獨立列帳</div></div>
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

  <!-- 8. 出納對帳單列印中心 -->
  <div id="printCenterView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>DRIVER CASH REPORT (出納對帳與交現結算)</div></div>
      <div class="po-company-info"><div>依司機與起迄日期產出</div></div>
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

  <!-- 9. 應付帳款系統 (含月份與日期區間篩選) -->
  <div id="apView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>ACCOUNTS PAYABLE (應付帳款與付款管理)</div></div>
      <div class="po-company-info"><div>進貨自動拋轉應付帳款</div></div>
    </div>
    <div style="padding:20px 30px;">
      <div class="section-block no-print" style="background:#f8fafc; padding:15px; border-radius:6px; border:1px solid var(--border); margin-bottom:15px;">
        <div class="grid-3" style="align-items:end;">
          <div class="form-group"><label>依付款/進貨月份篩選 (YYYY-MM)</label><input type="month" id="ap_filter_month" oninput="loadAP()"></div>
          <div class="form-group"><label>日期區間 (起)</label><input type="date" id="ap_filter_start" onchange="loadAP()"></div>
          <div class="form-group"><label>日期區間 (迄)</label><input type="date" id="ap_filter_end" onchange="loadAP()"></div>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:10px;">
          <button type="button" class="btn-reset" onclick="resetApFilter()" style="padding:5px 10px; font-size:12px;">清除篩選</button>
          <button type="button" class="btn-print" onclick="window.print()" style="padding:5px 12px; font-size:12px;">🖨️ 列印報表</button>
        </div>
      </div>
      <table class="items-table">
        <thead><tr><th>進貨單號</th><th>進貨日期</th><th>供應商</th><th>應付總額</th><th>付款條件</th><th>預計付款日</th><th>已付金額</th><th>未付餘額</th><th>狀態</th><th class="no-print">操作</th></tr></thead>
        <tbody id="apTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 10. 應收帳款系統 (含月份與日期區間篩選) -->
  <div id="arView" class="app-view">
    <div class="po-header">
      <div class="po-title"><h1>珮藏居傢俱有限公司</h1><div>ACCOUNTS RECEIVABLE (應收帳款與收款管理)</div></div>
      <div class="po-company-info"><div>銷貨自動拋轉應收帳款</div></div>
    </div>
    <div style="padding:20px 30px;">
      <div class="section-block no-print" style="background:#f8fafc; padding:15px; border-radius:6px; border:1px solid var(--border); margin-bottom:15px;">
        <div class="grid-3" style="align-items:end;">
          <div class="form-group"><label>依收款/出貨月份篩選 (YYYY-MM)</label><input type="month" id="ar_filter_month" oninput="loadAR()"></div>
          <div class="form-group"><label>日期區間 (起)</label><input type="date" id="ar_filter_start" onchange="loadAR()"></div>
          <div class="form-group"><label>日期區間 (迄)</label><input type="date" id="ar_filter_end" onchange="loadAR()"></div>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:10px;">
          <button type="button" class="btn-reset" onclick="resetArFilter()" style="padding:5px 10px; font-size:12px;">清除篩選</button>
          <button type="button" class="btn-print" onclick="window.print()" style="padding:5px 12px; font-size:12px;">🖨️ 列印報表</button>
        </div>
      </div>
      <table class="items-table">
        <thead><tr><th>出貨單號</th><th>出貨日期</th><th>客戶名稱</th><th>應收總額</th><th>付款條件</th><th>預計收款日</th><th>已收金額</th><th>未收餘額</th><th>狀態</th></tr></thead>
        <tbody id="arTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 11. 財務系統 -->
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
  let arBaseOrder = null;
  let arEditTargetRow = 0;

  window.addEventListener('DOMContentLoaded', () => {
    ['po_order_date', 'po_delivery_date', 'in_date', 'so_order_date', 'do_date', 'arReceiveDate', 'transDate'].forEach(id => {
      const el = document.getElementById(id); if (el) el.valueAsDate = new Date();
    });
    const mEl = document.getElementById('in_month'); if (mEl) mEl.value = new Date().toISOString().slice(0, 7);
    const today = new Date();
    const firstDayStr = today.getFullYear() + "-" + String(today.getMonth() + 1).padStart(2, '0') + "-01";
    const todayStr = today.toISOString().split("T")[0];
    const pStart = document.getElementById('printStartDate'); if (pStart) pStart.value = firstDayStr;
    const pEnd = document.getElementById('printEndDate'); if (pEnd) pEnd.value = todayStr;

    for (let i = 0; i < 4; i++) { addPoItemRow(); addSoItemRow(); }
    fetch('/api/warehouses').then(r => r.json()).then(d => { if (d && d.length) warehouseOptionsList = d; });
    loadInventory();
    updateDriverLogic();
    toggleARCheckFields();
  });

  function switchTab(tab) {
    currentTab = tab;
    ['purchase', 'inbound', 'so', 'delivery', 'inventory', 'trans', 'arPro', 'printCenter', 'ap', 'ar', 'finance'].forEach(t => {
      const btn = document.getElementById('btnTab' + t.charAt(0).toUpperCase() + t.slice(1));
      const view = document.getElementById(t + 'View');
      if(btn) btn.className = (t === tab) ? 'tab-btn active' : 'tab-btn';
      if(view) view.className = (t === tab) ? 'app-view active' : 'app-view';
    });
    if (tab === 'inventory') loadInventory();
    else if (tab === 'trans') prepareTransForm();
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
    else if (currentTab === 'trans') document.getElementById('transForm').requestSubmit();
    else if (currentTab === 'arPro') document.getElementById('arForm').requestSubmit();
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

  // 庫存、進退/銷退
  function loadInventory() {
    fetch('/api/inventory/list').then(r => r.json()).then(data => {
      cachedInventory = data || [];
      const tb = document.getElementById('inventoryTableBody'); tb.innerHTML = '';
      if (!cachedInventory.length) { tb.innerHTML = `<tr><td colspan="6" class="text-muted py-3">尚無庫存資料</td></tr>`; return; }
      cachedInventory.forEach(item => {
        tb.innerHTML += `<tr><td>${item.sku}</td><td class="text-start">${item.name}</td><td>${item.category}</td><td class="text-end">$${item.cost.toLocaleString()}</td><td class="text-end">$${item.price.toLocaleString()}</td><td class="text-end fw-bold text-success">${item.stock.toLocaleString()} 件</td></tr>`;
      });
    });
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

  // 出納對帳報表中心
  function loadPrintData() {
    const start = document.getElementById("printStartDate").value;
    const end = document.getElementById("printEndDate").value;
    const driverFilter = document.getElementById("printDriverFilter").value;
    const container = document.getElementById("printContainer");
    if (!start || !end) return alert("⚠️ 請選取起迄日期！");
    container.innerHTML = '<div class="text-center py-4 text-muted">載入報表中...</div>';

    fetch(`/api/print/data?startDate=${start}&endDate=${end}`).then(r => r.json()).then(res => {
      let list = res.list || [];
      if (driverFilter !== "ALL") list = list.filter(item => item.driver === driverFilter);
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
          <tr><th colspan="11" class="bg-dark text-white py-2" style="font-size:11pt;">🚚 珮藏居 - ${title} 代收現金對帳單 (${start} ~ ${end})</th></tr>
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
    const fMonth = document.getElementById('ap_filter_month').value;
    const fStart = document.getElementById('ap_filter_start').value;
    const fEnd = document.getElementById('ap_filter_end').value;
    fetch('/api/ap/summary').then(r => r.json()).then(res => {
      const tb = document.getElementById('apTableBody'); tb.innerHTML = '';
      if (!res.data.length) { tb.innerHTML = `<tr><td colspan="10" class="text-center py-3 text-muted">無應付帳款資料</td></tr>`; return; }
      let filtered = res.data.filter(d => {
        let dt = d.inbound_date;
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
  function resetApFilter() { document.getElementById('ap_filter_month').value = ''; document.getElementById('ap_filter_start').value = ''; document.getElementById('ap_filter_end').value = ''; loadAP(); }

  function loadAR() {
    const fMonth = document.getElementById('ar_filter_month').value;
    const fStart = document.getElementById('ar_filter_start').value;
    const fEnd = document.getElementById('ar_filter_end').value;
    fetch('/api/ar/summary').then(r => r.json()).then(res => {
      const tb = document.getElementById('arTableBody'); tb.innerHTML = '';
      if (!res.data.length) { tb.innerHTML = `<tr><td colspan="9" class="text-center py-3 text-muted">無應收帳款資料</td></tr>`; return; }
      let filtered = res.data.filter(d => {
        let dt = d.delivery_date;
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
  function resetArFilter() { document.getElementById('ar_filter_month').value = ''; document.getElementById('ar_filter_start').value = ''; document.getElementById('ar_filter_end').value = ''; loadAR(); }

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)