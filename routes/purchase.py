from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from database import get_db_connection
from datetime import datetime
import re

purchase_bp = Blueprint("purchase", __name__)

@purchase_bp.route("/suppliers")
def suppliers_page():
    if "user_id" not in session: return redirect(url_for("auth.login_page"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers ORDER BY supplier_code")
    suppliers_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("suppliers.html", suppliers=suppliers_list, user_name=session.get("user_name"))

@purchase_bp.route("/suppliers/add", methods=["POST"])
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
    except Exception as e: print(e)
    return redirect(url_for("purchase.suppliers_page"))

@purchase_bp.route("/suppliers/edit/<string:code>", methods=["POST"])
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
    return redirect(url_for("purchase.suppliers_page"))

@purchase_bp.route("/api/vendor/<string:v_id>")
def get_vendor(v_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT supplier_name FROM suppliers WHERE supplier_code = %s", (v_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify({"found": True, "vendor_name": row["supplier_name"]} if row else {"found": False})

@purchase_bp.route("/api/po/save", methods=["POST"])
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
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@purchase_bp.route("/api/po/<string:po_no>")
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

@purchase_bp.route("/api/inbound/save", methods=["POST"])
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
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@purchase_bp.route("/api/inbound/<string:in_no>")
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