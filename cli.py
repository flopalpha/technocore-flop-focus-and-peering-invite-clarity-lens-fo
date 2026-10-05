"""Command line wrapper for the FLOP clarity lens. Offline only."""
import argparse
import json
from pathlib import Path
import lens


def read_lines(input_path):
    text = Path(input_path).read_text(encoding="utf-8")
    return text.splitlines()


def write_text(output_path, content):
    Path(output_path).write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="FLOP focus and peering invite clarity lens, offline only."
    )
    parser.add_argument("input", help="input log file, one message per line")
    parser.add_argument("--markdown", default="", help="output markdown digest path")
    parser.add_argument("--json", default="", help="output json digest path")
    parser.add_argument("--report", default="", help="output audit report path")
    args = parser.parse_args()
    lines = read_lines(args.input)
    records = lens.process_lines(lines)
    groups = lens.deduplicate_invites(records)
    digest = lens.build_digest(records, groups)
    markdown = lens.build_markdown(records, groups, digest)
    if args.markdown:
        write_text(args.markdown, markdown)
    else:
        print(markdown)
    if args.json:
        write_text(args.json, json.dumps(digest, indent=2, sort_keys=True))
    if args.report:
        raw = Path(args.input).read_bytes()
        report = lens.build_report(records, groups, raw)
        write_text(args.report, json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
