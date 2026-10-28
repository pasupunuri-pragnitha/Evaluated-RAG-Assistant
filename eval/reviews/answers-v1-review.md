# Manual Review: answers-v1

Verdicts below are first-pass drafts written by Claude and checked by the author against each cited chunk. This deviates from the pre-registered protocol (PREREGISTRATION_ANSWERS.md, item E), which specified author-only scoring. The sample is the first 15 answered questions by id, not a random draw.

Reviewing 15 answered questions (ordered by id).
Score each question as: correct / partly / incorrect.

## [q001] How do I declare optional query parameters?

**Reference Answer**:
Declare optional query parameters by setting their default value to None in the function signature.

**Generated Answer**:
To declare optional query parameters, you can set their default to `None` [1]. For example:

```python
@app.get("/items/{item_id}")
async def read_item(item_id: str, q: str | None = None):
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}
```

This way, the function parameter `q` will be optional, and will be `None` by default [1].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/query-params.md > Query Parameters > Optional parameters]**:
```
The same way, you can declare optional query parameters, by setting their default to `None`:



```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/items/{item_id}")
async def read_item(item_id: str, q: str | None = None):
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}
```


In this case, the function parameter `q` will be optional, and will be `None` by default.

/// tip

Also notice that **FastAPI** is smart enough to notice that the path parameter `item_id` is a path parameter and `q` is not, so, it's a query parameter.

///
```

verdict: correct

---

## [q003] Where can I change the default 200 ok number when a new item gets saved?

**Reference Answer**:
Specify the status_code parameter in the path operation decorator, such as status_code=201.

**Generated Answer**:
You can change the default 200 OK number when a new item gets saved by changing the `status_code` in the `JSONResponse` object in the `else` block of the `upsert_item` function.

In the code snippet from [3], you can see that the `status_code` is set to `status.HTTP_201_CREATED` when a new item is created. This is the line that you would need to change to set a different default status code.

```python
return JSONResponse(status_code=status.HTTP_201_CREATED, content=item)
```

To change the default status code, you would replace `status.HTTP_201_CREATED` with the desired status code. For example, to change it to 201, you would use `status.HTTP_201`.

**Cited Sources & Chunk Content**:
- **[docs/fastapi/advanced/additional-status-codes.md > Additional Status Codes > Additional status codes]**:
```
By default, **FastAPI** will return the responses using a `JSONResponse`, putting the content you return from your *path operation* inside of that `JSONResponse`.

It will use the default status code or the one you set in your *path operation*.

If you want to return additional status codes apart from the main one, you can do that by returning a `Response` directly, like a `JSONResponse`, and set the additional status code directly.

For example, let's say that you want to have a *path operation* that allows updating items, and returns HTTP status codes of 200 "OK" when successful.

But you also want it to accept new items. And when the items didn't exist before, it creates them, and returns an HTTP status code of 201 "Created".

To achieve that, import `JSONResponse`, and return your content there directly, setting the `status_code` that you want:

```python
from typing import Annotated

from fastapi import Body, FastAPI, status
from fastapi.responses import JSONResponse

app = FastAPI()

items = {"foo": {"name": "Fighters", "size": 6}, "bar": {"name": "Tenders", "size": 3}}

@app.put("/items/{item_id}")
async def upsert_item(
    item_id: str,
    name: Annotated[str | None, Body()] = None,
    size: Annotated[int | None, Body()] = None,
):
    if item_id in items:
        item = items[item_id]
        item["name"] = name
        item["size"] = size
        return item
    else:
        item = {"name": name, "size": size}
        items[item_id] = item
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=item)
```

/// warning
```

verdict: incorrect - never gives the real answer (status_code in the decorator); misreads the additional-status-codes example as a way to change a default and invents status.HTTP_201.

---

## [q004] How do I restrict a path parameter so users can only pass predefined choices?

**Reference Answer**:
Use a standard Python Enum class as the type annotation for the path parameter to restrict it to predefined values.

**Generated Answer**:
You can use a standard Python `Enum` to restrict a path parameter to predefined choices. Create a sub-class that inherits from `str` and from `Enum`, and define class attributes with fixed values, which will be the available valid values.

