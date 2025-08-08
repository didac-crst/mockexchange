FROM python:3.11-slim

WORKDIR /app

# --- install Poetry -------------------------------------------------
RUN pip install --no-cache-dir poetry==1.8.2           # or any pinned version

# --- copy dependency spec first (better layer-caching) -------------
# If poetry.lock is existent, we copy it to ensure that the dependencies are locked.
COPY pyproject.toml poetry.lock ./
# If poetry.lock is not present, we skip poetry.lock copy.
# COPY pyproject.toml ./

# install runtime deps only
# If poetry.lock is not present, we will generate it with the next command.
RUN poetry install --no-root --only main

# --- copy the actual source code -----------------------------------
COPY src ./src
RUN ls -l ./src

# make the package importable for uvicorn
RUN python -m pip install --no-cache-dir --editable .

EXPOSE 8000
CMD ["uvicorn", "mockexchange_api.server:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "./src/mockexchange_api/log_cfg.json"]