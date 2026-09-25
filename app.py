from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import sqlite3
from blockchain import Blockchain

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
DB = os.environ.get("DATABASE_PATH", "bank.db")
blockchain = Blockchain()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        account_number TEXT UNIQUE NOT NULL,
        balance REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        amount REAL NOT NULL,
        transaction_type TEXT NOT NULL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        block_hash TEXT,
        status TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def make_account_number(user_id):
    return "2026" + str(user_id).zfill(6)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        phone = request.form["phone"].strip()
        password = request.form["password"]

        if not name or not email or not phone or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO users (name,email,phone,password_hash,account_number) VALUES (?,?,?,?,?)",
                (name, email, phone, generate_password_hash(password), "TEMP")
            )
            user_id = cur.lastrowid
            account = make_account_number(user_id)
            conn.execute("UPDATE users SET account_number=? WHERE id=?", (account, user_id))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("Email already registered.", "error")
            return redirect(url_for("register"))
        conn.close()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    transactions = conn.execute("""
        SELECT * FROM transactions
        WHERE sender=? OR receiver=?
        ORDER BY id DESC LIMIT 5
    """, (user["account_number"], user["account_number"])).fetchall()
    conn.close()
    return render_template("dashboard.html", user=user, transactions=transactions)

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Enter a valid positive amount.", "error")
            return redirect(url_for("deposit"))

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        new_balance = user["balance"] + amount

        tx = {
            "type": "DEPOSIT",
            "sender": "BANK",
            "receiver": user["account_number"],
            "amount": amount
        }
        block = blockchain.add_block(tx)

        conn.execute("UPDATE users SET balance=? WHERE id=?", (new_balance, user["id"]))
        conn.execute("""
            INSERT INTO transactions
            (sender,receiver,amount,transaction_type,block_hash,status)
            VALUES (?,?,?,?,?,?)
        """, ("BANK", user["account_number"], amount, "DEPOSIT", block.hash, "SUCCESS"))
        conn.commit()
        conn.close()

        flash(f"₹{amount:.2f} deposited successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("deposit.html")

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Enter a valid positive amount.", "error")
            return redirect(url_for("withdraw"))

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

        if user["balance"] < amount:
            conn.close()
            flash("Insufficient balance.", "error")
            return redirect(url_for("withdraw"))

        new_balance = user["balance"] - amount
        tx = {
            "type": "WITHDRAW",
            "sender": user["account_number"],
            "receiver": "BANK",
            "amount": amount
        }
        block = blockchain.add_block(tx)

        conn.execute("UPDATE users SET balance=? WHERE id=?", (new_balance, user["id"]))
        conn.execute("""
            INSERT INTO transactions
            (sender,receiver,amount,transaction_type,block_hash,status)
            VALUES (?,?,?,?,?,?)
        """, (user["account_number"], "BANK", amount, "WITHDRAW", block.hash, "SUCCESS"))
        conn.commit()
        conn.close()

        flash(f"₹{amount:.2f} withdrawn successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("withdraw.html")

@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    if request.method == "POST":
        receiver = request.form["receiver"].strip()
        try:
            amount = float(request.form["amount"])
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Enter a valid positive amount.", "error")
            return redirect(url_for("transfer"))

        conn = get_db()
        sender = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        recipient = conn.execute("SELECT * FROM users WHERE account_number=?", (receiver,)).fetchone()

        if not recipient:
            conn.close()
            flash("Receiver account does not exist.", "error")
            return redirect(url_for("transfer"))

        if recipient["id"] == sender["id"]:
            conn.close()
            flash("You cannot transfer money to yourself.", "error")
            return redirect(url_for("transfer"))

        if sender["balance"] < amount:
            conn.close()
            flash("Insufficient balance.", "error")
            return redirect(url_for("transfer"))

        tx = {
            "type": "TRANSFER",
            "sender": sender["account_number"],
            "receiver": recipient["account_number"],
            "amount": amount
        }
        block = blockchain.add_block(tx)

        conn.execute("UPDATE users SET balance=balance-? WHERE id=?", (amount, sender["id"]))
        conn.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, recipient["id"]))
        conn.execute("""
            INSERT INTO transactions
            (sender,receiver,amount,transaction_type,block_hash,status)
            VALUES (?,?,?,?,?,?)
        """, (sender["account_number"], recipient["account_number"], amount, "TRANSFER", block.hash, "SUCCESS"))
        conn.commit()
        conn.close()

        flash(f"₹{amount:.2f} transferred successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("transfer.html")

@app.route("/transactions")
@login_required
def transactions():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    rows = conn.execute("""
        SELECT * FROM transactions
        WHERE sender=? OR receiver=?
        ORDER BY id DESC
    """, (user["account_number"], user["account_number"])).fetchall()
    conn.close()
    return render_template("transactions.html", transactions=rows, account=user["account_number"])

@app.route("/blockchain")
@login_required
def blockchain_view():
    return render_template("blockchain.html", chain=blockchain.chain)

@app.route("/verify")
@login_required
def verify():
    valid, errors = blockchain.is_valid()
    return render_template("verify.html", valid=valid, errors=errors)

@app.route("/api/blockchain")
@login_required
def api_blockchain():
    return jsonify(blockchain.to_dict())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
