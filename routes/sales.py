from flask import Blueprint, jsonify, request, session
from database import get_db_connection
from datetime import datetime

sales_bp = Blueprint("sales", __name__)

@sales_bp.route("/api/customer/<string:c_id>")
def get_customer(c_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_name FROM customers WHERE customer_code = %s", (c_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify({"found": True, "customer_name": row["customer_name"]} if row else {"found": False})

@sales_bp.route("/api/employee/<string:emp_id>")
def get_employee(emp_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT emp_name FROM employees WHERE emp_id = %s", (emp_id.upper(),))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify({"found": True, "emp_name": row["emp_name"]} if row else {"found": False})

@sales_bp.route("/api/so/save", methods=["POST"])
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
        balance_due = float(data.get("balance_due") or max(0, grand_total - deposit_paid))

        cursor.execute("""
            INSERT INTO sales_orders (so_number, sales_person, order_date, customer_code, customer_name, currency, grand_total, deposit_paid, pay_method, balance_due, remark, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (so_no, data.get("sales_person"), data.get("order_date"), data.get("customer_code"),
              data.get("customer_name"), data.get("currency"), grand_total, deposit_paid,
              data.get("pay_method"), balance_due, data.get("remark"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        for item in data.get("items", []):
            qty = int(item.get("qty") or 0)
            unit_price = float(item.get("unit_price") or 0)
            subtotal = qty * unit_price
            cursor.execute("""
                INSERT INTO sales_items (so_number, model, product_name, specification, color, quantity, unit_price, subtotal, remarks)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (so_no, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                  qty, unit_price, subtotal, item.get("remarks")))
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@sales_bp.route("/api/so/<string:so_no>")
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

@sales_bp.route("/api/delivery/save", methods=["POST"])
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
        driver_area = data.get("driver_area", "")
        freight = float(data.get("freight", 0))
        old_item_fee = float(data.get("old_item_fee", 0))
        extra_fee1 = float(data.get("extra_fee1", 0))
        extra_fee2 = float(data.get("extra_fee2", 0))
        grand_total = float(data.get("grand_total", 0))
        
        net_cash = grand_total - freight - old_item_fee - extra_fee1 - extra_fee2

        cursor.execute("""
            INSERT INTO delivery_orders (do_number, shipper_name, warehouse, so_number, delivery_date, customer_code, customer_name, driver, driver_area, freight, old_item_fee, extra_fee1, extra_fee2, net_cash, grand_total, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (do_no, data.get("shipper_name"), data.get("warehouse", "八里倉"), data.get("so_no"),
              data.get("delivery_date"), c_id, c_name, driver, driver_area, freight, old_item_fee, extra_fee1, extra_fee2, net_cash, grand_total, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        total_amt = 0
        for item in data.get("items", []):
            shipped_qty = int(item.get("shipped_qty", 0))
            unit_price = float(item.get("unit_price", 0))
            sub = shipped_qty * unit_price
            total_amt += sub
            wh = item.get("warehouse", "八里倉")
            
            cursor.execute("""
                INSERT INTO delivery_items (do_number, warehouse, model, product_name, specification, color, shipped_qty, unit_price, subtotal, remarks)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (do_no, wh, item.get("model"), item.get("name"), item.get("size"), item.get("color"),
                  shipped_qty, unit_price, sub, item.get("remarks")))
            
            sku = item.get("model")
            cursor.execute("UPDATE inventory_items SET stock = stock - %s WHERE sku = %s", (shipped_qty, sku))

        c_display = f"{c_id} {c_name}".strip() if c_id else c_name
        delivery_date = data.get("delivery_date")
        cursor.execute("""
            INSERT INTO ar_invoices (do_number, delivery_date, customer_display, total_amount, payment_term, due_date, status)
            VALUES (%s, %s, %s, %s, '月結30天', %s, '未收')
            ON CONFLICT (do_number) DO UPDATE 
            SET delivery_date = EXCLUDED.delivery_date, customer_display = EXCLUDED.customer_display, total_amount = EXCLUDED.total_amount, due_date = EXCLUDED.due_date
        """, (do_no, delivery_date, c_display, total_amt, delivery_date))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@sales_bp.route("/api/delivery/<string:do_no>")
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

@sales_bp.route("/api/sales/performance")
def get_sales_performance():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales_performance ORDER BY order_date DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@sales_bp.route("/api/sales/performance/save", methods=["POST"])
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
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@sales_bp.route("/api/sales/performance/delete/<int:sp_id>", methods=["POST"])
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