#!/usr/bin/env python3
"""
Pandoc Kroki filter using POST (stderr logging only, no stdout prints).
Avoids 414 URL length issues and works with large Vega/Vega-Lite specs.
"""

import os
import sys
import json
import hashlib
import requests
import logging
from pandocfilters import Image, Para, get_caption, toJSONFilter

# ---------------------------
# Logging: nur auf STDERR!
# ---------------------------
VERBOSE = str(os.environ.get("KROKI_VERBOSE", "0")).lower() in ("1", "true", "yes")
logger = logging.getLogger("kroki")
_handler = logging.StreamHandler(sys.stderr)
_fmt = logging.Formatter("[kroki] %(levelname)s: %(message)s")
_handler.setFormatter(_fmt)
logger.addHandler(_handler)
logger.setLevel(logging.INFO if VERBOSE else logging.WARNING)

# ---------------------------
# Diagram-Typen + Synonyme
# ---------------------------
DIAGRAM_TYPES = [
    "blockdiag", "bpmn", "bytefield", "seqdiag", "actdiag", "nwdiag", "packetdiag",
    "rackdiag", "c4plantuml", "ditaa", "erd", "excalidraw", "graphviz", "mermaid",
    "nomnoml", "plantuml", "svgbob", "umlet", "vega", "vegalite", "wavedrom", "pikchr"
]
DIAGRAM_SYNONYMS = {
    "kroki-dot": "graphviz",
    "kroki-c4": "c4plantuml",
    "kroki-vega-lite": "vegalite",
}
for t in DIAGRAM_TYPES:
    DIAGRAM_SYNONYMS[f"kroki-{t}"] = t
AVAILABLE = set(DIAGRAM_TYPES) | set(DIAGRAM_SYNONYMS.keys())

# Blacklist aus Env
BLACKLIST = set(
    d for d in os.environ.get("KROKI_DIAGRAM_BLACKLIST", "").split(",") if d in AVAILABLE
)

# ---------------------------
# Server-URL bereinigen
# ---------------------------
raw_server = os.environ.get("KROKI_SERVER", "https://kroki.io")
KROKI_SERVER = raw_server.strip().strip('"').strip("'").rstrip("/")
if raw_server != KROKI_SERVER:
    logger.info(f"Sanitized KROKI_SERVER: {raw_server!r} -> {KROKI_SERVER!r}")

# Cache-Verzeichnis
CACHE_DIR = os.environ.get("KROKI_CACHE", ".kroki-cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------------------
# POST-Render (mehrere Varianten)
# ---------------------------
def kroki_render_post(diagram_type: str, diagram_text: str, output_format: str = "svg", timeout: int = 40) -> bytes:
    headers_svg = {"Accept": "image/svg+xml"} if output_format == "svg" else {"Accept": "*/*"}
    url_tf = f"{KROKI_SERVER}/{diagram_type}/{output_format}"

    # 1) JSON an /{type}/{format}
    try:
        r = requests.post(url_tf, json={"diagram_source": diagram_text}, headers=headers_svg, timeout=timeout)
        if r.ok:
            return r.content
        logger.info(f"POST JSON {r.status_code} at {url_tf}\n{r.text}")
    except Exception as e:
        logger.info(f"POST JSON error at {url_tf}: {e}")

    # 2) text/plain an /{type}/{format}
    try:
        r = requests.post(
            url_tf,
            data=diagram_text.encode("utf-8"),
            headers={**headers_svg, "Content-Type": "text/plain; charset=utf-8"},
            timeout=timeout
        )
        if r.ok:
            return r.content
        logger.info(f"POST text {r.status_code} at {url_tf}\n{r.text}")
    except Exception as e:
        logger.info(f"POST text error at {url_tf}: {e}")

    # 3) JSON an /render (bzw. /)
    for suffix in ("render", ""):
        url_r = f"{KROKI_SERVER}/{suffix}".rstrip("/")
        try:
            r = requests.post(
                url_r,
                json={"diagram_source": diagram_text, "diagram_type": diagram_type, "output_format": output_format},
                headers=headers_svg,
                timeout=timeout
            )
            if r.ok:
                return r.content
            logger.info(f"POST /{suffix or ''} {r.status_code} at {url_r}\n{r.text}")
        except Exception as e:
            logger.info(f"POST /{suffix or ''} error at {url_r}: {e}")

    raise requests.HTTPError(
        f"Kroki POST failed for diagram_type='{diagram_type}' format='{output_format}' server='{KROKI_SERVER}'."
    )

# ---------------------------
# Pandoc-Filter
# ---------------------------
def kroki(key, value, format_, meta):
    if key != "CodeBlock":
        return None

    [[ident, classes, keyvals], content] = value

    # Welche Klasse matcht?
    matches = list(AVAILABLE & set(classes))
    if len(matches) != 1:
        return None

    cls = matches[0]
    if cls in BLACKLIST:
        return None

    diagram_type = DIAGRAM_SYNONYMS.get(cls, cls)

    # Caption/Title extrahieren
    caption, typef, keyvals = get_caption(keyvals)

    # Cache-Key (Type + Content)
    h = hashlib.sha256()
    h.update(diagram_type.encode("utf-8"))
    h.update(content.encode("utf-8"))
    cache_key = h.hexdigest()
    outfile = os.path.join(CACHE_DIR, f"{cache_key}.svg")

    # Rendern (wenn nötig)
    if not os.path.exists(outfile):
        logger.info(f"rendering via POST -> {diagram_type} (cache miss)")
        svg = kroki_render_post(diagram_type, content, "svg")
        with open(outfile, "wb") as f:
            f.write(svg)
    else:
        logger.info(f"using cache -> {outfile}")

    # Pandoc-Image zurückgeben
    return Para([
        Image([ident, [], keyvals], caption, [outfile, typef])
    ])

# ---------------------------
# main
# ---------------------------
if __name__ == "__main__":
    toJSONFilter(kroki)