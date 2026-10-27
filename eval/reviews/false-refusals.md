# False Refusals Analysis

3 of 4 reviewed refusals were real false refusals (q011, q024 on v1; v016 on v2). 1 (q002) was defensible. Note: some chunk texts in this file were fetched by source_path and heading_path, so chunks sharing a heading may show duplicated text; the verdicts above rely only on chunks whose text is distinct.

Detailed inspection of false-refusal questions from v1 (q002, q011, q024) and v2 (v016).

## [q002] (v1) How do I add OAuth2 authentication?

- **Top Vector Score**: 0.7875
- **Expected Sources**: `['docs/fastapi/tutorial/security/index.md', 'docs/fastapi/tutorial/security/first-steps.md', 'docs/fastapi/tutorial/security/simple-oauth2.md']`
- **Reference Answer**: Create an OAuth2PasswordBearer instance with the tokenUrl and pass it to a dependency to retrieve the token and authenticate the user.
- **Generated Response**: I don't know based on the documentation.
- **Reviewer verdict**: NO, the answer was not in the retrieved chunks. They cover what OAuth2 is, the Authorize demo, a scopes example and a recap, but none shows OAuth2PasswordBearer or tokenUrl. Refusal was defensible; the gap is retrieval.

### Retrieved Chunks (in Rank Order):

#### Rank 1: `docs/fastapi/tutorial/security/index.md` > `Security > OAuth2` [EXPECTED PAGE]
- **Scores**: vector_score=0.7875, rrf_score=0.032787
```markdown
If you don't care about any of these terms and you just need to add security with authentication based on username and password *right now*, skip to the next chapters.

OAuth2 is a specification that defines several ways to handle authentication and authorization.

It is quite an extensive specification and covers several complex use cases.

It includes ways to authenticate using a "third party".

That's what all the systems with "login with Facebook, Google, X (Twitter), GitHub" use underneath.
```

#### Rank 2: `docs/fastapi/tutorial/security/simple-oauth2.md` > `Simple OAuth2 with Password and Bearer > See it in action > Authenticate` [EXPECTED PAGE]
- **Scores**: vector_score=0.7836, rrf_score=0.029643
```markdown
Open the interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Click the "Authorize" button.

Use the credentials:

User: `johndoe`

Password: `secret`



After authenticating in the system, you will see it like:
```

#### Rank 3: `docs/fastapi/advanced/security/oauth2-scopes.md` > `OAuth2 scopes > OAuth2 Security scheme`
- **Scores**: vector_score=0.7341, rrf_score=0.028485
```markdown
async def get_current_active_user(
    current_user: Annotated[User, Security(get_current_user, scopes=["me"])],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scope": " ".join(form_data.scopes)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")

@app.get("/users/me/")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    return current_user
```

#### Rank 4: `docs/fastapi/tutorial/security/first-steps.md` > `Security - First Steps` [EXPECTED PAGE]
- **Scores**: vector_score=0.7498, rrf_score=0.026879
```markdown
Let's imagine that you have your **backend** API in some domain.

And you have a **frontend** in another domain or in a different path of the same domain (or in a mobile application).

And you want to have a way for the frontend to authenticate with the backend, using a **username** and **password**.

We can use **OAuth2** to build that with **FastAPI**.

But let's save you the time of reading the full long specification just to find those little pieces of information you need.

Let's use the tools provided by **FastAPI** to handle security.
```

#### Rank 5: `docs/fastapi/tutorial/security/simple-oauth2.md` > `Simple OAuth2 with Password and Bearer > Recap` [EXPECTED PAGE]
- **Scores**: vector_score=0.7414, rrf_score=0.025362
```markdown
Now try with an inactive user, authenticate with:

User: `alice`

Password: `secret2`

And try to use the operation `GET` with the path `/users/me`.

You will get an "Inactive user" error, like:

```JSON
{
  "detail": "Inactive user"
}
```

You now have the tools to implement a complete security system based on `username` and `password` for your API.

Using these tools, you can make the security system compatible with any database and with any user or data model.

The only detail missing is that it is not actually "secure" yet.

In the next chapter you'll see how to use a secure password hashing library and JWT tokens.
```