Example:
```python
class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"
```
Then, use this `Enum` as the type hint for the path parameter:
```python
@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    ...
```
This way, the API will only accept the values defined in the `ModelName` enum. [1], [2]

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/path-params.md > Path Parameters > Predefined values > Working with Python *enumerations* > Compare *enumeration members*]**:
```
Because the available values for the *path parameter* are predefined, the interactive docs can show them nicely:

The value of the *path parameter* will be an *enumeration member*.

You can compare it with the *enumeration member* in your created enum `ModelName`:



```python
from enum import Enum

from fastapi import FastAPI


class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"


app = FastAPI()


@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    if model_name is ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}

    if model_name.value == "lenet":
        return {"model_name": model_name, "message": "LeCNN all the images"}

    return {"model_name": model_name, "message": "Have some residuals"}
```
```
- **[docs/fastapi/tutorial/path-params.md > Path Parameters > Predefined values > Create an `Enum` class]**:
```
If you have a *path operation* that receives a *path parameter*, but you want the possible valid *path parameter* values to be predefined, you can use a standard Python `Enum`.

Import `Enum` and create a sub-class that inherits from `str` and from `Enum`.

By inheriting from `str` the API docs will be able to know that the values must be of type `string` and will be able to render correctly.

Then create class attributes with fixed values, which will be the available valid values:



```python
from enum import Enum

from fastapi import FastAPI


class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"


app = FastAPI()


@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    if model_name is ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}

    if model_name.value == "lenet":
        return {"model_name": model_name, "message": "LeCNN all the images"}

    return {"model_name": model_name, "message": "Have some residuals"}
```


/// tip

If you are wondering, "AlexNet", "ResNet", and "LeNet" are just names of Machine Learning models.

///
```

verdict: correct

---

## [q005] What exception does FastAPI automatically raise when a request contains invalid data?

**Reference Answer**:
FastAPI internally raises a RequestValidationError when a request contains invalid data.

**Generated Answer**:
[1] [2]
FastAPI internally raises a `RequestValidationError` when a request contains invalid data.

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/handling-errors.md > Handling Errors > Override the default exception handlers > Use the `RequestValidationError` body]**:
```
The `RequestValidationError` contains the `body` it received with invalid data.

You could use it while developing your app to log the body and debug it, return it to the user, etc.



```python
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


class Item(BaseModel):
    title: str
    size: int


@app.post("/items/")
async def create_item(item: Item):
    return item
```


Now try sending an invalid item like:

```JSON
{
  "title": "towel",
  "size": "XL"
}
```

You will receive a response telling you that the data is invalid containing the received body:

```JSON hl_lines="12-15"
{
  "detail": [
    {
      "loc": [
        "body",
        "size"
      ],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ],
  "body": {
    "title": "towel",
    "size": "XL"
  }
}
```
```
- **[docs/fastapi/tutorial/handling-errors.md > Handling Errors > Override the default exception handlers > Override request validation exceptions]**:
```
**FastAPI** has some default exception handlers.

These handlers are in charge of returning the default JSON responses when you `raise` an `HTTPException` and when the request has invalid data.

You can override these exception handlers with your own.

When a request contains invalid data, **FastAPI** internally raises a `RequestValidationError`.

And it also includes a default exception handler for it.

To override it, import the `RequestValidationError` and use it with `@app.exception_handler(RequestValidationError)` to decorate the exception handler.

The exception handler will receive a `Request` and the exception.

```python
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    message = "Validation errors:"
    for error in exc.errors():
        message += f"\nField: {error['loc']}, Error: {error['msg']}"
    return PlainTextResponse(message, status_code=400)

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id == 3:
        raise HTTPException(status_code=418, detail="Nope! I don't like 3.")
    return {"item_id": item_id}
```
```

verdict: correct - claim is in chunk 2; answer opens with a stray "[1] [2]".

---

## [q006] Is there a built in helper to transform my database models into regular python dicts for json?

**Reference Answer**:
Use jsonable_encoder to convert data objects or Pydantic models into JSON-compatible Python dictionaries.

**Generated Answer**:
Yes, there is a built-in helper called `jsonable_encoder()` [2]. It receives an object, like a Pydantic model, and returns a JSON compatible version [1].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/encoder.md > JSON Compatible Encoder > Using the `jsonable_encoder`]**:
```
Let's imagine that you have a database `fake_db` that only receives JSON compatible data.

For example, it doesn't receive `datetime` objects, as those are not compatible with JSON.

So, a `datetime` object would have to be converted to a `str` containing the data in [ISO format](https://en.wikipedia.org/wiki/ISO_8601).

The same way, this database wouldn't receive a Pydantic model (an object with attributes), only a `dict`.

You can use `jsonable_encoder` for that.

It receives an object, like a Pydantic model, and returns a JSON compatible version:

```python
from datetime import datetime

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

