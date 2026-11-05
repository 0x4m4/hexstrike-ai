# Security Policy

## Threat model

HexStrike AI is a remote command-execution service by design: `/api/command`, `/api/python/execute` and the `/api/tools/*` endpoints run shell commands and code on the host. Anyone who can send an authenticated request to the API can do anything the server's user can do. The security boundary is therefore **who can reach and authenticate to the API**, not the content of individual requests.

## Deployment requirements

- The server listens on `127.0.0.1` by default. Use `--host` (or `HEXSTRIKE_HOST`) to change it.
- Listening on a non-loopback address requires `HEXSTRIKE_API_TOKEN`. The server exits at startup otherwise. Clients must send `Authorization: Bearer <token>`.
- Without a token, the server rejects requests whose `Host` header is not `localhost`, `127.0.0.1` or `::1`, which blocks DNS-rebinding attacks from a browser on the same machine.
- `--debug` is refused on a non-loopback address, because the Flask debugger allows code execution.
- Run the server as an unprivileged user in a dedicated VM or container, and firewall its port.
- The file and Python-environment endpoints are confined to `/tmp/hexstrike_files` and `/tmp/hexstrike_envs`. Absolute paths and `..` components that escape those directories are rejected.

## Known limitations

- Tool endpoints build shell commands from request fields, so an authenticated caller can inject shell syntax through them. This is equivalent in power to `/api/command`, so the token is the control.
- Traffic is plain HTTP. Put a TLS-terminating reverse proxy in front of the server, or use an SSH tunnel, when the client and server are on different hosts, or the token is sent in clear text.

## Reporting a vulnerability

Report vulnerabilities privately through GitHub's **Report a vulnerability** button under this repository's **Security** tab (private vulnerability reporting). Please do not open public issues for unpatched vulnerabilities. Include the commit, the endpoint or file, reproduction steps, and the impact.

## References

- CVE-2025-35028 / GHSA-2j8m-rmq4-rcw5: unauthenticated command execution over HTTP POST on an all-interfaces bind.
