from flask import blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort
from .auth import login_required
from .db import get_db
bp = blueprint("blog", __name__)
@bp.route("/")
def index():
db = get_db()
posts = db.execute(
"select p.id, title, body, created, author_id, username"
" from post p join user u on p.author_id = u.id"
" order by created desc"
).fetchall()
return render_template("blog/index.html", posts=posts)
def get_post(id, check_author=true):
post = (
get_db()
.execute(
"select p.id, title, body, created, author_id, username"
" from post p join user u on p.author_id = u.id"
" where p.id = ?",
(id,),
)
.fetchone()
)
if post is none:
abort(404, f"post id {id} doesn't exist.")
if check_author and post["author_id"] != g.user["id"]:
abort(403)
return post
@bp.route("/create", methods=("get", "post"))
@login_required
def create():
if request.method == "post":
title = request.form["title"]
body = request.form["body"]
error = none
if not title:
error = "title is required."
if error is not none:
flash(error)
else:
db = get_db()
db.execute(
"insert into post (title, body, author_id) values (?, ?, ?)",
(title, body, g.user["id"]),
)
db.commit()
return redirect(url_for("blog.index"))
return render_template("blog/create.html")
@bp.route("/<int:id>/update", methods=("get", "post"))
@login_required
def update(id):
post = get_post(id)
if request.method == "post":
title = request.form["title"]
body = request.form["body"]
error = none
if not title:
error = "title is required."
if error is not none:
flash(error)
else:
db = get_db()
db.execute(
"update post set title = ?, body = ? where id = ?", (title, body, id)
)
db.commit()
return redirect(url_for("blog.index"))
return render_template("blog/update.html", post=post)
@bp.route("/<int:id>/delete", methods=("post",))
@login_required
def delete(id):
get_post(id)
db = get_db()
db.execute("delete from post where id = ?", (id,))
db.commit()
return redirect(url_for("blog.index"))