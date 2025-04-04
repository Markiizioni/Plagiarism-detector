from __future__ import annotations
import dataclasses
import decimal
import json
import typing as t
import uuid
import weakref
from datetime import date
from werkzeug.http import http_date
if t.type_checking:
from werkzeug.sansio.response import response
from ..sansio.app import app
class jsonprovider:
def __init__(self, app: app) -> none:
self._app: app = weakref.proxy(app)
def dumps(self, obj: t.any, **kwargs: t.any) -> str:
raise notimplementederror
def dump(self, obj: t.any, fp: t.io[str], **kwargs: t.any) -> none:
fp.write(self.dumps(obj, **kwargs))
def loads(self, s: str | bytes, **kwargs: t.any) -> t.any:
raise notimplementederror
def load(self, fp: t.io[t.anystr], **kwargs: t.any) -> t.any:
return self.loads(fp.read(), **kwargs)
def _prepare_response_obj(
self, args: tuple[t.any, ...], kwargs: dict[str, t.any]
) -> t.any:
if args and kwargs:
raise typeerror("app.json.response() takes either args or kwargs, not both")
if not args and not kwargs:
return none
if len(args) == 1:
return args[0]
return args or kwargs
def response(self, *args: t.any, **kwargs: t.any) -> response:
obj = self._prepare_response_obj(args, kwargs)
return self._app.response_class(self.dumps(obj), mimetype="application/json")
def _default(o: t.any) -> t.any:
if isinstance(o, date):
return http_date(o)
if isinstance(o, (decimal.decimal, uuid.uuid)):
return str(o)
if dataclasses and dataclasses.is_dataclass(o):
return dataclasses.asdict(o)
if hasattr(o, "__html__"):
return str(o.__html__())
raise typeerror(f"object of type {type(o).__name__} is not json serializable")
class defaultjsonprovider(jsonprovider):
default: t.callable[[t.any], t.any] = staticmethod(_default)
ensure_ascii = true
sort_keys = true
compact: bool | none = none
mimetype = "application/json"
def dumps(self, obj: t.any, **kwargs: t.any) -> str:
kwargs.setdefault("default", self.default)
kwargs.setdefault("ensure_ascii", self.ensure_ascii)
kwargs.setdefault("sort_keys", self.sort_keys)
return json.dumps(obj, **kwargs)
def loads(self, s: str | bytes, **kwargs: t.any) -> t.any:
return json.loads(s, **kwargs)
def response(self, *args: t.any, **kwargs: t.any) -> response:
obj = self._prepare_response_obj(args, kwargs)
dump_args: dict[str, t.any] = {}
if (self.compact is none and self._app.debug) or self.compact is false:
dump_args.setdefault("indent", 2)
else:
dump_args.setdefault("separators", (",", ":"))
return self._app.response_class(
f"{self.dumps(obj, **dump_args)}\n", mimetype=self.mimetype
)