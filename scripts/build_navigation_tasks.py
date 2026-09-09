"""Build verified task packs without replacing existing scene meshes."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.tasks import build_task_pack, load_task_pack

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--count', type=int, default=12)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--max-expansions', type=int, default=500000)
    args = parser.parse_args()
    result = build_task_pack(args.scene, args.output, args.count, args.seed, args.max_expansions)
    load_task_pack(args.output)
    print(json.dumps({k: result[k] for k in ['status', 'requested', 'passed', 'failed', 'total_seconds']}, indent=2))
