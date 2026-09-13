FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.4.0

RUN useradd --create-home --uid 65534 evaluator
USER evaluator
