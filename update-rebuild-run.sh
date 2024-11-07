#!/bin/bash

docker compose pull
docker compose -f docker-compose.yml down
docker compose -f docker-compose.yml rm -f
docker compose -f docker-compose.yml build --no-cache
docker compose -f docker-compose.yml up -d --force-recreate
docker compose logs -f
