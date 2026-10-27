# Manual Review: answers-v2

Reviewing 15 answered questions (ordered by id).
Score each question as: correct / partly / incorrect.

## [v001] How can I declare single primitive values like integers or strings as part of the JSON request body?

**Reference Answer**:
The same way there is a Query and Path to define extra data for query and path parameters, FastAPI provides an equivalent Body.

**Generated Answer**:
You can declare single primitive values like integers or strings as part of the JSON request body by using the `Body()` parameter with a Pydantic model that has a single field of the desired type.

For example, to declare a JSON request body with a single integer field, you can use the following code:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    id: int

@app.post("/item")
def create_item(item: Item):
    return item
```

Similarly, to declare a JSON request body with a single string field, you can use the following code:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str

@app.post("/item")
def create_item(item: Item):
    return item
```

This will automatically validate the incoming JSON request body and convert it to the corresponding Pydantic model instance. [1]

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/body.md > Request Body > Results]**:
```
With just that Python type declaration, **FastAPI** will:

* Read the body of the request as JSON.
* Convert the corresponding types (if needed).
* Validate the data.
    * If the data is invalid, it will return a nice and clear error, indicating exactly where and what was the incorrect data.
* Give you the received data in the parameter `item`.
    * As you declared it in the function to be of type `Item`, you will also have all the editor support (completion, etc) for all of the attributes and their types.
* Generate [JSON Schema](https://json-schema.org) definitions for your model, you can also use them anywhere else you like if it makes sense for your project.
* Those schemas will be part of the generated OpenAPI schema, and used by the automatic documentation UIs.
```

verdict: correct / partly / incorrect

---

## [v002] What does the JSON body look like when my endpoint takes two models?

**Reference Answer**:
FastAPI uses the parameter names as keys in the JSON body, expecting each model nested under its parameter name.

**Generated Answer**:
The JSON body will look like this:

```JSON
{
    "item": {
        "name": "Foo",
        "description": "The pretender",
        "price": 42.0,
        "tax": 3.2
    },
    "user": {
        "username": "dave",
        "full_name": "Dave Grohl"
    }
}
```

[1]

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/body-multiple-params.md > Body - Multiple Parameters > Multiple body parameters]**:
```
In the previous example, the *path operations* would expect a JSON body with the attributes of an `Item`, like:

```JSON
{
    "name": "Foo",
    "description": "The pretender",
    "price": 42.0,
    "tax": 3.2
}
```

But you can also declare multiple body parameters, e.g. `item` and `user`:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

class User(BaseModel):
    username: str
    full_name: str | None = None

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item, user: User):
    results = {"item_id": item_id, "item": item, "user": user}
    return results
```

In this case, **FastAPI** will notice that there is more than one body parameter in the function (there are two parameters that are Pydantic models).

So, it will then use the parameter names as keys (field names) in the body, and expect a body like:

```JSON
{
    "item": {
        "name": "Foo",
        "description": "The pretender",
        "price": 42.0,
        "tax": 3.2
    },
    "user": {
        "username": "dave",
        "full_name": "Dave Grohl"
    }
}
```

/// note
```

verdict: correct / partly / incorrect

---

## [v003] How do I read browser cookie values as handler parameters in my route?

**Reference Answer**:
You can define Cookie parameters the same way you define Query and Path parameters.

**Generated Answer**:
To read browser cookie values as handler parameters in your route, you need to use the `Cookie` parameter, which is a "sister" class of `Path` and `Query`. It also inherits from the same common `Param` class.

You can declare the cookie parameters using the same structure as with `Path` and `Query`, and define the default value as well as all the extra validation or annotation parameters.

Here's an example:

```python
from typing import Annotated

from fastapi import Cookie, FastAPI

app = FastAPI()


@app.get("/items/")
async def read_items(ads_id: Annotated[str | None, Cookie()] = None):
    return {"ads_id": ads_id}
