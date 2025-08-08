#!/bin/bash

# This allows to start from scratch a dry run by resetting the back-end (mockexchange-api)

cd on_docker
# Create a flag to indicate reset
touch ./scripts/reset.flag
docker compose build --no-cache
docker compose up -d
# Remove the reset flag after starting
rm ./scripts/reset.flag