from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from pathlib import Path
import sqlite3
from functools import wraps


# =========================================================
# APP CONFIGURATION
# =========================================================

app = Flask(__name__)

app.secret_key = "smart-hospital-secret-key-2026"

BASE_DIR = Path(__file__).resolve().parent

DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "hospital.db"

DB_DIR.mkdir(exist_ok=True)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# DATABASE HELPERS
# =========================================================

def add_column_if_missing(conn, table, column, definition):

    columns = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    existing_columns = [
        column_info["name"]
        for column_info in columns
    ]

    if column not in existing_columns:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db()

    # -----------------------------------------------------
    # PATIENTS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            phone TEXT NOT NULL,
            department TEXT NOT NULL,
            emergency_level TEXT NOT NULL,
            symptoms TEXT,
            status TEXT DEFAULT 'Waiting',
            created_at TEXT NOT NULL
        )
    """)


    # -----------------------------------------------------
    # BEDS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS beds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bed_number TEXT UNIQUE NOT NULL,
            ward TEXT NOT NULL,
            bed_type TEXT NOT NULL,
            status TEXT DEFAULT 'Available'
        )
    """)


    # -----------------------------------------------------
    # AMBULANCES
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ambulances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ambulance_number TEXT UNIQUE NOT NULL,
            driver_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            status TEXT DEFAULT 'Available'
        )
    """)


    # -----------------------------------------------------
    # COMPATIBILITY COLUMNS
    # -----------------------------------------------------

    add_column_if_missing(
        conn,
        "beds",
        "floor",
        "TEXT DEFAULT 'Ground Floor'"
    )

    add_column_if_missing(
        conn,
        "beds",
        "room",
        "TEXT DEFAULT 'General Ward'"
    )

    add_column_if_missing(
        conn,
        "ambulances",
        "location",
        "TEXT DEFAULT 'Hospital Campus'"
    )


    # -----------------------------------------------------
    # DEMO BEDS
    # -----------------------------------------------------

    bed_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM beds
    """).fetchone()["total"]


    if bed_count == 0:

        beds = [

            (
                "B-101",
                "General Ward",
                "General",
                "Ground Floor",
                "Room 101"
            ),

            (
                "B-102",
                "General Ward",
                "General",
                "Ground Floor",
                "Room 102"
            ),

            (
                "B-103",
                "General Ward",
                "General",
                "Ground Floor",
                "Room 103"
            ),

            (
                "B-104",
                "General Ward",
                "General",
                "Ground Floor",
                "Room 104"
            ),

            (
                "ICU-01",
                "ICU",
                "ICU",
                "First Floor",
                "ICU Room 01"
            ),

            (
                "ICU-02",
                "ICU",
                "ICU",
                "First Floor",
                "ICU Room 02"
            ),

            (
                "ICU-03",
                "ICU",
                "ICU",
                "First Floor",
                "ICU Room 03"
            ),

            (
                "ICU-04",
                "ICU",
                "ICU",
                "First Floor",
                "ICU Room 04"
            )

        ]


        conn.executemany("""
            INSERT INTO beds
            (
                bed_number,
                ward,
                bed_type,
                floor,
                room,
                status
            )
            VALUES (?, ?, ?, ?, ?, 'Available')
        """, beds)


    # -----------------------------------------------------
    # DEMO AMBULANCES
    # -----------------------------------------------------

    ambulance_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM ambulances
    """).fetchone()["total"]


    if ambulance_count == 0:

        ambulances = [

            (
                "AMB-01",
                "Rahul Kumar",
                "9876543210",
                "Emergency Gate"
            ),

            (
                "AMB-02",
                "Amit Singh",
                "9876543211",
                "Hospital Campus"
            ),

            (
                "AMB-03",
                "Arjun Sharma",
                "9876543212",
                "City Route"
            )

        ]


        conn.executemany("""
            INSERT INTO ambulances
            (
                ambulance_number,
                driver_name,
                phone,
                location,
                status
            )
            VALUES (?, ?, ?, ?, 'Available')
        """, ambulances)


    conn.commit()
    conn.close()


# =========================================================
# LOGIN HELPERS
# =========================================================

def login_required(role=None):

    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):

            if "user_role" not in session:

                return redirect(url_for("login"))

            if role and session.get("user_role") != role:

                return redirect(url_for("login"))

            return function(*args, **kwargs)

        return wrapper

    return decorator


# =========================================================
# TOKEN GENERATOR
# =========================================================

def generate_token():

    conn = get_db()

    total = conn.execute("""
        SELECT COUNT(*) AS total
        FROM patients
        WHERE date(created_at) =
              date('now', 'localtime')
    """).fetchone()["total"]

    conn.close()

    return f"E-{total + 1:03d}"


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():

    return render_template("index.html")


# =========================================================
# GENERAL LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        # Demo login system
        if email == "admin@smarthospital.com" and password == "admin123":

            session["user_role"] = "admin"
            session["user_email"] = email

            return redirect(url_for("admin"))

        elif email == "doctor@smarthospital.com" and password == "doctor123":

            session["user_role"] = "doctor"
            session["user_email"] = email

            return redirect(url_for("doctor"))

        elif email == "staff@smarthospital.com" and password == "staff123":

            session["user_role"] = "staff"
            session["user_email"] = email

            return redirect(url_for("staff"))

        else:

            return render_template(
                "login.html",
                error="Invalid email or password."
            )

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


# =========================================================
# PATIENT REGISTRATION
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        age = request.form.get("age", "").strip()

        gender = request.form.get("gender", "").strip()

        phone = request.form.get("phone", "").strip()

        department = request.form.get(
            "department",
            ""
        ).strip()

        emergency_level = request.form.get(
            "emergency_level",
            "Normal"
        ).strip()

        symptoms = request.form.get(
            "symptoms",
            ""
        ).strip()


        if not name or not age or not gender or not phone:

            return render_template(
                "register.html",
                error="Please fill all required fields."
            )


        token = generate_token()


        created_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )


        conn = get_db()


        conn.execute("""
            INSERT INTO patients
            (
                token,
                name,
                age,
                gender,
                phone,
                department,
                emergency_level,
                symptoms,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            token,
            name,
            age,
            gender,
            phone,
            department,
            emergency_level,
            symptoms,
            "Waiting",
            created_at

        ))


        conn.commit()
        conn.close()


        return redirect(
            url_for(
                "token",
                token=token
            )
        )


    return render_template("register.html")


