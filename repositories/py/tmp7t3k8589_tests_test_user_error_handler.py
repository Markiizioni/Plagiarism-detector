import pytest
from werkzeug.exceptions import forbidden
from werkzeug.exceptions import httpexception
from werkzeug.exceptions import internalservererror
from werkzeug.exceptions import notfound
import flask
def test_error_handler_no_match(app, client):
class customexception(exception):
pass
@app.errorhandler(customexception)
def custom_exception_handler(e):
assert isinstance(e, customexception)
return "custom"
with pytest.raises(typeerror) as exc_info:
app.register_error_handler(customexception(), none)
assert "customexception() is an instance, not a class." in str(exc_info.value)
with pytest.raises(valueerror) as exc_info:
app.register_error_handler(list, none)
assert "'list' is not a subclass of exception." in str(exc_info.value)
@app.errorhandler(500)
def handle_500(e):
assert isinstance(e, internalservererror)
if e.original_exception is not none:
return f"wrapped {type(e.original_exception).__name__}"
return "direct"
with pytest.raises(valueerror) as exc_info:
app.register_error_handler(999, none)
assert "use a subclass of httpexception" in str(exc_info.value)
@app.route("/custom")
def custom_test():
raise customexception()
@app.route("/keyerror")
def key_error():
raise keyerror()
@app.route("/abort")
def do_abort():
flask.abort(500)
app.testing = false
assert client.get("/custom").data == b"custom"
assert client.get("/keyerror").data == b"wrapped keyerror"
assert client.get("/abort").data == b"direct"
def test_error_handler_subclass(app):
class parentexception(exception):
pass
class childexceptionunregistered(parentexception):
pass
class childexceptionregistered(parentexception):
pass
@app.errorhandler(parentexception)
def parent_exception_handler(e):
assert isinstance(e, parentexception)
return "parent"
@app.errorhandler(childexceptionregistered)
def child_exception_handler(e):
assert isinstance(e, childexceptionregistered)
return "child-registered"
@app.route("/parent")
def parent_test():
raise parentexception()
@app.route("/child-unregistered")
def unregistered_test():
raise childexceptionunregistered()
@app.route("/child-registered")
def registered_test():
raise childexceptionregistered()
c = app.test_client()
assert c.get("/parent").data == b"parent"
assert c.get("/child-unregistered").data == b"parent"
assert c.get("/child-registered").data == b"child-registered"
def test_error_handler_http_subclass(app):
class forbiddensubclassregistered(forbidden):
pass
class forbiddensubclassunregistered(forbidden):
pass
@app.errorhandler(403)
def code_exception_handler(e):
assert isinstance(e, forbidden)
return "forbidden"
@app.errorhandler(forbiddensubclassregistered)
def subclass_exception_handler(e):
assert isinstance(e, forbiddensubclassregistered)
return "forbidden-registered"
@app.route("/forbidden")
def forbidden_test():
raise forbidden()
@app.route("/forbidden-registered")
def registered_test():
raise forbiddensubclassregistered()
@app.route("/forbidden-unregistered")
def unregistered_test():
raise forbiddensubclassunregistered()
c = app.test_client()
assert c.get("/forbidden").data == b"forbidden"
assert c.get("/forbidden-unregistered").data == b"forbidden"
assert c.get("/forbidden-registered").data == b"forbidden-registered"
def test_error_handler_blueprint(app):
bp = flask.blueprint("bp", __name__)
@bp.errorhandler(500)
def bp_exception_handler(e):
return "bp-error"
@bp.route("/error")
def bp_test():
raise internalservererror()
@app.errorhandler(500)
def app_exception_handler(e):
return "app-error"
@app.route("/error")
def app_test():
raise internalservererror()
app.register_blueprint(bp, url_prefix="/bp")
c = app.test_client()
assert c.get("/error").data == b"app-error"
assert c.get("/bp/error").data == b"bp-error"
def test_default_error_handler():
bp = flask.blueprint("bp", __name__)
@bp.errorhandler(httpexception)
def bp_exception_handler(e):
assert isinstance(e, httpexception)
assert isinstance(e, notfound)
return "bp-default"
@bp.errorhandler(forbidden)
def bp_forbidden_handler(e):
assert isinstance(e, forbidden)
return "bp-forbidden"
@bp.route("/undefined")
def bp_registered_test():
raise notfound()
@bp.route("/forbidden")
def bp_forbidden_test():
raise forbidden()
app = flask.flask(__name__)
@app.errorhandler(httpexception)
def catchall_exception_handler(e):
assert isinstance(e, httpexception)
assert isinstance(e, notfound)
return "default"
@app.errorhandler(forbidden)
def catchall_forbidden_handler(e):
assert isinstance(e, forbidden)
return "forbidden"
@app.route("/forbidden")
def forbidden():
raise forbidden()
@app.route("/slash/")
def slash():
return "slash"
app.register_blueprint(bp, url_prefix="/bp")
c = app.test_client()
assert c.get("/bp/undefined").data == b"bp-default"
assert c.get("/bp/forbidden").data == b"bp-forbidden"
assert c.get("/undefined").data == b"default"
assert c.get("/forbidden").data == b"forbidden"
assert c.get("/slash", follow_redirects=true).data == b"slash"
class testgenerichandlers:
class custom(exception):
pass
@pytest.fixture()
def app(self, app):
@app.route("/custom")
def do_custom():
raise self.custom()
@app.route("/error")
def do_error():
raise keyerror()
@app.route("/abort")
def do_abort():
flask.abort(500)
@app.route("/raise")
def do_raise():
raise internalservererror()
app.config["propagate_exceptions"] = false
return app
def report_error(self, e):
original = getattr(e, "original_exception", none)
if original is not none:
return f"wrapped {type(original).__name__}"
return f"direct {type(e).__name__}"
@pytest.mark.parametrize("to_handle", (internalservererror, 500))
def test_handle_class_or_code(self, app, client, to_handle):
@app.errorhandler(to_handle)
def handle_500(e):
assert isinstance(e, internalservererror)
return self.report_error(e)
assert client.get("/custom").data == b"wrapped custom"
assert client.get("/error").data == b"wrapped keyerror"
assert client.get("/abort").data == b"direct internalservererror"
assert client.get("/raise").data == b"direct internalservererror"
def test_handle_generic_http(self, app, client):
@app.errorhandler(httpexception)
def handle_http(e):
assert isinstance(e, httpexception)
return str(e.code)
assert client.get("/error").data == b"500"
assert client.get("/abort").data == b"500"
assert client.get("/not-found").data == b"404"
def test_handle_generic(self, app, client):
@app.errorhandler(exception)
def handle_exception(e):
return self.report_error(e)
assert client.get("/custom").data == b"direct custom"
assert client.get("/error").data == b"direct keyerror"
assert client.get("/abort").data == b"direct internalservererror"
assert client.get("/not-found").data == b"direct notfound"