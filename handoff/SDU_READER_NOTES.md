# Private SDU reader notes

The three original SDU files are retained separately and must remain unchanged. These are ZIP containers holding Paradox tables, not the mock JSON catalog accepted by the current host. Reading selected tables does not yet constitute a validated complete inventory importer.

Reader used during the previous session: pypxlib **2.5**, with pxlib **0.6.8** built from `https://github.com/steinm/pxlib.git`, commit `e32d17611e5ee353c4e3ce04e61b0b38feb95855`. Source copies accompany these notes. Native compiled libraries and installed Python environments were intentionally omitted; rebuild for the new Mac's architecture. pypxlib source: `https://github.com/mherrmann/pypxlib` and its versioned PyPI package. Retain their upstream licenses; the included package metadata records licensing.

The pypxlib wheel's bundled Intel dylib did not load on the prior Apple Silicon Mac. A successful local workaround built pxlib using CMake and copied the resulting native dylib into the scratch pypxlib installation's `pxlib_ctypes/libpx_x64.dylib`, the filename selected by that package on macOS. The filename alone does not describe the replacement binary architecture. Verify the native library with `file` and test a selected known table before trusting it. Do not modify a system Python package or copy the old compiled library blindly.

Suggested isolated procedure, after reviewing the supplied source:

```sh
# In the restored project, using the project Python environment:
.venv/bin/python -m pip install --target private/sdu-reader/python pypxlib==2.5
.venv/bin/cmake -S /path/to/bundle/site-inputs/sdu-tools/pxlib-source \
  -B private/sdu-reader/pxlib-build -DCMAKE_BUILD_TYPE=Release
.venv/bin/cmake --build private/sdu-reader/pxlib-build -j 4
```

Inspect the output library path and the package loader before installing the native dylib into that scratch target. The copied upstream sources are an offline reference; installing a native matching dependency through a supported package path is also acceptable. No native reader command is required to restore or manage the firmware.

For selected tables, the prior session successfully used `Table(path)`, `len(table)`, `table[i]`, and explicit named fields. Avoid unrestricted dumps. The package iterator was incompatible with the environment, so indexed access was used. Bound record counts and memory, validate schema and handle nullable/encoded fields explicitly. Extract matching `.MB` blob files only when needed for verified fields; absence of a blob file can produce warnings even when the selected scalar fields are readable.

Review summaries are restored to `private/sdu-review/`. They retain original source paths as provenance; find the corresponding archives by filename and SHA-256 under the new bundle's `site-inputs/sdu/`. The newest archive's filename is `100_ENTR_01_01_02_15.SDU`; it has 2026-03-04 cabinet data, while the file named "Most updated 2025" contains older cabinet records.

`ECP.DB` header active-record count was zero in all three backups. The underlying reader could warn about stale/empty data blocks; those blocks must not become asserted live ECP configurations. Raw port enum values 1/4 were retained without guessed labels. Project PC download communications baud is not the auxiliary Port 2 baud. The live 9600 printer reports are the actual working serial evidence.

Project/access-control tables may contain passwords or sensitive settings. Do not print all rows, publish extracted tables or import them into the live panel. Keep original archive hashes, perform analysis on scratch copies, and validate a supported inventory schema before generating real registry objects.
