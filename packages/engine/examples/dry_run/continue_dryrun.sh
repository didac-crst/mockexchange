#!/bin/bash
# This allows to continue a dry run without resetting the back-end (mockexchange-api)

cd on_docker
docker compose build --no-cache
docker compose up -d