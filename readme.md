# pandoc-kroki-filter
> A Pandoc JSON filter that renders Kroki diagrams via **HTTP POST** (to avoid 414 URL-length issues) and replaces fenced code blocks with embedded **SVG images**, with optional caching and stderr-only logging.

`pandoc-kroki-filter` lets you write diagrams directly in Markdown (e.g., Mermaid, PlantUML, Graphviz, Vega/Vega-Lite) and have Pandoc automatically render them using a Kroki server. Unlike GET-based renderers, this filter uses **POST** requests to support large diagram sources (notably Vega/Vega-Lite specs) and avoid **414 Request-URI Too Large** problems. It also supports a local on-disk cache so repeated builds are fast, and it logs only to **stderr** (never polluting Pandoc stdout). 

---

## Installation

### OS X & Linux

```sh
python3 -m pip install pandocfilters requests
chmod +x pandoc-kroki-filter.py
```

### Windows (PowerShell)

```powershell
py -m pip install pandocfilters requests
# Ensure python is on PATH or call the script with `py pandoc-kroki-filter.py`
```

> **Note:** This repository ships a single executable Python script (`pandoc-kroki-filter.py`). It is invoked by Pandoc as a JSON filter.

***

## Usage example

Write a Kroki-supported diagram in a fenced code block and add the diagram type as the code block class.

### Example: Mermaid

````markdown
```kroki-mermaid
sequenceDiagram
  Alice->>Bob: Hello Bob, how are you?
  Bob-->>Alice: I'm good thanks!
```
````

Convert with Pandoc:

```sh
pandoc input.md \
  --filter ./pandoc-kroki-filter.py \
  -o output.html
```

The filter detects `CodeBlock`s whose class matches one of the supported Kroki diagram types (and synonyms), renders the diagram through your Kroki server, caches the SVG, and returns a Pandoc `Image` node pointing at the cached `.svg`

### Supported diagram types

Out of the box, the filter recognizes these classes (and `kroki-<type>` aliases), including special synonyms like `kroki-dot -> graphviz`, `kroki-c4 -> c4plantuml`, and `kroki-vega-lite -> vegalite`: 

*   `blockdiag`, `bpmn`, `bytefield`, `seqdiag`, `actdiag`, `nwdiag`, `packetdiag`, `rackdiag`
*   `c4plantuml`, `ditaa`, `erd`, `excalidraw`, `graphviz`, `mermaid`, `nomnoml`, `plantuml`
*   `svgbob`, `umlet`, `vega`, `vegalite`, `wavedrom`, `pikchr`

### Environment variables

Configure behavior via environment variables:

*   `KROKI_SERVER` — Kroki base URL (default: `https://kroki.io`). The script sanitizes quotes and trailing slashes. 
*   `KROKI_CACHE` — Cache directory (default: `.kroki-cache`). 
*   `KROKI_VERBOSE` — Enable informational stderr logging (`1|true|yes`); otherwise only warnings/errors are emitted. 
*   `KROKI_DIAGRAM_BLACKLIST` — Comma-separated list of diagram classes to ignore (must match known types).

Example:

```sh
export KROKI_SERVER="https://kroki.mycompany.example"
export KROKI_CACHE=".cache/kroki"
export KROKI_VERBOSE=1
export KROKI_DIAGRAM_BLACKLIST="excalidraw,vega"
pandoc input.md --filter ./pandoc-kroki-filter.py -o output.pdf
```

### Caption support

If you supply a caption in Pandoc’s supported syntax for code blocks (as processed by `pandocfilters.get_caption`), the filter passes it to the generated `Image`.

### How it works (quick overview)

*   The filter listens for Pandoc `CodeBlock` nodes and checks their classes against a known set of Kroki types and synonyms.
*   It computes a SHA-256 hash over `(diagram_type + content)` to create a stable cache key and writes `<hash>.svg` into the cache folder. 
*   Rendering is done via **POST** with multiple fallback variants (JSON payload, then `text/plain`, then `/render` style endpoints). 
*   Logging is configured to **stderr only**, with verbosity controlled by `KROKI_VERBOSE`.

***

## Release History

*   0.1.0
    *   Initial public version: POST-based rendering, caching, stderr-only logging, diagram type aliases and blacklist support.

***


Distributed under the MIT license. See `LICENSE` for more information.
