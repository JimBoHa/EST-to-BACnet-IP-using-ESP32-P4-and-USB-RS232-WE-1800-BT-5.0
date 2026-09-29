# Move this project to another Mac

## Transfer and restore

Use the **private ZIP**, not just GitHub. GitHub intentionally has no device credentials, SDU archives, raw panel reports, databases or firmware images. The bundle grants management/update access to the controller and contains site information. It is not password-encrypted; transfer it through a private trusted channel and keep it out of public repositories/shared download folders. File permissions are restricted on the source Mac, but ZIP extraction may not preserve them.

Extract the ZIP into a private local folder on the new Mac. Give the new Codex session that folder and `NEXT_SESSION_PROMPT.md`. Ask it to execute the work described there. Use a local disk, not a cloud-synced or network share, for the development checkout and live SQLite database.

The bundle contains:

- `START_HERE.md`, `NEXT_SESSION_PROMPT.md`, `COMPLETION_PLAN.md`, `TRANSFER.md` and `restore.py`.
- `BUNDLE_MANIFEST.json`: SHA-256/size of every packaged file, source/toolchain pins, input provenance and latest attempted device observation. The manifest is an integrity check, not a digital signature; verify the ZIP checksum received from the source machine when possible.
- `repositories/gateway.bundle` and `repositories/bacnet-stack.bundle`: complete Git history required to reconstruct the project and the pinned submodule without GitHub access.
- `source-preview/`: readable source/doc snapshot for review before restoring; it omits private files and the BACnet submodule contents, which are in the Git bundle.
- `payload/`: private credentials, raw captures, consistent host database snapshot, known-good release images, and original 32 MB flash backup. The restore script copies this into the checkout.
- `site-inputs/`: three original SDU backups, photos/previews and SDU reader source/review metadata.
- `original-spec/`: original detailed project specification, drawings, manuals and evidence. Its historical hardware/rate/no-attachment assumptions are superseded by the new prompt.

Prerequisites for restoration: Python 3.10+ and Git. For development use **Python 3.13**, matching the tested environment. Check `uname -m`; install native Apple Silicon or Intel tools accordingly. Do not copy the old Mac's virtual environment, compiled pxlib library, CMake cache or ESP-IDF Python environment.

From the extracted bundle directory:

```sh
python3 restore.py --verify-only
python3 restore.py --destination /absolute/new/path/est3-metasys-gateway
```

The destination must not exist. The script verifies every hash before creating it, restores exact Git commits and the submodule, copies private artifacts, restricts private file permissions and checks SQLite integrity. It does not install packages, open the controller, generate credentials, configure a host service or perform OTA. It refuses to overwrite an existing checkout. If an interrupted restore leaves a partial destination, inspect it and choose another destination; the script never deletes an existing project automatically.

GitHub authentication is not transferred. The new machine must authenticate using the owner's normal GitHub workflow to push changes. The remote is set to the already-renamed repository. Never commit `private/`, `site-inputs/`, the entire extracted bundle, raw reports or image binaries. Restored private material is placed under the project's existing ignore rules.

## Python and local tests

Install Xcode Command Line Tools if needed (`xcode-select --install`), plus a native Python 3.13 and Git. Homebrew is one possible source; use the owner's existing package manager rather than installing another one unnecessarily.

```sh
cd /absolute/new/path/est3-metasys-gateway
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
```

**Do not run `tools/provision.py`.** The private device certificate, device/host keys, management tokens, OTA signing key and `provision.h` are restored. Generating replacements does not rotate the already-installed controller and can lock out OTA. The device/host certificates were created on the prior machine and expire September 24, 2036; certificate time checks require a correct computer clock. Plan renewal before expiry rather than disabling validation.

The supplied full Python lockfile was installed successfully on the original Mac. If a different architecture lacks a wheel, diagnose that particular native dependency and preserve the lock unless a tested migration is necessary. Toolchain downloads need internet access; the bundle does not contain a full portable ESP-IDF compiler installation.

## Pinned ESP-IDF setup and firmware build

