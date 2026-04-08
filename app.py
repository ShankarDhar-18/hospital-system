from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- INIT DB ----------------
def init_db():
    conn = get_db()

    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        specialization TEXT,
        timing TEXT
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        doctor_id INTEGER,
        date TEXT,
        time TEXT,
        serial_number INTEGER,
        phone TEXT,
        status TEXT
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        medicine_name TEXT,
        total_price INTEGER,
        address TEXT,
        phone TEXT,
        status TEXT
    )
    ''')

    conn.commit()

    # Insert doctors
    if len(conn.execute("SELECT * FROM doctors").fetchall()) == 0:
        conn.execute("INSERT INTO doctors (name, specialization, timing) VALUES ('Dr. Sharma', 'Cardiologist', '10AM - 2PM')")
        conn.execute("INSERT INTO doctors (name, specialization, timing) VALUES ('Dr. Roy', 'Dermatologist', '2PM - 6PM')")
        conn.execute("INSERT INTO doctors (name, specialization, timing) VALUES ('Dr. Khan', 'Orthopedic', '6PM - 9PM')")
        conn.commit()

    # Insert medicines
    if len(conn.execute("SELECT * FROM medicines").fetchall()) == 0:
        conn.execute("INSERT INTO medicines (name, price) VALUES ('Paracetamol', 50)")
        conn.execute("INSERT INTO medicines (name, price) VALUES ('Cough Syrup', 120)")
        conn.execute("INSERT INTO medicines (name, price) VALUES ('Vitamin C', 200)")
        conn.commit()

# ---------------- HOME ----------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    if "admin" in session:
        return redirect("/admin_dashboard")
    return redirect("/register")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

        if user:
            return redirect("/login")

        conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()

        return redirect("/login")

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email == "admin" and password == "admin":
            session["admin"] = True
            return redirect("/admin_dashboard")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()

        if user:
            session["user_id"] = user["id"]
            return redirect("/dashboard")

        return "Invalid Email or Password"

    return render_template("login.html")

# ---------------- USER DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

# ---------------- DOCTORS ----------------
@app.route("/doctors")
def doctors():
    if "user_id" not in session:
        return redirect("/login")

    search = request.args.get("search")

    conn = get_db()

    if search:
        doctors = conn.execute(
            "SELECT * FROM doctors WHERE name LIKE ? OR specialization LIKE ?",
            ('%' + search + '%', '%' + search + '%')
        ).fetchall()
    else:
        doctors = conn.execute("SELECT * FROM doctors").fetchall()

    return render_template("doctors.html", doctors=doctors)
# ---------------- BOOK APPOINTMENT ----------------
@app.route("/book/<int:doctor_id>", methods=["GET", "POST"])
def book(doctor_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    if request.method == "POST":
        user_id = session["user_id"]
        date = request.form["date"]
        time = request.form["time"]
        phone = request.form["phone"]

        count = conn.execute(
            "SELECT COUNT(*) as total FROM appointments WHERE doctor_id=? AND date=? AND time=?",
            (doctor_id, date, time)
        ).fetchone()

        serial_number = count["total"] + 1

        conn.execute(
            "INSERT INTO appointments (user_id, doctor_id, date, time, serial_number, phone, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, doctor_id, date, time, serial_number, phone, "Pending")
        )
        conn.commit()

        return "Booking Requested! Wait for Admin Confirmation."

    return render_template("book.html")

# ---------------- MEDICINES ----------------
@app.route("/medicines")
def medicines():
    if "user_id" not in session:
        return redirect("/login")

    search = request.args.get("search")

    conn = get_db()

    if search:
        meds = conn.execute(
            "SELECT * FROM medicines WHERE name LIKE ?",
            ('%' + search + '%',)
        ).fetchall()
    else:
        meds = conn.execute("SELECT * FROM medicines").fetchall()

    return render_template("medicines.html", meds=meds)
# ---------------- ORDER MEDICINE ----------------
@app.route("/order/<int:id>", methods=["GET", "POST"])
def order(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    med = conn.execute("SELECT * FROM medicines WHERE id=?", (id,)).fetchone()

    if request.method == "POST":
        address = request.form["address"]
        phone = request.form["phone"]
        price = med["price"]

        if price >= 600:
            price -= 50

        conn.execute(
            "INSERT INTO orders (user_id, medicine_name, total_price, address, phone, status) VALUES (?, ?, ?, ?, ?, ?)",
            (session["user_id"], med["name"], price, address, phone, "Pending")
        )
        conn.commit()

        return f"Order placed! Total Price: ₹{price}"

    return render_template("order.html", med=med)

# ---------------- MY APPOINTMENTS ----------------
@app.route("/my_appointments")
def my_appointments():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    appointments = conn.execute('''
    SELECT a.*, d.name as doctor_name FROM appointments a
    JOIN doctors d ON a.doctor_id = d.id
    WHERE a.user_id=?
    ''', (session["user_id"],)).fetchall()

    return render_template("appointments.html", appointments=appointments)


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/login")

    conn = get_db()

    appointments = conn.execute('''
    SELECT a.*, u.name as user_name, d.name as doctor_name
    FROM appointments a
    JOIN users u ON a.user_id = u.id
    JOIN doctors d ON a.doctor_id = d.id
    ''').fetchall()

    orders = conn.execute('''
    SELECT o.*, u.name FROM orders o
    JOIN users u ON o.user_id = u.id
    ''').fetchall()

    doctors = conn.execute("SELECT * FROM doctors").fetchall()

    # ✅ NEW
    medicines = conn.execute("SELECT * FROM medicines").fetchall()

    return render_template("admin_dashboard.html",
                           appointments=appointments,
                           orders=orders,
                           doctors=doctors,
                           medicines=medicines)

# ---------------- ADD DOCTOR ----------------
@app.route("/add_doctor", methods=["GET", "POST"])
def add_doctor():
    if "admin" not in session:
        return redirect("/login")

    if request.method == "POST":
        name = request.form["name"]
        specialization = request.form["specialization"]
        timing = request.form["timing"]

        conn = get_db()
        conn.execute("INSERT INTO doctors (name, specialization, timing) VALUES (?, ?, ?)",
                     (name, specialization, timing))
        conn.commit()

        return redirect("/admin_dashboard")

    return render_template("add_doctor.html")

# ---------------- DELETE DOCTOR ----------------
@app.route("/delete_doctor/<int:id>")
def delete_doctor(id):
    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    conn.execute("DELETE FROM doctors WHERE id=?", (id,))
    conn.commit()

    return redirect("/admin_dashboard")

# ---------------- ADD MEDICINE ----------------
@app.route("/add_medicine", methods=["GET", "POST"])
def add_medicine():
    if "admin" not in session:
        return redirect("/login")

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]

        conn = get_db()
        conn.execute("INSERT INTO medicines (name, price) VALUES (?, ?)", (name, price))
        conn.commit()

        return redirect("/admin_dashboard")

    return render_template("add_medicine.html")

# ---------------- DELETE MEDICINE ----------------
@app.route("/delete_medicine/<int:id>")
def delete_medicine(id):
    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    conn.execute("DELETE FROM medicines WHERE id=?", (id,))
    conn.commit()

    return redirect("/admin_dashboard")

# ---------------- CONFIRM APPOINTMENT ----------------
@app.route("/confirm/<int:id>")
def confirm(id):
    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    data = conn.execute("SELECT * FROM appointments WHERE id=?", (id,)).fetchone()

    conn.execute("UPDATE appointments SET status='Confirmed' WHERE id=?", (id,))
    conn.commit()

    phone = data["phone"]
    message = f"Appointment confirmed! Date: {data['date']} Time: {data['time']} Serial: {data['serial_number']}"

    return redirect(f"https://wa.me/{phone}?text={message}")

# ---------------- CONFIRM ORDER ----------------
@app.route("/confirm_order/<int:id>")
def confirm_order(id):
    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    data = conn.execute("SELECT * FROM orders WHERE id=?", (id,)).fetchone()

    conn.execute("UPDATE orders SET status='Confirmed' WHERE id=?", (id,))
    conn.commit()

    phone = data["phone"]
    message = f"Your medicine order is confirmed! Medicine: {data['medicine_name']} Price: ₹{data['total_price']} Delivery: Tomorrow"

    return redirect(f"https://wa.me/{phone}?text={message}")

# ---------------- ABOUT ----------------
@app.route("/about")
def about():
    return render_template("about.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run()