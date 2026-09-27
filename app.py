import os
import re
import difflib
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

app.secret_key = os.environ.get("SECRET_KEY", "plagiarism-detector-secret-key")


# -----------------------------
# Home
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# Login
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username and password:
            session["username"] = username
            return redirect(url_for("dashboard"))

        flash("Please enter username and password.")

    return render_template("login.html")


# -----------------------------
# Register
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username and password:
            session["username"] = username
            return redirect(url_for("dashboard"))

        flash("Please enter username and password.")

    return render_template("register.html")


# -----------------------------
# Dashboard
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["username"]
    )


# -----------------------------
# Source code upload
# -----------------------------
@app.route("/upload_source", methods=["GET", "POST"])
def upload_source():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        source_file = request.files.get("source_file")

        if not source_file or source_file.filename == "":
            flash("Please select a source-code file.")
            return redirect(url_for("upload_source"))

        try:
            source_code = source_file.read().decode("utf-8", errors="ignore")

            session["source_code"] = source_code
            session["source_filename"] = source_file.filename

            return redirect(url_for("upload_code"))

        except Exception as e:
            flash(f"Could not read the file: {e}")

    return render_template("upload_source.html")


# -----------------------------
# Code upload / comparison
# -----------------------------
@app.route("/upload_code", methods=["GET", "POST"])
def upload_code():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        code_file = request.files.get("code_file")

        if not code_file or code_file.filename == "":
            flash("Please select a code file.")
            return redirect(url_for("upload_code"))

        try:
            source_code = session.get("source_code", "")
            source_filename = session.get(
                "source_filename",
                "Source Code"
            )

            uploaded_code = code_file.read().decode(
                "utf-8",
                errors="ignore"
            )

            similarity = calculate_similarity(
                source_code,
                uploaded_code
            )

            if similarity >= 80:
                status = "High Similarity"
            elif similarity >= 50:
                status = "Moderate Similarity"
            else:
                status = "Low Similarity"

            return render_template(
                "result.html",
                similarity=similarity,
                status=status,
                source_filename=source_filename,
                uploaded_filename=code_file.filename
            )

        except Exception as e:
            flash(f"Could not process the code: {e}")

    return render_template("upload_code.html")


# -----------------------------
# Result page
# -----------------------------
@app.route("/result")
def result():
    return render_template("result.html")


# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# -----------------------------
# Code normalization
# -----------------------------
def normalize_code(code):
    """
    Removes comments and unnecessary whitespace
    so that simple formatting changes do not
    completely change the comparison.
    """

    if not code:
        return ""

    # Remove Python-style comments
    code = re.sub(r"#.*", "", code)

    # Remove C/C++/Java style comments
    code = re.sub(r"//.*", "", code)

    # Remove multiline comments
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)

    # Normalize whitespace
    code = re.sub(r"\s+", " ", code)

    return code.strip().lower()


# -----------------------------
# Similarity calculation
# -----------------------------
def calculate_similarity(code1, code2):
    """
    Calculates a basic source-code similarity
    percentage using sequence matching.
    """

    normalized1 = normalize_code(code1)
    normalized2 = normalize_code(code2)

    if not normalized1 or not normalized2:
        return 0

    similarity = difflib.SequenceMatcher(
        None,
        normalized1,
        normalized2
    ).ratio()

    return round(similarity * 100, 2)


# -----------------------------
# Run application
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )