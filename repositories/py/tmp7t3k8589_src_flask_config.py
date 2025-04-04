from __future__ import annotations
import errno
import json
import os
import types
import typing as t
from werkzeug.utils import import_string
if t.type_checking:
import typing_extensions as te
from .sansio.app import app
t = t.typevar("t")
class configattribute(t.generic[t]):
def __init__(
self, name: str, get_converter: t.callable[[t.any], t] | none = none
) -> none:
self.__name__ = name
self.get_converter = get_converter
@t.overload
def __get__(self, obj: none, owner: none) -> te.self: ...
@t.overload
def __get__(self, obj: app, owner: type[app]) -> t: ...
def __get__(self, obj: app | none, owner: type[app] | none = none) -> t | te.self:
if obj is none:
return self
rv = obj.config[self.__name__]
if self.get_converter is not none:
rv = self.get_converter(rv)
return rv
def __set__(self, obj: app, value: t.any) -> none:
obj.config[self.__name__] = value
class config(dict):
def __init__(
self,
root_path: str | os.pathlike[str],
defaults: dict[str, t.any] | none = none,
) -> none:
super().__init__(defaults or {})
self.root_path = root_path
def from_envvar(self, variable_name: str, silent: bool = false) -> bool:
rv = os.environ.get(variable_name)
if not rv:
if silent:
return false
raise runtimeerror(
f"the environment variable {variable_name!r} is not set"
" and as such configuration could not be loaded. set"
" this variable and make it point to a configuration"
" file"
)
return self.from_pyfile(rv, silent=silent)
def from_prefixed_env(
self, prefix: str = "flask", *, loads: t.callable[[str], t.any] = json.loads
) -> bool:
prefix = f"{prefix}_"
for key in sorted(os.environ):
if not key.startswith(prefix):
continue
value = os.environ[key]
key = key.removeprefix(prefix)
try:
value = loads(value)
except exception:
pass
if "__" not in key:
self[key] = value
continue
current = self
*parts, tail = key.split("__")
for part in parts:
if part not in current:
current[part] = {}
current = current[part]
current[tail] = value
return true
def from_pyfile(
self, filename: str | os.pathlike[str], silent: bool = false
) -> bool:
filename = os.path.join(self.root_path, filename)
d = types.moduletype("config")
d.__file__ = filename
try:
with open(filename, mode="rb") as config_file:
exec(compile(config_file.read(), filename, "exec"), d.__dict__)
except oserror as e:
if silent and e.errno in (errno.enoent, errno.eisdir, errno.enotdir):
return false
e.strerror = f"unable to load configuration file ({e.strerror})"
raise
self.from_object(d)
return true
def from_object(self, obj: object | str) -> none:
if isinstance(obj, str):
obj = import_string(obj)
for key in dir(obj):
if key.isupper():
self[key] = getattr(obj, key)
def from_file(
self,
filename: str | os.pathlike[str],
load: t.callable[[t.io[t.any]], t.mapping[str, t.any]],
silent: bool = false,
text: bool = true,
) -> bool:
filename = os.path.join(self.root_path, filename)
try:
with open(filename, "r" if text else "rb") as f:
obj = load(f)
except oserror as e:
if silent and e.errno in (errno.enoent, errno.eisdir):
return false
e.strerror = f"unable to load configuration file ({e.strerror})"
raise
return self.from_mapping(obj)
def from_mapping(
self, mapping: t.mapping[str, t.any] | none = none, **kwargs: t.any
) -> bool:
mappings: dict[str, t.any] = {}
if mapping is not none:
mappings.update(mapping)
mappings.update(kwargs)
for key, value in mappings.items():
if key.isupper():
self[key] = value
return true
def get_namespace(
self, namespace: str, lowercase: bool = true, trim_namespace: bool = true
) -> dict[str, t.any]:
rv = {}
for k, v in self.items():
if not k.startswith(namespace):
continue
if trim_namespace:
key = k[len(namespace) :]
else:
key = k
if lowercase:
key = key.lower()
rv[key] = v
return rv
def __repr__(self) -> str:
return f"<{type(self).__name__} {dict.__repr__(self)}>"