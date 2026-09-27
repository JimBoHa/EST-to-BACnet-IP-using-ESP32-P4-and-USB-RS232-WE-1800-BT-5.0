# Synthetic examples

These records demonstrate application-level identity, state, catalog and event handling. **They are invented.** Addresses beginning `SIM-` and codes beginning `SIM_` are not EST addresses or ECP codes. The JSON is not a panel wire format, contractor export format, BACnet encoding or deployable configuration.

- `catalog-v1.json`: two normal devices with stable logical UUIDs and test-only BACnet allocations.
- `catalog-v2.json`: one rename plus an added normal device; existing identifiers remain unchanged.
- `catalog-v3-address-reuse-pending.json`: a source address reassigned to a different logical function; the change must be quarantined, not automatically applied.
- `events.jsonl`: concurrent conditions and a single-condition restoration, an unknown code, and an explicit history gap. Old labels remain in historical events after a rename.
- `site-config-template.json`: safe placeholder settings; production ECP TX is disabled and all unknown protocol details remain null.

Implementing code must validate schemas, capabilities and source provenance. Do not trust a fixture's `declared_complete` flag as evidence that an actual panel inventory is complete. Do not automatically use these Device/object IDs on a real network. Any `simulation` source mode is restricted to the test profile.

Expected assertions: the rename preserves all existing IDs; adding a normal never-alarmed device updates the directory; the first device's trouble can remain active after its alarm restores; an unknown code stays visible without changing a condition to normal; address reuse requires explicit resolution; a history gap is durable and advances the delivery cursor only under the defined gap-acknowledgement rule.
