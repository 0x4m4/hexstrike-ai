# Testing the security hardening

How to check, on your own machine, that the server is local-only by default, needs a token before it listens on any other address, and keeps file paths inside their folders.

The guide has two parts:

- **Part A, automated tests (about 2 minutes):** needs only Flask and requests.
- **Part B, manual checks against a running server (about 10 minutes):** needs the full `requirements.txt`.

The expected results for A1 to B6 were produced by running these exact commands on this branch, on Linux with Python 3.12.

That Part B run installed the server's runtime imports (Flask, requests, psutil, beautifulsoup4, selenium, aiohttp, mitmproxy 10.4) rather than all of `requirements.txt`. B7 was not run, because the test machine had no chromedriver.

## Before you start

- Python 3.8 to 3.12. Python 3.13 works for Part A only, because mitmproxy below 11 doesn't build on 3.13.
- `git` and `curl`.
- Nothing else listening on port 8888.

Get the branch:

```bash
git clone https://github.com/0x4m4/hexstrike-ai && cd hexstrike-ai
git fetch origin pull/292/head:security-hardening
git checkout security-hardening
```

## Part A: automated tests

### A1. Run the tests

```bash
python3 -m venv .venv-test && . .venv-test/bin/activate
pip install flask requests
python3 -m unittest discover -s tests -v
```

**Expected:** `Ran 21 tests` and `OK`.

The tests stub selenium, mitmproxy and the other heavy dependencies when they aren't installed.

| Test group | What it checks |
|---|---|
| `TestAuth` | Requests without the right `Bearer` token get `401`, including malformed or non-ASCII tokens. Without a token set, only a `localhost`, `127.0.0.1` or `::1` `Host` header is served; anything else gets `403`. |
| `TestFileContainment` | Absolute paths, `..`, symlink escapes, deleting the base folder, and escaping Python env names are all refused. Normal create, modify, list and delete still work. |
| `TestBrowserScheme` | `file:`, `javascript:`, `data:` and `chrome:` URLs are refused before Chrome starts. |
| `TestStartup` | The default bind is `127.0.0.1`, and `HEXSTRIKE_HOST` is honoured. A non-local host is refused without a token and refused with `--debug`; it is allowed with a token. |
| `TestMcpClient` | The MCP client sends `Authorization: Bearer <token>` from `HEXSTRIKE_API_TOKEN`. |

### A2. Confirm the tests catch the problems on `master`

This runs the same test file against the unpatched code:

```bash
git worktree add --detach ../hexstrike-master origin/master
mkdir -p ../hexstrike-master/tests
cp tests/test_security_hardening.py ../hexstrike-master/tests/
(cd ../hexstrike-master && python3 -m unittest discover -s tests 2>&1 | tail -1)
git worktree remove --force ../hexstrike-master
```

**Expected:** `FAILED (failures=13, errors=6)`.

19 of the 21 tests fail on `master`. The two that pass check normal file operations, which already worked.

## Part B: manual checks against a running server

Install the full dependencies in a separate environment:

```bash
deactivate 2>/dev/null; python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

These steps use two terminals. **Terminal 1** runs the server, and **Terminal 2** sends requests. Activate `.venv` in both. Stop the server with `Ctrl+C` between steps.

### B1. Startup refuses unsafe configurations

In Terminal 1:

```bash
unset HEXSTRIKE_API_TOKEN HEXSTRIKE_HOST
python3 hexstrike_server.py --host 0.0.0.0; echo "exit: $?"
```

**Expected:** the server exits instead of starting.

```
ERROR - Refusing to listen on 0.0.0.0 without authentication: set HEXSTRIKE_API_TOKEN
exit: 1
```

Then try a token together with `--debug`:

```bash
HEXSTRIKE_API_TOKEN=x python3 hexstrike_server.py --host 0.0.0.0 --debug; echo "exit: $?"
```

**Expected:** this is also refused.

```
ERROR - Refusing to expose the Flask debugger on 0.0.0.0: use a loopback host with --debug
exit: 1
```

### B2. The default mode is local-only

In Terminal 1:

```bash
python3 hexstrike_server.py
```

**Expected:** the startup box shows `Listening: 127.0.0.1:8888` and `API Token: not set (loopback only)`.

In Terminal 2, check the address the server actually listens on:

```bash
python3 -c "import psutil; print(sorted({c.laddr.ip for c in psutil.net_connections('tcp') if c.laddr.port == 8888 and c.status == 'LISTEN'}))"
```

**Expected:** `['127.0.0.1']`. On `master` this prints `['0.0.0.0']`.

You can also check with `ss -ltn 'sport = :8888'` on Linux, or `lsof -nP -iTCP:8888 -sTCP:LISTEN` on macOS.

### B3. Only local host names are served without a token

In Terminal 2:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8888/health
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: example.com' http://127.0.0.1:8888/health
```

