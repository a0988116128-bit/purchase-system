from flask import Blueprint, jsonify, request, session
from database import get_db_connection
from datetime import datetime

inventory_bp = Blueprint("inventory", __name__)

@inventory_bp.route("/api/inventory/list")
def get_inventory():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT sku, name, category, spec, color, cost, price, stock, safety_stock, note FROM inventory_items ORDER BY sku")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@inventory_bp.route("/api/inventory/save", methods=["POST"])
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

@inventory_bp.route("/api/inventory/delete/<string:sku>", methods=["POST"])
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

@inventory_bp.route("/api/inventory/transaction/save", methods=["POST"])
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