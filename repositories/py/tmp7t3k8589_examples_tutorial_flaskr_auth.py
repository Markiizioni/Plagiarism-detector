import functools
from flask import blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from .db import get_db
bp = blueprint("auth", __name__, url_prefix="/auth")
def login_required(view):
@functools.wraps(view)
def wrapped_view(**kwargs):
if g.user is none:
return redirect(url_for("auth.login"))
return view(**kwargs)
return wrapped_view
@bp.before_app_request
def load_logged_in_user():
user_id = session.get("user_id")
if user_id is none:
g.user = none
else:
g.user = (
get_db().execute("select * from user where id = ?", (user_id,)).fetchone()
)
@bp.route("/register", methods=("get", "post"))
def register():
if request.method == "post":
username = request.form["username"]
password = request.form["password"]
db = get_db()
error = none
if not username:
error = "username is required."
elif not password:
error = "password is required."
if error is none:
try:
db.execute(
"insert into user (username, password) values (?, ?)",
(username, generate_password_hash(password)),
)
db.commit()
except db.integrityerror:
error = f"user {username} is already registered."
else:
return redirect(url_for("auth.login"))
flash(error)
return render_template("auth/register.html")
@bp.route("/login", methods=("get", "post"))
def login():
if request.method == "post":
username = request.form["username"]
password = request.form["password"]
db = get_db()
error = none
user = db.execute(
"select * from user where username = ?", (username,)
).fetchone()
if user is none:
error = "incorrect username."
elif not check_password_hash(user["password"], password):
error = "incorrect password."
if error is none:
session.clear()
session["user_id"] = user["id"]
return redirect(url_for("index"))
flash(error)
return render_template("auth/login.html")
@bp.route("/logout")
def logout():
session.clear()
return redirect(url_for("index"))