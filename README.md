# Pytest Fixture Classes

Typed [factory fixtures](https://docs.pytest.org/en/6.2.x/fixture.html#factories-as-fixtures) that work well with dependency injection, autocompletetion, type checkers, and language servers.

No mypy plugins required!

## Installation

`pip install pytest-fixture-classes`

## Usage

### Quickstart

Here's a factory fixture from [pytest's documentation](https://docs.pytest.org/en/6.2.x/fixture.html#factories-as-fixtures):

```python
from typing import Any
import pytest


@pytest.fixture()
def orders() -> list[str]:
    return ["order1", "order2"]


@pytest.fixture
def make_customer_record(orders: list[str]) -> Callable[str, dict[str, Any]]:
    def _make_customer_record(name):
        return {"name": name, "orders": orders}

    return _make_customer_record


def test_customer_records(make_customer_record: Callable[str, dict[str, Any]]):
    customer_1 = make_customer_record("Lisa")
    customer_2 = make_customer_record("Mike")
    customer_3 = make_customer_record("Meredith")
```

And here's the same factory implemented using fixture classes:

```python
from pytest_fixture_classes import fixture_class
from typing import Any
import pytest


@pytest.fixture()
def orders():
    return ["order1", "order2"]


@fixture_class(name="make_customer_record")
class MakeCustomerRecord:
    orders: list[str]

    def __call__(self, name: str) -> dict[str, Any]:
        return return {"name": name, "orders": orders}


def test_customer_records(make_customer_record: MakeCustomerRecord):
    customer_1 = make_customer_record("Lisa")
    customer_2 = make_customer_record("Mike")
    customer_3 = make_customer_record("Meredith")
```

You can, of course, add any methods you like into the class but I prefer to keep it a simple callable.

### Rationale

If we want factory fixtures that automatically make use of pytest's dependency injection, we are essentially giving up any IDE/typechecker/language server support because such fixtures cannot be properly typehinted because they are returning a callable, not a value. And python is still pretty new to typehinting callables.

So we can't use ctrl + click, we don't get any autocompletion, and mypy/pyright won't warn us when we are using the factory incorrectly. Additionally, any changes to the factory's interface will require us to search for its usages by hand and fix every single one.

Fixture classes solve all of the problems I mentioned:

* Autocompletion out of the box
* Return type of the fixture will automatically be inferred by pyright/mypy
* When the interface of the fixture changes or when you use it incorrectly, your type checker will warn you
* Search all references and show definition (ctrl + click) also works out of the box

### Usage scenario

Let's say that we have a few pre-existing fixtures: `db_connection`, `http_session`, and `current_user`. Now we would like to write a new fixture that can create arbitrary users based on `name`, `age`, and `height` arguments. We want our new fixture, `create_user`, to automatically get our old fixtures using dependency injection. Let's see what such a fixture will look like:

```python
import pytest
import requests

@pytest.fixture
def db_connection() -> dict[str, str]:
    ...

@pytest.fixture
def http_session() -> requests.Session:
    ...


@pytest.fixture
def current_user() -> requests.Session:
    ...


@pytest.fixture
async def create_user(
    db_connection: dict[str, str],
    http_session: requests.Session,
    current_user: requests.Session,
) -> Callable[[str, int, int], dict[str, str | int | bool]]:
    async def inner(name: str, age: int, height: int):
        user = {...}
        self.db_connection.execute(...)
        if self.current_user[...] is not None:
            self.http_session.post(...)
        
        return user

    return inner

def test_my_code(create_user: Callable[[str, int str], dict[str, str | int | bool]]):
    johny = create_user("Johny", 27, 183)
    michael = create_user("Michael", 43, 165)
    loretta = create_user("Loretta", 31, 172)

    # Some testing code below
    ...

```

See how ugly and vague the typehints for create_user are? Also, see how we duplicate the return type and argument information? Additionally, if you had thousands of tests and if `test_my_code` with `create_user` were in different files, you would have to use plaintext search to find the definition of the fixture if you wanted to see how to use it. Not too nice.

Now let's rewrite this code to solve all of the problems I mentioned:

```python
from pytest_fixture_classes import fixture_class
from collections.abc import Mapping
import requests
import pytest


@pytest.fixture
def db_connection() -> dict[str, str]:
    ...


@pytest.fixture
def http_session() -> requests.Session:
    ...


@pytest.fixture
def current_user() -> Mapping[str, str | int | bool]:
    ...


@fixture_class(name="create_user")
class CreateUser:
    db_connection: Mapping[str, str]
    http_session: requests.Session
    current_user: Mapping[str, str | int | bool]

    def __call__(self, name: str, age: int, height: int) -> dict[str, str | int | bool]:
        user = {...}
        self.db_connection.execute(...)
        if self.current_user[...] is not None:
            self.http_session.post(...)
        
        return user


def test_my_code(create_user: CreateUser):
    johny = create_user("Johny", 27, 183)
    michael = create_user("Michael", 43, 165)
    loretta = create_user("Loretta", 31, 172)

    # Some testing code below
    ...
```

## Implementation details

* The fixture_class decorator turns your class into a frozen dataclass with slots so you won't be able to add new attributes to it after definiton. You can, however, define any methods you like except `__init__`.
