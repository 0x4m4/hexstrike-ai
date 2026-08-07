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
