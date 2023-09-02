import http.server
import socketserver
import threading


class ServeSite:
    def __init__(self, port: int = 8181):
        # Start the SimpleHTTPServer in a separate thread
        self.PORT = port
        self.Handler = http.server.SimpleHTTPRequestHandler
        self.httpd = socketserver.TCPServer(("", self.PORT), self.Handler)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.start()

    def end(self):
        # Stop the SimpleHTTPServer when the instance is deleted
        self.httpd.shutdown()
        self.httpd.server_close()
        self.server_thread.join()

    def __del__(self):
        self.end()
