"""Audit cave-level source roles before running a transfer experiment."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import atomic_json
from cave_composer.reference_data import audit_reference_registry

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = audit_reference_registry(json.loads(Path(args.registry).read_text(encoding='utf-8')))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(args.report, report)
    print(json.dumps(report, indent=2))
    if report['status'] != 'PASS':
        sys.exit(1)
