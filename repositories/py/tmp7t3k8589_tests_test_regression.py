import flask
def test_aborting(app):
class foo(exception):
whatever = 42
@app.errorhandler(foo)
def handle_foo(e):
return str(e.whatever)
@app.route("/")
def index():
raise flask.abort(flask.redirect(flask.url_for("test")))
@app.route("/test")
def test():
raise foo()
with app.test_client() as c:
rv = c.get("/")
location_parts = rv.headers["location"].rpartition("/")
if location_parts[0]:
assert location_parts[0] == "http:
assert location_parts[2] == "test"
rv = c.get("/test")
assert rv.data == b"42"