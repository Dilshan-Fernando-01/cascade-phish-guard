import functools
import http.server
import os
import threading

HERE = os.path.dirname(os.path.abspath(__file__))

SITES = [
    ("real", 5173, "corvanetrust.test"),
    ("copy", 5174, "corvanetrust-secure-login.test"),
]


def serve(sub, port):
    directory = os.path.join(HERE, sub)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    httpd.serve_forever()


def main():
    threads = []
    for sub, port, hostname in SITES:
        t = threading.Thread(target=serve, args=(sub, port), daemon=True)
        t.start()
        threads.append(t)
        print(f"serving {sub}/ on http://127.0.0.1:{port}/  ->  http://{hostname}:{port}/ (once /etc/hosts is set)")
    print("\nPress Ctrl+C to stop both servers.")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
