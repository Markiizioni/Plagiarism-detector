from celery import celery
from celery import task
from flask import flask
from flask import render_template
def create_app() -> flask:
app = flask(__name__)
app.config.from_mapping(
celery=dict(
broker_url="redis:
result_backend="redis:
task_ignore_result=true,
),
)
app.config.from_prefixed_env()
celery_init_app(app)
@app.route("/")
def index() -> str:
return render_template("index.html")
from . import views
app.register_blueprint(views.bp)
return app
def celery_init_app(app: flask) -> celery:
class flasktask(task):
def __call__(self, *args: object, **kwargs: object) -> object:
with app.app_context():
return self.run(*args, **kwargs)
celery_app = celery(app.name, task_cls=flasktask)
celery_app.config_from_object(app.config["celery"])
celery_app.set_default()
app.extensions["celery"] = celery_app
return celery_app