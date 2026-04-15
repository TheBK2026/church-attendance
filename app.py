from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
from datetime import date
import os
import pandas as pd
from reportlab.pdfgen import canvas
import smtplib
import schedule
import time
import threading
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "church_system_key"


# ===================== DATABASE =====================
def init_db():
    conn = sqlite3.connect("church.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        role TEXT,
        class_id INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS kids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        father_phone TEXT,
        mother_phone TEXT,
        dob TEXT,
        notes TEXT,
        class_id INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kid_id INTEGER,
        date TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ===================== LANDING =====================
@app.route("/")
def landing():
    conn = sqlite3.connect("church.db")
    c = conn.cursor()
    c.execute("SELECT * FROM classes")
    classes = c.fetchall()
    conn.close()
    return render_template("landing.html", classes=classes)


# ===================== LOGIN (NO PASSWORDS YET) =====================
@app.route("/login/<role>")
def login(role):

    session["role"] = role

    if role == "admin":
        return redirect("/admin")

    conn = sqlite3.connect("church.db")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE role='servant' LIMIT 1")
    servant = c.fetchone()
    conn.close()

    if servant:
        session["class_id"] = servant[4]
        return redirect(f"/class/{servant[4]}")

    return "No servant assigned"


# ===================== ADMIN =====================
@app.route("/admin")
def admin():

    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect("church.db")
    c = conn.cursor()

    c.execute("SELECT * FROM classes")
    classes = c.fetchall()

    c.execute("SELECT * FROM users WHERE role='servant'")
    servants = c.fetchall()

    conn.close()

    return render_template("admin_dashboard.html",
                           classes=classes,
                           servants=servants)


# ===================== CREATE CLASS =====================
@app.route("/add_class", methods=["POST"])
def add_class():
    name = request.form.get("name")

    conn = sqlite3.connect("church.db")
    c = conn.cursor()
    c.execute("INSERT INTO classes (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

    return redirect("/admin")


# ===================== ADD SERVANT (FIXED - SINGLE VERSION) =====================
@app.route("/add_servant", methods=["POST"])
def add_servant():

    if session.get("role") != "admin":
        return "Access Denied"

    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    class_id = request.form.get("class_id")

    conn = sqlite3.connect("church.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO users (first_name, last_name, role, class_id)
        VALUES (?, ?, 'servant', ?)
    """, (first_name, last_name, class_id))

    conn.commit()
    conn.close()

    return redirect("/admin")


# ===================== SWITCH SERVANT CLASS =====================
@app.route("/switch_servant", methods=["POST"])
def switch_servant():

    if session.get("role") != "admin":
        return "Access Denied"

    servant_id = request.form.get("servant_id")
    new_class = request.form.get("class_id")

    conn = sqlite3.connect("church.db")
    c = conn.cursor()

    c.execute("""
        UPDATE users
        SET class_id=?
        WHERE id=?
    """, (new_class, servant_id))

    conn.commit()
    conn.close()

    return redirect("/admin")


# ===================== CLASS DASHBOARD =====================
@app.route("/class/<int:class_id>")
def class_dashboard(class_id):

    conn = sqlite3.connect("church.db")
    c = conn.cursor()

    c.execute("SELECT * FROM classes")
    classes = c.fetchall()

    c.execute("SELECT * FROM kids WHERE class_id=?", (class_id,))
    kids = c.fetchall()

    conn.close()

    return render_template("class_dashboard.html",
                           classes=classes,
                           kids=kids,
                           class_id=class_id)


# ===================== ADD KID =====================
@app.route("/add_kid", methods=["POST"])
def add_kid():

    data = request.form

    conn = sqlite3.connect("church.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO kids (
            first_name, last_name,
            father_phone, mother_phone,
            dob, notes, class_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["first_name"],
        data["last_name"],
        data["father_phone"],
        data["mother_phone"],
        data["dob"],
        data["notes"],
        data["class_id"]
    ))

    conn.commit()
    conn.close()

    return redirect(f"/class/{data['class_id']}")


# ===================== ATTENDANCE =====================
@app.route("/attendance", methods=["POST"])
def attendance():

    kid_id = request.form.get("kid_id")
    status = request.form.get("status")
    today = str(date.today())

    conn = sqlite3.connect("church.db")
    c = conn.cursor()

    c.execute("""
        SELECT * FROM attendance WHERE kid_id=? AND date=?
    """, (kid_id, today))

    if c.fetchone():
        c.execute("""
            UPDATE attendance SET status=?
            WHERE kid_id=? AND date=?
        """, (status, kid_id, today))
    else:
        c.execute("""
            INSERT INTO attendance (kid_id, date, status)
            VALUES (?, ?, ?)
        """, (kid_id, today, status))

    conn.commit()
    conn.close()

    return redirect(request.referrer)


# ===================== RUN =====================
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)