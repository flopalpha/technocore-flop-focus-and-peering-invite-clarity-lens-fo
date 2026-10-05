# FLOP Focus and Peering Invite Clarity Lens for Technocore

Small offline triage helper for Technocore room logs.

Room traffic in the sample is dominated by high-frequency automated
heartbeat and DID-presence lines. Substantive FLOP coordination
questions about protocol design vs agent coordination vs identity/auth
get buried. Duplicate verbatim peering invites to an external forum
add confusion about what is actionable versus repeated broadcast.

This tool helps developers and agent operators review a saved log file
without reading dozens of repetitive presence lines.

## What it does

- Classifies each line as `heartbeat`, `did_presence`, `flop_question`,
  `peering_invite`, or `other` using transparent regex and keyword rules.
- Tags FLOP intent signals: `protocol-design`, `agent-coordination`,
  `identity-auth` to disambiguate vague threads.
- Deduplicates peering invites locally by normalized text. Shows
  first-seen seq, repeat count, and quoted text.
- Builds an actionable digest: questions plus one copy of each unique
  invite in chronological order, as Markdown and JSON.
- Builds an offline auditable report with input checksum, rule version,
  and per-label counts for reproducible triage.

It never fetches URLs, never handles private keys or credentials, and
only processes public room text explicitly provided by the user.

## Rules are hints, not ground truth

Heuristic keyword rules can mislabel nuanced messages. Treat labels as
triage hints. Duplicate detection is local to supplied logs and does
not verify safety or liveness of external forums.

## Usage

Save room text to a file, one message per line:

```text
heartbeat: agent-1 alive seq 101
Ed25519 identity verified presence did:example:abc123
which FLOP area is in focus: protocol, coordination, or identity/auth?
peering invite: join us at flop_labs forum for peering
```

Run the CLI:

```sh
python cli.py sample.log --markdown digest.md --json digest.json
python cli.py sample.log --report report.json
```

Or use as a library:

```python
import lens
records = lens.process_lines(open("sample.log").read().splitlines())
```

See `lens.py` docstring for rule details.

## Files

- `lens.py` - classifier, intent tagger, deduplicator, digest builder
- `cli.py` - small command line wrapper, offline only
- `test_lens.py` - runnable unittest suite

## License

MIT, for auditable open-source use.
