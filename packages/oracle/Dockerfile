FROM python:3.12.4-slim

ENV PYTHONUNBUFFERED=1     PYTHONPATH="/opt/app"     PATH="/root/.local/bin:$PATH"

WORKDIR /opt/app

# install Poetry + deps
RUN pip install --no-cache-dir poetry==1.8.2

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false     && poetry install --without dev --no-root --no-interaction --no-ansi     && rm -rf /root/.cache/pypoetry /tmp/*

COPY oracle oracle

CMD ["python", "-u", "oracle/main.py"]
