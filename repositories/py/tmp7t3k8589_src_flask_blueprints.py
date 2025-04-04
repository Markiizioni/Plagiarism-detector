from __future__ import annotations
import os
import typing as t
from datetime import timedelta
from .cli import appgroup
from .globals import current_app
from .helpers import send_from_directory
from .sansio.blueprints import blueprint as sansioblueprint
from .sansio.blueprints import blueprintsetupstate as blueprintsetupstate
from .sansio.scaffold import _sentinel
if t.type_checking:
from .wrappers import response
class blueprint(sansioblueprint):
def __init__(
self,
name: str,
import_name: str,
static_folder: str | os.pathlike[str] | none = none,
static_url_path: str | none = none,
template_folder: str | os.pathlike[str] | none = none,
url_prefix: str | none = none,
subdomain: str | none = none,
url_defaults: dict[str, t.any] | none = none,
root_path: str | none = none,
cli_group: str | none = _sentinel,
) -> none:
super().__init__(
name,
import_name,
static_folder,
static_url_path,
template_folder,
url_prefix,
subdomain,
url_defaults,
root_path,
cli_group,
)
self.cli = appgroup()
self.cli.name = self.name
def get_send_file_max_age(self, filename: str | none) -> int | none:
value = current_app.config["send_file_max_age_default"]
if value is none:
return none
if isinstance(value, timedelta):
return int(value.total_seconds())
return value
def send_static_file(self, filename: str) -> response:
if not self.has_static_folder:
raise runtimeerror("'static_folder' must be set to serve static_files.")
max_age = self.get_send_file_max_age(filename)
return send_from_directory(
t.cast(str, self.static_folder), filename, max_age=max_age
)
def open_resource(
self, resource: str, mode: str = "rb", encoding: str | none = "utf-8"
) -> t.io[t.anystr]:
if mode not in {"r", "rt", "rb"}:
raise valueerror("resources can only be opened for reading.")
path = os.path.join(self.root_path, resource)
if mode == "rb":
return open(path, mode)
return open(path, mode, encoding=encoding)