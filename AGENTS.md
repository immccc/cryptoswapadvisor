# AGENTS.md

This file contains instructions for AI agents working on this codebase.

## Code Structure

Follow a Domain-Driven Design (DDD) approach, organizing code by domain. Every component must follow this folder structure:

```
component/
   __init__.py
   model.py              # Entity classes based on Pydantic BaseModel
   actions.py            # Functionality provided by the component
   chat_handlers.py      # Telegram interaction handlers
   db/
       __init__.py
       repository.py     # Interface holding functions to interact with different database types
       redis.py          # Redis implementation of repository (if needed)
       test_db.py        # Basic in-memory implementation of repository, used in tests and backtests
       sql/
           __init__.py
           _mapping.py   # Mapping ORM objects to component public objects
           model.py      # ORM mapping objects using SQLModel
           repository.py # Relational DB implementation of repository.py using SQLModel
```

## Unit Testing

1. All changes must carry unit tests.
2. Tests must be `pytest` tests. Use `pytest-mock` for mocks when possible. Use `freezegun` for date manipulation.
3. Reuse existing mocks when possible. If new mocks are needed, create them in the closest `conftest.py` to the file being created or edited.
4. Use an arrange, act, assert approach.
5. Use clear, short names for test functions that make it easy to understand what is being tested. Avoid overly long function names.
6. Place tests next to the file contained by the function subject to test. For example: `simulation/actions.py` => `simulation/some_new_action_test.py`

## AI-Generated Code

All AI-generated code must be enclosed with comments that reflect its AI origin:

```python
# AI-GENERATED-START
def my_function():
    pass
# AI-GENERATED-END
```

## General Rules

1. **Enforce code quality and legibility**. Follow Clean Code principles. Split large functions into smaller ones with clear names, treating them as sequential steps.
2. **Stick to SOLID principles**.
3. **Performance**: Computing-intensive functions must be implemented using Numba. Avoid Pythonic code that slows down Numba-generated code. Follow performance best practices from the [Numba documentation](https://numba.pydata.org/numba-doc/dev/user/performance-tips.html).
