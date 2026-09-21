# Database layer: SQLModel

**Date:** 2026-09-21

Using [SQLModel](https://sqlmodel.tiangolo.com/) (by the FastAPI author, combines SQLAlchemy + Pydantic) over raw `sqlite3`. It's the current standard pairing for FastAPI + a database, integrates cleanly with FastAPI's Pydantic models, and isn't meaningfully more code than going raw for this project's scope.