fake_db = {}

class Item(BaseModel):
    title: str
    timestamp: datetime
    description: str | None = None

app = FastAPI()

@app.put("/items/{id}")
def update_item(id: str, item: Item):
    json_compatible_item_data = jsonable_encoder(item)
    fake_db[id] = json_compatible_item_data
```

In this example, it would convert the Pydantic model to a `dict`, and the `datetime` to a `str`.

The result of calling it is something that can be encoded with the Python standard [`json.dumps()`](https://docs.python.org/3/library/json.html#json.dumps).
```
- **[docs/fastapi/tutorial/encoder.md > JSON Compatible Encoder]**:
```
There are some cases where you might need to convert a data type (like a Pydantic model) to something compatible with JSON (like a `dict`, `list`, etc).

For example, if you need to store it in a database.

For that, **FastAPI** provides a `jsonable_encoder()` function.
```

verdict: correct

---

## [q008] What command line tool starts up the server in live reload mode during local coding?

**Reference Answer**:
Run the development server with live reload using the fastapi dev command.

**Generated Answer**:
`fastapi dev` [2]

**Cited Sources & Chunk Content**:
- **[docs/fastapi/index.md > FastAPI > Example > Run it]**:
```
Run the server with:



```console
$ uv run fastapi dev

 ╭────────── FastAPI CLI - Development mode ───────────╮
 │                                                     │
 │  Serving at: http://127.0.0.1:8000                  │
 │                                                     │
 │  API docs: http://127.0.0.1:8000/docs               │
 │                                                     │
 │  Running in development mode, for production use:   │
 │                                                     │
 │  fastapi run                                        │
 │                                                     │
 ╰─────────────────────────────────────────────────────╯

INFO:     Will watch for changes in these directories: ['/home/user/code/awesomeapp']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [2248755] using WatchFiles
INFO:     Started server process [2248757]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```




About the command fastapi dev...

The command `fastapi dev` reads your `main.py` file automatically, detects the **FastAPI** app in it, and starts a server using [Uvicorn](https://uvicorn.dev).

By default, `fastapi dev` will start with auto-reload enabled for local development.

You can read more about it in the [FastAPI CLI docs](https://fastapi.tiangolo.com/fastapi-cli/).
```

verdict: correct - terse but supported.

---

## [q009] My script needs to fire off an email after the request finishes so the user doesn't wait. What do I write in the function?

**Reference Answer**:
Declare a BackgroundTasks parameter in your path operation function and call background_tasks.add_task() with your task function.

**Generated Answer**:
You should write the function to be run in the background as a normal `def` function, without `async def`, as shown in the example [1]. The function should take any necessary parameters, such as the email address and message, and perform the necessary operations, such as writing to a file.

In this case, the function `write_notification` is an example of such a function [1]. It takes two parameters, `email` and `message`, and writes a notification to a file.

Here is an example of how to use it:
```python
def write_notification(email: str, message=""):
    with open("log.txt", mode="w") as email_file:
        content = f"notification for {email}: {message}"
        email_file.write(content)
```
You can then pass this function to the `background_tasks` object with the method `.add_task()` [3].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/background-tasks.md > Background Tasks > Create a task function]**:
```
Create a function to be run as the background task.

It is just a standard function that can receive parameters.

It can be an `async def` or normal `def` function, **FastAPI** will know how to handle it correctly.

In this case, the task function will write to a file (simulating sending an email).

And as the write operation doesn't use `async` and `await`, we define the function with normal `def`:



```python
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()


