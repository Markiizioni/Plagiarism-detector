flask is a lightweight [wsgi] web application framework. it is designed
to make getting started quick and easy, with the ability to scale up to
complex applications. it began as a simple wrapper around [werkzeug]
and [jinja], and has become one of the most popular python web
application frameworks.
flask offers suggestions, but doesn't enforce any dependencies or
project layout. it is up to the developer to choose the tools and
libraries they want to use. there are many extensions provided by the
community that make adding new functionality easy.
[wsgi]: https:
[werkzeug]: https:
[jinja]: https:
```python
from flask import flask
app = flask(__name__)
@app.route("/")
def hello():
return "hello, world!"
```
```
$ flask run
* running on http:
```
the pallets organization develops and supports flask and the libraries
it uses. in order to grow the community of contributors and users, and
allow the maintainers to devote more time to the projects, [please
donate today].
[please donate today]: https:
see our [detailed contributing documentation][contrib] for many ways to
contribute, including reporting issues, requesting features, asking or answering
questions, and making prs.
[contrib]: https: