"""Bakes simulation results into a standalone dashboard.html.

No web server, no build tools, no network. The generated file is fully
self-contained and opens directly in any browser.
"""

import json
import os

TEMPLATE = os.path.join(os.path.dirname(__file__), "template.html")


def build(data, sweep_data, out_path="dashboard.html"):
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    html = html.replace("__SWEEP__", json.dumps(sweep_data, separators=(",", ":")))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
