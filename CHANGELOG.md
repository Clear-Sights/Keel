# Changelog

## [2.2.1] — 2026-09-09

### Fixed

- Terminal reconciliation omits provably missing U12/U13/U19 content targets and
  records each retirement in the decision journal. Original ledger debt remains:
  no guard licence is invented, returning targets block again, and older versions
  conservatively retain the obligation. Relative, truncated and uncertain paths
  remain owed because the historical ledger does not prove their original root.
- Group Stop refusals by clause with up to five subjects and an overflow count;
  keep every obligation in the ledger and the full block journal record.
- Describe U08's existing supported signature forms accurately without broadening
  its recognizer, and keep generated documentation byte-stable across platforms.

Earlier release history is preserved in Git and the existing release tags.
