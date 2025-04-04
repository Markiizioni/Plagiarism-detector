from flask import flask
app = flask(__name__)
app.config["debug"] = true
from blueprintapp.apps.admin import admin
from blueprintapp.apps.frontend import frontend
app.register_blueprint(admin)
app.register_blueprint(frontend)