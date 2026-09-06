"""Replay metrics with fresh native spatial indices and retain every exception."""
import argparse
import gc
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np
import trimesh
import rtree
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.spec import load_spec
from cave_composer.routes import build_routes, navigation_graph
from cave_composer.field import CaveField
from cave_composer.metrics import compute_metrics
from cave_composer.bundle import atomic_json, environment_signature


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene')
    parser.add_argument('--output', required=True)
    parser.add_argument('--repeats', type=int, default=12)
    args = parser.parse_args()
    scene, output = Path(args.scene), Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    spec = load_spec(scene / 'metadata/config.yaml')
    run = json.loads((scene / 'metadata/run.json').read_text())
    routes = build_routes(spec)
    field = CaveField(spec, routes, run['seed'])
    graph = navigation_graph(routes, field.chamber_records, spec['bottlenecks'])
    clearance = np.asarray(json.loads((scene / 'navigation/clearance.json').read_text())['collision'])
    expected = json.loads((scene / 'metadata/metrics.json').read_text())
    with np.load(scene / 'collision/mesh.npz') as data:
        vertices, faces = data['vertices'].copy(), data['faces'].copy()
    result = {'scene': str(scene), 'requested': args.repeats, 'environment': environment_signature(),
              'rtree': rtree.__version__, 'libspatialindex': rtree.core.rt.SIDX_Version().decode(), 'records': [],
              'scope': 'Fresh meshes and explicit garbage collection; regression evidence, not proof of absence of native-library bugs.'}
    reference = None
    for i in range(args.repeats):
        began = time.perf_counter()
        record = {'iteration': i}
        try:
            mesh = trimesh.Trimesh(vertices=vertices.copy(), faces=faces.copy(), process=False)
            metrics, visibility = compute_metrics(spec, routes, graph, mesh, clearance)
            encoded = json.dumps([metrics, visibility], sort_keys=True)
            if reference is None:
                reference = encoded
            same = all(np.allclose(value, expected[key], rtol=0, atol=1e-9) if isinstance(value, (int, float, list))
                       else value == expected[key] for key, value in metrics.items())
            record.update(status='PASS', identical_across_replays=encoded == reference, matches_saved_metrics=same)
            del mesh
            gc.collect()
        except Exception:
            record.update(status='FAIL', traceback=traceback.format_exc())
        record['seconds'] = time.perf_counter() - began
        result['records'].append(record)
        result['passed'] = sum(r['status'] == 'PASS' for r in result['records'])
        atomic_json(output, result)
        print(json.dumps(record), flush=True)
        if record['status'] == 'FAIL':
            raise SystemExit(2)


if __name__ == '__main__':
    main()