```

In this example, `ads_id` is a cookie parameter that can be accessed in the route handler.

**Cited Sources & Chunk Content**:
*(No cited sources)*

verdict: correct / partly / incorrect

---

## [v004] Why doesn't my cookie get sent when I click Execute in the docs page?

**Reference Answer**:
Because the docs UI runs with JavaScript and browsers restrict JavaScript access to cookies, the cookies are not sent when clicking Execute.

**Generated Answer**:
Because the docs UI works with JavaScript, and browsers handle cookies in special ways, they don't easily allow JavaScript to touch them [1].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/cookie-param-models.md > Cookie Parameter Models > Check the Docs]**:
```
You can see the defined cookies in the docs UI at `/docs`:





/// note

Have in mind that, as **browsers handle cookies** in special ways and behind the scenes, they **don't** easily allow **JavaScript** to touch them.

If you go to the **API docs UI** at `/docs` you will be able to see the **documentation** for cookies for your *path operations*.

But even if you **fill the data** and click "Execute", because the docs UI works with **JavaScript**, the cookies won't be sent, and you will see an **error** message as if you didn't write any values.

///
```

verdict: correct / partly / incorrect

---

## [v006] How do I specify the schema of the returned data using standard Python type annotations on my endpoint function?

**Reference Answer**:
You can declare the type used for the response by annotating the path operation function return type.

**Generated Answer**:
You can specify the schema of the returned data using the `response_model` parameter, which includes dataclasses. You can combine dataclasses with standard type annotations to form complex data structures. For example, if you have a dataclass `Author` and you want to return a list of `Author` objects, you can use the following type annotation: `response_model=List[Author]` [3].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/advanced/dataclasses.md > Using Dataclasses > Dataclasses in Nested Data Structures]**:
```
7. Here the `response_model` is using a type annotation of a list of `Author` dataclasses.

Again, you can combine `dataclasses` with standard type annotations.

8. Notice that this *path operation function* uses regular `def` instead of `async def`.

As always, in FastAPI you can combine `def` and `async def` as needed.

