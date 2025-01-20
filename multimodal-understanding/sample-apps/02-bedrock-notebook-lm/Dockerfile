FROM python:3.11-slim

WORKDIR /app


# Install FFmpeg and Python dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg&& \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 --no-cache-dir install poetry

COPY pyproject.toml poetry.lock .

# Install dependencies without creating virtualenv
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi


COPY src src
EXPOSE 7860

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

WORKDIR /app/src
CMD ["python3", "app.py"]
