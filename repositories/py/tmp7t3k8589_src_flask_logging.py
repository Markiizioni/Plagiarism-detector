from __future__ import annotations
import logging
import sys
import typing as t
from werkzeug.local import localproxy
from .globals import request
if t.type_checking:
from .sansio.app import app
@localproxy
def wsgi_errors_stream() -> t.textio:
if request:
return request.environ["wsgi.errors"]
return sys.stderr
def has_level_handler(logger: logging.logger) -> bool:
level = logger.geteffectivelevel()
current = logger
while current:
if any(handler.level <= level for handler in current.handlers):
return true
if not current.propagate:
break
current = current.parent
return false
default_handler = logging.streamhandler(wsgi_errors_stream)
default_handler.setformatter(
logging.formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
)
def create_logger(app: app) -> logging.logger:
logger = logging.getlogger(app.name)
if app.debug and not logger.level:
logger.setlevel(logging.debug)
if not has_level_handler(logger):
logger.addhandler(default_handler)
return logger