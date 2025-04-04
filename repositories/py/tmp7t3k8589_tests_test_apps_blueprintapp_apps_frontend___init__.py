from flask import blueprint
from flask import render_template
frontend = blueprint("frontend", __name__, template_folder="templates")
@frontend.route("/")
def index():
return render_template("frontend/index.html")
@frontend.route("/missing")
def missing_template():
return render_template("missing_template.html")