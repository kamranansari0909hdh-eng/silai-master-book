import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st


# ============================================================
# SILAI MASTER BOOK - Advanced Tailoring Management System
# ============================================================
# Features:
# - Customer management
# - One bill with multiple clothes/items
# - Separate measurements for every cloth
# - Design/photo gallery for every cloth
# - Order status and delivery date
# - Payment history (advance/partial/final payments)
# - Automatic balance calculation
# - Search
# - Printable bill
# - WhatsApp bill sharing
# - SQLite data persistence
#
# Run:
#     pip install -r requirements.txt
#     streamlit run app.py
# ============================================================

DB_FILE = "silai_master_book.db"
DESIGN_DIR = Path("design_gallery")
DESIGN_DIR.mkdir(exist_ok=True)

STATUSES = ["Pending", "In Progress", "Completed"]

MEASUREMENT_FIELDS = [
    "Chest",
    "Waist",
    "Hip",
    "Shoulder",
    "Neck",
    "Armhole",
    "Sleeves",
    "Sleeves Opening",
    "Front Length",
    "Back Length",
    "Kurti/Blouse Length",
    "Pant Length",
    "Knee",
    "Thigh",
    "Bottom",
    "Rise",
    "Other Notes",
]


# ============================================================
# DATABASE
# ============================================================

def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            delivery_date TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Pending',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            price REAL NOT NULL DEFAULT 0,
            description TEXT DEFAULT '',
            measurements TEXT DEFAULT '{}',
            design_file TEXT DEFAULT '',
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            method TEXT NOT NULL DEFAULT 'Cash',
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ---------------- Customers ----------------

def add_customer(name, phone, address, notes):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO customers (name, phone, address, notes, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        name.strip(),
        phone.strip(),
        address.strip(),
        notes.strip(),
        now(),
    ))
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def update_customer(cid, name, phone, address, notes):
    conn = db()
    conn.execute("""
        UPDATE customers
        SET name=?, phone=?, address=?, notes=?
        WHERE id=?
    """, (name.strip(), phone.strip(), address.strip(), notes.strip(), cid))
    conn.commit()
    conn.close()


def customers():
    conn = db()
    rows = conn.execute(
        "SELECT * FROM customers ORDER BY name COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return rows


def customer(cid):
    conn = db()
    row = conn.execute(
        "SELECT * FROM customers WHERE id=?", (cid,)
    ).fetchone()
    conn.close()
    return row


# ---------------- Orders ----------------

def create_order(customer_id, delivery_date, status, notes, items):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO orders
        (customer_id, order_date, delivery_date, status, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        date.today().isoformat(),
        delivery_date.isoformat() if delivery_date else "",
        status,
        notes.strip(),
        now(),
    ))

    order_id = cur.lastrowid

    for item in items:
        cur.execute("""
            INSERT INTO order_items
            (order_id, item_name, quantity, price, description,
             measurements, design_file)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            item["item_name"].strip(),
            int(item["quantity"]),
            float(item["price"]),
            item["description"].strip(),
            json.dumps(item["measurements"], ensure_ascii=False),
            item["design_file"],
        ))

    conn.commit()
    conn.close()
    return order_id


def orders():
    conn = db()
    rows = conn.execute("""
        SELECT
            o.*,
            c.name AS customer_name,
            c.phone AS customer_phone
        FROM orders o
        JOIN customers c ON c.id=o.customer_id
        ORDER BY o.id DESC
    """).fetchall()
    conn.close()
    return rows


def order(order_id):
    conn = db()
    row = conn.execute("""
        SELECT
            o.*,
            c.name AS customer_name,
            c.phone AS customer_phone,
            c.address AS customer_address
        FROM orders o
        JOIN customers c ON c.id=o.customer_id
        WHERE o.id=?
    """, (order_id,)).fetchone()
    conn.close()
    return row


def order_items(order_id):
    conn = db()
    rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id=? ORDER BY id",
        (order_id,)
    ).fetchall()
    conn.close()
    return rows


def update_order_status(order_id, status):
    conn = db()
    conn.execute(
        "UPDATE orders SET status=? WHERE id=?",
        (status, order_id)
    )
    conn.commit()
    conn.close()


# ---------------- Payments ----------------

def add_payment(order_id, amount, payment_date, method, note):
    conn = db()
    conn.execute("""
        INSERT INTO payments
        (order_id, amount, payment_date, method, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        order_id,
        float(amount),
        payment_date.isoformat(),
        method,
        note.strip(),
        now(),
    ))
    conn.commit()
    conn.close()


def payments(order_id):
    conn = db()
    rows = conn.execute("""
        SELECT * FROM payments
        WHERE order_id=?
        ORDER BY payment_date DESC, id DESC
    """, (order_id,)).fetchall()
    conn.close()
    return rows


def total_bill(order_id):
    conn = db()
    value = conn.execute("""
        SELECT COALESCE(SUM(quantity * price), 0)
        FROM order_items
        WHERE order_id=?
    """, (order_id,)).fetchone()[0]
    conn.close()
    return float(value)


