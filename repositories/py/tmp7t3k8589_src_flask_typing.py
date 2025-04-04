from __future__ import annotations
import collections.abc as cabc
import typing as t
if t.type_checking:
from _typeshed.wsgi import wsgiapplication
from werkzeug.datastructures import headers
from werkzeug.sansio.response import response
responsevalue = t.union[
"response",
str,
bytes,
list[t.any],
t.mapping[str, t.any],
t.iterator[str],
t.iterator[bytes],
cabc.asynciterable[str],
cabc.asynciterable[bytes],
]
headervalue = t.union[str, list[str], tuple[str, ...]]
headersvalue = t.union[
"headers",
t.mapping[str, headervalue],
t.sequence[tuple[str, headervalue]],
]
responsereturnvalue = t.union[
responsevalue,
tuple[responsevalue, headersvalue],
tuple[responsevalue, int],
tuple[responsevalue, int, headersvalue],
"wsgiapplication",
]
responseclass = t.typevar("responseclass", bound="response")
apporblueprintkey = t.optional[str]
afterrequestcallable = t.union[
t.callable[[responseclass], responseclass],
t.callable[[responseclass], t.awaitable[responseclass]],
]
beforefirstrequestcallable = t.union[
t.callable[[], none], t.callable[[], t.awaitable[none]]
]
beforerequestcallable = t.union[
t.callable[[], t.optional[responsereturnvalue]],
t.callable[[], t.awaitable[t.optional[responsereturnvalue]]],
]
shellcontextprocessorcallable = t.callable[[], dict[str, t.any]]
teardowncallable = t.union[
t.callable[[t.optional[baseexception]], none],
t.callable[[t.optional[baseexception]], t.awaitable[none]],
]
templatecontextprocessorcallable = t.union[
t.callable[[], dict[str, t.any]],
t.callable[[], t.awaitable[dict[str, t.any]]],
]
templatefiltercallable = t.callable[..., t.any]
templateglobalcallable = t.callable[..., t.any]
templatetestcallable = t.callable[..., bool]
urldefaultcallable = t.callable[[str, dict[str, t.any]], none]
urlvaluepreprocessorcallable = t.callable[
[t.optional[str], t.optional[dict[str, t.any]]], none
]
errorhandlercallable = t.union[
t.callable[[t.any], responsereturnvalue],
t.callable[[t.any], t.awaitable[responsereturnvalue]],
]
routecallable = t.union[
t.callable[..., responsereturnvalue],
t.callable[..., t.awaitable[responsereturnvalue]],
]