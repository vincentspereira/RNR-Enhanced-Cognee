# Full legacy Enhanced Cognee image. The restricted Hermes image is
# docker/Dockerfile.memory. Both use a hashed, resolved dependency lock.
FROM python:3.12.15-slim-trixie AS dependencies
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev cmake git libmagic1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-build.lock /app/
RUN pip install --no-cache-dir --require-hashes -r requirements-build.lock \
    && python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --require-hashes -r requirements-build.lock
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements-full.lock /app/
RUN pip install --no-cache-dir --require-hashes -r requirements-full.lock

FROM dependencies AS build
COPY pyproject.toml README.md /app/
COPY src/ /app/src/
COPY bin/ /app/bin/
COPY cognee/ /app/cognee/
COPY distributed/ /app/distributed/
RUN pip install --no-cache-dir --no-deps --no-build-isolation --target /app/runtime .
COPY config/ /app/config/
COPY migrations/ /app/migrations/
COPY alembic/ /app/alembic/
COPY alembic_enhanced/ /app/alembic_enhanced/
COPY alembic.ini alembic-enhanced.ini entrypoint.sh /app/
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

FROM python:3.12.15-slim-trixie
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 libmagic1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-build.lock /app/
RUN pip install --no-cache-dir --require-hashes -r requirements-build.lock
COPY --from=dependencies /opt/venv /opt/venv
COPY --from=build /app /app
RUN PYTHONPATH=/app/runtime /opt/venv/bin/python -m pip check \
    && python -m pip uninstall -y pip \
    && /opt/venv/bin/python -m pip uninstall -y pip
RUN groupadd --system appuser \
    && useradd --system --gid appuser --create-home --home-dir /home/appuser appuser \
    && mkdir -p /app/data /app/logs /app/tmp \
    && chown -R appuser:appuser /app/data /app/logs /app/tmp
ENV PATH="/app/runtime/bin:/opt/venv/bin:$PATH" PYTHONPATH=/app:/app/runtime PYTHONUNBUFFERED=1 COGNEE_TELEMETRY_ENABLED=0 COGNEE_LOG_FILE=false ENHANCED_LOAD_DOTENV=0
# The service never needs setuid/setgid helpers. Keep their files but remove
# privilege-changing mode bits, including those inherited from the base image.
RUN find / -xdev -type f -perm /6000 -exec chmod a-s {} +
USER appuser
EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
