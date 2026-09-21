from flask import Flask, redirect, session, url_for
from database import get_db_connection
import os

app = Flask(__name__)
app.secret_key = "pezang_fixed_duplicate_endpoint_2026"

# 匯入並註冊各個功能的 Blueprint (路由藍圖)
from routes.auth import auth_bp
from routes.inventory import inventory_bp
from routes.purchase import purchase_bp
from routes.sales import sales_bp
from routes.finance import finance_bp

app.register_blueprint(auth_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(purchase_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(finance_bp)

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("auth.login_page"))
    is_accountant = session["user_id"] in ["EMP01", "EMP02", "admin"]
    from flask import render_template
    return render_template("index.html", user_name=session["user_name"], user_id=session["user_id"], is_accountant=is_accountant)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)