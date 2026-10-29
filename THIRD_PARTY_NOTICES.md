# Third-party licenses and notices

Lumen's original source, documentation, synthetic fixtures and original visual assets are licensed under [MIT](LICENSE). That license does **not** relicense Python or third-party dependencies. This source release contains no dependency wheels, copied dependency implementation, downloaded embedding model or model weights. Dependencies are obtained separately from their normal package distributions.

## Direct runtime dependencies reviewed

These identifiers summarize the installed distribution metadata and license notices reviewed on 2026-10-29. The exact versions and notice-file hashes are in [the JSON inventory](docs/audit/dependency-licenses.json); [CSV](docs/audit/dependency-licenses.csv) is easier to scan.

| Package | Version | Declared / principal license | Review notes |
|---|---|---|---|
| pandas | 2.3.3 | BSD 3-Clause | Distribution notice also includes third-party notices. |
| NumPy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 19 notice files identified; binary-wheel notices additionally cover bundled numerical/runtime libraries. |
| DuckDB | 1.5.6 | MIT | The optional experimental Spark package carries additional notices; Lumen does not use it. |
| Streamlit | 1.66.1 | Apache-2.0 | Metadata declares Apache-2.0. This installed wheel exposes no notice file via its file inventory; the official upstream LICENSE was checked separately. |
| Plotly | 6.9.0 | MIT | Installed notice reviewed. |
| Matplotlib | 3.11.2 | PSF-based Matplotlib license | Includes third-party and font notices; this is not simply the Python PSF license. |
| scikit-learn | 1.9.1 | BSD-3-Clause | Installed COPYING and external-array helper notices reviewed. |
| RapidFuzz | 3.14.6 | MIT | Installed notice reviewed. |

The full inventory records **83 installed third-party/tooling distributions**, including development dependencies and pip. None had unknown declared license metadata in this environment. This is a metadata inventory with notice hashes, not a claim that every bundled component has only its top-level package's license.

## Distribution conditions

MIT/BSD notices require preservation of their notices and applicable conditions when redistributing those packages. Apache-2.0 has its own license/notice and change-documentation terms. Matplotlib has its own license agreement and third-party/font terms. NumPy/SciPy binary-wheel notice bundles contain GCC GPL/runtime-exception text; font/rendering libraries can carry alternative license terms. These must not be reduced to a single blanket MIT claim.

The release prepared here redistributes Lumen source and original artifacts, with dependencies installed from upstream distributions; it does not vendor those wheels or libraries. If a future release bundles binaries, containers, third-party source, fonts or models, retain the corresponding full notices and review that exact redistribution separately.

Development tools and their transitive dependencies remain under their respective declared terms, listed in the inventory. `scripts/dependency_inventory.py` can regenerate the inventory on another platform; bundled notices and dependency versions may differ there.

## Optional semantic matching

`sentence-transformers` and its transitive dependency graph are **not installed or reviewed in this core inventory**. No local embedding model was supplied or executed. A model's own license is separate from its Python library license. Installing the optional extra or redistributing a model requires a new inventory and model-license review; the core application remains functional without them.

## Primary references

- [MIT license](https://choosealicense.com/licenses/mit/)
- [NumPy license](https://numpy.org/doc/stable/license.html)
- [Matplotlib license and bundled notices](https://matplotlib.org/stable/project/license.html)
- [Streamlit upstream LICENSE](https://github.com/streamlit/streamlit/blob/develop/LICENSE)

Installed version-specific metadata and notice hashes are the reproducible local evidence for this release. Upstream reference pages may evolve.
