from flask import Blueprint, jsonify, request, session
from database import get_db_connection
from datetime import datetime

finance_bp = Blueprint("finance", __name__)

@finance_bp.route("/api/vouchers/list")
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

@finance_bp.route("/api/vouchers/save", methods=["POST"])
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
            return jsonify({"success": False, "message": f"❌ 借貸不平衡！借方總計 (${total_dr:,.2f}) 與貸方總計 (${total_cr:,.2f}) 不符。"})
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

@finance_bp.route("/api/vouchers/delete/<string:v_no>", methods=["POST"])
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

@finance_bp.route("/api/finance/reports")
def get_finance_reports():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT account_code, account_name, SUM(debit) as dr, SUM(credit) as cr FROM voucher_items GROUP BY account_code")
    v_items = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"trial_balance": [dict(r) for r in v_items]})

@finance_bp.route("/api/ar/search/<string:order_id>")
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
            "oldItemFee": r["old_item_fee"], "extraFee1": r["extra_fee1"], "extraFee2": r["extra_fee2"],
            "user": r["keyin_user"], "note": r["note"]
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
            "extraFee1": base["extra_fee1"], "extraFee2": base["extra_fee2"],
            "historyRecords": history
        }
    })

@finance_bp.route("/api/ar/save", methods=["POST"])
def save_ar_record():
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        is_edit = data.get("isEditSpecificRow")
        target_id = data.get("targetRowIndex")
        
        freight = float(data.get("freight", 0))
        old_item_fee = float(data.get("oldItemFee", 0))
        extra_fee1 = float(data.get("extraFee1", 0))
        extra_fee2 = float(data.get("extraFee2", 0))
        receive_amt = float(data.get("receiveAmount", 0))
        net_cash = receive_amt - freight - old_item_fee - extra_fee1 - extra_fee2

        if is_edit and target_id:
            cursor.execute("""
                UPDATE ar_records SET receive_amount=%s, pay_type=%s, check_no=%s, check_due_date=%s, receive_date=%s, unpaid_amount=%s, driver=%s, driver_area=%s, freight=%s, old_item_fee=%s, extra_fee1=%s, extra_fee2=%s, net_cash=%s, note=%s WHERE id=%s
            """, (receive_amt, data.get("payType"), data.get("checkNo"), data.get("checkDueDate"),
                  data.get("receiveDate"), data.get("unpaidAmount"), data.get("driver"), data.get("driverArea"),
                  freight, old_item_fee, extra_fee1, extra_fee2, net_cash, data.get("note"), target_id))
        else:
            cursor.execute("""
                INSERT INTO ar_records (order_id, customer, sales_amount, deposit, receive_amount, pay_type, check_no, check_due_date, receive_date, unpaid_amount, driver, driver_area, freight, old_item_fee, extra_fee1, extra_fee2, net_cash, keyin_user, note, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (data.get("orderId"), data.get("customer"), data.get("salesAmount"), data.get("deposit"),
                  receive_amt, data.get("payType"), data.get("checkNo"), data.get("checkDueDate"),
                  data.get("receiveDate"), data.get("unpaidAmount"), data.get("driver"), data.get("driverArea"),
                  freight, old_item_fee, extra_fee1, extra_fee2, net_cash, data.get("keyinUser"), data.get("note"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "🎉 收款紀錄儲存成功！"})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

@finance_bp.route("/api/print/data")
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
            "freight": r["freight"], "oldFee": r["old_item_fee"], "extraFee1": r["extra_fee1"], "extraFee2": r["extra_fee2"],
            "netCash": r["net_cash"], "user": r["keyin_user"], "note": r["note"]
        })
    return jsonify({"type": "AR", "list": lst})

@finance_bp.route("/api/ap/summary")
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

@finance_bp.route("/api/ap/pay", methods=["POST"])
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

@finance_bp.route("/api/ap/search/<string:inbound_no>")
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

@finance_bp.route("/api/ar/summary")
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

@finance_bp.route("/api/finance/summary")
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