import functools
import http.server
import os

HERE = os.path.dirname(os.path.abspath(__file__))

PORT = 5175
HOSTNAME = "amaz0n-secure.com"


def main():
    directory = os.path.join(HERE, "fake")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    print(f"serving fake/ on http://127.0.0.1:{PORT}/  ->  http://{HOSTNAME}:{PORT}/ (once /etc/hosts is set)")
    print("the real comparison side is just the real https://www.amazon.com/ -- no local copy needed")
    print("\nPress Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
