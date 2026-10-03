# Sanitized printer trouble fixture

Derived from eight CPU 05.30 trouble ACT/RST records captured automatically on
the field P4 before the 0.1.15 update. Addresses, labels and dates are changed.
CRLF framing is reconstructed from retained line records; this is not an exact
copy of the entire UART capture. The operator-command text is inbound evidence
only and is never transmitted or executed.

`printer-test-registry.json` contains two artificial addresses and a zero source
hash for disconnected tests. It is not a site inventory or an import candidate.
`printer_bacnet` binds localhost and reads a local fixture file; it is never
linked into the embedded application. Production and test runs share the same
C parser, restricted observation reducer and BACnet stack.

These fixtures validate only LOCAL/COMMON TRBL ACT/RST observations. They do not
establish current-state recovery, alarm/supervisory/disable semantics, inventory
discovery, or routing coverage.
