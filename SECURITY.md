# Security

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub: open the repository's
**Security** tab and choose **Report a vulnerability**. Please don't open a
public issue for a security problem.

This is an early-stage project maintained by one person. Reports will be
acknowledged as soon as possible, but no response time is guaranteed.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x (unreleased) | yes |

## Running the battery safely

`nullcase-battery` and `nullcase-coverage` **execute the target project's
tests**, over a hundred times per battery run. Test code can do anything the
current user can do. Only run them on code you trust, or run them in the
Docker image, which runs as a non-root user and can be started without
network or write access:

```bash
docker run --rm --network none -v "$PWD:/repo:ro" nullcase-battery tests/test_x.py::test_y
```

The container isolates the host filesystem and network, but it isn't a
hardened sandbox. The planned hosted service runs untrusted code in ephemeral
microVMs instead (see §3.6 of
[docs/technical-guide.md](docs/technical-guide.md)); that isn't part of this
repository.
