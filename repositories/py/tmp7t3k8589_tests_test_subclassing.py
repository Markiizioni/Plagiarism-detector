from io import stringio
import flask
def test_suppressed_exception_logging():
class suppressedflask(flask.flask):
def log_exception(self, exc_info):
pass
out = stringio()
app = suppressedflask(__name__)
@app.route("/")
def index():
raise exception("test")
rv = app.test_client().get("/", errors_stream=out)
assert rv.status_code == 500
assert b"internal server error" in rv.data
assert not out.getvalue()