from __future__ import annotations
from flask import flask
from flask import response
app = flask(__name__)
@app.after_request
def after_sync(response: response) -> response:
return response()
@app.after_request
async def after_async(response: response) -> response:
return response()
@app.before_request
def before_sync() -> none: ...
@app.before_request
async def before_async() -> none: ...
@app.teardown_appcontext
def teardown_sync(exc: baseexception | none) -> none: ...
@app.teardown_appcontext
async def teardown_async(exc: baseexception | none) -> none: ...