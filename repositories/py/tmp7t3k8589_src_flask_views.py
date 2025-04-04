from __future__ import annotations
import typing as t
from . import typing as ft
from .globals import current_app
from .globals import request
f = t.typevar("f", bound=t.callable[..., t.any])
http_method_funcs = frozenset(
["get", "post", "head", "options", "delete", "put", "trace", "patch"]
)
class view:
methods: t.classvar[t.collection[str] | none] = none
provide_automatic_options: t.classvar[bool | none] = none
decorators: t.classvar[list[t.callable[..., t.any]]] = []
init_every_request: t.classvar[bool] = true
def dispatch_request(self) -> ft.responsereturnvalue:
raise notimplementederror()
@classmethod
def as_view(
cls, name: str, *class_args: t.any, **class_kwargs: t.any
) -> ft.routecallable:
if cls.init_every_request:
def view(**kwargs: t.any) -> ft.responsereturnvalue:
self = view.view_class(
*class_args, **class_kwargs
)
return current_app.ensure_sync(self.dispatch_request)(**kwargs)
else:
self = cls(*class_args, **class_kwargs)
def view(**kwargs: t.any) -> ft.responsereturnvalue:
return current_app.ensure_sync(self.dispatch_request)(**kwargs)
if cls.decorators:
view.__name__ = name
view.__module__ = cls.__module__
for decorator in cls.decorators:
view = decorator(view)
view.view_class = cls
view.__name__ = name
view.__doc__ = cls.__doc__
view.__module__ = cls.__module__
view.methods = cls.methods
view.provide_automatic_options = cls.provide_automatic_options
return view
class methodview(view):
def __init_subclass__(cls, **kwargs: t.any) -> none:
super().__init_subclass__(**kwargs)
if "methods" not in cls.__dict__:
methods = set()
for base in cls.__bases__:
if getattr(base, "methods", none):
methods.update(base.methods)
for key in http_method_funcs:
if hasattr(cls, key):
methods.add(key.upper())
if methods:
cls.methods = methods
def dispatch_request(self, **kwargs: t.any) -> ft.responsereturnvalue:
meth = getattr(self, request.method.lower(), none)
if meth is none and request.method == "head":
meth = getattr(self, "get", none)
assert meth is not none, f"unimplemented method {request.method!r}"
return current_app.ensure_sync(meth)(**kwargs)