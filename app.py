from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, url_for
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# 自動判斷環境：如果是 Render 雲端就用 /tmp/database.db，本地則用 database.db
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
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. 使用者資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # 2. 供應商主檔資料表
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

    # 3. 採購單主檔 (Purchase Orders)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_number TEXT PRIMARY KEY,
            purchaser TEXT NOT NULL,
            order_date TEXT NOT NULL,
            delivery_date TEXT,
            price_term TEXT,
            supplier_code TEXT,
            currency TEXT,
            grand_total REAL,
            deposit_pct REAL,
            deposit_amount REAL,
            balance_pct REAL,
            balance_amount REAL,
            remark TEXT,
            shipping_mark TEXT,
            packing TEXT,
            bank_info TEXT,
            created_at TEXT,
            FOREIGN KEY (supplier_code) REFERENCES suppliers (supplier_code)
        )
    """)

    # 4. 採購單明細 (Purchase Items)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_number TEXT NOT NULL,
            model TEXT,
            product_name TEXT,
            specification TEXT,
            color TEXT,
            quantity INTEGER,
            unit_price REAL,
            subtotal REAL,
            FOREIGN KEY (po_number) REFERENCES purchase_orders (po_number)
        )
    """)

    # 初始化預設帳號
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_users = [
            ("01", "黃詠甯", "0320"),
            ("02", "江婉秀", "1234"),
        ]
        cursor.executemany(
            "INSERT INTO users (id, name, password) VALUES (?, ?, ?)",
            default_users,
        )

    # 初始化預設供應商
    cursor.execute("SELECT COUNT(*) FROM suppliers")
    if cursor.fetchone()[0] == 0:
        default_suppliers = [
            ("328", "席德瑞思", "24567891", "王經理", "月結30天", "台新銀行 1234-5678"),
            ("427", "興隆", "87654321", "陳小姐", "現金付款", "合作金庫 8765-4321"),
        ]
        cursor.executemany(
            """INSERT INTO suppliers (supplier_code, supplier_name, tax_id, contact_info, payment_terms, bank_info) 
                VALUES (?, ?, ?, ?, ?, ?)""",
            default_suppliers,
        )

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user_name=session["user_name"])


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form["user_id"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE id = ? AND password = ?", (user_id, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("index"))
        else:
            flash("帳號或密碼錯誤，請重新輸入", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- 供應商管理 ---
@app.route("/suppliers")
def suppliers():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    suppliers_list = conn.execute(
        "SELECT * FROM suppliers ORDER BY supplier_code"
    ).fetchall()
    conn.close()

    return render_template("suppliers.html", suppliers=suppliers_list)


@app.route("/suppliers/add", methods=["POST"])
def add_supplier():
    if "user_id" not in session:
        return redirect(url_for("login"))

    code = request.form["supplier_code"]
    name = request.form["supplier_name"]
    tax_id = request.form["tax_id"]
    contact = request.form["contact_info"]
    terms = request.form["payment_terms"]
    bank = request.form["bank_info"]

    try:
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO suppliers (supplier_code, supplier_name, tax_id, contact_info, payment_terms, bank_info)
                VALUES (?, ?, ?, ?, ?, ?)""",
            (code, name, tax_id, contact, terms, bank),
        )
        conn.commit()
        conn.close()
        flash("供應商新增成功！", "success")
    except sqlite3.IntegrityError:
        flash("新增失敗：此供應商代號已存在！", "danger")

    return redirect(url_for("suppliers"))


# --- 採購單管理 ---
@app.route("/purchase-orders")
def po_list():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    pos = conn.execute("""
        SELECT po.*, s.supplier_name 
        FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_code = s.supplier_code
        ORDER BY po.order_date DESC
    """).fetchall()
    conn.close()

    return render_template("po_list.html", purchase_orders=pos)


@app.route("/purchase-orders/new", methods=["GET", "POST"])
def po_add():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    if request.method == "POST":
        po_number = request.form["po_number"]
        purchaser = session["user_name"]
        order_date = request.form["order_date"]
        delivery_date = request.form["delivery_date"]
        price_term = request.form["price_term"]
        supplier_code = request.form["supplier_code"]
        currency = request.form["currency"]

        models = request.form.getlist("model[]")
        product_names = request.form.getlist("product_name[]")
        specs = request.form.getlist("specification[]")
        colors = request.form.getlist("color[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]")

        grand_total = 0.0
        items_data = []

        for i in range(len(models)):
            if models[i].strip() != "":
                qty = int(quantities[i]) if quantities[i] else 0
                price = float(unit_prices[i]) if unit_prices[i] else 0.0
                subtotal = qty * price
                grand_total += subtotal

                items_data.append((
                    po_number,
                    models[i],
                    product_names[i],
                    specs[i],
                    colors[i],
                    qty,
                    price,
                    subtotal,
                ))

        deposit_pct = float(request.form["deposit_pct"] or 0)
        deposit_amount = grand_total * (deposit_pct / 100)
        balance_pct = 100 - deposit_pct
        balance_amount = grand_total - deposit_amount

        remark = request.form["remark"]
        shipping_mark = request.form["shipping_mark"]
        packing = request.form["packing"]
        bank_info = request.form["bank_info"]
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            conn.execute(
                """INSERT INTO purchase_orders 
                       (po_number, purchaser, order_date, delivery_date, price_term, supplier_code, currency, 
                        grand_total, deposit_pct, deposit_amount, balance_pct, balance_amount, 
                        remark, shipping_mark, packing, bank_info, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    po_number,
                    purchaser,
                    order_date,
                    delivery_date,
                    price_term,
                    supplier_code,
                    currency,
                    grand_total,
                    deposit_pct,
                    deposit_amount,
                    balance_pct,
                    balance_amount,
                    remark,
                    shipping_mark,
                    packing,
                    bank_info,
                    created_at,
                ),
            )
            conn.executemany(
                """INSERT INTO purchase_items 
                       (po_number, model, product_name, specification, color, quantity, unit_price, subtotal)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                items_data,
            )
            conn.commit()
            conn.close()
            flash("採購單建立成功！", "success")
            return redirect(url_for("po_list"))
        except sqlite3.IntegrityError:
            flash("建立失敗：此採購編號已存在！", "danger")

    suppliers_list = conn.execute("SELECT * FROM suppliers").fetchall()
    conn.close()

    default_po_no = datetime.now().strftime("%Y%m%d") + "001"

    return render_template(
        "po_add.html", suppliers=suppliers_list, default_po_no=default_po_no
    )