def write_notification(email: str, message=""):
    with open("log.txt", mode="w") as email_file:
        content = f"notification for {email}: {message}"
        email_file.write(content)


@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(write_notification, email, message="some notification")
    return {"message": "Notification sent in the background"}
```
```
- **[docs/fastapi/tutorial/background-tasks.md > Background Tasks > Add the background task]**:
```
Inside of your *path operation function*, pass your task function to the *background tasks* object with the method `.add_task()`:



```python
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()


def write_notification(email: str, message=""):
    with open("log.txt", mode="w") as email_file:
        content = f"notification for {email}: {message}"
        email_file.write(content)


@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(write_notification, email, message="some notification")
    return {"message": "Notification sent in the background"}
```


`.add_task()` receives as arguments:

* A task function to be run in the background (`write_notification`).
* Any sequence of arguments that should be passed to the task function in order (`email`).
* Any keyword arguments that should be passed to the task function (`message="some notification"`).
```

verdict: partly - says the task function must be a normal def without async def, but the chunk says either works; never shows the BackgroundTasks parameter.

---

## [q010] How do I make a parameter accept numbers that must be greater than zero and less than 100?

**Reference Answer**:
Declare numeric validations using gt and lt parameters inside Path() or Query() with Annotated.

**Generated Answer**:
You can use the `ge` and `le` constraints in the `Annotated` type hint, like this:

```python
item_id: Annotated[int, Path(title="The ID of the item to get", ge=0, le=100)]
```

This will make the `item_id` parameter accept integers that are greater than or equal to 0 and less than or equal to 100. [1]

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/path-params-numeric-validations.md > Path Parameters and Numeric Validations > Number validations: floats, greater than and less than]**:
```
Number validations also work for `float` values.

Here's where it becomes important to be able to declare gt and not just ge. As with it you can require, for example, that a value must be greater than `0`, even if it is less than `1`.

So, `0.5` would be a valid value. But `0.0` or `0` would not.

And the same for lt.



```python
from typing import Annotated

from fastapi import FastAPI, Path, Query

app = FastAPI()


@app.get("/items/{item_id}")
async def read_items(
    *,
    item_id: Annotated[int, Path(title="The ID of the item to get", ge=0, le=1000)],
    q: str,
    size: Annotated[float, Query(gt=0, lt=10.5)],
):
    results = {"item_id": item_id}
    if q:
        results.update({"q": q})
    if size:
        results.update({"size": size})
    return results
```
```

verdict: incorrect - question asks for greater than 0 and less than 100 (gt/lt); answer uses ge=0, le=100, and the chunk's code has le=1000.

---

## [q012] How do I throw a 404 message when a record is not found in the database?

**Reference Answer**:
Raise an HTTPException with status_code=404 and detail containing the error message.

**Generated Answer**:
You can use `HTTPException` to throw a 404 message when a record is not found in the database. 

Here is an example from [4]:
```python
raise HTTPException(status_code=404, detail="Item not found")
```
You can also use the `JSONResponse` with a status code of 404, as shown in the original code:
```python
return JSONResponse(status_code=404, content={"message": "Item not found"})
```
Both of these methods will return a 404 status code and a JSON response with the specified message.

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/handling-errors.md > Handling Errors > Use `HTTPException` > Import `HTTPException`]**:
```
To return HTTP responses with errors to the client you use `HTTPException`.

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

items = {"foo": "The Foo Wrestlers"}


@app.get("/items/{item_id}")
async def read_item(item_id: str):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": items[item_id]}
```
```

verdict: partly - HTTPException part is right; the "original code" with JSONResponse(status_code=404, ...) is not in the chunk.

---

## [q013] I want to share my database session across handlers and close it when done. How is that written?

**Reference Answer**:
Create a dependency function using yield instead of return, placing cleanup code like closing database sessions after the yield.

**Generated Answer**:
You can use the `get_session` function as a dependency with `yield` to share the database session across handlers and close it when done. Here's an example:

```python
def get_session():
    with Session(engine) as session:
        yield session
