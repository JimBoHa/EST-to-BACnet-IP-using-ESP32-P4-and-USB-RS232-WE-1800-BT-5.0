# Owner-supplied as-built evidence review — 2026-09-29

The added 2019-completion folder was read without changing its contents. Source
PDFs, CAD files, source archives, extracted text and rendered inspection pages
remain private. The full file/hash index is `private/as-built-review/index.json`.

## What the added material establishes

- All three supplied SDU archives are byte-identical to archives already in the
  original handoff. The newest archive has SHA-256
  `c8bd4dedb598fea590bd5167b6fcb692e74625cfb1d00e56bd1b71b275aa200b`.
  It is the source of the installed epoch-1, 1,214-object registry. These copies
  do not represent a new programming revision or justify changing identities.
- The newly supplied Phase 1 as-built is a distinct 41-page revision. Visually
  inspected cover/BOM and sheet LS5-01 (PDF page 38) identify EST3, 3-CPU3,
  3-RS485A and 3-RS232 hardware. LS5-01 includes node/card and address ranges.
  These are useful historical configuration evidence, not a live port-setting
  readback. LS5-02 (PDF page 39) is enclosure/battery layout.
- Other Phase 1/2/3 drawing copies match the previously supplied PDFs by hash.
  Phase 2 and Phase 3 cover/BOM pages were visually checked. The floor plans
  provide layout material, but no coordinate-to-current-UUID mapping has been
  validated. A floor-plan text hit for “Printer Alcove” is an ordinary room label,
  not proof of a fire-panel printer or its automatic routing.
- The included 298-page technical manual is **EST3X Technical Reference Manual,
  P/N 3101888-EN REV 03, issued 28 August 2013**. It describes SFS1-CPU/EST3X;
  the installed panel is EST3/3-CPU3 with CPU 05.30.00. Do not substitute its
  SFS1-CPU TB5 diagram for the verified 3-CPU3 TX2/COM2 connection.

## Relevant manual passages and their limits

| PDF page / printed page | Finding | Limit |
|---|---|---|
| 19 / 9 | Message annunciation can be routed to panels and printer ports | Does not identify this panel's enabled routes or filters |
| 106 / 96 | Optional FSB-PC2/FSB-PCLW BMS bridges support EST3/EST3X and convert the external communications protocol to supported interfaces | Does not prove a bridge is installed; no complete wire specification is supplied |
| 149 / 139 | Supervised/unsupervised printer examples on SFS1-CPU TB5 | Different CPU/terminal arrangement from this installation |
| 240 / 230 | HyperTerminal programming-connection example uses 9600, 8N1, no flow control | Not proof of the installed auxiliary Port 2 mode or event grammar |

All manual pages were text-extracted/searchable; relevant wiring/architecture
pages were visually inspected. This is a targeted integration review, not a
claim that every scanned floor-plan detail or CAD layer was independently
validated.

## Effect on the implementation

The as-built material supports the retained EST3 hardware model and provides
future placement/reference material. It does **not** supply an installed CPU
5.30 alarm/restore byte log, exact printer-event grammar, verified Port 2 routing,
or an unsolicited startup snapshot. The owner confirms no existing event log
is available. Revision reports remain the only captured live record syntax.

No wiring, panel configuration, clock, operational state or credentials were
changed. No manual print or staged alarm was requested during this continuation.
The controller retains naturally arriving unknown records in bounded RAM, and
all BACnet condition points remain invalid until their source semantics and
state recovery are established. See [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).