**Expected:** `200`, then `403`.

The second request imitates a DNS-rebinding page. The browser would send the attacker's domain as the `Host` header, so the server refuses it.

### B4. File paths stay inside `/tmp/hexstrike_files`

With the same server running, in Terminal 2:

```bash
curl -s -X POST http://127.0.0.1:8888/api/files/create -H 'Content-Type: application/json' \
  -d '{"filename": "/tmp/hexstrike-outside.txt", "content": "test"}'
curl -s -X POST http://127.0.0.1:8888/api/files/create -H 'Content-Type: application/json' \
  -d '{"filename": "../hexstrike-outside.txt", "content": "test"}'
ls /tmp/hexstrike-outside.txt
```

**Expected:** both requests are refused, and the file is never created.

```
{"error":"Path escapes /tmp/hexstrike_files: /tmp/hexstrike-outside.txt","success":false}
{"error":"Path escapes /tmp/hexstrike_files: ../hexstrike-outside.txt","success":false}
ls: cannot access '/tmp/hexstrike-outside.txt': No such file or directory
```

On macOS the error names `/private/tmp/hexstrike_files`, because `/tmp` is a symlink there.

Then check that normal use still works:

```bash
curl -s -X POST http://127.0.0.1:8888/api/files/create -H 'Content-Type: application/json' \
  -d '{"filename": "review/ok.txt", "content": "test"}'
curl -s -X DELETE http://127.0.0.1:8888/api/files/delete -H 'Content-Type: application/json' \
  -d '{"filename": "review"}'
```

**Expected:** `{"path":"/tmp/hexstrike_files/review/ok.txt","size":4,"success":true}`, then `{"success":true}`.

Stop the server with `Ctrl+C`.

### B5. Token mode

In Terminal 1:

```bash
export HEXSTRIKE_API_TOKEN=review-token
python3 hexstrike_server.py --host 0.0.0.0
```

**Expected:** the server starts, and the startup box shows `Listening: 0.0.0.0:8888` and `API Token: required`.

In Terminal 2:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8888/health
curl -s -o /dev/null -w '%{http_code}\n' -H 'Authorization: Bearer wrong' http://127.0.0.1:8888/health
curl -s -o /dev/null -w '%{http_code}\n' -H 'Authorization: Bearer review-token' http://127.0.0.1:8888/health
```

**Expected:** `401`, `401`, `200`.

To test across the network, run the same requests from a second machine against this machine's IP address.

### B6. The MCP client sends the token

Keep the B5 server running. In Terminal 2, run the client once with the token and once without:

```bash
HEXSTRIKE_API_TOKEN=review-token python3 hexstrike_mcp.py --server http://127.0.0.1:8888 </dev/null 2>&1 | grep -E "Successfully connected|401" | head -2
python3 hexstrike_mcp.py --server http://127.0.0.1:8888 </dev/null 2>&1 | grep -E "Successfully connected|401" | head -2
```

**Expected:** the first run prints `Successfully connected to HexStrike AI API Server at http://127.0.0.1:8888`. The second prints `Connection test failed: 401 Client Error: UNAUTHORIZED`.

The client needs `mcp` below 2.0. The `.venv` from `requirements.txt` already has it: `fastmcp<1` requires `mcp<2`. If you install packages by hand instead, use `pip install "mcp<2"`.

Stop the server with `Ctrl+C`.

### B7. Optional: the browser agent through HTTP

The `/api/tools/browser-agent` endpoint starts Chrome before it navigates, so this check needs Chrome and chromedriver installed. `TestBrowserScheme` in Part A covers the same check without a browser.

With the B2 server running:

```bash
curl -s -X POST http://127.0.0.1:8888/api/tools/browser-agent -H 'Content-Type: application/json' \
  -d '{"action": "navigate", "url": "file:///etc/hostname"}'
```

**Expected:** a response that includes `"error":"Unsupported URL scheme: file"` and `"success":false`. If you get `Failed to setup browser`, Chrome or chromedriver isn't available. In that case rely on `TestBrowserScheme`.

## Cleanup

```bash
unset HEXSTRIKE_API_TOKEN
deactivate
rm -rf .venv .venv-test hexstrike.log
```

## Results checklist

| # | Check | Expected |
|---|---|---|
| A1 | Unit tests on this branch | 21 pass |
| A2 | Same tests on `master` | 19 fail |
| B1 | Non-local host without a token; `--debug` on a non-local host | Exit 1, nothing listening |
| B2 | Default bind | `127.0.0.1` only |
| B3 | Foreign `Host` header, no token set | `403` |
| B4 | Absolute or `..` file path | Refused, no file written |
| B5 | Missing, wrong, then correct token | `401`, `401`, `200` |
| B6 | MCP client with and without the token | Connects; `401` |
| B7 | `file://` in the browser agent (optional) | `Unsupported URL scheme` |