---

## [q011] (v1) How can I catch image uploads from a web form in my handler function?

- **Top Vector Score**: 0.6815
- **Expected Sources**: `['docs/fastapi/tutorial/request-files.md']`
- **Reference Answer**: Define a parameter with type UploadFile and annotate it with File() to receive uploaded files.
- **Generated Response**: I don't know based on the documentation.
- **Reviewer verdict**: YES, the answer was in the chunks. Rank 2 shows UploadFile and File() in a POST handler and says uploads arrive as form data.

### Retrieved Chunks (in Rank Order):

#### Rank 1: `docs/fastapi/tutorial/handling-errors.md` > `Handling Errors > Override the default exception handlers > Use the `RequestValidationError` body > FastAPI's `HTTPException` vs Starlette's `HTTPException``
- **Scores**: vector_score=0.6686, rrf_score=0.031498
```markdown
**FastAPI** has its own `HTTPException`.

And **FastAPI**'s `HTTPException` error class inherits from Starlette's `HTTPException` error class.

The only difference is that **FastAPI**'s `HTTPException` accepts any JSON-able data for the `detail` field, while Starlette's `HTTPException` only accepts strings for it.

So, you can keep raising **FastAPI**'s `HTTPException` as normally in your code.

But when you register an exception handler, you should register it for Starlette's `HTTPException`.

This way, if any part of Starlette's internal code, or a Starlette extension or plug-in, raises a Starlette `HTTPException`, your handler will be able to catch and handle it.

In this example, to be able to have both `HTTPException`s in the same code, Starlette's exceptions is renamed to `StarletteHTTPException`:

```Python
from starlette.exceptions import HTTPException as StarletteHTTPException
```
```

#### Rank 2: `docs/fastapi/tutorial/request-files.md` > `Request Files > Define `File` Parameters` [EXPECTED PAGE]
- **Scores**: vector_score=0.6564, rrf_score=0.029958
```markdown
Create file parameters the same way you would for `Body` or `Form`:



```python
from typing import Annotated

from fastapi import FastAPI, File, UploadFile

app = FastAPI()


@app.post("/files/")
async def create_file(file: Annotated[bytes, File()]):
    return {"file_size": len(file)}


@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile):
    return {"filename": file.filename}
```


/// note

`File` is a class that inherits directly from `Form`.

But remember that when you import `Query`, `Path`, `File` and others from `fastapi`, those are actually functions that return special classes.

///

/// tip

To declare File bodies, you need to use `File`, because otherwise the parameters would be interpreted as query parameters or body (JSON) parameters.

///

The files will be uploaded as "form data".

If you declare the type of your *path operation function* parameter as `bytes`, **FastAPI** will read the file for you and you will receive the contents as `bytes`.

Keep in mind that this means that the whole contents will be stored in memory. This will work well for small files.

But there are several cases in which you might benefit from using `UploadFile`.
```

#### Rank 3: `docs/fastapi/tutorial/request-forms-and-files.md` > `Request Forms and Files > Define `File` and `Form` parameters`
- **Scores**: vector_score=0.6644, rrf_score=0.029644
```markdown
Create file and form parameters the same way you would for `Body` or `Query`:



```python
from typing import Annotated

from fastapi import FastAPI, File, Form, UploadFile

app = FastAPI()


@app.post("/files/")
async def create_file(
    file: Annotated[bytes, File()],
    fileb: Annotated[UploadFile, File()],
    token: Annotated[str, Form()],
):
    return {
        "file_size": len(file),
        "token": token,
        "fileb_content_type": fileb.content_type,
    }
