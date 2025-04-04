from celery.result import asyncresult
from flask import blueprint
from flask import request
from . import tasks
bp = blueprint("tasks", __name__, url_prefix="/tasks")
@bp.get("/result/<id>")
def result(id: str) -> dict[str, object]:
result = asyncresult(id)
ready = result.ready()
return {
"ready": ready,
"successful": result.successful() if ready else none,
"value": result.get() if ready else result.result,
}
@bp.post("/add")
def add() -> dict[str, object]:
a = request.form.get("a", type=int)
b = request.form.get("b", type=int)
result = tasks.add.delay(a, b)
return {"result_id": result.id}
@bp.post("/block")
def block() -> dict[str, object]:
result = tasks.block.delay()
return {"result_id": result.id}
@bp.post("/process")
def process() -> dict[str, object]:
result = tasks.process.delay(total=request.form.get("total", type=int))
return {"result_id": result.id}