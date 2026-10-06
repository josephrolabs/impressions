# Pinned for reproducibility. Base image digest for python:3.12-slim,
# resolved 2026-09-29. Re-resolve with:
#   docker buildx imagetools inspect python:3.12-slim --format '{{json .Manifest}}'
# then update the digest below and rebuild.
FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f

RUN pip install --no-cache-dir pytest==8.4.0

RUN useradd --create-home --uid 65534 evaluator
USER evaluator
