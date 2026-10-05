"""Cliente HTTP para leer el JSON que publica el ESP32 por WiFi."""
from __future__ import annotations

import json
import urllib.request


class ESP32Error(Exception):
    pass


def leer(host: str, timeout: float = 1.5) -> dict:
    """GET http://<host>/data -> dict. host puede ser '192.168.1.50' o 'ip:puerto'."""
    host = host.strip().removeprefix("http://").rstrip("/")
    try:
        with urllib.request.urlopen(f"http://{host}/data", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:  # red caída, JSON inválido, timeout...
        raise ESP32Error(str(e)) from e


def enviar_comando(host: str, cmd: str, timeout: float = 1.5) -> dict:
    """GET /cmd?c=<cmd> (reset, dron_start...). Devuelve la respuesta JSON."""
    host = host.strip().removeprefix("http://").rstrip("/")
    try:
        with urllib.request.urlopen(f"http://{host}/cmd?c={cmd}", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise ESP32Error(str(e)) from e
