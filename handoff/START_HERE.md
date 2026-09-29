# EST3 private continuation bundle

Prepared for a new Codex session on **macOS**. This bundle contains the implemented project and the local materials needed to continue without access to the previous Mac.

1. Transfer and extract the complete private ZIP on the new Mac.
2. Give Codex the extracted folder and `NEXT_SESSION_PROMPT.md`.
3. Have it read `TRANSFER.md`, verify/restore with `restore.py`, and continue the work in `COMPLETION_PLAN.md`.

Paste this into the new Codex session, replacing the path:

> Continue the existing EST3 gateway project using the complete private handoff at `/absolute/path/to/extracted/EST3-Codex-Handoff-2026-09-28`. Read `NEXT_SESSION_PROMPT.md` and the referenced files, verify and restore the bundle, then implement and test the remaining work. The controller is deployed on PoE and cannot return to USB. Preserve the existing keys, Ethernet OTA and RX-only panel connection. Follow the recorded working 9600 8N1 printer profile; do not restart from the obsolete candidate ECP/19200 assumptions. Build the complete supported monitoring, inventory, history, BACnet and Metasys system, with explicit source coverage and honest limits. Continue independent work when a specific site input is missing.

The latest successfully tested firmware is **0.1.5** at last-known IP **192.168.75.157**. Five complete panel revision reports were captured cleanly at **9600 8N1**, including after Ethernet OTA/reboot. This is not yet live alarm/state decoding. The manifest records any more recent connectivity attempt separately; verify the route from the new Mac.

**Private contents include credentials and signing keys that control the gateway, site SDU files, drawings/photos, reports, databases and firmware images. This ZIP is not encrypted. Transfer/store it privately; never upload it to GitHub or a public link.** The source-only prompt and public repository do not contain the credentials needed to manage this deployed unit.

The restore script is local-only and refuses an existing destination. It never provisions credentials, installs tools, contacts the controller or flashes anything. Full instructions are in `TRANSFER.md`.
