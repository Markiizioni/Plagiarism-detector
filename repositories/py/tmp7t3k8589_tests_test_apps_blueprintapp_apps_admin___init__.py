from flask import blueprint
from flask import render_template
admin = blueprint(
"admin",
__name__,
url_prefix="/admin",
template_folder="templates",
static_folder="static",
)
@admin.route("/")
def index():
return render_template("admin/index.html")
@admin.route("/index2")
def index2():
return render_template("./admin/index.html")