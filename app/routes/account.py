from datetime import datetime

from flask import Blueprint, redirect, render_template, request, session, url_for

from .. import limiter
from ..models import ReadingProgress, User, db
from ..utils import (
    current_user,
    get_reader_token,
    login_required_reader,
    upgrade_anonymous_progress,
)

account_bp = Blueprint("account", __name__, url_prefix="/account")


@account_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")

        error = None
        if not email or not display_name or not password:
            error = "All fields are required."
        elif User.query.filter_by(email=email).first():
            error = "An account with that email already exists."

        if error:
            return render_template("account/signup.html", error=error, email=email,
                                    display_name=display_name)

        user = User(email=email, display_name=display_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        upgrade_anonymous_progress(user.id, get_reader_token())

        next_url = request.args.get("next") or url_for("account.my_account")
        return redirect(next_url)

    return render_template("account/signup.html", error=None)


@account_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return render_template(
                "account/login.html",
                error="Email or password is incorrect.",
                email=email,
            )

        session["user_id"] = user.id
        user.last_login_at = datetime.utcnow()
        db.session.commit()
        upgrade_anonymous_progress(user.id, get_reader_token())

        next_url = request.form.get("next") or request.args.get("next") or url_for(
            "account.my_account"
        )
        return redirect(next_url)

    next_url = request.args.get("next", "")
    return render_template("account/login.html", error=None, next_url=next_url)


@account_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return redirect(url_for("reader.home"))


@account_bp.route("")
@login_required_reader
def my_account():
    user = current_user()
    progress_rows = (
        ReadingProgress.query.filter_by(user_id=user.id)
        .order_by(ReadingProgress.updated_at.desc())
        .all()
    )
    return render_template("account/account.html", user=user, progress_rows=progress_rows)
