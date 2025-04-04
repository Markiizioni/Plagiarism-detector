import time
from celery import shared_task
from celery import task
@shared_task(ignore_result=false)
def add(a: int, b: int) -> int:
return a + b
@shared_task()
def block() -> none:
time.sleep(5)
@shared_task(bind=true, ignore_result=false)
def process(self: task, total: int) -> object:
for i in range(total):
self.update_state(state="progress", meta={"current": i + 1, "total": total})
time.sleep(1)
return {"current": total, "total": total}