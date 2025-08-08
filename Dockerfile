FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH="/opt/app" \
    PATH="/root/.local/bin:$PATH" \
    PORT=8501

WORKDIR /opt/app

# ----- install Poetry + dependencies -----
RUN pip install --no-cache-dir poetry==1.8.2

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-root --no-interaction --no-ansi \
    # clean Poetry + tmp caches to shrink image
    && rm -rf /root/.cache/pypoetry /tmp/*

# ----- copy source code -----
COPY app app
COPY misc app/misc

# ----- launch Streamlit -----
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.headless=true"]