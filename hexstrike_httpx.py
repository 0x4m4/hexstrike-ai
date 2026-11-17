"""ProjectDiscovery httpx integration helpers (issue #77).

The Python ``httpx`` library ships a command-line client that is also
named ``httpx``. When it is pip-installed into HexStrike's virtualenv it
shadows the intended `ProjectDiscovery httpx
<https://github.com/projectdiscovery/httpx>`_ binary on ``PATH``:

* ``which httpx`` succeeds, so ``/health`` used to report ``httpx: true``
  even though no usable prober was installed.
* The Python CLI rejects ProjectDiscovery flags (``httpx -version`` fails
  with ``Error: No such option '-e'.``), so every probe failed.

These helpers keep the two binaries apart:

* :func:`is_projectdiscovery_httpx` validates a candidate binary by
  running ``<binary> -version`` and requiring a zero exit code plus a
  ``vX.Y.Z`` version string in the output.
* :func:`find_projectdiscovery_httpx` searches the ``PATH`` binary, the
  usual Go install locations, and the ``HEXSTRIKE_HTTPX_BINARY``
  override, returning the first candidate that passes validation.
* :func:`build_httpx_command` builds the probe command, using ``-u``
  for a single target and ``-l`` only for an existing file of targets
  (ProjectDiscovery ``-l`` expects a file, not a bare host).

This module is deliberately stdlib-only so it can be unit-tested without
importing ``hexstrike_server`` (which pulls in the full Flask / pwntools /
angr stack).
"""

import os
import re
import shlex
import shutil
import subprocess

# ProjectDiscovery httpx prints a version such as ``v1.7.1`` for
# ``httpx -version``. The Python httpx CLI instead exits non-zero with
# ``Error: No such option '-e'.`` for the same invocation.
_PD_HTTPX_VERSION_RE = re.compile(r"v?\d+\.\d+\.\d+")

#: Install hint shown when no ProjectDiscovery httpx binary is found.
INSTALL_HINT = (
    "ProjectDiscovery httpx binary not found. The Python 'httpx' package "
    "(if installed) is a different tool and cannot run this probe. Install "
    "ProjectDiscovery httpx, e.g. "
    "`go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest`, "
    "or set HEXSTRIKE_HTTPX_BINARY to the path of the httpx binary."
)


def is_projectdiscovery_httpx(binary, timeout=10):
    """Return True if *binary* is the ProjectDiscovery httpx binary.

    Runs ``<binary> -version`` and requires a zero exit code plus a
    ``vX.Y.Z`` version string in the combined output. The Python httpx
    CLI fails this check: it exits non-zero with ``No such option '-e'``.
    """
    if not binary:
        return False
    try:
        proc = subprocess.run(
            [binary, "-version"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0 and _PD_HTTPX_VERSION_RE.search(output) is not None


def _go_bin_candidates():
    """Candidate install paths for a Go-installed httpx binary."""
    candidates = []
    gopath = os.environ.get("GOPATH")
    if not gopath:
        try:
            proc = subprocess.run(
                ["go", "env", "GOPATH"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode == 0:
                gopath = proc.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            gopath = None
    if gopath:
        candidates.append(os.path.join(gopath, "bin", "httpx"))
    candidates.append(os.path.expanduser("~/go/bin/httpx"))
    return candidates


def find_projectdiscovery_httpx():
    """Locate the ProjectDiscovery httpx binary, or return None.

    Search order: the ``HEXSTRIKE_HTTPX_BINARY`` override, the ``httpx``
    on ``PATH`` (validated -- a pip-installed Python httpx CLI is
    rejected), then the usual Go binary locations. Returns the first
    candidate that passes :func:`is_projectdiscovery_httpx`.
    """
    seen = set()
    candidates = []

    override = os.environ.get("HEXSTRIKE_HTTPX_BINARY")
    if override:
        candidates.append(override)
    on_path = shutil.which("httpx")
    if on_path:
        candidates.append(on_path)
    candidates.extend(_go_bin_candidates())

    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if os.path.isfile(candidate) and is_projectdiscovery_httpx(candidate):
            return candidate
    return None


def build_httpx_command(binary, target, threads=50, probe=True,
                        tech_detect=False, status_code=False,
                        content_length=False, title=False, web_server=False,
                        additional_args=""):
    """Build the shell command probing *target* with ProjectDiscovery httpx.

    A single target (URL or host) uses ``-u``; ``-l`` is used only when
    *target* is an existing file of targets, because ProjectDiscovery
    ``-l`` expects a file, not a bare host.
    """
    parts = [shlex.quote(binary)]
    if os.path.isfile(target):
        parts.extend(["-l", shlex.quote(target)])
    else:
        parts.extend(["-u", shlex.quote(target)])
    parts.extend(["-t", str(int(threads))])
    if probe:
        parts.append("-probe")
    if tech_detect:
        parts.append("-tech-detect")
    if status_code:
        parts.append("-sc")
    if content_length:
        parts.append("-cl")
    if title:
        parts.append("-title")
    if web_server:
        parts.append("-server")
    if additional_args:
        parts.append(additional_args)
    return " ".join(parts)
