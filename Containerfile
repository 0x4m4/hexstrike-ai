# ============================================================================
# HexStrike AI API — contenedor aislado (2026-08-06)
#
# HexStrike ejecuta comandos arbitrarios SIN auth (shell=True). El contenedor
# añade la capa de aislamiento: usuario no-root, rootfs read-only, cap-drop
# ALL, no-new-privileges. El auth por X-API-Key sigue siendo OBLIGATORIO
# (HEXSTRIKE_API_KEY) — el contenedor NO reemplaza al token, lo complementa.
#
# Build:  podman build -t hexstrike-ai:isolated .
# Run:    podman run -d --name hexstrike-ai \
#           -p 127.0.0.1:8888:8888 \
#           --read-only \
#           --cap-drop ALL \
#           --security-opt no-new-privileges \
#           --tmpfs /tmp:rw,size=512m \
#           -v hexstrike-data:/home/hexstrike/data \
#           -e HEXSTRIKE_API_KEY=$(cat ~/.config/hexstrike.env | cut -d= -f2) \
#           hexstrike-ai:isolated
# ============================================================================
FROM python:3.11-slim-bookworm

# Dependencias del sistema: mínimas (el server NO necesita las 150 tools para
# arrancar; las rutas de binario angr/pwn son lazy). curl para HEALTHCHECK.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/hexstrike

# Primero requirements (cachea la capa pip): los deps de ARRANQUE del
# server — verificado 2026-08-06 que importa top-level flask, requests,
# aiohttp, selenium, mitmproxy. angr/pwntools son lazy (rutas de binario)
# y se omiten para mantener la imagen pequeña; añadir si se necesitan.
COPY requirements.txt .
RUN pip install --no-cache-dir \
        "flask>=2.3.0,<4.0.0" \
        "requests>=2.31.0,<3.0.0" \
        "psutil>=5.9.0,<6.0.0" \
        "fastmcp>=0.2.0,<1.0.0" \
        "beautifulsoup4>=4.12.0,<5.0.0" \
        "aiohttp>=3.8.0,<4.0.0" \
        "selenium>=4.15.0,<5.0.0" \
        "webdriver-manager>=4.0.0,<5.0.0" \
        "mitmproxy>=9.0.0,<11.0.0"

# App
COPY hexstrike_server.py .
COPY hexstrike_mcp.py .
COPY assets/ assets/

# Usuario no-root
RUN useradd --create-home --uid 10001 hexstrike \
    && mkdir -p /home/hexstrike/data \
    && chown -R hexstrike:hexstrike /home/hexstrike /opt/hexstrike

USER hexstrike

# WORKDIR en home del usuario (writable bajo --read-only via tmpfs/volumen).
# El server escribe hexstrike.log en el cwd — con /opt/hexstrike read-only
# moriría con OSError Errno 30 (verificado 2026-08-06). El log va a /tmp
# (tmpfs declarado en el run).
WORKDIR /home/hexstrike

# Aislamiento por defecto (reforzable desde el run): rootfs read-only se
# declara en `podman run --read-only`; /tmp va como tmpfs.
ENV HEXSTRIKE_HOST=127.0.0.1 \
    HEXSTRIKE_PORT=8888 \
    PYTHONUNBUFFERED=1

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8888/health >/dev/null || exit 1

CMD ["python", "/opt/hexstrike/hexstrike_server.py"]
