"""Search collision occupancy without the generator's centerline or graph.

The occupancy supplies candidates; final triangle-mesh distance and parity tests
certify the entire resulting polyline for a spherical robot. No policy or robot
dynamics are evaluated here.
"""
import heapq
import time
import numpy as np
from scipy import ndimage
from .validation import mesh_clearance


def certify_polyline(mesh, points, safety, sample_step=.25):
    if not np.isfinite(safety) or safety<=0 or not np.isfinite(sample_step) or sample_step<=0:
        raise ValueError('Safety radius and sample step must be finite and positive')
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or not np.isfinite(points).all():
        raise ValueError('A path must contain at least two finite 3D points')
    samples = [points[0]]
    maximum_step = 0.
    for a, b in zip(points[:-1], points[1:]):
        length = float(np.linalg.norm(b - a))
        count = max(1, int(np.ceil(length / sample_step)))
        maximum_step = max(maximum_step, length / count)
        samples.extend(np.linspace(a, b, count + 1)[1:])
    samples = np.asarray(samples)
    distances = mesh_clearance(mesh, samples)
    lower = float(distances.min() - maximum_step / 2)
    inside = bool(np.all(mesh.contains(samples)))
    return {'status': 'PASS' if inside and lower > safety else 'FAIL',
            'samples_inside': inside, 'samples': len(samples),
            'sample_max_step': maximum_step, 'minimum_sampled_clearance': float(distances.min()),
            'continuous_clearance_lower_bound': lower, 'required_radius': float(safety),
            'method': 'final-mesh proximity minus half maximum sample step, plus mesh parity inside tests'}


def _search(safe, clearance, start, goal, voxel, safety, max_expansions):
    shape = safe.shape
    strides = (shape[1] * shape[2], shape[2], 1)
    def flat(p): return int(p[0] * strides[0] + p[1] * strides[1] + p[2])
    source, target = flat(start), flat(goal)
    costs = {source: 0.}
    parents = {}
    queue = [(float(np.linalg.norm(np.asarray(start) - goal)) * voxel, 0., source, tuple(start))]
    expanded = 0
    while queue:
        _, cost, current, p = heapq.heappop(queue)
        if cost != costs.get(current):
            continue
        if current == target:
            chain = [current]
            while chain[-1] != source:
                chain.append(parents[chain[-1]])
            chain.reverse()
            return np.asarray(np.unravel_index(chain, shape)).T, expanded, cost
        if expanded >= max_expansions:
            return None, expanded, None
        expanded += 1
        for axis in range(3):
            for direction in (-1, 1):
                q = list(p)
                q[axis] += direction
                if not 0 <= q[axis] < shape[axis]:
                    continue
                q = tuple(q)
                if not safe[q]:
                    continue
                nxt = current + direction * strides[axis]
                edge = voxel * (1 + (safety / min(clearance[p], clearance[q])) ** 2)
                alternative = cost + edge
                if alternative >= costs.get(nxt, float('inf')):
                    continue
                costs[nxt] = alternative
                parents[nxt] = current
                heuristic = float(np.linalg.norm(np.asarray(q) - goal)) * voxel
                heapq.heappush(queue, (alternative + heuristic, alternative, nxt, q))
    return None, expanded, None


def plan_navigation(mesh, grid, origin, voxel, start, goal, safety, max_expansions=500000):
    """Return an independently found and mesh-certified start-to-goal witness."""
    began = time.perf_counter()
    origin = np.asarray(origin)
    start, goal = np.asarray(start, dtype=float), np.asarray(goal, dtype=float)
    a, b = np.rint((np.stack([start, goal]) - origin) / voxel).astype(int)
    report = {'status': 'FAIL', 'method': '6-neighbor clearance-weighted A*',
              'input': 'collision occupancy and endpoints only; no centerline or semantic graph',
              'start': start.tolist(), 'goal': goal.tolist(), 'voxel_size': voxel,
              'max_expansions': max_expansions,
              'limitations': 'A grid witness with a final-mesh spherical-robot certificate; no dynamics, global geometric optimality or failure-proof unreachability claim.'}
    def finish(reason=None):
        if reason:
            report['reason'] = reason
        report['seconds'] = time.perf_counter() - began
        return report
    if np.any(a < 0) or np.any(b < 0) or np.any(a >= grid.shape) or np.any(b >= grid.shape):
        return finish('endpoint_outside_grid')
    clearance = ndimage.distance_transform_edt(grid > 0, sampling=voxel) - voxel * np.sqrt(3) / 2
    # Extra half-edge allowance protects axis-aligned transitions between nodes.
    safe = clearance > safety + voxel / 2
    if not safe[tuple(a)] or not safe[tuple(b)]:
        return finish('endpoint_not_in_conservative_robot_space')
    labels, _ = ndimage.label(safe)
    if labels[tuple(a)] != labels[tuple(b)]:
        return finish('no_connection_in_conservative_grid')
    del labels
    chain, expanded, objective = _search(safe, clearance, a, b, voxel, safety, max_expansions)
    report['expanded_nodes'] = expanded
    if chain is None:
        return finish('search_budget_exhausted' if expanded >= max_expansions else 'no_grid_path')
    points = np.vstack([start, chain * voxel + origin, goal])
    points = points[np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-9]]
    if len(points)==1:
        points=np.vstack([points,points])
    report['points'] = points.tolist()
    report['length_metres'] = float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
    report['search_objective'] = objective
    report['collision_certificate'] = certify_polyline(mesh, points, safety)
    report['status'] = report['collision_certificate']['status']
    return finish(None if report['status'] == 'PASS' else 'candidate_failed_final_mesh_certificate')
