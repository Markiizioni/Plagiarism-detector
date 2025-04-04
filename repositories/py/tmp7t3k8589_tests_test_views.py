import pytest
from werkzeug.http import parse_set_header
import flask.views
def common_test(app):
c = app.test_client()
assert c.get("/").data == b"get"
assert c.post("/").data == b"post"
assert c.put("/").status_code == 405
meths = parse_set_header(c.open("/", method="options").headers["allow"])
assert sorted(meths) == ["get", "head", "options", "post"]
def test_basic_view(app):
class index(flask.views.view):
methods = ["get", "post"]
def dispatch_request(self):
return flask.request.method
app.add_url_rule("/", view_func=index.as_view("index"))
common_test(app)
def test_method_based_view(app):
class index(flask.views.methodview):
def get(self):
return "get"
def post(self):
return "post"
app.add_url_rule("/", view_func=index.as_view("index"))
common_test(app)
def test_view_patching(app):
class index(flask.views.methodview):
def get(self):
raise zerodivisionerror
def post(self):
raise zerodivisionerror
class other(index):
def get(self):
return "get"
def post(self):
return "post"
view = index.as_view("index")
view.view_class = other
app.add_url_rule("/", view_func=view)
common_test(app)
def test_view_inheritance(app, client):
class index(flask.views.methodview):
def get(self):
return "get"
def post(self):
return "post"
class betterindex(index):
def delete(self):
return "delete"
app.add_url_rule("/", view_func=betterindex.as_view("index"))
meths = parse_set_header(client.open("/", method="options").headers["allow"])
assert sorted(meths) == ["delete", "get", "head", "options", "post"]
def test_view_decorators(app, client):
def add_x_parachute(f):
def new_function(*args, **kwargs):
resp = flask.make_response(f(*args, **kwargs))
resp.headers["x-parachute"] = "awesome"
return resp
return new_function
class index(flask.views.view):
decorators = [add_x_parachute]
def dispatch_request(self):
return "awesome"
app.add_url_rule("/", view_func=index.as_view("index"))
rv = client.get("/")
assert rv.headers["x-parachute"] == "awesome"
assert rv.data == b"awesome"
def test_view_provide_automatic_options_attr():
app = flask.flask(__name__)
class index1(flask.views.view):
provide_automatic_options = false
def dispatch_request(self):
return "hello world!"
app.add_url_rule("/", view_func=index1.as_view("index"))
c = app.test_client()
rv = c.open("/", method="options")
assert rv.status_code == 405
app = flask.flask(__name__)
class index2(flask.views.view):
methods = ["options"]
provide_automatic_options = true
def dispatch_request(self):
return "hello world!"
app.add_url_rule("/", view_func=index2.as_view("index"))
c = app.test_client()
rv = c.open("/", method="options")
assert sorted(rv.allow) == ["options"]
app = flask.flask(__name__)
class index3(flask.views.view):
def dispatch_request(self):
return "hello world!"
app.add_url_rule("/", view_func=index3.as_view("index"))
c = app.test_client()
rv = c.open("/", method="options")
assert "options" in rv.allow
def test_implicit_head(app, client):
class index(flask.views.methodview):
def get(self):
return flask.response("blub", headers={"x-method": flask.request.method})
app.add_url_rule("/", view_func=index.as_view("index"))
rv = client.get("/")
assert rv.data == b"blub"
assert rv.headers["x-method"] == "get"
rv = client.head("/")
assert rv.data == b""
assert rv.headers["x-method"] == "head"
def test_explicit_head(app, client):
class index(flask.views.methodview):
def get(self):
return "get"
def head(self):
return flask.response("", headers={"x-method": "head"})
app.add_url_rule("/", view_func=index.as_view("index"))
rv = client.get("/")
assert rv.data == b"get"
rv = client.head("/")
assert rv.data == b""
assert rv.headers["x-method"] == "head"
def test_endpoint_override(app):
app.debug = true
class index(flask.views.view):
methods = ["get", "post"]
def dispatch_request(self):
return flask.request.method
app.add_url_rule("/", view_func=index.as_view("index"))
with pytest.raises(assertionerror):
app.add_url_rule("/", view_func=index.as_view("index"))
common_test(app)
def test_methods_var_inheritance(app, client):
class baseview(flask.views.methodview):
methods = ["get", "propfind"]
class childview(baseview):
def get(self):
return "get"
def propfind(self):
return "propfind"
app.add_url_rule("/", view_func=childview.as_view("index"))
assert client.get("/").data == b"get"
assert client.open("/", method="propfind").data == b"propfind"
assert childview.methods == {"propfind", "get"}
def test_multiple_inheritance(app, client):
class getview(flask.views.methodview):
def get(self):
return "get"
class deleteview(flask.views.methodview):
def delete(self):
return "delete"
class getdeleteview(getview, deleteview):
pass
app.add_url_rule("/", view_func=getdeleteview.as_view("index"))
assert client.get("/").data == b"get"
assert client.delete("/").data == b"delete"
assert sorted(getdeleteview.methods) == ["delete", "get"]
def test_remove_method_from_parent(app, client):
class getview(flask.views.methodview):
def get(self):
return "get"
class otherview(flask.views.methodview):
def post(self):
return "post"
class view(getview, otherview):
methods = ["get"]
app.add_url_rule("/", view_func=view.as_view("index"))
assert client.get("/").data == b"get"
assert client.post("/").status_code == 405
assert sorted(view.methods) == ["get"]
def test_init_once(app, client):
n = 0
class countinit(flask.views.view):
init_every_request = false
def __init__(self):
nonlocal n
n += 1
def dispatch_request(self):
return str(n)
app.add_url_rule("/", view_func=countinit.as_view("index"))
assert client.get("/").data == b"1"
assert client.get("/").data == b"1"