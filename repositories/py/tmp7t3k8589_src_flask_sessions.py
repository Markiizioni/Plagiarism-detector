from __future__ import annotations
import collections.abc as c
import hashlib
import typing as t
from collections.abc import mutablemapping
from datetime import datetime
from datetime import timezone
from itsdangerous import badsignature
from itsdangerous import urlsafetimedserializer
from werkzeug.datastructures import callbackdict
from .json.tag import taggedjsonserializer
if t.type_checking:
import typing_extensions as te
from .app import flask
from .wrappers import request
from .wrappers import response
class sessionmixin(mutablemapping[str, t.any]):
@property
def permanent(self) -> bool:
return self.get("_permanent", false)
@permanent.setter
def permanent(self, value: bool) -> none:
self["_permanent"] = bool(value)
new = false
modified = true
accessed = true
class securecookiesession(callbackdict[str, t.any], sessionmixin):
modified = false
accessed = false
def __init__(
self,
initial: c.mapping[str, t.any] | c.iterable[tuple[str, t.any]] | none = none,
) -> none:
def on_update(self: te.self) -> none:
self.modified = true
self.accessed = true
super().__init__(initial, on_update)
def __getitem__(self, key: str) -> t.any:
self.accessed = true
return super().__getitem__(key)
def get(self, key: str, default: t.any = none) -> t.any:
self.accessed = true
return super().get(key, default)
def setdefault(self, key: str, default: t.any = none) -> t.any:
self.accessed = true
return super().setdefault(key, default)
class nullsession(securecookiesession):
def _fail(self, *args: t.any, **kwargs: t.any) -> t.noreturn:
raise runtimeerror(
"the session is unavailable because no secret "
"key was set.  set the secret_key on the "
"application to something unique and secret."
)
__setitem__ = __delitem__ = clear = pop = popitem = update = setdefault = _fail
del _fail
class sessioninterface:
null_session_class = nullsession
pickle_based = false
def make_null_session(self, app: flask) -> nullsession:
return self.null_session_class()
def is_null_session(self, obj: object) -> bool:
return isinstance(obj, self.null_session_class)
def get_cookie_name(self, app: flask) -> str:
return app.config["session_cookie_name"]
def get_cookie_domain(self, app: flask) -> str | none:
return app.config["session_cookie_domain"]
def get_cookie_path(self, app: flask) -> str:
return app.config["session_cookie_path"] or app.config["application_root"]
def get_cookie_httponly(self, app: flask) -> bool:
return app.config["session_cookie_httponly"]
def get_cookie_secure(self, app: flask) -> bool:
return app.config["session_cookie_secure"]
def get_cookie_samesite(self, app: flask) -> str | none:
return app.config["session_cookie_samesite"]
def get_cookie_partitioned(self, app: flask) -> bool:
return app.config["session_cookie_partitioned"]
def get_expiration_time(self, app: flask, session: sessionmixin) -> datetime | none:
if session.permanent:
return datetime.now(timezone.utc) + app.permanent_session_lifetime
return none
def should_set_cookie(self, app: flask, session: sessionmixin) -> bool:
return session.modified or (
session.permanent and app.config["session_refresh_each_request"]
)
def open_session(self, app: flask, request: request) -> sessionmixin | none:
raise notimplementederror()
def save_session(
self, app: flask, session: sessionmixin, response: response
) -> none:
raise notimplementederror()
session_json_serializer = taggedjsonserializer()
def _lazy_sha1(string: bytes = b"") -> t.any:
return hashlib.sha1(string)
class securecookiesessioninterface(sessioninterface):
salt = "cookie-session"
digest_method = staticmethod(_lazy_sha1)
key_derivation = "hmac"
serializer = session_json_serializer
session_class = securecookiesession
def get_signing_serializer(self, app: flask) -> urlsafetimedserializer | none:
if not app.secret_key:
return none
keys: list[str | bytes] = [app.secret_key]
if fallbacks := app.config["secret_key_fallbacks"]:
keys.extend(fallbacks)
return urlsafetimedserializer(
keys,
salt=self.salt,
serializer=self.serializer,
signer_kwargs={
"key_derivation": self.key_derivation,
"digest_method": self.digest_method,
},
)
def open_session(self, app: flask, request: request) -> securecookiesession | none:
s = self.get_signing_serializer(app)
if s is none:
return none
val = request.cookies.get(self.get_cookie_name(app))
if not val:
return self.session_class()
max_age = int(app.permanent_session_lifetime.total_seconds())
try:
data = s.loads(val, max_age=max_age)
return self.session_class(data)
except badsignature:
return self.session_class()
def save_session(
self, app: flask, session: sessionmixin, response: response
) -> none:
name = self.get_cookie_name(app)
domain = self.get_cookie_domain(app)
path = self.get_cookie_path(app)
secure = self.get_cookie_secure(app)
partitioned = self.get_cookie_partitioned(app)
samesite = self.get_cookie_samesite(app)
httponly = self.get_cookie_httponly(app)
if session.accessed:
response.vary.add("cookie")
if not session:
if session.modified:
response.delete_cookie(
name,
domain=domain,
path=path,
secure=secure,
partitioned=partitioned,
samesite=samesite,
httponly=httponly,
)
response.vary.add("cookie")
return
if not self.should_set_cookie(app, session):
return
expires = self.get_expiration_time(app, session)
val = self.get_signing_serializer(app).dumps(dict(session))
response.set_cookie(
name,
val,
expires=expires,
httponly=httponly,
domain=domain,
path=path,
secure=secure,
partitioned=partitioned,
samesite=samesite,
)
response.vary.add("cookie")