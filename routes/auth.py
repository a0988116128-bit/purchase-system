from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from database import get_db_connection

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
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

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))