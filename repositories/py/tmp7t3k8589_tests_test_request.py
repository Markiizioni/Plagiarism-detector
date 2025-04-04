from __future__ import annotations
from flask import flask
from flask import request
from flask import request
from flask.testing import flaskclient
def test_max_content_length(app: flask, client: flaskclient) -> none:
app.config["max_content_length"] = 50
@app.post("/")
def index():
request.form["myfile"]
assertionerror()
@app.errorhandler(413)
def catcher(error):
return "42"
rv = client.post("/", data={"myfile": "foo" * 50})
assert rv.data == b"42"
def test_limit_config(app: flask):
app.config["max_content_length"] = 100
app.config["max_form_memory_size"] = 50
app.config["max_form_parts"] = 3
r = request({})
assert r.max_content_length is none
assert r.max_form_memory_size == 500_000
assert r.max_form_parts == 1_000
with app.app_context():
assert r.max_content_length == 100
assert r.max_form_memory_size == 50
assert r.max_form_parts == 3
r.max_content_length = 90
r.max_form_memory_size = 30
r.max_form_parts = 4
assert r.max_content_length == 90
assert r.max_form_memory_size == 30
assert r.max_form_parts == 4
with app.app_context():
assert r.max_content_length == 90
assert r.max_form_memory_size == 30
assert r.max_form_parts == 4
def test_trusted_hosts_config(app: flask) -> none:
app.config["trusted_hosts"] = ["example.test", ".other.test"]
@app.get("/")
def index() -> str:
return ""
client = app.test_client()
r = client.get(base_url="http:
assert r.status_code == 200
r = client.get(base_url="http:
assert r.status_code == 200
r = client.get(base_url="http:
assert r.status_code == 400