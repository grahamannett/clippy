import http.server
import socketserver
import threading


class ServeSite:
    def __init__(self, directory: str, base_url: str = "http://localhost", port: int = 8080, print_info: bool = True):
        self.directory = directory
        self.port = port
        self.base_url = base_url
        self.print_info = print_info

    @property
    def url(self):
        return f"{self.base_url}:{self.port}"

    def __enter__(self):
        self.start_server()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop_server()

    def print(self, *args, **kwargs):
        if self.print_info:
            print(*args, **kwargs)

    def start_server(self):
        _directory = self.directory

        class HTTPHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=_directory, **kwargs)

        class StoppableHTTPServer(http.server.HTTPServer):
            def run(self):
                try:
                    self.serve_forever()
                except KeyboardInterrupt:
                    pass
                finally:
                    self.server_close()

        Handler = HTTPHandler
        httpd = StoppableHTTPServer(("localhost", self.port), Handler)
        server_thread = threading.Thread(target=httpd.run)
        server_thread.start()

        self.print(f"Server started. Serving folder {self.directory} at {self.base_url}")
        self.httpd = httpd
        self.server_thread = server_thread

    def stop_server(self):
        self.httpd.shutdown()
        self.server_thread.join()
        self.print("Server stopped. No longer serving folder {self.directory} at {self.base_url}")
