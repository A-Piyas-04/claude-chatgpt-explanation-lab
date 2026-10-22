FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependency layer first, so source edits do not reinstall the world.
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY explanationlab ./explanationlab
COPY alembic ./alembic
COPY alembic.ini ./

# Non-root: this process holds provider API keys.
RUN useradd --create-home --uid 10001 explab && chown -R explab:explab /app
USER explab

EXPOSE 8000
CMD ["uvicorn", "explanationlab.main:app", "--host", "0.0.0.0", "--port", "8000"]
