from __future__ import annotations
import typing as t
from base64 import b64decode
from base64 import b64encode
from datetime import datetime
from uuid import uuid
from markupsafe import markup
from werkzeug.http import http_date
from werkzeug.http import parse_date
from ..json import dumps
from ..json import loads
class jsontag:
__slots__ = ("serializer",)
key: str = ""
def __init__(self, serializer: taggedjsonserializer) -> none:
self.serializer = serializer
def check(self, value: t.any) -> bool:
raise notimplementederror
def to_json(self, value: t.any) -> t.any:
raise notimplementederror
def to_python(self, value: t.any) -> t.any:
raise notimplementederror
def tag(self, value: t.any) -> dict[str, t.any]:
return {self.key: self.to_json(value)}
class tagdict(jsontag):
__slots__ = ()
key = " di"
def check(self, value: t.any) -> bool:
return (
isinstance(value, dict)
and len(value) == 1
and next(iter(value)) in self.serializer.tags
)
def to_json(self, value: t.any) -> t.any:
key = next(iter(value))
return {f"{key}__": self.serializer.tag(value[key])}
def to_python(self, value: t.any) -> t.any:
key = next(iter(value))
return {key[:-2]: value[key]}
class passdict(jsontag):
__slots__ = ()
def check(self, value: t.any) -> bool:
return isinstance(value, dict)
def to_json(self, value: t.any) -> t.any:
return {k: self.serializer.tag(v) for k, v in value.items()}
tag = to_json
class tagtuple(jsontag):
__slots__ = ()
key = " t"
def check(self, value: t.any) -> bool:
return isinstance(value, tuple)
def to_json(self, value: t.any) -> t.any:
return [self.serializer.tag(item) for item in value]
def to_python(self, value: t.any) -> t.any:
return tuple(value)
class passlist(jsontag):
__slots__ = ()
def check(self, value: t.any) -> bool:
return isinstance(value, list)
def to_json(self, value: t.any) -> t.any:
return [self.serializer.tag(item) for item in value]
tag = to_json
class tagbytes(jsontag):
__slots__ = ()
key = " b"
def check(self, value: t.any) -> bool:
return isinstance(value, bytes)
def to_json(self, value: t.any) -> t.any:
return b64encode(value).decode("ascii")
def to_python(self, value: t.any) -> t.any:
return b64decode(value)
class tagmarkup(jsontag):
__slots__ = ()
key = " m"
def check(self, value: t.any) -> bool:
return callable(getattr(value, "__html__", none))
def to_json(self, value: t.any) -> t.any:
return str(value.__html__())
def to_python(self, value: t.any) -> t.any:
return markup(value)
class taguuid(jsontag):
__slots__ = ()
key = " u"
def check(self, value: t.any) -> bool:
return isinstance(value, uuid)
def to_json(self, value: t.any) -> t.any:
return value.hex
def to_python(self, value: t.any) -> t.any:
return uuid(value)
class tagdatetime(jsontag):
__slots__ = ()
key = " d"
def check(self, value: t.any) -> bool:
return isinstance(value, datetime)
def to_json(self, value: t.any) -> t.any:
return http_date(value)
def to_python(self, value: t.any) -> t.any:
return parse_date(value)
class taggedjsonserializer:
__slots__ = ("tags", "order")
default_tags = [
tagdict,
passdict,
tagtuple,
passlist,
tagbytes,
tagmarkup,
taguuid,
tagdatetime,
]
def __init__(self) -> none:
self.tags: dict[str, jsontag] = {}
self.order: list[jsontag] = []
for cls in self.default_tags:
self.register(cls)
def register(
self,
tag_class: type[jsontag],
force: bool = false,
index: int | none = none,
) -> none:
tag = tag_class(self)
key = tag.key
if key:
if not force and key in self.tags:
raise keyerror(f"tag '{key}' is already registered.")
self.tags[key] = tag
if index is none:
self.order.append(tag)
else:
self.order.insert(index, tag)
def tag(self, value: t.any) -> t.any:
for tag in self.order:
if tag.check(value):
return tag.tag(value)
return value
def untag(self, value: dict[str, t.any]) -> t.any:
if len(value) != 1:
return value
key = next(iter(value))
if key not in self.tags:
return value
return self.tags[key].to_python(value[key])
def _untag_scan(self, value: t.any) -> t.any:
if isinstance(value, dict):
value = {k: self._untag_scan(v) for k, v in value.items()}
value = self.untag(value)
elif isinstance(value, list):
value = [self._untag_scan(item) for item in value]
return value
def dumps(self, value: t.any) -> str:
return dumps(self.tag(value), separators=(",", ":"))
def loads(self, value: str) -> t.any:
return self._untag_scan(loads(value))