def total_paid(order_id):
    conn = db()
    value = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM payments
        WHERE order_id=?
    """, (order_id,)).fetchone()[0]
    conn.close()
    return float(value)


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now().isoformat(timespec="seconds")


def money(value):
    return f"₹{float(value):,.2f}"


def customer_label(row):
    phone = row["phone"] or ""
    return f"{row['name']} — {phone}" if phone else row["name"]


def safe_filename(name):
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-."
    return "".join(ch if ch in allowed else "_" for ch in name)


def save_design(uploaded_file, order_temp_name):
    if not uploaded_file:
        return ""

    suffix = Path(uploaded_file.name).suffix.lower()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = safe_filename(f"{order_temp_name}_{stamp}{suffix}")
    path = DESIGN_DIR / filename
    path.write_bytes(uploaded_file.getbuffer())
    return str(path)


def load_measurements(row):
    try:
        return json.loads(row["measurements"] or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


def whatsapp_url(phone, message):
    number = "".join(ch for ch in (phone or "") if ch.isdigit())

    # If an Indian 10-digit number is entered, add country code.
    if len(number) == 10:
        number = "91" + number

    if not number:
        return None

    return f"https://wa.me/{number}?text={quote(message)}"


def build_whatsapp_message(order_id):
    o = order(order_id)
    items = order_items(order_id)
    paid = total_paid(order_id)
    total = total_bill(order_id)
    balance = total - paid

    lines = [
        "🧵 SILAI MASTER BOOK",
        f"Order #: {order_id}",
        f"Customer: {o['customer_name']}",
        f"Order Date: {o['order_date']}",
        f"Delivery Date: {o['delivery_date'] or '-'}",
        f"Status: {o['status']}",
        "",
        "Items:",
    ]

    for i, item in enumerate(items, 1):
        amount = item["quantity"] * item["price"]
        lines.append(
            f"{i}. {item['item_name']} x {item['quantity']} = {money(amount)}"
        )

    lines += [
        "",
        f"Total Bill: {money(total)}",
        f"Paid: {money(paid)}",
        f"Balance Due: {money(balance)}",
        "",
        "Thank you for choosing Silai Master Book.",
    ]

    return "\n".join(lines)


def bill_html(order_id):
    o = order(order_id)
    items = order_items(order_id)
    pay = payments(order_id)
    total = total_bill(order_id)
    paid = total_paid(order_id)
    balance = total - paid

    rows = ""
    for i, item in enumerate(items, 1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td>{item['item_name']}</td>
            <td>{item['quantity']}</td>
            <td>{money(item['price'])}</td>
            <td>{money(item['quantity'] * item['price'])}</td>
        </tr>
        """

    payment_rows = ""
    for p in pay:
        payment_rows += f"""
        <tr>
            <td>{p['payment_date']}</td>
            <td>{p['method']}</td>
            <td>{money(p['amount'])}</td>
            <td>{p['note'] or ''}</td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Silai Master Book - Order #{order_id}</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 30px;
    color: #222;
}}
h1 {{ margin-bottom: 4px; }}
.small {{ color: #666; }}
.box {{
    border: 1px solid #ddd;
    padding: 14px;
    margin: 12px 0;
    border-radius: 8px;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 12px;
}}
th, td {{
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}}
th {{ background: #f3f3f3; }}
.total {{
    text-align: right;
    font-size: 18px;
    line-height: 1.7;
}}
@media print {{
    body {{ margin: 10px; }}
    .no-print {{ display:none; }}
}}
</style>
</head>
<body>
<h1>🧵 Silai Master Book</h1>
<div class="small">Tailoring Bill</div>

<div class="box">
<strong>Order #:</strong> {order_id}<br>
<strong>Customer:</strong> {o['customer_name']}<br>
<strong>Phone:</strong> {o['customer_phone'] or '-'}<br>
<strong>Order Date:</strong> {o['order_date']}<br>
<strong>Delivery Date:</strong> {o['delivery_date'] or '-'}<br>
<strong>Status:</strong> {o['status']}
</div>

<h3>Items</h3>
<table>
<tr>
<th>#</th><th>Item</th><th>Qty</th><th>Price</th><th>Amount</th>
</tr>
{rows}
</table>

<div class="box total">
<strong>Total: {money(total)}</strong><br>
Paid: {money(paid)}<br>
<strong>Balance Due: {money(balance)}</strong>
</div>

<h3>Payment History</h3>
<table>
<tr><th>Date</th><th>Method</th><th>Amount</th><th>Note</th></tr>
{payment_rows if payment_rows else '<tr><td colspan="4">No payments recorded</td></tr>'}
</table>

<div class="box">
<strong>Order Notes:</strong><br>
{o['notes'] or '-'}
</div>

<p class="small">Generated by Silai Master Book</p>
</body>
</html>
"""


# ============================================================
# APP CONFIG
# ============================================================

st.set_page_config(
    page_title="Silai Master Book",
    page_icon="🧵",
    layout="wide",
)

init_db()

st.title("🧵 Silai Master Book")
st.caption(
    "Advanced Tailoring Management — Customers • Measurements • "
    "Multi-item Bills • Payments • WhatsApp"
)

with st.sidebar:
    st.header("📋 Menu")

    page = st.radio(
        "Open section",
        [
            "Dashboard",
            "Customers",
            "New Bill",
            "Orders & Payments",
            "Measurements",
            "Design Gallery",
        ],
    )

    st.divider()
    st.info(
        "All business data is saved in SQLite.\n\n"
        f"Database: `{DB_FILE}`\n\n"
        f"Design photos: `{DESIGN_DIR}/`"
    )