# =========================================================
# TOKEN PAGE
# =========================================================

@app.route("/token/<token>")
def token(token):

    conn = get_db()


    patient = conn.execute("""
        SELECT *
        FROM patients
        WHERE token = ?
    """, (token,)).fetchone()


    conn.close()


    if patient is None:

        return "Token not found", 404


    return render_template(
        "token.html",
        patient=patient
    )


# =========================================================
# PATIENTS PAGE
# =========================================================

@app.route("/patients")
def patients():

    conn = get_db()


    patient_list = conn.execute("""
        SELECT *
        FROM patients
        ORDER BY id DESC
    """).fetchall()


    conn.close()


    return render_template(
        "patients.html",
        patients=patient_list
    )


# =========================================================
# DOCTOR LOGIN
# =========================================================

@app.route(
    "/doctor-login",
    methods=["GET", "POST"]
)
def doctor_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()


        if (
            email == "doctor@smarthospital.com"
            and
            password == "doctor123"
        ):

            session["user_role"] = "doctor"

            session["user_email"] = email

            return redirect(
                url_for("doctor")
            )


        return render_template(
            "doctor_login.html",
            error="Invalid doctor credentials."
        )


    return render_template(
        "doctor_login.html"
    )


# =========================================================
# DOCTOR PORTAL
# =========================================================

@app.route("/doctor")
def doctor():

    return render_template(
        "doctor.html"
    )


# =========================================================
# DOCTOR DASHBOARD / LIVE QUEUE
# =========================================================

