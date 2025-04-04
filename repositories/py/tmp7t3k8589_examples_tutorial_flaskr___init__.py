import os
from flask import flask
def create_app(test_config=none):
app = flask(__name__, instance_relative_config=true)
app.config.from_mapping(
secret_key="dev",
database=os.path.join(app.instance_path, "flaskr.sqlite"),
)
if test_config is none:
app.config.from_pyfile("config.py", silent=true)
else:
app.config.update(test_config)
try:
os.makedirs(app.instance_path)
except oserror:
pass
@app.route("/hello")
def hello():
return "hello, world!"
from . import db
db.init_app(app)
from . import auth
from . import blog
app.register_blueprint(auth.bp)
app.register_blueprint(blog.bp)
app.add_url_rule("/", endpoint="index")
return app