from __future__ import annotations
import typing as t
from contextvars import contextvar
from werkzeug.local import localproxy
if t.type_checking:
from .app import flask
from .ctx import _appctxglobals
from .ctx import appcontext
from .ctx import requestcontext
from .sessions import sessionmixin
from .wrappers import request
_no_app_msg =
_cv_app: contextvar[appcontext] = contextvar("flask.app_ctx")
app_ctx: appcontext = localproxy(
_cv_app, unbound_message=_no_app_msg
)
current_app: flask = localproxy(
_cv_app, "app", unbound_message=_no_app_msg
)
g: _appctxglobals = localproxy(
_cv_app, "g", unbound_message=_no_app_msg
)
_no_req_msg =
_cv_request: contextvar[requestcontext] = contextvar("flask.request_ctx")
request_ctx: requestcontext = localproxy(
_cv_request, unbound_message=_no_req_msg
)
request: request = localproxy(
_cv_request, "request", unbound_message=_no_req_msg
)
session: sessionmixin = localproxy(
_cv_request, "session", unbound_message=_no_req_msg
)