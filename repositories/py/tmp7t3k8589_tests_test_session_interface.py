import flask
from flask.globals import request_ctx
from flask.sessions import sessioninterface
def test_open_session_with_endpoint():
class mysessioninterface(sessioninterface):
def save_session(self, app, session, response):
pass
def open_session(self, app, request):
request_ctx.match_request()
assert request.endpoint is not none
app = flask.flask(__name__)
app.session_interface = mysessioninterface()
@app.get("/")
def index():
return "hello, world!"
response = app.test_client().get("/")
assert response.status_code == 200