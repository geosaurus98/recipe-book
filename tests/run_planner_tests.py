"""Runs tests/planner_tests.js inside the built planner in headless Chrome or Edge.

Build first (python planner/build.py), then:  python tests/run_planner_tests.py
Set CHROME to the browser's path if it isn't found automatically.
"""
import http.server
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CANDIDATES = [
    os.environ.get("CHROME"), "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_browser():
    for c in CANDIDATES:
        if c and (shutil.which(c) or Path(c).exists()):
            return shutil.which(c) or c
    sys.exit("No Chrome, Chromium or Edge found. Set CHROME to its path.")


def close(browser):
    """Stop the browser and all its helper processes, or they can stall the next run."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(browser.pid)], capture_output=True)
    else:
        os.killpg(browser.pid, signal.SIGKILL)
    browser.wait()


class Results(http.server.BaseHTTPRequestHandler):
    """Receives the results the test page POSTs back."""
    results = None
    done = threading.Event()

    def do_POST(self):
        Results.results = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Results.done.set()
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def log_message(self, *args):
        pass


def test_page(report_url):
    """The built planner with the tests added: no saved plan to start with, errors recorded."""
    html = (ROOT / "planner" / "index.html").read_text(encoding="utf-8")
    before = ('<script>try { localStorage.clear(); } catch {} window.__errors = [];'
              f' window.__report = {json.dumps(report_url)};'
              ' addEventListener("error", e => __errors.push(String(e.message)));'
              ' addEventListener("unhandledrejection", e => __errors.push("promise: " + e.reason));</script>')
    tests = (ROOT / "tests" / "planner_tests.js").read_text(encoding="utf-8")
    return html.replace("<head>", "<head>" + before, 1) + "<script>\n" + tests + "\n</script>\n"


def run_page(server, uri_suffix=""):
    """Open the test page once (George's planner, or GP's with "#as=gp") and return its results."""
    Results.results = None
    Results.done.clear()
    with tempfile.TemporaryDirectory() as tmp:
        # Loaded from a file: serving the 850 KB page over local HTTP sometimes stalled on Windows.
        page = Path(tmp) / "test.html"
        page.write_text(test_page(f"http://127.0.0.1:{server.server_address[1]}/results"), encoding="utf-8")
        browser = subprocess.Popen(
            [find_browser(), "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
             f"--user-data-dir={Path(tmp) / 'profile'}",
             # Offline: Google Fonts can stall the page, and the tests shouldn't need the internet.
             "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1", page.as_uri() + uri_suffix],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=os.name != "nt")
        finished = Results.done.wait(180)
        close(browser)
    if not finished:
        sys.exit("The tests didn't finish within 3 minutes.")
    return Results.results


def main():
    if not (ROOT / "planner" / "index.html").exists():
        sys.exit("planner/index.html is missing. Run python planner/build.py first.")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Results)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    passed, failed = 0, []
    for label, suffix in (("George", ""), ("GP", "#as=gp")):
        res = run_page(server, suffix)
        passed += res["passed"]
        failed += [f"[{label}] {f}" for f in res["failed"]]
    server.shutdown()
    for f in failed:
        print("FAIL", f)
    print(f"{passed} passed, {len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