Use [Espressif's official Linux/macOS setup guide](https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32p4/get-started/linux-macos-setup.html) for prerequisites, but checkout the project's exact **v5.5.5** tag/commit below. Avoid silently following the latest branch or a new board example for v3 silicon.

```sh
git clone --branch v5.5.5 --recursive https://github.com/espressif/esp-idf.git /absolute/new/path/esp-idf-v5.5.5
git -C /absolute/new/path/esp-idf-v5.5.5 rev-parse HEAD
# Expected: b774170ff46c393eeb5e495ea37936038d3f4f4f

export IDF_PATH=/absolute/new/path/esp-idf-v5.5.5
"$IDF_PATH/install.sh" esp32p4
cd /absolute/new/path/est3-metasys-gateway
tools/idf.sh build
```

`tools/idf.sh` has the old Mac's path as its fallback; **explicitly set `IDF_PATH`** in the new terminal and future service/build environments. The wrapper sources the IDF environment and prefers the project `.venv` tools for CMake/Ninja. It does not flash anything. Start from committed `sdkconfig.defaults`; the bundle retains the previous generated config under `site-inputs/build/` for comparison, not as a portable CMake cache.

Check the generated settings against P4 revision 1.3, revision range 1.0–1.99, 32 MB flash, 32 MB PSRAM, native EMAC/IP101, high-speed USB host, rollback support and the committed partition layout. Do not issue serial flash, erase, bootloader, partition-table, fuse or blanket provisioning commands on the deployed unit.

For native tests after IDF is available:

```sh
export PATH="$PWD/.venv/bin:$PATH"
cmake -S tests -B build-tests -G Ninja
cmake --build build-tests
ctest --test-dir build-tests --output-on-failure
.venv/bin/python -m pytest tests -q
```

The actual baseline was 25 pytest cases and two C ASan/UBSan cases on macOS. New-machine execution remains to be performed there. A baseline rebuild can differ in binary hash because of build metadata/environment; do not overwrite archived 0.1.5 images with different bytes. Bump the project version for the next deployed change, then run `tools/package_release.py` and retain the new manifest. Review/update the production symbol audit deliberately when adding a real decoder; retain the prohibition on simulation injection and payload TX.

## First device check: read-only

The new Mac needs a route to the site. Use its actual routed interface address, not the old Mac's `192.168.2.34`. Last device IP is `192.168.75.157`; verify current lease/identity if it changed. BACnet broadcasts may not cross routers; the independent check supports unicast.

```sh
.venv/bin/python tools/gateway_client.py --host 192.168.75.157 status
.venv/bin/python tools/bench_bacnet.py --host 192.168.75.157 \
  --local-ip YOUR_ACTUAL_ROUTED_MAC_IP --output private/new-machine-bacnet.json
```

Expected last verified state: 0.1.5, full ELF hash in the handoff, confirmed image, USB attached, TX disabled, simulation false, zero real devices. Boot count may increase if the owner has powered the board since the last observation. Read `/api/v1/serial` through `gateway_client.Client` to confirm requested/applied 9600 and configuration error zero. Keep `capture_hex` out of public logs. `tools/serial_capture.py` is for the old **USB-C programming console**, not Ethernet panel capture; do not use it here.

A timeout means network/device access has not been established; it is not sufficient evidence to diagnose firmware failure. Check authorized routing, DHCP lease and certificate identity before changing firmware or IP settings. No credentials should go to an unverified device.

## OTA after a reviewed, tested change

The restore/setup commands never upload. For an intentional next application release:

```sh
.venv/bin/python tools/package_release.py
.venv/bin/python tools/gateway_client.py --host 192.168.75.157 \
  upload firmware/build/est3_gateway_rxonly.bin
```

Use the app image only. The client signs with the retained private OTA key, verifies the device certificate before authentication, compares all 64 running ELF hash characters and explicitly confirms after 10 seconds of local checks. An unconfirmed boot rolls back after 180 seconds. Check serial settings, parser/storage health, registry quality and management/BACnet after each change; strengthen confirmation checks as new required subsystems are added. Retain a known-good private recovery image and update the resume notes.

`--no-confirm` is a deliberately disruptive rollback test, already exercised on the disconnected bench. Do not use it casually on the attached field unit. OTA cannot restore a damaged bootloader/partition table or fix physical network/power failures. Retained 0.1.4 uses a 19200 default; its receiver API can return it to 9600 without USB if that image is recovered.

## Host migration

`private/hardware-bench.sqlite` in the bundle is a SQLite backup-API snapshot, including committed WAL contents, from the former diagnostics host. It contains development diagnostics, not a completed real panel registry/history system. New permanent deployment needs a chosen host address/service owner and the real-event pipeline described in the completion plan.

For a deliberate local host test, from the repository:

```sh
export EST3_DB="$PWD/private/hardware-bench.sqlite"
export EST3_GATEWAY_ID=P4-e8f60ae41fe8
export EST3_BIND=127.0.0.1
.venv/bin/python tools/run_host.py
```

The viewer Basic-auth password is `tokens.json`'s viewer value; use it locally without echoing it or placing it in a URL. The helper loads the three API roles from the private tokens file. For a gateway-reachable service, explicitly choose the Mac's reachable bind address and verify firewall/routing, host trust and persistence first. Then configure the device host URL with authenticated `POST /api/v1/host`. Do not copy the old unreachable `10.0.7.6` setting by default. Only one production host should own the chosen database/identity.

An always-on service, retention, backups, monitoring, clock source and certificate lifecycle still need implementation/validation. The new Mac may be a development machine only; do not install an assumed permanent service without establishing that role with the owner.

## SDU reader portability

The three original SDU ZIP/Paradox archives and selected review JSON are included. The native pxlib source and pypxlib Python source are retained under `site-inputs/sdu-tools/`; build a native library for the new Mac. Source provenance is recorded there. The prior bundled Intel dylib did not run on Apple Silicon; the prior session built pxlib 0.6.8 natively and used it with pypxlib 2.5. Do not run a Mac dylib from the opposite architecture or trust a zero-row table's stale blocks as active records.

All archive reading must use scratch copies; never save changes into the original SDU or load it into the live panel. Validate a real importer before writing registry/catalog data. The original Windows-only 3-SDU tool is not installed or supplied by this handoff; obtaining a legitimate supported export remains an alternative if direct schema interpretation cannot be validated.
