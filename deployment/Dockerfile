FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_INSTALL_DIR=/python

# Change the working directory to the `app` directory
WORKDIR /app

RUN apt update && apt install -y curl gnupg

# Microsoft GPG-Schlüssel korrekt importieren
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg

# Repository-Liste mit signed-by Option manuell erstellen
RUN echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list

# ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && ACCEPT_EULA=Y apt install -y build-essential locales libldap2-dev libsasl2-dev unixodbc-dev msodbcsql18 mssql-tools18
RUN uv python install 3.14

COPY kanbanapi /app

# Install dependencies
RUN uv sync --no-dev

FROM gcr.io/distroless/cc

# Copy the Python version
COPY --from=builder --chown=python:python /python /python
COPY --from=builder /usr/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/
COPY --from=builder /lib/x86_64-linux-gnu/ /lib/x86_64-linux-gnu/

# Copy ODBC drivers and configuration
COPY --from=builder /opt/microsoft/ /opt/microsoft/
COPY --from=builder /etc/odbcinst.ini /etc/odbcinst.ini

ENV LD_LIBRARY_PATH="/usr/lib"

WORKDIR /app

# Copy the application from the builder
COPY --from=builder --chown=app:app /app/ /app/

ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["/app/.venv/bin/gunicorn", "--bind", ":80", "kanbanapi.wsgi", "--access-logfile", "'-'"]

