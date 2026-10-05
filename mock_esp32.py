"""ESP32 falso: sirve /data por HTTP igual que el firmware real.
Úsalo para probar la ruta WiFi de la app sin hardware:

    python mock_esp32.py            # escucha en :8080
    (en la app: fuente = ESP32 por WiFi, host = localhost:8080)
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from simulador import Simulador

sim = Simulador()


class H(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/data":
            self._json(sim.estado())
        elif u.path == "/cmd":
            c = parse_qs(u.query).get("c", [""])[0]
            if c == "reset":
                sim.reset()
            self._json({"ok": True, "cmd": c})
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("ESP32 simulado en http://localhost:8080/data")
    HTTPServer(("0.0.0.0", 8080), H).serve_forever()
