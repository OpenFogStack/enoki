#!/usr/bin/env python3

import typing
import http.server

if __name__ == "__main__":
    try:
        import fn
    except ImportError:
        raise ImportError("Failed to import fn.py")

    # create a webserver at port 8080 and execute fn.fn for every request
    class tinyFaaSFNHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                self.send_response(200)
                self.end_headers()
                self.wfile.write("OK".encode("utf-8"))
                print("reporting health: OK")
                return

            self.log_error(f"GET request to unknown path {self.path}")
            self.send_response(404)
            self.end_headers()
            return

        def do_POST(self) -> None:
            d: typing.Optional[str] = self.rfile.read(
                int(self.headers["Content-Length"])
            ).decode("utf-8")
            if d == "":
                d = None
            try:
                res = fn.fn(d)
                self.send_response(200)
                self.end_headers()
                if res is not None:
                    self.wfile.write(res.encode("utf-8"))

                return
            except Exception as e:
                self.log_error(str(e))
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
                return

    with http.server.ThreadingHTTPServer(("", 8000), tinyFaaSFNHandler) as httpd:
        httpd.serve_forever()
