# routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, Employee

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = Employee.query.filter_by(username=username, password=password).first()

        if user:
            session["user_id"] = user.id
            flash("Login successful!", "success")
            return redirect(url_for("dashboard.dashboard"))
        else:
            flash("Invalid credentials!", "error")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully", "success")
    return redirect(url_for("auth.login"))
