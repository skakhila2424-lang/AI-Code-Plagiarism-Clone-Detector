from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import re
from difflib import SequenceMatcher

app = Flask(__name__)
app.secret_key = "ai_code_plagiarism_detector_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------- DATABASE ----------------

def init_database():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


# ---------------- CODE CLEANING ----------------

def clean_code(code):
    code = re.sub(r"#.*", "", code)
    code = re.sub(r"//.*", "", code)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r"\s+", " ", code)

    return code.strip().lower()


# ---------------- SIMILARITY ----------------

def calculate_similarity(code1, code2):

    code1 = clean_code(code1)
    code2 = clean_code(code2)

    if not code1 or not code2:
        return 0.0

    similarity = SequenceMatcher(
        None,
        code1,
        code2
    ).ratio()

    return round(similarity * 100, 2)


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    message = ""

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:

            message = "Username and password are required."

            return render_template(
                "register.html",
                message=message
            )

        connection = sqlite3.connect(DATABASE)
        cursor = connection.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users
                (username, email, password)
                VALUES (?, ?, ?)
                """,
                (username, email, password)
            )

            connection.commit()
            connection.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            connection.close()

            message = "Username already exists."

            return render_template(
                "register.html",
                message=message
            )

    return render_template(
        "register.html",
        message=message
    )


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    message = ""

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        connection = sqlite3.connect(DATABASE)
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, username
            FROM users
            WHERE username = ?
            AND password = ?
            """,
            (username, password)
        )

        user = cursor.fetchone()

        connection.close()

        if user:

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect(url_for("dashboard"))

        message = "Invalid username or password."

    return render_template(
        "login.html",
        message=message
    )


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session.get("username")
    )


# ---------------- SOURCE FILE UPLOAD ----------------

@app.route("/upload-source", methods=["GET", "POST"])
def upload_source():

    if "user_id" not in session:
        return redirect(url_for("login"))

    message = ""

    if request.method == "POST":

        files = request.files.getlist("source_files")

        saved = 0

        for file in files:

            if file and file.filename:

                filename = os.path.basename(
                    file.filename
                )

                path = os.path.join(
                    UPLOAD_FOLDER,
                    "source_" + filename
                )

                file.save(path)

                saved += 1

        message = (
            f"{saved} source file(s) uploaded successfully."
        )

    return render_template(
        "upload_source.html",
        message=message
    )


# ---------------- SUSPICIOUS CODE UPLOAD ----------------

@app.route("/upload-code", methods=["GET", "POST"])
def upload_code():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        file = request.files.get("code_file")

        if not file or not file.filename:

            return render_template(
                "upload_code.html",
                message="Please select a code file."
            )

        filename = os.path.basename(
            file.filename
        )

        suspicious_path = os.path.join(
            UPLOAD_FOLDER,
            "suspicious_" + filename
        )

        file.save(suspicious_path)

        return redirect(
            url_for("check_plagiarism")
        )

    return render_template(
        "upload_code.html",
        message=""
    )


# ---------------- CHECK PLAGIARISM ----------------

@app.route("/check-plagiarism")
def check_plagiarism():

    if "user_id" not in session:
        return redirect(url_for("login"))

    suspicious_files = [
        f
        for f in os.listdir(UPLOAD_FOLDER)
        if f.startswith("suspicious_")
    ]

    if not suspicious_files:

        return render_template(
            "result.html",
            error="Please upload a suspicious code file first."
        )

    suspicious_file = suspicious_files[-1]

    suspicious_path = os.path.join(
        UPLOAD_FOLDER,
        suspicious_file
    )

    try:

        with open(
            suspicious_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:

            suspicious_code = file.read()

    except Exception:

        return render_template(
            "result.html",
            error="Unable to read the suspicious code file."
        )

    source_files = [
        f
        for f in os.listdir(UPLOAD_FOLDER)
        if f.startswith("source_")
    ]

    if not source_files:

        return render_template(
            "result.html",
            error="Please upload source files first."
        )

    highest_similarity = 0
    matched_file = "No match"

    for filename in source_files:

        source_path = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        try:

            with open(
                source_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                source_code = file.read()

            similarity = calculate_similarity(
                suspicious_code,
                source_code
            )

            if similarity > highest_similarity:

                highest_similarity = similarity

                matched_file = filename.replace(
                    "source_",
                    "",
                    1
                )

        except Exception:
            continue

    if highest_similarity >= 50:

        result = "PLAGIARISM DETECTED"

    else:

        result = "NO PLAGIARISM DETECTED"

    return render_template(
        "result.html",
        similarity=highest_similarity,
        matched_file=matched_file,
        result=result
    )


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# ---------------- START ----------------

if __name__ == "__main__":

    init_database()

    print()
    print("==============================================")
    print(" AI CODE PLAGIARISM / CLONE DETECTOR")
    print("==============================================")
    print("Website starting...")
    print("Open: http://127.0.0.1:5000")
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )