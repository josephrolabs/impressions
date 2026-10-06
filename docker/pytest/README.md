# Pytest execution image

`impressions run` grades generated code inside this image. The base image is
pinned by digest in the `Dockerfile` and pytest is pinned to `8.4.0`, so builds
are reproducible.

Build it from the repository root:

```bash
docker build -t impressions-python-pytest:3.12 docker/pytest
```

Verify the pinned contents:

```bash
docker run --rm impressions-python-pytest:3.12 python -m pytest --version
docker run --rm impressions-python-pytest:3.12 python --version
```

The harness checks for this image before grading and prints the build command
when it is missing.
