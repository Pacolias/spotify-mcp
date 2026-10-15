# The production image (journal 48). Two stages: the first installs the
# locked dependencies with uv, the second copies only the resulting
# virtualenv into a clean image, so build tools don't ship.

FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

# Dependencies first, in their own layer: rebuilt only when uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.14-slim
RUN useradd --create-home --uid 1000 app
COPY --from=build --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
# Don't run as root inside the container.
USER app
WORKDIR /home/app

EXPOSE 8000
# Render tells the service which port to listen on through $PORT. The schema
# migrations run at startup (init_db in the app's lifespan).
CMD ["sh", "-c", "exec spotify-mcp serve --host 0.0.0.0 --port ${PORT:-8000}"]
