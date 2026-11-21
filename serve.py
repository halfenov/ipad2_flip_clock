#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Мини-сервер для перекидных часов (iPad 2 / iOS 9.3 Safari).

Запуск:
    python3 serve.py            # http://0.0.0.0:8000
    python3 serve.py 8080       # свой порт

Особенности:
  * отдаёт index.html на любой адрес (удобно для «на экран Домой»);
  * запрещает кэширование HTML, чтобы правки были видны сразу после перезагрузки;
  * печатает адреса, которые надо открыть на iPad.
"""

import os
import socket
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    # iPad 2 шлёт запросы по HTTP/1.1 — отвечаем тем же, но без keep-alive сюрпризов
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html") or path.endswith(".html"):
            # HTML всегда свежий
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        else:
            # иконку можно кэшировать на час
            self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_GET(self):
        # любой неизвестный путь -> index.html (часы открываются с любого URL)
        candidate = os.path.normpath(os.path.join(ROOT, self.path.split("?", 1)[0].lstrip("/")))
        if not os.path.isfile(candidate):
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


def lan_ips():
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print("=" * 62)
    print("  Перекидные часы запущены")
    print("  На этом компьютере : http://localhost:%d" % port)
    for ip in lan_ips():
        print("  На iPad (в той же сети) : http://%s:%d" % (ip, port))
    print("=" * 62)
    print("  Остановить: Ctrl+C")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")
        httpd.server_close()


if __name__ == "__main__":
    main()