If you need a refresher about when to use which, check out the section _"In a hurry?"_ in the docs about [`async` and `await`](../async.md#in-a-hurry).

9. This *path operation function* is not returning dataclasses (although it could), but a list of dictionaries with internal data.

FastAPI will use the `response_model` parameter (that includes dataclasses) to convert the response.

You can combine `dataclasses` with other type annotations in many different combinations to form complex data structures.

Check the in-code annotation tips above to see more specific details.
```

verdict: correct / partly / incorrect

---

## [v007] How are time durations represented in requests and responses?

**Reference Answer**:
Time durations typed as datetime.timedelta are represented in requests and responses as a float of total seconds.

**Generated Answer**:
According to [4], in requests and responses, `datetime.timedelta` is represented as a `float` of total seconds.

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/extra-data-types.md > Extra Data Types > Other data types]**:
```
Here are some of the additional data types you can use:

* `UUID`:
    * A standard "Universally Unique Identifier", common as an ID in many databases and systems.

* In requests and responses will be represented as a `str`.

* `datetime.datetime`:
    * A Python `datetime.datetime`.

* In requests and responses will be represented as a `str` in ISO 8601 format, like: `2008-09-15T15:53:00+05:00`.

* `datetime.date`:
    * Python `datetime.date`.

* In requests and responses will be represented as a `str` in ISO 8601 format, like: `2008-09-15`.

* `datetime.time`:
    * A Python `datetime.time`.

* In requests and responses will be represented as a `str` in ISO 8601 format, like: `14:23:55.003`.

* `datetime.timedelta`:
    * A Python `datetime.timedelta`.

* In requests and responses will be represented as a `float` of total seconds.

* Pydantic also allows representing it as an "ISO 8601 time diff encoding", [see the docs for more info](https://pydantic.dev/docs/validation/latest/concepts/serialization/#custom-serializers).

* `frozenset`:
    * In requests and responses, treated the same as a `set`:
        * In requests, a list will be read, eliminating duplicates and converting it to a `set`.

* In responses, the `set` will be converted to a `list`.
```

verdict: correct / partly / incorrect

---

## [v008] What format do dates and times take in JSON requests and responses?

**Reference Answer**:
Dates and times are represented in JSON requests and responses as strings in ISO 8601 format.

**Generated Answer**:
According to the documentation [1], dates and times in JSON requests and responses are represented as strings in ISO 8601 format.

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/extra-data-types.md > Extra Data Types > Other data types]**:
```
Here are some of the additional data types you can use:

* `UUID`:
    * A standard "Universally Unique Identifier", common as an ID in many databases and systems.

* In requests and responses will be represented as a `str`.

* `datetime.datetime`:
    * A Python `datetime.datetime`.

* In requests and responses will be represented as a `str` in ISO 8601 format, like: `2008-09-15T15:53:00+05:00`.

* `datetime.date`:
    * Python `datetime.date`.

* In requests and responses will be represented as a `str` in ISO 8601 format, like: `2008-09-15`.

* `datetime.time`:
    * A Python `datetime.time`.

* In requests and responses will be represented as a `str` in ISO 8601 format, like: `14:23:55.003`.

* `datetime.timedelta`:
    * A Python `datetime.timedelta`.

* In requests and responses will be represented as a `float` of total seconds.

* Pydantic also allows representing it as an "ISO 8601 time diff encoding", [see the docs for more info](https://pydantic.dev/docs/validation/latest/concepts/serialization/#custom-serializers).

* `frozenset`:
    * In requests and responses, treated the same as a `set`:
        * In requests, a list will be read, eliminating duplicates and converting it to a `set`.

* In responses, the `set` will be converted to a `list`.
```

verdict: correct / partly / incorrect

---

## [v009] How can I tell if someone tampered with a token?

**Reference Answer**:
If someone attempts to modify the token or change its expiration, you can tell because the cryptographic signatures will not match.

**Generated Answer**:
According to [2], a JWT token is not encrypted, but it is signed. This means that when you receive a token that you issued, you can verify that it was you who issued it by checking the signature. If someone tries to modify the token, the signature will not match.

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/security/oauth2-jwt.md > OAuth2 with Password (and hashing), Bearer with JWT tokens > About JWT]**:
```
Now that we have all the security flow, let's make the application actually secure, using JWT tokens and secure password hashing.

This code is something you can actually use in your application, save the password hashes in your database, etc.

We are going to start from where we left in the previous chapter and increment it.

JWT means "JSON Web Tokens".

It's a standard to codify a JSON object in a long dense string without spaces. It looks like this:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

It is not encrypted, so, anyone could recover the information from the contents.

But it's signed. So, when you receive a token that you issued, you can verify that it was you who issued it.

That way, you can create a token with an expiration of, let's say, 1 week. And then when the user comes back the next day with the token, you know that user is still logged in to your system.

After a week, the token will be expired and the user will not be authorized and will have to sign in again to get a new token. And if the user (or a third party) tried to modify the token to change the expiration, you would be able to discover it, because the signatures would not match.

If you want to play with JWT tokens and see how they work, check [https://jwt.io](https://jwt.io/).
```

verdict: correct / partly / incorrect

---

## [v010] What is the format used by a JSON Web Token to serialize a JSON object into a transmission string?

**Reference Answer**:
It's a standard to codify a JSON object in a long dense string without spaces.

**Generated Answer**:
The format used by a JSON Web Token to serialize a JSON object into a transmission string is a dense string without spaces, as described in [3].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/tutorial/security/oauth2-jwt.md > OAuth2 with Password (and hashing), Bearer with JWT tokens > About JWT]**:
```
Now that we have all the security flow, let's make the application actually secure, using JWT tokens and secure password hashing.

This code is something you can actually use in your application, save the password hashes in your database, etc.

We are going to start from where we left in the previous chapter and increment it.

JWT means "JSON Web Tokens".

It's a standard to codify a JSON object in a long dense string without spaces. It looks like this:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

It is not encrypted, so, anyone could recover the information from the contents.

But it's signed. So, when you receive a token that you issued, you can verify that it was you who issued it.

That way, you can create a token with an expiration of, let's say, 1 week. And then when the user comes back the next day with the token, you know that user is still logged in to your system.

After a week, the token will be expired and the user will not be authorized and will have to sign in again to get a new token. And if the user (or a third party) tried to modify the token to change the expiration, you would be able to discover it, because the signatures would not match.

If you want to play with JWT tokens and see how they work, check [https://jwt.io](https://jwt.io/).
```

verdict: correct / partly / incorrect

---

## [v011] How do I import the WebSocket class?

**Reference Answer**:
Import WebSocket directly from fastapi as a convenience, or from starlette.websockets.

**Generated Answer**:
You can import the `WebSocket` class from `fastapi` or `starlette.websockets` [1]. 

```python
from fastapi import WebSocket
```

or

```python
from starlette.websockets import WebSocket
```

**Cited Sources & Chunk Content**:
- **[docs/fastapi/advanced/websockets.md > WebSockets > Create a `websocket`]**:
```
In your **FastAPI** application, create a `websocket`:

```python
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>

Chat

WebSocket Chat

var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }

"""

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")
```

/// note | Technical Details

You could also use `from starlette.websockets import WebSocket`.

**FastAPI** provides the same `WebSocket` directly just as a convenience for you, the developer. But it comes directly from Starlette.
```

verdict: correct / partly / incorrect

---

## [v012] Can a mobile app connect to a WebSocket endpoint?

**Reference Answer**:
Yes, native mobile applications can communicate directly with your WebSocket backend using native code.

**Generated Answer**:
Yes [2].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/advanced/websockets.md > WebSockets > WebSockets client > In production]**:
```
In your production system, you probably have a frontend created with a modern framework like React, Vue.js or Angular.

And to communicate using WebSockets with your backend you would probably use your frontend's utilities.

Or you might have a native mobile application that communicates with your WebSocket backend directly, in native code.

Or you might have any other way to communicate with the WebSocket endpoint.

---

But for this example, we'll use a very simple HTML document with some JavaScript, all inside a long string.

This, of course, is not optimal and you wouldn't use it for production.

In production you would have one of the options above.

But it's the simplest way to focus on the server-side of WebSockets and have a working example:

```python
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>

Chat

WebSocket Chat

var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }

"""
```

verdict: correct / partly / incorrect

---

## [v013] How do I define startup logic that must run before the application starts receiving incoming requests?

**Reference Answer**:
You can define logic (code) that should be executed before the application starts up.

**Generated Answer**:
You can define startup logic that must run before the application starts receiving incoming requests by declaring a function with the event `"startup"` using the `@app.on_event("startup")` decorator [2]. 

Here's an example:
```python
@app.on_event("startup")
async def startup_event():
    # Your startup logic here
```
This function will be executed once, before the application starts receiving requests [1].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/advanced/events.md > Lifespan Events]**:
```
You can define logic (code) that should be executed before the application **starts up**. This means that this code will be executed **once**, **before** the application **starts receiving requests**.

The same way, you can define logic (code) that should be executed when the application is **shutting down**. In this case, this code will be executed **once**, **after** having handled possibly **many requests**.

Because this code is executed before the application **starts** taking requests, and right after it **finishes** handling requests, it covers the whole application **lifespan** (the word "lifespan" will be important in a second 😉).

This can be very useful for setting up **resources** that you need to use for the whole app, and that are **shared** among requests, and/or that you need to **clean up** afterwards. For example, a database connection pool, or loading a shared machine learning model.
```
- **[docs/fastapi/advanced/events.md > Lifespan Events > Alternative Events (deprecated) > `startup` event]**:
```
To add a function that should be run before the application starts, declare it with the event `"startup"`:



```python
from fastapi import FastAPI

app = FastAPI()

items = {}


@app.on_event("startup")
async def startup_event():
    items["foo"] = {"name": "Fighters"}
    items["bar"] = {"name": "Tenders"}


@app.get("/items/{item_id}")
async def read_items(item_id: str):
    return items[item_id]
```


In this case, the `startup` event handler function will initialize the items "database" (just a `dict`) with some values.

You can add more than one event handler function.

And your application won't start receiving requests until all the `startup` event handlers have completed.
```

verdict: correct / partly / incorrect

---

## [v014] How do I run cleanup code when my app shuts down?

**Reference Answer**:
Define an async lifespan context manager and put the cleanup code right after the yield statement, which executes when the application finishes handling requests right before shutdown.

**Generated Answer**:
To run cleanup code when your app shuts down, you can declare a function with the event `"shutdown"` and use the `open()` function to write to a file, as shown in the example code [1]:

```python
@app.on_event("shutdown")
def shutdown_event():
    with open("log.txt", mode="a") as log:
        log.write("Application shutdown")
```

This code will write a text line to a file `log.txt` when the application is shutting down.

**Cited Sources & Chunk Content**:
- **[docs/fastapi/advanced/events.md > Lifespan Events > Alternative Events (deprecated) > `shutdown` event]**:
```
To add a function that should be run when the application is shutting down, declare it with the event `"shutdown"`:



```python
from fastapi import FastAPI

app = FastAPI()


@app.on_event("shutdown")
def shutdown_event():
    with open("log.txt", mode="a") as log:
        log.write("Application shutdown")


@app.get("/items/")
async def read_items():
    return [{"name": "Foo"}]
```


Here, the `shutdown` event handler function will write a text line `"Application shutdown"` to a file `log.txt`.

/// note

In the `open()` function, the `mode="a"` means "append", so, the line will be added after whatever is on that file, without overwriting the previous contents.

///

/// tip

Notice that in this case we are using a standard Python `open()` function that interacts with a file.

So, it involves I/O (input/output), that requires "waiting" for things to be written to disk.

But `open()` doesn't use `async` and `await`.

So, we declare the event handler function with standard `def` instead of `async def`.

///
```

verdict: correct / partly / incorrect

---

## [v015] At what level does HTTPS encryption of the connection happen?

**Reference Answer**:
The encryption of an HTTPS connection happens at the TCP level, one layer below HTTP.

**Generated Answer**:
The encryption of the connection happens at the **TCP level** [1].

**Cited Sources & Chunk Content**:
- **[docs/fastapi/deployment/https.md > About HTTPS > HTTPS for Developers > TLS with SNI Extension]**:
```
After this, the client and the server have an **encrypted TCP connection**, this is what TLS provides. And then they can use that connection to start the actual **HTTP communication**.

And that's what **HTTPS** is, it's just plain **HTTP** inside a **secure TLS connection** instead of a pure (unencrypted) TCP connection.

/// tip

Notice that the encryption of the communication happens at the **TCP level**, not at the HTTP level.

///
```

verdict: correct / partly / incorrect

---

## [v017] How do I run a second independent app inside my FastAPI app?

**Reference Answer**:
Mount the independent sub-application at a designated path using app.mount('/subpath', sub_app).

**Generated Answer**:
You can use the `fastapi` CLI to mount a sub-application. To do this, you need to configure the `entrypoint` in your `pyproject.toml` file to point to the sub-application. 

For example, if your sub-application is in `app2/main.py`, you would configure the `entrypoint` like this:

```toml
[tool.fastapi]
entrypoint = "app2.main:app"
```

Then, you can run the sub-application using the `fastapi` CLI:

```console
$ fastapi dev
```

This will start the sub-application in the specified path.

**Cited Sources & Chunk Content**:
*(No cited sources)*

verdict: correct / partly / incorrect

---
