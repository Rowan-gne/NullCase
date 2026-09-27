# Battery image for local runs. Build from the repository root:
#   docker build -f sandbox/Dockerfile -t nullcase-battery .
# Run against a project mounted at /repo:
#   docker run --rm -v "$PWD:/repo" nullcase-battery tests/test_x.py::test_y
# The target project's own dependencies must also be installed in the image
# (e.g. a derived image that pip-installs them). With `--network none` the
# baseline cannot reach the network, so network-dependent tests fail there too.
FROM python:3.14-slim

COPY packages/pytest-plugin /src/packages/pytest-plugin
COPY sandbox /src/sandbox
RUN pip install --no-cache-dir /src/packages/pytest-plugin /src/sandbox \
    && rm -rf /src

RUN useradd --create-home battery
USER battery
WORKDIR /repo
ENTRYPOINT ["nullcase-battery", "--project", "/repo"]
