# Flagged Answered Questions: v1

Answered questions that have a warning or are not page-grounded, and were NOT in the standard review file (2 questions).

## [q021] How do I configure OAuth2PasswordBearer with a custom tokenUrl in my security scheme?

- **Page-Grounded**: True
- **Expected Pages**: `['docs/fastapi/tutorial/security/first-steps.md', 'docs/fastapi/tutorial/security/simple-oauth2.md']`
- **Warnings**: `['code block not found in cited sources']`

**Answer**:
You can configure `OAuth2PasswordBearer` with a custom `tokenUrl` by passing it as an argument when creating an instance of the class. 

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="custom-token-url")
```

[1]

**Cited Chunk Text**:
- **[docs/fastapi/tutorial/security/first-steps.md > Security - First Steps > **FastAPI**'s `OAuth2PasswordBearer` > Use it]**:
```
It could be called as:

```Python
oauth2_scheme(some, parameters)
```

So, it can be used with `Depends`.

Now you can pass that `oauth2_scheme` in a dependency with `Depends`.



```python
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/items/")
async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}
```


This dependency will provide a `str` that is assigned to the parameter `token` of the *path operation function*.

**FastAPI** will know that it can use this dependency to define a "security scheme" in the OpenAPI schema (and the automatic API docs).

/// note | Technical Details

**FastAPI** will know that it can use the class `OAuth2PasswordBearer` (declared in a dependency) to define the security scheme in OpenAPI because it inherits from `fastapi.security.oauth2.OAuth2`, which in turn inherits from `fastapi.security.base.SecurityBase`.

All the security utilities that integrate with OpenAPI (and the automatic API docs) inherit from `SecurityBase`, that's how **FastAPI** can know how to integrate them in OpenAPI.

///
```

verdict: correct / partly / incorrect

---

## [q038] How do I run my app with multiple workers?

- **Page-Grounded**: True
- **Expected Pages**: `['docs/fastapi/deployment/server-workers.md']`
- **Warnings**: `['code block not found in cited sources']`

**Answer**:
You can run your app with multiple workers using the `--workers` command line option with the `fastapi` or `uvicorn` commands. For example, you can use the following command:

```bash
$ fastapi run --workers 4 main.py
```

Or, if you prefer to use the `uvicorn` command directly:

```bash
$ uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

[1], [2], [4]

**Cited Chunk Text**:
- **[docs/fastapi/deployment/concepts.md > Deployments Concepts > Replication - Processes and Memory > Multiple Processes - Workers]**:
```
With a FastAPI application, using a server program like the `fastapi` command that runs Uvicorn, running it once in **one process** can serve multiple clients concurrently.

But in many cases, you will want to run several worker processes at the same time.

If you have more clients than what a single process can handle (for example if the virtual machine is not too big) and you have **multiple cores** in the server's CPU, then you could have **multiple processes** running with the same application at the same time, and distribute all the requests among them.

When you run **multiple processes** of the same API program, they are commonly called **workers**.
```
- **[docs/fastapi/deployment/server-workers.md > Server Workers - Uvicorn with Workers > Recap]**:
```
You can use multiple worker processes with the `--workers` CLI option with the `fastapi` or `uvicorn` commands to take advantage of **multi-core CPUs**, to run **multiple processes in parallel**.

You could use these tools and ideas if you are setting up **your own deployment system** while taking care of the other deployment concepts yourself.

Check out the next chapter to learn about **FastAPI** with containers (e.g. Docker and Kubernetes). You will see that those tools have simple ways to solve the other **deployment concepts** as well. ✨
```
- **[docs/fastapi/deployment/server-workers.md > Server Workers - Uvicorn with Workers > Multiple Workers]**:
```
You can start multiple workers with the `--workers` command line option:

//// tab | `fastapi`

If you use the `fastapi` command:

```console
$ fastapi run --workers 4 main.py

FastAPI   Starting production server 🚀

Searching for package file structure from directories with
             __init__.py files
             Importing from /home/user/code/awesomeapp

module   🐍 main.py

code   Importing the FastAPI app object from the module with the
             following code:

from main import app

app   Using import string: main:app

server   Server started at http://0.0.0.0:8000
    server   Documentation at http://0.0.0.0:8000/docs

Logs:

INFO   Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to
             quit)
      INFO   Started parent process [27365]
      INFO   Started server process [27368]
      INFO   Started server process [27369]
      INFO   Started server process [27370]
      INFO   Started server process [27367]
      INFO   Waiting for application startup.
      INFO   Waiting for application startup.
      INFO   Waiting for application startup.
      INFO   Waiting for application startup.
      INFO   Application startup complete.
      INFO   Application startup complete.
      INFO   Application startup complete.
      INFO   Application startup complete.
```

////

//// tab | `uvicorn`

If you prefer to use the `uvicorn` command directly:
```

verdict: correct / partly / incorrect

---
