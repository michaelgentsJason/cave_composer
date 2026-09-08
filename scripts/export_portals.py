"""Open verified terminal portals without changing the reference bundle."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.portals import export_portals


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--outside-distance', type=float, default=3.)
    args = parser.parse_args()
    report = export_portals(args.scene, args.output, args.outside_distance)
    print(report['status'])
    for kind, item in report['meshes'].items():
        print(kind, 'openings:', len(item['boundary_loops']),
              'path clearance:', item['crossing_certificate']['continuous_clearance_lower_bound'])