@app.route("/dashboard")
def dashboard():

    conn = get_db()


    waiting = conn.execute("""
        SELECT COUNT(*) AS total
        FROM patients
        WHERE status = 'Waiting'
    """).fetchone()["total"]


    critical = conn.execute("""
        SELECT COUNT(*) AS total
        FROM patients
        WHERE emergency_level = 'Critical'
        AND status != 'Completed'
    """).fetchone()["total"]


    serious = conn.execute("""
        SELECT COUNT(*) AS total
        FROM patients
        WHERE emergency_level = 'Serious'
        AND status != 'Completed'
    """).fetchone()["total"]


    completed = conn.execute("""
        SELECT COUNT(*) AS total
        FROM patients
        WHERE status = 'Completed'
    """).fetchone()["total"]


    total_patients = conn.execute("""
        SELECT COUNT(*) AS total
        FROM patients
    """).fetchone()["total"]


    patient_list = conn.execute("""
        SELECT *
        FROM patients

        ORDER BY

            CASE emergency_level

                WHEN 'Critical' THEN 1

                WHEN 'Serious' THEN 2

                WHEN 'Normal' THEN 3

                ELSE 4

            END,

            id ASC
    """).fetchall()


    conn.close()


    stats = {

        "waiting": waiting,

        "critical": critical,

        "serious": serious,

        "completed": completed,

        "total": total_patients

    }


    return render_template(

        "dashboard.html",

        stats=stats,

        patients=patient_list

    )


# =========================================================
# UPDATE PATIENT STATUS
# =========================================================

@app.route(
    "/update-status/<int:patient_id>",
    methods=["POST"]
)
def update_status(patient_id):

    status = request.form.get(
        "status",
        ""
    )


    allowed_statuses = [

        "Waiting",

        "In Treatment",

        "Completed"

    ]


    if status not in allowed_statuses:

        return "Invalid status", 400


    conn = get_db()


    conn.execute("""
        UPDATE patients

        SET status = ?

        WHERE id = ?
    """, (

        status,

        patient_id

    ))


    conn.commit()

    conn.close()


    return redirect(
        url_for("dashboard")
    )


# =========================================================
# BEDS & ICU
# =========================================================

@app.route("/beds")
def beds():

    conn = get_db()


    all_beds = conn.execute("""
        SELECT
            id,
            bed_number,
            ward,
            bed_type,
            status,
            floor,
            room
        FROM beds

        ORDER BY

            CASE bed_type

                WHEN 'ICU' THEN 1

                ELSE 2

            END,

            id ASC
    """).fetchall()


    total_beds = conn.execute("""
        SELECT COUNT(*) AS total
        FROM beds
    """).fetchone()["total"]


    available_beds = conn.execute("""
        SELECT COUNT(*) AS total
        FROM beds
        WHERE status = 'Available'
    """).fetchone()["total"]


    occupied_beds = conn.execute("""
        SELECT COUNT(*) AS total
        FROM beds
        WHERE status = 'Occupied'
    """).fetchone()["total"]


    available_icu = conn.execute("""
        SELECT COUNT(*) AS total
        FROM beds

        WHERE bed_type = 'ICU'

        AND status = 'Available'
    """).fetchone()["total"]


    conn.close()


    bed_stats = {

        "total": total_beds,

        "available": available_beds,

        "occupied": occupied_beds,

        "icu": available_icu

    }


    return render_template(

        "beds.html",

        beds=all_beds,

        stats=bed_stats

    )


# =========================================================
# UPDATE BED
# =========================================================

@app.route(
    "/update-bed/<int:bed_id>",
    methods=["POST"]
)
def update_bed(bed_id):

    status = request.form.get(
        "status",
        ""
    )


    allowed_statuses = [

        "Available",

        "Occupied",

        "Maintenance"

    ]


    if status not in allowed_statuses:

        return "Invalid bed status", 400


    conn = get_db()


    conn.execute("""
        UPDATE beds

        SET status = ?

        WHERE id = ?
    """, (

        status,

        bed_id

    ))


    conn.commit()

    conn.close()


    return redirect(
        url_for("beds")
    )


# =========================================================
# AMBULANCES
# =========================================================

