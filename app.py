from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "church_secret_key"

# ----------------------------
# DATABASE SETUP
# ----------------------------
def init_db():
    conn = sqlite3.connect("church.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kid_id INTEGER,
            date TEXT,
            status TEXT
        )
    """)

    # create default admin (only once)
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", "1234", "admin")
        )

    conn.commit()
    conn.close()

init_db()

# ----------------------------
# LOGIN
# ----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        conn = sqlite3.connect("church.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()

        conn.close()

        if user:
            session["user"] = user[1]
            session["role"] = user[3]
            return redirect("/")
        else:
            return "Invalid login"

    return render_template("login.html")

# ----------------------------
# LOGOUT
# ----------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ----------------------------
# HOME
# ----------------------------
@app.route('/')
def home():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("church.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM classes")
    classes = cursor.fetchall()

    cursor.execute("""
        SELECT kids.id, kids.name, classes.name
        FROM kids
        LEFT JOIN classes ON kids.class_id = classes.id
    """)
    kids = cursor.fetchall()

    conn.close()

    return render_template("index.html", classes=classes, kids=kids, role=session["role"])

# ----------------------------
# REPORT (ADMIN ONLY)
# ----------------------------
@app.route('/report')
def report():
    if "user" not in session or session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect("church.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            kids.name,
            SUM(CASE WHEN attendance.status='Present' THEN 1 ELSE 0 END),
            SUM(CASE WHEN attendance.status='Absent' THEN 1 ELSE 0 END)
        FROM kids
        LEFT JOIN attendance ON kids.id = attendance.kid_id
        GROUP BY kids.id
    """)

    data = cursor.fetchall()
    conn.close()

    return render_template("report.html", data=data)

# ----------------------------
# ADD CLASS
# ----------------------------
@app.route('/add_class', methods=['POST'])
def add_class():
    name = request.form.get("name")

    conn = sqlite3.connect("church.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO classes (name) VALUES (?)", (name,))

    conn.commit()
    conn.close()

    return redirect('/')

# ----------------------------
# ADD KID
# ----------------------------
@app.route('/add_kid', methods=['POST'])
def add_kid():
    name = request.form.get("name")
    class_id = request.form.get("class_id")

    conn = sqlite3.connect("church.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO kids (name, class_id) VALUES (?, ?)", (name, class_id))

    conn.commit()
    conn.close()

    return redirect('/')

# ----------------------------
# ATTENDANCE
# ----------------------------
@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    kid_id = request.form.get("kid_id")
    status = request.form.get("status")
    today = str(date.today())

    conn = sqlite3.connect("church.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO attendance (kid_id, date, status)
        VALUES (?, ?, ?)
    """, (kid_id, today, status))

    conn.commit()
    conn.close()

    return redirect('/')

# ----------------------------
# RUN
# ----------------------------
if __name__ == '__main__':
    app.run(debug=True)