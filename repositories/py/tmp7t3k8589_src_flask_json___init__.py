from __future__ import annotations
import json as _json
import typing as t
from ..globals import current_app
from .provider import _default
if t.type_checking:
from ..wrappers import response
def dumps(obj: t.any, **kwargs: t.any) -> str:
if current_app:
return current_app.json.dumps(obj, **kwargs)
kwargs.setdefault("default", _default)
return _json.dumps(obj, **kwargs)
def dump(obj: t.any, fp: t.io[str], **kwargs: t.any) -> none:
if current_app:
current_app.json.dump(obj, fp, **kwargs)
else:
kwargs.setdefault("default", _default)
_json.dump(obj, fp, **kwargs)
def loads(s: str | bytes, **kwargs: t.any) -> t.any:
if current_app:
return current_app.json.loads(s, **kwargs)
return _json.loads(s, **kwargs)
def load(fp: t.io[t.anystr], **kwargs: t.any) -> t.any:
if current_app:
return current_app.json.load(fp, **kwargs)
return _json.load(fp, **kwargs)
def jsonify(*args: t.any, **kwargs: t.any) -> response:
return current_app.json.response(*args, **kwargs)