@app.route("/ambulances")
def ambulances():

    conn = get_db()


    ambulance_list = conn.execute("""
        SELECT
            id,
            ambulance_number,
            driver_name,
            phone,
            location,
            status
        FROM ambulances

        ORDER BY id ASC
    """).fetchall()


    total = conn.execute("""
        SELECT COUNT(*) AS total
        FROM ambulances
    """).fetchone()["total"]


    available = conn.execute("""
        SELECT COUNT(*) AS total
        FROM ambulances
        WHERE status = 'Available'
    """).fetchone()["total"]


    on_duty = conn.execute("""
        SELECT COUNT(*) AS total
        FROM ambulances
        WHERE status = 'On Duty'
    """).fetchone()["total"]


    maintenance = conn.execute("""
        SELECT COUNT(*) AS total
        FROM ambulances
        WHERE status = 'Maintenance'
    """).fetchone()["total"]


    conn.close()


    stats = {

        "total": total,

        "available": available,

        "on_duty": on_duty,

        "maintenance": maintenance

    }


    return render_template(

        "ambulances.html",

        ambulances=ambulance_list,

        stats=stats

    )


# =========================================================
# UPDATE AMBULANCE
# =========================================================

@app.route(
    "/update-ambulance/<int:ambulance_id>",
    methods=["POST"]
)
def update_ambulance(ambulance_id):

    status = request.form.get(
        "status",
        ""
    )


    allowed_statuses = [

        "Available",

        "On Duty",

        "Maintenance"

    ]


    if status not in allowed_statuses:

        return "Invalid ambulance status", 400


    conn = get_db()


    conn.execute("""
        UPDATE ambulances

        SET status = ?

        WHERE id = ?
    """, (

        status,

        ambulance_id

    ))


    conn.commit()

    conn.close()


    return redirect(
        url_for("ambulances")
    )


# =========================================================
# STAFF LOGIN
# =========================================================

@app.route(
    "/staff-login",
    methods=["GET", "POST"]
)
def staff_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()


        if (
            email == "staff@smarthospital.com"
            and
            password == "staff123"
        ):

            session["user_role"] = "staff"

            session["user_email"] = email

            return redirect(
                url_for("staff")
            )


        return render_template(

            "staff_login.html",

            error="Invalid staff credentials."

        )


    return render_template(
        "staff_login.html"
    )


# =========================================================
# STAFF PORTAL
# =========================================================

@app.route("/staff")
def staff():

    return render_template(
        "staff.html"
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin-login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()


        if (
            email == "admin@smarthospital.com"
            and
            password == "admin123"
        ):

            session["user_role"] = "admin"

            session["user_email"] = email

            return redirect(
                url_for("admin")
            )


        return render_template(

            "admin_login.html",

            error="Invalid admin credentials."

        )


    return render_template(
        "admin_login.html"
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    conn = get_db()


    total_patients = conn.execute("""
        SELECT COUNT(*) AS total
        FROM patients
    """).fetchone()["total"]


    critical_cases = conn.execute("""
        SELECT COUNT(*) AS total
        FROM patients

        WHERE emergency_level = 'Critical'

        AND status != 'Completed'
    """).fetchone()["total"]


    completed_cases = conn.execute("""
        SELECT COUNT(*) AS total
        FROM patients

        WHERE status = 'Completed'
    """).fetchone()["total"]


    available_beds = conn.execute("""
        SELECT COUNT(*) AS total
        FROM beds

        WHERE status = 'Available'
    """).fetchone()["total"]


    available_icu = conn.execute("""
        SELECT COUNT(*) AS total
        FROM beds

        WHERE bed_type = 'ICU'

        AND status = 'Available'
    """).fetchone()["total"]


    available_ambulances = conn.execute("""
        SELECT COUNT(*) AS total
        FROM ambulances

        WHERE status = 'Available'
    """).fetchone()["total"]


    conn.close()


    stats = {

        "total_patients": total_patients,

        "critical": critical_cases,

        "completed": completed_cases,

        "available_beds": available_beds,

        "available_icu": available_icu,

        "available_ambulances":
            available_ambulances

    }


    return render_template(

        "admin.html",

        stats=stats

    )


# =========================================================
# ABOUT
# =========================================================

@app.route("/about")
def about():

    return render_template(
        "about.html"
    )


# =========================================================
# DATABASE START
# =========================================================

init_db()


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )