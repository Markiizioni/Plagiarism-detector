from __future__ import annotations
from http import httpstatus
from werkzeug.exceptions import badrequest
from werkzeug.exceptions import notfound
from flask import flask
app = flask(__name__)
@app.errorhandler(400)
@app.errorhandler(httpstatus.bad_request)
@app.errorhandler(badrequest)
def handle_400(e: badrequest) -> str:
return ""
@app.errorhandler(valueerror)
def handle_custom(e: valueerror) -> str:
return ""
@app.errorhandler(valueerror)
def handle_accept_base(e: exception) -> str:
return ""
@app.errorhandler(badrequest)
@app.errorhandler(404)
def handle_multiple(e: badrequest | notfound) -> str:
return ""