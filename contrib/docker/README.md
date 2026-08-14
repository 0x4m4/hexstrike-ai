# HexStrike-AI MCP (Docker)

A single self-contained Kali image that runs **HexStrike-AI** and exposes its
150+ security tools as a **Streamable HTTP MCP server** (endpoint `/mcp`) that
any native MCP client can connect to directly. Set **`OPENAPI=true`** to instead
front it with **[mcpo](https://github.com/open-webui/mcpo)** and serve an OpenAPI
schema + `/docs` UI (for Open WebUI, `curl`, and OpenAPI-only agents).

> **Authorized use only.** This image bundles offensive security tooling
> (port scanners, exploit frameworks, password crackers, web fuzzers, C2-style
> responders). Run it **only** against systems you own or are explicitly
> authorized to test. You are responsible for how it is used.

---

## Architecture

```
   default: MCP client         OPENAPI=true: OpenAPI client
   (Streamable HTTP, /mcp)      (Open WebUI, curl)
                 │                        │
                 │                   ┌────▼────┐  wraps stdio MCP as OpenAPI
                 │                   │  mcpo   │  (/opt/mcpo-venv)
                 │                   └────┬────┘
                 │  streamable-http       │ stdio
                 └───────────┬────────────┘
                    exposed port :8000
        ┌───────────────────▼─────────────┐
        │ hexstrike_mcp.py │  FastMCP      │  (/opt/hexstrike-venv)
        └───────────────────┬─────────────┘
                 │ HTTP  --server http://127.0.0.1:8888
      ┌──────────▼───────────┐
      │ hexstrike_server.py  │  Flask REST API (:8888)  (/opt/hexstrike-venv)
      └──────────┬───────────┘
                 │ subprocess
        ┌────────▼─────────┐
        │  security tools  │  nmap, nuclei, sqlmap, ghidra, ...
        └──────────────────┘
```

In the **default** mode `hexstrike_mcp.py` binds the exposed port itself and
speaks the MCP Streamable HTTP transport at `/mcp`. With **`OPENAPI=true`** it is
instead spawned over stdio behind `mcpo`, which serves OpenAPI on the same port.

Two **isolated Python venvs** are used because HexStrike pins
`fastmcp>=0.2.0,<1.0.0` (an older `mcp`) while mcpo needs a newer `mcp` — they
cannot coexist in one environment:

| venv | Python | Contents | Runs |
|------|--------|----------|------|
| `/opt/hexstrike-venv` | 3.13 | `requirements.txt` (flask, fastmcp, pwntools, angr, selenium, …) | `hexstrike_server.py` + `hexstrike_mcp.py` |
| `/opt/mcpo-venv` | system 3 | `mcpo` | `mcpo` |

Startup order is enforced by `entrypoint.sh`: Flask API first → health-gate on
`/health` → then the front-end (the MCP server by default, or `mcpo` when
`OPENAPI=true`), which connects back to Flask. The `mcpo` venv is only used in
OpenAPI mode.

---

## Build

Most of the HexStrike repo is **git-cloned inside the image** at build time,
not copied from the host. The build context is the **repo root** so the
Dockerfile can overlay the patched `hexstrike_mcp.py` (which lives at the repo
root) onto that clone.

```bash
# from the repo root
docker build -f contrib/docker/Dockerfile -t hexstrike-ai-mcp:latest .
# builds regardless of transport; the transport is chosen at run time (OPENAPI)
```

Or with Compose (paths in `docker-compose.yml` already point the context at
the repo root, so run it from this directory):

```bash
# from contrib/docker/
docker compose build
```

> First build is large and slow: Kali pulls a lot of security packages
> (`seclists` alone is ~1 GB) plus Go/gem/pip builds. Expect a multi-GB image.
> The build targets **amd64** (several prebuilt binaries — rustscan, x8,
> aquatone, pwninit, pwndbg, helm/opa/kube-bench/terrascan — are x86_64).

---

## Run

**Default — Streamable HTTP MCP server** (endpoint `/mcp`):

```bash
docker compose up -d
```

or plain Docker:

```bash
docker run -d --name hexstrike-ai-mcp \
  -p 8000:8000 -p 127.0.0.1:8888:8888 \
  --shm-size=2g \
  --cap-add=NET_ADMIN --cap-add=NET_RAW \
  hexstrike-ai-mcp:latest
# MCP endpoint -> http://localhost:8000/mcp
```

**OpenAPI mode** — front with `mcpo` (`/docs` UI), optionally API-key gated:

```bash
OPENAPI=true MCPO_API_KEY='choose-a-long-secret' docker compose up -d
# then open http://localhost:8000/docs
```

### Ports

| Port | Service | Purpose |
|------|---------|---------|
| **8000** | front-end | **Primary.** `/mcp` (default MCP transport) or `/docs` + `/openapi.json` (when `OPENAPI=true`). Point clients here. |
| 8888 | hexstrike Flask API | Optional/debug, **published to loopback only** (`127.0.0.1:8888`). Unauthenticated command/file endpoints — never publish network-wide. |

### Environment variables

| Var | Default | Meaning |
|-----|---------|---------|
| `OPENAPI` | *(false)* | *(false)* = Streamable HTTP MCP server at `/mcp` (**default**). `true` = OpenAPI via mcpo at `/docs`. See [Transports](#transports-mcp-default-vs-openapi). |
| `MCPO_API_KEY` | *(empty)* | **OPENAPI mode only.** If set, mcpo requires `Authorization: Bearer <key>` on every request. If empty, the endpoint is **unauthenticated**. Ignored in the default MCP mode (which has no built-in auth). |
| `PORT` | `8000` | Exposed front-end port (the MCP server or mcpo). `MCPO_PORT` is accepted as a legacy alias. |
| `HEXSTRIKE_PORT` | `8888` | Flask API port. |

### Secrets — `.env`

Private values (`MCPO_API_KEY`, `MULLVAD_ACCOUNT`, `MULLVAD_PRIVATE_KEY`,
`MULLVAD_ADDRESS`) live in a git-ignored **`.env`** file (perms `600`), not on the
command line. `docker compose` loads it automatically; for plain Docker use
`--env-file .env`. It is excluded from the image build context, so secrets never
bake into a layer. Copy `.env.example` → `.env` to start. Non-secret config
(`OPENAPI`, `MULLVAD_LOCATION`, ports) stays in `docker-compose.yml` or on
the command line.

```bash
# compose (auto-loads .env); OPENAPI is non-secret so pass it inline:
OPENAPI=true PUBLISH_PORT=8334 docker compose up -d
# plain docker (default MCP transport on host port 8334):
docker run -d --env-file .env -p 8334:8000 \
  --cap-add=NET_ADMIN --cap-add=NET_RAW --device /dev/net/tun \
  --sysctl net.ipv4.conf.all.src_valid_mark=1 --shm-size=2g \
  -e MULLVAD_LOCATION=ca hexstrike-ai-mcp:latest
```

### Runtime notes

- `--shm-size=2g` / `shm_size: '2gb'` is required for the headless Chromium
  browser agent and `aquatone`; without it headless Chrome crashes.
- `NET_ADMIN` / `NET_RAW` enable raw-socket tools (`nmap -sS`, `masscan`,
  `responder`, `arp-scan`). Drop them if you only run connect-scans.
- The container runs as root, so Chromium is launched with `--no-sandbox`
  `--headless=new` `--disable-dev-shm-usage`. Selenium is pointed at the
  **system** `/usr/bin/chromedriver` (`CHROMEDRIVER` env) so it works offline
  and never downloads a driver via webdriver-manager.

---

## Transports: MCP (default) vs. OpenAPI

The front-end on the exposed port has two modes, selected by `OPENAPI`:

| `OPENAPI` | Exposed port serves | Endpoint | Auth |
|-----------|---------------------|----------|------|
| *(unset / false)* — **default** | **`hexstrike_mcp.py` directly**, as a Streamable HTTP MCP server (no mcpo, no stdio bridge) | `/mcp` | none (front it with a proxy if needed) |
| `true` | **mcpo** OpenAPI proxy over the stdio MCP server | `/docs`, `/openapi.json`, `/<tool>` | `MCPO_API_KEY` (bearer) |

In the default MCP mode the server binds `0.0.0.0:<exposed port>` and speaks the
MCP **Streamable HTTP** transport at `/mcp` — point a native MCP client
(`"type": "streamable-http", "url": "http://<host>:<port>/mcp"`) straight at it.
The Flask tool backend (`:8888`) and VPN egress work identically in both modes.

```bash
# OpenAPI (mcpo) on host port 8334, egress via Mullvad CA:
docker run -d --name hexstrike-ai-mcp -p 8334:8000 \
  --cap-add=NET_ADMIN --cap-add=NET_RAW --device /dev/net/tun \
  --sysctl net.ipv4.conf.all.src_valid_mark=1 --shm-size=2g \
  -e OPENAPI=true -e MCPO_API_KEY='choose-a-long-secret' \
  -e MULLVAD_ACCOUNT=<your-mullvad-account-number> -e MULLVAD_LOCATION=ca \
  hexstrike-ai-mcp:latest
# OpenAPI docs -> http://<host>:8334/docs
```

---

## Routing egress through Mullvad VPN

The image can tunnel **all container-initiated (outbound) traffic** — every
security tool, DNS, updates — through **Mullvad WireGuard**, while the published
front-end port stays reachable from outside. This is opt-in: set `MULLVAD_ACCOUNT`.

```bash
docker run -d --name hexstrike-ai-mcp --restart unless-stopped \
  -p 8334:8000 \
  --cap-add=NET_ADMIN --cap-add=NET_RAW \
  --device /dev/net/tun \
  --sysctl net.ipv4.conf.all.src_valid_mark=1 \
  --shm-size=2g \
  -e MCPO_API_KEY=fake-key \
  -e MULLVAD_ACCOUNT=<your-mullvad-account-number> \
  -e MULLVAD_LOCATION=ca \
  hexstrike-ai-mcp:latest
```

Here the host's port **8334** forwards to the container's front-end (`:8000`), and
every connection the container *initiates* exits through a Canadian Mullvad
relay. Inbound requests to `:8334` are answered directly (not via the VPN) using
policy routing, so the API keeps working.

**How it works** (`vpn-up.sh`, run by the entrypoint before the app starts):
1. Registers an ephemeral WireGuard key with the Mullvad account (or reuses one
   you supply), and selects an active relay for `MULLVAD_LOCATION`.
2. Brings up `wg0` and sets the **default route** through it; pins the tunnel's
   own encrypted packets to the real interface so they don't recurse.
3. **Split routing for inbound:** connections arriving on the published port are
   `CONNMARK`-tagged and their replies routed back out the original gateway, so
   the published port answers normally while everything else goes via the VPN.
4. Points DNS at Mullvad (`10.64.0.1`) to avoid DNS leaks.
5. **Kill switch** (`MULLVAD_KILLSWITCH=1`, default): drops any egress that is
   not the tunnel, so tools can never leak your real IP. If the VPN is requested
   but fails to come up, the container refuses to start (fail-closed).

### VPN environment variables

| Var | Default | Meaning |
|-----|---------|---------|
| `MULLVAD_ACCOUNT` | *(empty)* | Mullvad account number. **Set this to enable the VPN.** Empty = no VPN. |
| `MULLVAD_LOCATION` | `ca` | Exit location: country code (`ca`), city code (e.g. `mtr`), or a full relay hostname (e.g. `ca-tor-wg-001`). |
| `MULLVAD_PRIVATE_KEY` / `MULLVAD_ADDRESS` | *(empty)* | Optional: reuse a pre-registered WireGuard key + tunnel address instead of registering a fresh one each start (Mullvad limits keys per account). |
| `MULLVAD_DNS` | `10.64.0.1` | In-tunnel DNS resolver. |
| `MULLVAD_KILLSWITCH` | `1` | `1` = block all non-tunnel egress. `0` = allow (not recommended). |

### Requirements

- Run flags: `--cap-add=NET_ADMIN`, `--device /dev/net/tun`, and
  `--sysctl net.ipv4.conf.all.src_valid_mark=1` (all set in `docker-compose.yml`).
- The **host** must have the `wireguard` kernel module available
  (`modprobe wireguard` — standard on modern kernels).
- Verify the exit from inside the container:
  `docker exec hexstrike-ai-mcp curl -s https://am.i.mullvad.net/json`
  → `mullvad_exit_ip: true`, `country: Canada`.

---

## Connecting a client

### Native MCP client (default)

Point any Streamable HTTP MCP client at the `/mcp` endpoint — e.g. in a client's
`mcpServers` config:

```json
{
  "hexstrike": {
    "type": "streamable-http",
    "url": "http://<host>:8000/mcp"
  }
}
```

The default mode has no built-in auth; put it behind the VPN, a reverse proxy,
or loopback if the port is reachable by anything untrusted.

### Open WebUI / OpenAPI clients (`OPENAPI=true`)

Start with `OPENAPI=true` (see [Transports](#transports-mcp-default-vs-openapi)),
then consume mcpo's OpenAPI. In Open WebUI, **Settings → Tools** (or
**Admin → Tools**) add a tool server:

- **URL:** `http://<host>:8000`
- **API key:** the value of `MCPO_API_KEY` (if set)

For any OpenAPI client/agent:

- Schema: `http://<host>:8000/openapi.json`
- Docs:   `http://<host>:8000/docs`
- Auth (if a key is set): `Authorization: Bearer <MCPO_API_KEY>`

```bash
curl -H "Authorization: Bearer $MCPO_API_KEY" http://localhost:8000/openapi.json
```

---

## Installed tool categories & channels

Every tool is installed through exactly one channel. `apt` names were verified
against the live `kali-rolling` index; Go/pip/gem/binary channels are used only
where apt has no correct package.

| Category | apt | Go (`go install`) | pipx | gem | git / prebuilt binary |
|----------|-----|-------------------|------|-----|-----------------------|
| **Network Recon / DNS / SMB** | nmap, masscan, autorecon, amass, subfinder, fierce, dnsenum, theharvester, arp-scan, nbtscan, smbclient, samba-common-bin, enum4linux, enum4linux-ng, smbmap, responder, netexec, onesixtyone, snmp | — | — | — | rustscan (.deb) |
| **Web Application Security** | gobuster, feroxbuster, dirsearch, ffuf, dirb, httpx-toolkit, hakrawler, nuclei, nikto, sqlmap, wpscan, arjun, paramspider, wafw00f, testssl.sh, sslscan, sslyze, uro, whatweb, wfuzz, commix, zaproxy, python2 | katana, gau, waybackurls, anew, qsreplace, jaeles, dalfox | — | — | x8, jwt_tool, nosqlmap, tplmap |
| **Password / Auth cracking** | hydra, john, john-data, hashcat, medusa, patator, netexec, crackmapexec, smbmap, evil-winrm, hash-identifier, hashid, ophcrack-cli, wordlists, seclists | — | — | — | — |
| **Binary / RE / Forensics** | gdb, gdb-peda, gef, radare2, ghidra, binwalk, python3-ropgadget, ropper, checksec, binutils, xxd*, upx-ucl, foremost, testdisk (+photorec), steghide, libimage-exiftool-perl, scalpel, bulk-extractor, sleuthkit, metasploit-framework, stegseek | — | volatility3 | one_gadget, zsteg | pwndbg (.deb), outguess (src), pwninit (bin), libc-database (git) |
| **Cloud / Container** | pacu, trivy, awscli (v2), azure-cli, kubectl | — | prowler, ScoutSuite, kube-hunter, checkov | — | helm, opa, kube-bench, terrascan, docker-bench-security, cloudmapper |
| **OSINT + toolchain + browser** | sherlock, spiderfoot, recon-ng, trufflehog, subjack, chromium, chromium-driver | — | social-analyzer, shodan, censys | — | aquatone (bin) |

\* `xxd` is installed as its own apt package; `pwntools` and `angr` come from
`requirements.txt` inside `/opt/hexstrike-venv` (not double-installed).

### Notes on notable resolutions

- **httpx** = apt `httpx-toolkit` (ProjectDiscovery Go binary), **not** the
  Python `httpx` library.
- **gau** installed via `go install` (apt `getallurls` names the binary
  `getallurls`, but HexStrike invokes `gau`).
- **netexec** is the maintained successor to crackmapexec; both are installed
  (README references both) — no conflict.
- **nosqlmap / tplmap** are Python 2 tools (not on PyPI) → git-built with
  `python2` wrappers. The PyPI `nosqlmap` name is a reserved placeholder and is
  deliberately **not** installed.
- **terrascan** is the Go tool from `tenable/terrascan` — the PyPI `terrascan`
  is the abandoned v0.2.x and is deliberately **not** installed.
- Three GDB plugins (`gdb-peda`, `gef`, `pwndbg`) are all installed but fight
  over `~/.gdbinit`; enable only one at a time.

### Health-probe coverage & compatibility aliases

HexStrike's `/health` endpoint probes **124** command names with `which <name>`.
This image satisfies **111/124**. Two things make that work:

1. **Extra apt tools** installed specifically to match probe names —
   `aircrack-ng` (airmon-ng/airodump-ng/aireplay-ng), `exploitdb`
   (`searchsploit`), `dotdotpwn`, `xsser`, `httpie`, `hashcat-utils`,
   `tcpdump`, `tshark`, `autopsy`, `kismet`, plus source-built `outguess`.
2. **Compatibility symlinks** (`/usr/local/bin`) where HexStrike's expected
   name differs from the packaged binary:

   | HexStrike probes | Real binary |
   |------------------|-------------|
   | `volatility3` | `vol` (pipx volatility3) |
   | `scout-suite` | `scout` (ScoutSuite) |
   | `shodan-cli` / `censys-cli` | `shodan` / `censys` |
   | `one-gadget` | `one_gadget` (gem) |
   | `ropgadget` | `ROPgadget` |
   | `bulk-extractor` | `bulk_extractor` |
   | `pwntools` | `pwn` |
   | `metasploit` | `msfconsole` |
   | `ophcrack` | `ophcrack-cli` |
   | `exploit-db` | `searchsploit` |
   | `jwt-analyzer` | `jwt_tool` |
   | `sleuthkit` | `fls` |
   | `libc-database` | `/opt/libc-database/find` |

---

## Intentionally NOT included

These are the **13 `/health` probes that remain unsatisfied** — each is a
GUI/commercial app, a server/kernel daemon, an online service, or a name with
no real CLI. None can run as a headless CLI in a container.

| Tool(s) | Why not included | Use instead |
|---------|------------------|-------------|
| **burpsuite, maltego, stegsolve, postman, insomnia, wireshark** | Desktop GUI / commercial apps (Java/Qt); useless headless. | `zaproxy`, `spiderfoot`/`recon-ng`/`theharvester`, `zsteg`/`steghide`, `httpie`/`curl`, `tshark` (CLI). |
| **clair, falco** | Need a separate server backend (Clair) / eBPF-kernel host privileges (Falco); not self-contained CLIs. The `clair_*` / `falco_*` MCP tools report `command not found`. | `trivy` for image CVEs; deploy Falco on the host. |
| **volatility (v2)** | End-of-life Python 2 tool. Only **volatility3** is installed (`vol`, aliased). The legacy v2 endpoint has no backing binary. | `volatility3_analyze`. |
| **have-i-been-pwned** | Online lookup service, not an installable CLI. | — |
| **hashpump** | Upstream repo (`bwall/HashPump`) was removed (404) and it is not in apt. | `hashpumpy` (Python lib) if you need hash-length-extension. |
| **api-schema-analyzer, graphql-scanner** | Placeholder probe names with no corresponding public CLI tool. | `httpx`, `nuclei` GraphQL templates, `jwt_tool`. |

Best-effort installs that may be skipped at build time if upstream breaks
(logged as `WARN`, non-fatal): **kube-hunter** (archived upstream, may fail on
Python 3.13 resolution), **cloudmapper** (archived upstream), and **outguess**
(source build). Everything else is a hard install.

---

## Security model

This image is an offensive-security toolbox; treat it as privileged and
untrusted-facing.

- **Runs as root, by design.** Many bundled tools (raw-socket scanners,
  `responder`, WireGuard) need root and/or specific capabilities. There is no
  drop to an unprivileged user. Run it in an isolated environment, not on a
  shared/multi-tenant host.
- **Capabilities, not `--privileged`.** The compose file grants only what the
  workloads need — `NET_RAW`/`NET_ADMIN` for raw-socket scanning and the VPN
  tunnel, plus `/dev/net/tun` and the `net.ipv4` sysctls. Nothing here requires
  `--privileged`; don't add it. If you never run privileged tooling or the VPN,
  drop the caps (see the comments in `docker-compose.yml`).
- **Network exposure.** Only the front-end port (`:8000`) is published. The Flask
  API (`:8888`) is container-internal — do **not** publish it. The **default MCP
  transport has no built-in auth** — bind it to loopback or keep it behind the
  VPN / a reverse proxy. In `OPENAPI=true` mode, set `MCPO_API_KEY` whenever the
  port is reachable by anything but localhost.
- **Secrets.** `MCPO_API_KEY` and Mullvad credentials live in `.env`
  (git-ignored, excluded from the build context and image). They are read at
  runtime, never baked into a layer.
- **Egress.** Optionally forced through Mullvad WireGuard (see *Routing egress
  through Mullvad VPN*), with a kill-switch so tool traffic can't leak to your
  real IP if the tunnel drops.
- **Authorized use only.** As stated up top — only against systems you own or
  are explicitly authorized to test.

---

## Troubleshooting

- **`docker logs hexstrike-ai-mcp`** — the Flask server output is prefixed
  `[hexstrike-server]`; entrypoint messages are prefixed `[entrypoint]`.
- **`/mcp` or `/docs` connection refused at startup** — the health-gate waits
  up to 60s for Flask; the container HEALTHCHECK has a 90s start-period. Give it
  a moment on first boot.
- **`/docs` returns 404** — you're in the default MCP mode; the OpenAPI UI only
  exists when `OPENAPI=true`. The MCP endpoint is `/mcp`.
- **mcpo `ImportError` / OpenAPI mode won't start** — only relevant with
  `OPENAPI=true`; see the `mcp<2` pin note below.
- **headless Chrome crashes** — ensure `--shm-size=2g` is set.
- **raw-socket scans fail / permission denied** — ensure `NET_RAW`/`NET_ADMIN`
  are granted.
- **arm64 host** — several prebuilt binaries are amd64-only; run under
  emulation or swap the arm64 asset URLs in the Dockerfile.
- **mcpo `ImportError: streamablehttp_client`** — mcpo 0.0.20 targets the
  `mcp` 1.x SDK; `mcp` 2.x removed that symbol. The Dockerfile pins `mcp<2` in
  `/opt/mcpo-venv` to avoid this. If you bump mcpo, revisit the pin.
