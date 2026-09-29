# Dependencies and licenses

| Dependency | Exact pin / evidence | License |
|---|---|---|
| ESP-IDF | v5.5.5, b774170ff46c393eeb5e495ea37936038d3f4f4f | Apache-2.0 plus component notices; retained in installed source |
| FTDI host component | 2.1.1, hash in firmware/dependencies.lock | Apache-2.0; managed component LICENSE retained |
| CDC ACM host component | 2.3.0, hash in firmware/dependencies.lock | Apache-2.0; managed component LICENSE retained |
| Espressif mDNS | 1.13.1, hash in firmware/dependencies.lock | Apache-2.0; managed component LICENSE retained |
| Embedded page layout/CSS reference | JimBoHa/ESP32-S3-PoE-ETH-8DI-8RO-C-BACnet-IP-Firmware, local commit 97c46a33dcc39ceee794c962dfbc0d94efd2788a | 0BSD; notice below |
| bacnet-stack | 1.5.2, d2468d56de3d156659a9051c95119e3a6e11c421 | Per-file SPDX, principally GPL-2.0-or-later WITH GCC-exception-2.0 and MIT; license/ retained in Git submodule |
| cJSON | ESP-IDF's pinned submodule | MIT; original source/license used by firmware and native tests |
| FastAPI, Pydantic, Uvicorn, HTTPX | requirements.lock | MIT / BSD as recorded in installed package metadata |
| BACpypes3 independent test client | 0.0.110 | MIT |
| Python cryptography | requirements.lock | Apache-2.0 OR BSD-3-Clause |
| pytest and build dependencies | requirements.lock | Original package licenses retained in installed distributions |

No modifications are made to bacnet-stack's upstream source. The project provides its own read-only object table, local-subnet socket port and wrappers. CMake supplies a cJSON nesting limit of 16. This is a development integration, not a BACnet certification claim.

The IDF C FTDI API is used. The project enables the C++ exception runtime requested by the component's C++ wrapper, although no C++ VCP object is needed by this release. Exactly one FTDI status-byte removal layer is used.

Use `git submodule update --init` to fetch the pinned BACnet source. The full resolved Python environment is in `requirements.lock`, not only top-level dependency ranges. Package metadata/license names can be reproduced with `importlib.metadata`. Tool versions and build logs are retained under evidence/.

The page's CSS/layout was adapted from the owner's [reference firmware](https://github.com/JimBoHa/ESP32-S3-PoE-ETH-8DI-8RO-C-BACnet-IP-Firmware).
Its device-control logic and hardware architecture were not imported. The original
license grants use, copying, modification and distribution for any purpose with
or without fee, and disclaims all warranties and author liability (BSD Zero Clause,
0BSD). The original LICENSE is available in that repository.

Optional desktop-only SDU import uses pypxlib 2.5 and locally rebuilt pxlib 0.6.8
from source commit `e32d17611e5ee353c4e3ce04e61b0b38feb95855`.
Both readers carry GPL-2.0 licensing in their supplied package/source metadata.
These are not linked into the firmware. Preserve their package/source license
files with private transfer tooling; see `handoff/SDU_READER_NOTES.md`.
