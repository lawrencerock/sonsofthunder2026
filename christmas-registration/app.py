
import csv
import io
import os
import re
import secrets
from datetime import date, datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, make_response, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash


# --------------------------------------------------
# 1. APPLICATION CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "Set a strong SECRET_KEY environment variable before running."
    )

database_url = os.environ.get("DATABASE_URL", "sqlite:///christmas.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("COOKIE_SECURE", "false").lower() == "true"
)

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "admin_login"
login_manager.login_message = "Please log in to access the admin dashboard."


# --------------------------------------------------
# 2. EVENT SETTINGS
# Change these values for your event.
# --------------------------------------------------

TEAM_NAME = "Sons of Thunder"
EVENT_NAME = "యవ్వనస్తుల ఐక్య క్రిస్మస్"
EVENT_CODE = "03"
EVENT_DATE = date(2026, 12, 15)
EVENT_TIME = "5:00 PM onwards"
REGISTRATION_DEADLINE = datetime(2026, 12, 12, 23, 59, 59)
EVENT_VENUE = "Chitrada near Highway Road Ambedkar Park"
EVENT_CONTACT = "Update with your event contact number"

# Set REGISTRATION_OPEN=false to close registrations manually.
REGISTRATION_OPEN = (
    os.environ.get("REGISTRATION_OPEN", "true").lower() == "true"
)


def registration_is_open():
    return (
        REGISTRATION_OPEN
        and datetime.now() < REGISTRATION_DEADLINE
    )


def event_context():
    return {
        "team_name": TEAM_NAME,
        "event_name": EVENT_NAME,
        "event_code": EVENT_CODE,
        "event_date": EVENT_DATE,
        "event_time": EVENT_TIME,
        "registration_deadline": REGISTRATION_DEADLINE,
        "event_venue": EVENT_VENUE,
        "event_contact": EVENT_CONTACT,
        "registration_open": registration_is_open(),
    }


@app.context_processor
def inject_event_details():
    return event_context()


# --------------------------------------------------
# 3. DATABASE MODELS
# --------------------------------------------------

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(
        db.String(30), unique=True, nullable=False, index=True
    )
    full_name = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(10), nullable=False, index=True)
    gender = db.Column(db.String(20), nullable=False)
    church_name = db.Column(db.String(150), nullable=True)
    address = db.Column(db.String(500), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )


class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    mobile = db.Column(db.String(10), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(Admin, int(user_id))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------
# 4. REGISTRATION ID GENERATOR
# Example: 26SOT0300001
# --------------------------------------------------

def generate_registration_id():
    year_code = str(EVENT_DATE.year)[-2:]
    prefix = f"{year_code}SOT{EVENT_CODE}"

    # Generate and check a candidate ID. The database's unique
    # constraint protects against duplicate IDs during concurrency.
    latest = db.session.execute(
        select(Registration.registration_id)
        .where(Registration.registration_id.like(f"{prefix}%"))
        .order_by(Registration.registration_id.desc())
        .limit(1)
    ).scalar_one_or_none()

    next_number = int(latest[-5:]) + 1 if latest else 1

    if next_number > 99999:
        raise RuntimeError("Registration ID limit reached.")

    return f"{prefix}{next_number:05d}"


# --------------------------------------------------
# 5. PUBLIC LANDING PAGE
# --------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# --------------------------------------------------
# 6. REGISTRATION FORM
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if not registration_is_open():
        flash("Registration is currently closed.", "error")
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template("register.html")

    full_name = request.form.get("full_name", "").strip()
    mobile = request.form.get("mobile", "").strip()
    gender = request.form.get("gender", "").strip()
    church_name = request.form.get("church_name", "").strip()
    address = request.form.get("address", "").strip()

    errors = []

    if not full_name or len(full_name) > 120:
        errors.append("Enter a valid full name (up to 120 characters).")

    if not re.fullmatch(r"[6-9][0-9]{9}", mobile):
        errors.append("Enter a valid 10-digit Indian mobile number.")

    if gender not in {"Male", "Female", "Other"}:
        errors.append("Select a valid gender.")

    if len(church_name) > 150:
        errors.append("Church name must be 150 characters or fewer.")

    if not address or len(address) > 500:
        errors.append("Enter an address (up to 500 characters).")

    if errors:
        for error in errors:
            flash(error, "error")
        return render_template("register.html"), 400

    try:
        registration = Registration(
            registration_id=generate_registration_id(),
            full_name=full_name,
            mobile=mobile,
            gender=gender,
            church_name=church_name or None,
            address=address,
        )

        db.session.add(registration)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        flash(
            "A registration conflict occurred. Please submit again.",
            "error",
        )
        return render_template("register.html"), 409

    return redirect(
        url_for(
            "confirmation",
            registration_id=registration.registration_id,
        )
    )


# --------------------------------------------------
# 7. REGISTRATION CONFIRMATION / PRINT PAGE
# --------------------------------------------------

@app.route("/confirmation/<registration_id>")
def confirmation(registration_id):
    registration = db.session.execute(
        select(Registration).where(
            Registration.registration_id == registration_id
        )
    ).scalar_one_or_none()

    if registration is None:
        abort(404)

    return render_template(
        "confirmation.html",
        registration=registration,
    )


# --------------------------------------------------
# 8. ADMIN LOGIN
# --------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")

        admin = db.session.execute(
            select(Admin).where(Admin.mobile == mobile)
        ).scalar_one_or_none()

        if admin and admin.check_password(password):
            login_user(admin, remember=False)
            return redirect(url_for("admin_dashboard"))

        flash("Invalid mobile number or password.", "error")

    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
@login_required
def admin_logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("admin_login"))


# --------------------------------------------------
# 9. ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/admin")
@login_required
def admin_dashboard():
    search = request.args.get("q", "").strip()[:100]

    query = select(Registration)

    if search:
        pattern = f"%{search}%"
        query = query.where(
            db.or_(
                Registration.registration_id.ilike(pattern),
                Registration.full_name.ilike(pattern),
                Registration.mobile.ilike(pattern),
            )
        )

    registrations = db.session.execute(
        query.order_by(Registration.id.desc())
    ).scalars().all()

    total_registrations = db.session.scalar(
        select(func.count()).select_from(Registration)
    )

    return render_template(
        "dashboard.html",
        registrations=registrations,
        total_registrations=total_registrations,
        search=search,
    )


# --------------------------------------------------
# 10. CSV EXPORT
# --------------------------------------------------

@app.route("/admin/download-csv")
@login_required
def download_csv():
    registrations = db.session.execute(
        select(Registration).order_by(Registration.id.asc())
    ).scalars().all()

    output = io.StringIO(newline="")
    writer = csv.writer(output)

    writer.writerow([
        "Registration ID",
        "Full Name",
        "Mobile Number",
        "Gender",
        "Church Name",
        "Address",
        "Registration Date",
    ])

    for item in registrations:
        writer.writerow([
            item.registration_id,
            item.full_name,
            item.mobile,
            item.gender,
            item.church_name or "",
            item.address,
            item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ])

    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-DispositionFFF"] = (
        "attachment; filename=christmas_registrations.csv"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


# --------------------------------------------------
# 11. DATABASE INITIALIZATION
# --------------------------------------------------

with app.app_context():
    db.create_all()


# --------------------------------------------------
# 12. DEVELOPMENT SERVER
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