```

Then, in your path operation, you can use the `Annotated` dependency `SessionDep` to inject the session:

```python
SessionDep = Annotated[Session, Depends(get_session)]
```

This way, the session will be created and closed automatically for each request.

**Cited Sources & Chunk Content**:
*(No cited sources)*

verdict: partly - no cited sources, so the answer cannot be checked against retrieved text.

---

## [q014] How do I write a custom middleware that measures and prints how many milliseconds each request took?

**Reference Answer**:
Use the @app.middleware('http') decorator with an async function that accepts the request and call_next, executing logic before and after awaiting call_next.

**Generated Answer**:
You can use the following code as an example:

```python
import time

from fastapi import FastAPI, Request

app = FastAPI()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    print(f"Request took {process_time * 1000:.2f} ms")
    return response
```

This middleware measures the time it takes to process each request and prints it in milliseconds. 

Note: The `time.perf_counter()` function is used to measure the time, which is more precise than `time.time()` for these use cases [1]. 

Also, note that this middleware will print the time for each request, so you will see the time printed in the console for each request. 

You can add this middleware to your FastAPI application by decorating a function with `@app.middleware("http")` [3]. 

This middleware will run before any path operation receives the request, and after the response is generated, before returning it [1]. 

You can also use this middleware to add a custom header to the response with the time it took to process the request [1]. 

You can add multiple middlewares to your application, and they will be executed in a predictable and controllable order [5]. 

The last middleware added is the outermost, and the first is the innermost [5]. 

On the request path, the outermost middleware runs first [5]. 

On the response path, it runs last [5]. 

You can read more about middlewares in the [Advanced User Guide: Advanced Middleware](../advanced/middleware.md) [5]. 

You can also read more about CORS with a middleware in the next section [5]. 

Note: You can also use `from starlette.requests import Request` instead of `from fastapi import Request` [1]. 

References: [1], [3], [5].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/middleware.md > Middleware > Create a middleware > Before and after the `response`]**:
```
///

/// note | Technical Details

You could also use `from starlette.requests import Request`.

**FastAPI** provides it as a convenience for you, the developer. But it comes directly from Starlette.

///

You can add code to be run with the `request`,  before any *path operation* receives it.

And also after the `response` is generated, before returning it.

For example, you could add a custom header `X-Process-Time` containing the time in seconds that it took to process the request and generate a response:



```python
import time

from fastapi import FastAPI, Request

app = FastAPI()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```


/// tip

