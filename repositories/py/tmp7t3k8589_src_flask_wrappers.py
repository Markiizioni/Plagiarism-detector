from __future__ import annotations
import typing as t
from werkzeug.exceptions import badrequest
from werkzeug.exceptions import httpexception
from werkzeug.wrappers import request as requestbase
from werkzeug.wrappers import response as responsebase
from . import json
from .globals import current_app
from .helpers import _split_blueprint_path
if t.type_checking:
from werkzeug.routing import rule
class request(requestbase):
json_module: t.any = json
url_rule: rule | none = none
view_args: dict[str, t.any] | none = none
routing_exception: httpexception | none = none
_max_content_length: int | none = none
_max_form_memory_size: int | none = none
_max_form_parts: int | none = none
@property
def max_content_length(self) -> int | none:
if self._max_content_length is not none:
return self._max_content_length
if not current_app:
return super().max_content_length
return current_app.config["max_content_length"]
@max_content_length.setter
def max_content_length(self, value: int | none) -> none:
self._max_content_length = value
@property
def max_form_memory_size(self) -> int | none:
if self._max_form_memory_size is not none:
return self._max_form_memory_size
if not current_app:
return super().max_form_memory_size
return current_app.config["max_form_memory_size"]
@max_form_memory_size.setter
def max_form_memory_size(self, value: int | none) -> none:
self._max_form_memory_size = value
@property
def max_form_parts(self) -> int | none:
if self._max_form_parts is not none:
return self._max_form_parts
if not current_app:
return super().max_form_parts
return current_app.config["max_form_parts"]
@max_form_parts.setter
def max_form_parts(self, value: int | none) -> none:
self._max_form_parts = value
@property
def endpoint(self) -> str | none:
if self.url_rule is not none:
return self.url_rule.endpoint
return none
@property
def blueprint(self) -> str | none:
endpoint = self.endpoint
if endpoint is not none and "." in endpoint:
return endpoint.rpartition(".")[0]
return none
@property
def blueprints(self) -> list[str]:
name = self.blueprint
if name is none:
return []
return _split_blueprint_path(name)
def _load_form_data(self) -> none:
super()._load_form_data()
if (
current_app
and current_app.debug
and self.mimetype != "multipart/form-data"
and not self.files
):
from .debughelpers import attach_enctype_error_multidict
attach_enctype_error_multidict(self)
def on_json_loading_failed(self, e: valueerror | none) -> t.any:
try:
return super().on_json_loading_failed(e)
except badrequest as ebr:
if current_app and current_app.debug:
raise
raise badrequest() from ebr
class response(responsebase):
default_mimetype: str | none = "text/html"
json_module = json
autocorrect_location_header = false
@property
def max_cookie_size(self) -> int:
if current_app:
return current_app.config["max_cookie_size"]
return super().max_cookie_size