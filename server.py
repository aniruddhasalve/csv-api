
"""Small dependency-free REST utility service."""
from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def response(status: int, payload, content_type: str = "application/json"):
    if content_type == "application/json":
        data = json.dumps(payload, ensure_ascii=False).encode()
    elif isinstance(payload, str):
        data = payload.encode()
    else:
        data = payload
    return status, {"Content-Type": content_type, "Content-Length": str(len(data))}, data


def error(message: str, status: int = 400):
    return response(status, {"error": message})


class Handler(BaseHTTPRequestHandler):
    def _serve(self, method: str):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            payload = None
        status, headers, body = handle(method, self.path.split("?", 1)[0], payload)
        self.send_response(status)
        for key, value in headers.items(): self.send_header(key, value)
        self.end_headers(); self.wfile.write(body)
    do_GET = lambda self: self._serve("GET")
    do_POST = lambda self: self._serve("POST")
    do_PUT = lambda self: self._serve("PUT")
    do_DELETE = lambda self: self._serve("DELETE")
    def log_message(self, *_): pass


import csv, io

def handle(method,path,payload):
    if method=="GET" and path=="/health": return response(200,{"ok":True,"service":"csv-api"})
    if method=="POST" and path=="/to-json":
        if not isinstance(payload,dict) or not isinstance(payload.get("csv"),str): return error("csv is required")
        try: rows=list(csv.DictReader(io.StringIO(payload["csv"])))
        except csv.Error as exc: return error(str(exc))
        return response(200,{"rows":rows})
    if method=="POST" and path=="/from-json":
        rows=payload.get("rows") if isinstance(payload,dict) else None
        if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows): return error("rows must be a list of objects")
        fields=[]
        for row in rows:
            for field in row:
                if field not in fields: fields.append(field)
        out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=fields); writer.writeheader(); writer.writerows(rows); return response(200,{"csv":out.getvalue()})
    return error("route not found",404)


def serve(host="0.0.0.0", port=8080):
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