Here we use [`time.perf_counter()`](https://docs.python.org/3/library/time.html#time.perf_counter) instead of `time.time()` because it can be more precise for these use cases. 🤓

///
```
- **[docs/fastapi/tutorial/middleware.md > Middleware > Create a middleware]**:
```
To create a middleware you use the decorator `@app.middleware("http")` on top of a function.

The middleware function receives:

* The `request`.
* A function `call_next` that will receive the `request` as a parameter.
    * This function will pass the `request` to the corresponding *path operation*.
    * Then it returns the `response` generated by the corresponding *path operation*.
* You can then further modify the `response` before returning it.

```python
import time

from fastapi import FastAPI, Request

app = FastAPI()

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

/// tip

Keep in mind that custom proprietary headers can be added [using the `X-` prefix](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers).

But if you have custom headers that you want a client in a browser to be able to see, you need to add them to your CORS configurations ([CORS (Cross-Origin Resource Sharing)](cors.md)) using the parameter `expose_headers` documented in [Starlette's CORS docs](https://starlette.dev/middleware/#corsmiddleware).

///

/// note | Technical Details

You could also use `from starlette.requests import Request`.
```
- **[docs/fastapi/tutorial/middleware.md > Middleware > Multiple middleware execution order]**:
```
When you add multiple middlewares using either `@app.middleware()` decorator or `app.add_middleware()` method, each new middleware wraps the application, forming a stack. The last middleware added is the *outermost*, and the first is the *innermost*.

On the request path, the *outermost* middleware runs first.

On the response path, it runs last.

For example:

```Python
app.add_middleware(MiddlewareA)
app.add_middleware(MiddlewareB)
```

This results in the following execution order:

* **Request**: MiddlewareB → MiddlewareA → route

* **Response**: route → MiddlewareA → MiddlewareB

This stacking behavior ensures that middlewares are executed in a predictable and controllable order.

You can later read more about other middlewares in the [Advanced User Guide: Advanced Middleware](../advanced/middleware.md).

You will read about how to handle CORS with a middleware in the next section.
```

verdict: partly - middleware is correct but the print in milliseconds is the model's own adaptation (docs set a header in seconds); padded with unrelated middleware-order text.

---

## [q015] How do I serve a folder of css and javascript files at the /static address?

**Reference Answer**:
Mount a StaticFiles instance to a specific path using app.mount('/static', StaticFiles(directory='static'), name='static').

**Generated Answer**:
You can use the `StaticFiles` class from FastAPI to serve static files. Create a directory to store the static files, for example, `static/`, and then use the following code to serve it:

```python
from fastapi import FastAPI, StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
```

This will serve the static files at the `/static` address.

**Cited Sources & Chunk Content**:
*(No cited sources)*

verdict: incorrect - "from fastapi import FastAPI, StaticFiles" is wrong (should be from fastapi.staticfiles import StaticFiles) and nothing is cited.

---

## [q016] How do I write automated unit tests for my endpoints using pytest?

**Reference Answer**:
Import TestClient from fastapi.testclient, instantiate it with your app, and call HTTP methods like client.get() to write pytest assertions.

**Generated Answer**:
To write automated unit tests for your endpoints using pytest, you need to:

1. Install `pytest` by running `$ uv add pytest` [3].
2. Import `TestClient` from `fastapi.testclient` (or `starlette.testclient` as an alternative) [1].
3. Create a `TestClient` object by passing your FastAPI application to it [1].
4. Write test functions with a name that starts with `test_` (standard pytest convention) [1].
5. Use the `TestClient` object to send requests to your endpoints and assert the expected responses [1].
6. Run the tests using `$ uv run pytest` [3].

Here's an example code snippet:
```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/")
async def read_main():
    return {"msg": "Hello World"}

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}
```
Note that you can also use `AsyncClient` with the `@pytest.mark.anyio` marker to write asynchronous tests [2].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/testing.md > Testing > Using `TestClient`]**:
```
/// note

To use `TestClient`, first install [`httpx`](https://www.python-httpx.org).

Add it to your project:

```console
$ uv add httpx
```

///

Import `TestClient`.

Create a `TestClient` by passing your **FastAPI** application to it.

Create functions with a name that starts with `test_` (this is a standard `pytest` convention).

Use the `TestClient` object the same way as you do with `httpx`.

Write simple `assert` statements with the standard Python expressions that you need to check (again, standard `pytest`).

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/")
async def read_main():
    return {"msg": "Hello World"}

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}
```

/// tip

Notice that the testing functions are normal `def`, not `async def`.

And the calls to the client are also normal calls, not using `await`.

This allows you to use `pytest` directly without complications.

///

/// note | Technical Details

You could also use `from starlette.testclient import TestClient`.
```
- **[docs/fastapi/advanced/async-tests.md > Async Tests > In Detail]**:
```
You can run your tests as usual via:



```console
$ uv run pytest

---> 100%
```

The marker `@pytest.mark.anyio` tells pytest that this test function should be called asynchronously:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from .main import app

@pytest.mark.anyio
async def test_root():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Tomato"}
```

/// tip

Note that the test function is now `async def` instead of just `def` as before when using the `TestClient`.

///

Then we can create an `AsyncClient` with the app, and send async requests to it, using `await`.

```python
import pytest
from httpx import ASGITransport, AsyncClient

from .main import app

@pytest.mark.anyio
async def test_root():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Tomato"}
```

This is the equivalent to:

```Python
response = client.get("/")
```

...that we used to make our requests with the `TestClient`.

/// tip
```
- **[docs/fastapi/tutorial/testing.md > Testing > Run it]**:
```
After that, you just need to install `pytest`.

Add it to your project:



```console
$ uv add pytest

---> 100%
```



It will detect the files and tests automatically, execute them, and report the results back to you.

Run the tests with:



```console
$ uv run pytest

