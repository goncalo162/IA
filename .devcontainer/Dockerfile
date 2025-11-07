# Dockerfile
FROM mcr.microsoft.com/devcontainers/python:2-3.12-bullseye

# Install minimal useful packages
RUN apt-get update \
  && apt-get install -y --no-install-recommends git curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*