```


The files and form fields will be uploaded as form data and you will receive the files and form fields.

And you can declare some of the files as `bytes` and some as `UploadFile`.

/// warning

You can declare multiple `File` and `Form` parameters in a *path operation*, but you can't also declare `Body` fields that you expect to receive as JSON, as the request will have the body encoded using `multipart/form-data` instead of `application/json`.

This is not a limitation of **FastAPI**, it's part of the HTTP protocol.

///

Use `File` and `Form` together when you need to receive data and files in the same request.
```

#### Rank 4: `docs/fastapi/tutorial/handling-errors.md` > `Handling Errors > Override the default exception handlers > Override request validation exceptions`
- **Scores**: vector_score=0.6722, rrf_score=0.028034
```markdown
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

#### Rank 5: `docs/fastapi/tutorial/request-forms-and-files.md` > `Request Forms and Files`
- **Scores**: vector_score=0.6371, rrf_score=0.02724
```markdown
You can define files and form fields at the same time using `File` and `Form`.

/// note

To receive uploaded files and/or form data, first install [`python-multipart`](https://github.com/Kludex/python-multipart).

Add it to your project:

```console
$ uv add python-multipart
```

///
```

---

## [q024] (v1) How do I stream live events to browsers using EventSourceResponse or StreamingResponse?

- **Top Vector Score**: 0.7794
- **Expected Sources**: `['docs/fastapi/advanced/custom-response.md', 'docs/fastapi/tutorial/server-sent-events.md']`
- **Reference Answer**: To stream SSE with FastAPI, use yield in your path operation function and set response_class=EventSourceResponse.
- **Generated Response**: I don't know based on the documentation.
- **Reviewer verdict**: YES, the answer was in the chunks. Rank 3 says to use yield in the path operation function and set response_class=EventSourceResponse.

### Retrieved Chunks (in Rank Order):

#### Rank 1: `docs/fastapi/tutorial/server-sent-events.md` > `Server-Sent Events (SSE) > SSE with POST` [EXPECTED PAGE]
- **Scores**: vector_score=0.7233, rrf_score=0.032258
```markdown
SSE works with **any HTTP method**, not just `GET`.

This is useful for protocols like [MCP](https://modelcontextprotocol.io) that stream SSE over `POST`:



```python
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

app = FastAPI()


class Prompt(BaseModel):
    text: str


@app.post("/chat/stream", response_class=EventSourceResponse)
async def stream_chat(prompt: Prompt) -> AsyncIterable[ServerSentEvent]:
    words = prompt.text.split()
    for word in words:
        yield ServerSentEvent(data=word, event="token")
    yield ServerSentEvent(raw_data="[DONE]", event="done")
```
```

#### Rank 2: `docs/fastapi/tutorial/server-sent-events.md` > `Server-Sent Events (SSE)` [EXPECTED PAGE]
- **Scores**: vector_score=0.7794, rrf_score=0.032018
```markdown
You can stream data to the client using **Server-Sent Events** (SSE).

This is similar to [Stream JSON Lines](stream-json-lines.md), but uses the `text/event-stream` format, which is supported natively by browsers with the [`EventSource` API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource).

/// note

Added in FastAPI 0.135.0.

///
```

#### Rank 3: `docs/fastapi/tutorial/server-sent-events.md` > `Server-Sent Events (SSE) > Stream SSE with FastAPI` [EXPECTED PAGE]
- **Scores**: vector_score=0.705, rrf_score=0.031025
```markdown
To stream SSE with FastAPI, use `yield` in your *path operation function* and set `response_class=EventSourceResponse`.

Import `EventSourceResponse` from `fastapi.sse`:

```python
from collections.abc import AsyncIterable, Iterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str | None

items = [
    Item(name="Plumbus", description="A multi-purpose household device."),
    Item(name="Portal Gun", description="A portal opening device."),
    Item(name="Meeseeks Box", description="A box that summons a Meeseeks."),
]

@app.get("/items/stream", response_class=EventSourceResponse)
async def sse_items() -> AsyncIterable[Item]:
    for item in items:
        yield item
```

Each yielded item is encoded as JSON and sent in the `data:` field of an SSE event.

If you declare the return type as `AsyncIterable[Item]`, FastAPI will use it to **validate**, **document**, and **serialize** the data using Pydantic.

```python
from collections.abc import AsyncIterable, Iterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel

app = FastAPI()
```

#### Rank 4: `docs/fastapi/tutorial/server-sent-events.md` > `Server-Sent Events (SSE) > Stream SSE with FastAPI > No Return Type` [EXPECTED PAGE]
- **Scores**: vector_score=0.7142, rrf_score=0.030777
```markdown
You can also omit the return type. FastAPI will use the [`jsonable_encoder`](./encoder.md) to convert the data and send it.



```python
@app.get("/items/stream-no-annotation", response_class=EventSourceResponse)
async def sse_items_no_annotation():
    for item in items:
        yield item
```
```

#### Rank 5: `docs/fastapi/tutorial/server-sent-events.md` > `Server-Sent Events (SSE) > What are Server-Sent Events?` [EXPECTED PAGE]
- **Scores**: vector_score=0.7088, rrf_score=0.03031
```markdown
SSE is a standard for streaming data from the server to the client over HTTP.

Each event is a small text block with "fields" like `data`, `event`, `id`, and `retry`, separated by blank lines.

It looks like this:

```
data: {"name": "Portal Gun", "price": 999.99}

data: {"name": "Plumbus", "price": 32.99}

```

SSE is commonly used for AI chat streaming, live notifications, logs and observability, and other cases where the server pushes updates to the client.

/// tip

If you want to stream binary data, for example video or audio, check the advanced guide: [Stream Data](../advanced/stream-data.md).

///
```

---

## [v016] (v2) Can I use plain Python dataclasses for request and response models?

- **Top Vector Score**: 0.8264
- **Expected Sources**: `['docs/fastapi/advanced/dataclasses.md']`
- **Reference Answer**: Yes, FastAPI supports using standard Python dataclasses for request bodies and response models the same way as Pydantic models.
- **Generated Response**: I don't know based on the documentation.
- **Reviewer verdict**: YES, the answer was in the chunks. Rank 2 says FastAPI supports dataclasses the same way as Pydantic models, with a request body example, and rank 1 shows a dataclass in response_model.

### Retrieved Chunks (in Rank Order):

#### Rank 1: `docs/fastapi/advanced/dataclasses.md` > `Using Dataclasses > Dataclasses in `response_model`` [EXPECTED PAGE]
- **Scores**: vector_score=0.8264, rrf_score=0.032522
```markdown
/// note

Keep in mind that dataclasses can't do everything Pydantic models can do.

So, you might still need to use Pydantic models.

But if you have a bunch of dataclasses lying around, this is a nice trick to use them to power a web API using FastAPI. 🤓

///

You can also use `dataclasses` in the `response_model` parameter:



```python
from dataclasses import dataclass, field

from fastapi import FastAPI


@dataclass
class Item:
    name: str
    price: float
    tags: list[str] = field(default_factory=list)
    description: str | None = None
    tax: float | None = None


app = FastAPI()


@app.get("/items/next", response_model=Item)
async def read_next_item():
    return {
        "name": "Island In The Moon",
        "price": 12.99,
        "description": "A place to be playin' and havin' fun",
        "tags": ["breater"],
    }
```


The dataclass will be automatically converted to a Pydantic dataclass.

This way, its schema will show up in the API docs user interface:
```

#### Rank 2: `docs/fastapi/advanced/dataclasses.md` > `Using Dataclasses` [EXPECTED PAGE]
- **Scores**: vector_score=0.8067, rrf_score=0.032266
```markdown
FastAPI is built on top of **Pydantic**, and I have been showing you how to use Pydantic models to declare requests and responses.

But FastAPI also supports using [`dataclasses`](https://docs.python.org/3/library/dataclasses.html) the same way:

```python
from dataclasses import dataclass

from fastapi import FastAPI

@dataclass
class Item:
    name: str
    price: float
    description: str | None = None
    tax: float | None = None

app = FastAPI()

@app.post("/items/")
async def create_item(item: Item):
    return item
```

This is still supported thanks to **Pydantic**, as it has [internal support for `dataclasses`](https://pydantic.dev/docs/validation/latest/concepts/dataclasses/#usage-of-stdlib-dataclasses-with-basemodel).

So, even with the code above that doesn't use Pydantic explicitly, FastAPI is using Pydantic to convert those standard dataclasses to Pydantic's own flavor of dataclasses.

And of course, it supports the same:

* data validation
* data serialization
* data documentation, etc.

This works the same way as with Pydantic models. And it is actually achieved in the same way underneath, using Pydantic.

/// note

Keep in mind that dataclasses can't do everything Pydantic models can do.

So, you might still need to use Pydantic models.
```

#### Rank 3: `docs/fastapi/advanced/dataclasses.md` > `Using Dataclasses > Dataclasses in Nested Data Structures` [EXPECTED PAGE]
- **Scores**: vector_score=0.8147, rrf_score=0.032002
```markdown
You can also combine `dataclasses` with other type annotations to make nested data structures.

In some cases, you might still have to use Pydantic's version of `dataclasses`. For example, if you have errors with the automatically generated API documentation.

In that case, you can simply swap the standard `dataclasses` with `pydantic.dataclasses`, which is a drop-in replacement:

```python
from dataclasses import field  # (1)

from fastapi import FastAPI
from pydantic.dataclasses import dataclass  # (2)

@dataclass
class Item:
    name: str
    description: str | None = None

@dataclass
class Author:
    name: str
    items: list[Item] = field(default_factory=list)  # (3)

app = FastAPI()

@app.post("/authors/{author_id}/items/", response_model=Author)  # (4)
async def create_author_items(author_id: str, items: list[Item]):  # (5)
    return {"name": author_id, "items": items}  # (6)
```

#### Rank 4: `docs/fastapi/advanced/dataclasses.md` > `Using Dataclasses > Dataclasses in Nested Data Structures` [EXPECTED PAGE]
- **Scores**: vector_score=0.7962, rrf_score=0.03125
```markdown
You can also combine `dataclasses` with other type annotations to make nested data structures.

In some cases, you might still have to use Pydantic's version of `dataclasses`. For example, if you have errors with the automatically generated API documentation.

In that case, you can simply swap the standard `dataclasses` with `pydantic.dataclasses`, which is a drop-in replacement:

```python
from dataclasses import field  # (1)

from fastapi import FastAPI
from pydantic.dataclasses import dataclass  # (2)

@dataclass
class Item:
    name: str
    description: str | None = None

@dataclass
class Author:
    name: str
    items: list[Item] = field(default_factory=list)  # (3)

app = FastAPI()

@app.post("/authors/{author_id}/items/", response_model=Author)  # (4)
async def create_author_items(author_id: str, items: list[Item]):  # (5)
    return {"name": author_id, "items": items}  # (6)
```

#### Rank 5: `docs/fastapi/advanced/dataclasses.md` > `Using Dataclasses > Dataclasses in Nested Data Structures` [EXPECTED PAGE]
- **Scores**: vector_score=0.7605, rrf_score=0.029877
```markdown
You can also combine `dataclasses` with other type annotations to make nested data structures.

In some cases, you might still have to use Pydantic's version of `dataclasses`. For example, if you have errors with the automatically generated API documentation.

In that case, you can simply swap the standard `dataclasses` with `pydantic.dataclasses`, which is a drop-in replacement:

```python
from dataclasses import field  # (1)

from fastapi import FastAPI
from pydantic.dataclasses import dataclass  # (2)

@dataclass
class Item:
    name: str
    description: str | None = None

@dataclass
class Author:
    name: str
    items: list[Item] = field(default_factory=list)  # (3)

app = FastAPI()

@app.post("/authors/{author_id}/items/", response_model=Author)  # (4)
async def create_author_items(author_id: str, items: list[Item]):  # (5)
    return {"name": author_id, "items": items}  # (6)
```

---
