background tasks with celery
============================
this example shows how to configure celery with flask, how to set up an api for
submitting tasks and polling results, and how to use that api with javascript. see
[flask's documentation about celery](https:
from this directory, create a virtualenv and install the application into it. then run a
celery worker.
```shell
$ python3 -m venv .venv
$ . ./.venv/bin/activate
$ pip install -r requirements.txt && pip install -e .
$ celery -a make_celery worker --loglevel info
```
in a separate terminal, activate the virtualenv and run the flask development server.
```shell
$ . ./.venv/bin/activate
$ flask -a task_app run --debug
```
go to http:
requests in the browser dev tools and the flask logs. you can see the tasks submitting
and completing in the celery logs.