================ test session starts ================
platform linux -- Python 3.6.9, pytest-5.3.5, py-1.8.1, pluggy-0.13.1
rootdir: /home/user/code/superawesome-cli/app
plugins: forked-1.1.3, xdist-1.31.0, cov-2.8.1
collected 6 items

---> 100%

test_main.py ......                            [100%]

================= 1 passed in 0.03s =================
```
```

verdict: correct - omits the chunk's note to install httpx first.

---

## [q017] Why does the browser block my React frontend when making calls to my API on a different port?

**Reference Answer**:
The browser blocks the requests because the frontend and backend run on different origins, requiring you to add and configure CORSMiddleware with allowed origins.

**Generated Answer**:
The browser blocks your React frontend when making calls to your API on a different port because it's a different origin [5]. The browser sends an HTTP OPTIONS request to the backend to check if the communication is allowed, and if the backend doesn't include the correct headers, the browser won't let the JavaScript in the frontend send requests to the backend [1].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/cors.md > CORS (Cross-Origin Resource Sharing) > Steps]**:
```
So, let's say you have a frontend running in your browser at `http://localhost:8080`, and its JavaScript is trying to communicate with a backend running at `http://localhost` (because we don't specify a port, the browser will assume the default port `80`).

Then, the browser will send an HTTP `OPTIONS` request to the `:80`-backend, and if the backend sends the appropriate headers authorizing the communication from this different origin (`http://localhost:8080`) then the `:8080`-browser will let the JavaScript in the frontend send its request to the `:80`-backend.

To achieve this, the `:80`-backend must have a list of "allowed origins".

In this case, the list would have to include `http://localhost:8080` for the `:8080`-frontend to work correctly.
```
- **[docs/fastapi/tutorial/cors.md > CORS (Cross-Origin Resource Sharing) > Origin]**:
```
[CORS or "Cross-Origin Resource Sharing"](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) refers to the situations when a frontend running in a browser has JavaScript code that communicates with a backend, and the backend is in a different "origin" than the frontend.

An origin is the combination of protocol (`http`, `https`), domain (`myapp.com`, `localhost`, `localhost.tiangolo.com`), and port (`80`, `443`, `8080`).

So, all these are different origins:

* `http://localhost`
* `https://localhost`
* `http://localhost:8080`

Even if they are all in `localhost`, they use different protocols or ports, so, they are different "origins".
```

verdict: correct

---

## [q018] What is the difference between normal def endpoints and async def endpoints, and when should I avoid async?

**Reference Answer**:
Use async def when using libraries that support await; use regular def when using synchronous libraries so FastAPI runs them in a separate threadpool.

**Generated Answer**:
According to [3], when you declare a *path operation function* with normal `def` instead of `async def`, it is run in an external threadpool that is then awaited, instead of being called directly (as it would block the server). 

You should avoid using `async def` for trivial compute-only *path operation functions* unless your *path operation functions* use code that performs blocking I/O, as it may have the opposite effect in **FastAPI** [3].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/async.md > Concurrency and async / await > Very Technical Details > Path operation functions]**:
```
/// warning

You can probably skip this.

These are very technical details of how **FastAPI** works underneath.

If you have quite some technical knowledge (coroutines, threads, blocking, etc.) and are curious about how FastAPI handles `async def` vs normal `def`, go ahead.

///

When you declare a *path operation function* with normal `def` instead of `async def`, it is run in an external threadpool that is then awaited, instead of being called directly (as it would block the server).

If you are coming from another async framework that does not work in the way described above and you are used to defining trivial compute-only *path operation functions* with plain `def` for a tiny performance gain (about 100 nanoseconds), please note that in **FastAPI** the effect would be quite opposite. In these cases, it's better to use `async def` unless your *path operation functions* use code that performs blocking I/O.

Still, in both situations, chances are that **FastAPI** will [still be faster](index.md#performance) than (or at least comparable to) your previous framework.
```

verdict: incorrect - second sentence reverses the source: the chunk says to use async def for trivial functions unless they do blocking I/O, the answer says to avoid it.

---

Tally: 7 correct, 4 partly, 4 incorrect (n=15). Note: q003, q010 and q018 all cite an expected page, so page-level grounding counted them as grounded although they are incorrect.
