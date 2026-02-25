from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
import qrcode

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE = "database.db"

# ---------------- DATABASE INIT ----------------

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_name TEXT,
        description TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        sender_name TEXT,
        contact TEXT,
        message TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (name,email,password) VALUES (?,?,?)",
                (name, email, password)
            )
            conn.commit()
        except:
            conn.close()
            return "User already exists"

        conn.close()
        return redirect("/login")

    return render_template("register.html")

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["name"] = user[1]
            return redirect("/dashboard")
        else:
            return "Invalid Email or Password"

    return render_template("login.html")

# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("dashboard.html", name=session["name"])

# ---------------- REGISTER ITEM ----------------

@app.route("/register_item", methods=["GET", "POST"])
def register_item():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        item_name = request.form["item_name"]
        description = request.form["description"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO items (user_id,item_name,description) VALUES (?,?,?)",
            (session["user_id"], item_name, description)
        )
        conn.commit()

        item_id = cursor.lastrowid
        conn.close()

        # QR generate
        qr_data = f"http://127.0.0.1:5000/found/{item_id}"
        qr = qrcode.make(qr_data)

        if not os.path.exists("static"):
            os.makedirs("static")

        qr_filename = f"qr_{item_id}.png"
        qr.save(os.path.join("static", qr_filename))

        return redirect("/my_items")

    return render_template("register_item.html")

# ---------------- MY ITEMS ----------------

@app.route("/my_items")
def my_items():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM items WHERE user_id=?",
        (session["user_id"],)
    )
    items = cursor.fetchall()
    conn.close()

    return render_template("my_items.html", items=items)

# ---------------- ALL MESSAGES (OWNER SIDE) ----------------

@app.route("/all_messages")
def all_messages():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT items.item_name, messages.sender_name,
               messages.contact, messages.message
        FROM messages
        JOIN items ON messages.item_id = items.id
        WHERE items.user_id=?
    """, (session["user_id"],))

    messages = cursor.fetchall()
    conn.close()

    return render_template("all_messages.html", messages=messages)

# ---------------- FOUND PAGE ----------------

@app.route("/found/<int:item_id>", methods=["GET", "POST"])
def found_item(item_id):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT items.item_name, items.description, users.name
        FROM items
        JOIN users ON items.user_id = users.id
        WHERE items.id=?
    """, (item_id,))
    item = cursor.fetchone()

    if request.method == "POST":
        sender_name = request.form["sender_name"]
        contact = request.form["contact"]
        message = request.form["message"]

        cursor.execute(
            "INSERT INTO messages (item_id,sender_name,contact,message) VALUES (?,?,?,?)",
            (item_id, sender_name, contact, message)
        )
        conn.commit()
        conn.close()

        return "Message Sent Successfully"

    conn.close()
    return render_template("found_item.html", item=item)

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)