# Database schema

Alembic is the only thing that creates or changes the database schema. The
SQLAlchemy models in `backend/models.py` describe what the migrations produce,
and `alembic check` verifies the two agree.

- The web container runs `alembic upgrade head` at start (see `Dockerfile`).
- The pipeline (`python -m pipeline.run_pipeline`) refuses to start unless the
  database is at the Alembic head; it never runs migrations itself.
- `DATABASE_URL` overrides the URL in `alembic.ini` for every command below.

## New database

```sh
alembic upgrade head
alembic check   # should print "No new upgrade operations detected."
```

## Existing database with no `alembic_version` table

Before revision 007 the pipeline created tables with
`Base.metadata.create_all()`. A database built that way has no
`alembic_version` table, so `alembic upgrade head` fails with
`relation "raw_posts" already exists`. Stamp it as 006 and upgrade: revision
007 inspects the live schema and only creates the tables, columns, column
types and constraints that are missing, whatever vintage of the models
`create_all` ran from.

```sh
alembic stamp 006
alembic upgrade head
alembic check
```

## Adding a migration

Change the model in `backend/models.py`, then:

```sh
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
alembic check
```

Revision ids are sequential three-digit strings (`001`, `002`, ...); rename the
generated file and its `revision` / `down_revision` to match.
