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


def distance_allowance(mesh):
    """Explicit engineering tolerance, not an interval-arithmetic error proof."""
    return max(1e-6, 64*np.finfo(float).eps*max(1., float(np.abs(mesh.vertices).max())))


def certify_polyline(mesh, points, safety, sample_step=.25):
    if not np.isfinite(safety) or safety<=0 or not np.isfinite(sample_step) or sample_step<=0:
        raise ValueError('Safety radius and sample step must be finite and positive')
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or not np.isfinite(points).all():
        raise ValueError('A path must contain at least two finite 3D points')
    # Parity has no reliable cavity meaning for an open reference. Never let an
    # implementation-specific contains() result turn this into a passing check.
    if (not len(mesh.faces) or not np.isfinite(mesh.vertices).all()
            or not mesh.is_watertight or not mesh.is_winding_consistent):
        return {'status': 'FAIL', 'reason': 'closed_reference_protocol_not_applicable',
                'protocol_applicable': False, 'samples_inside': None,
                'required_radius': float(safety)}
    samples = [points[0]]
    maximum_step = 0.
    for a, b in zip(points[:-1], points[1:]):
        length = float(np.linalg.norm(b - a))
        count = max(1, int(np.ceil(length / sample_step)))
        maximum_step = max(maximum_step, length / count)
        samples.extend(np.linspace(a, b, count + 1)[1:])
    samples = np.asarray(samples)
    distances = mesh_clearance(mesh, samples)
    epsilon = distance_allowance(mesh)
    lower = float(distances.min() - maximum_step / 2 - epsilon)
    inside = bool(np.all(mesh.contains(samples)))
    return {'status': 'PASS' if inside and lower > safety else 'FAIL',
            'protocol_applicable': True, 'numerical_allowance': epsilon,
            'numerical_scope': 'floating-point proximity and parity; not a rigorous rounding-error certificate',
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


class NavigationSpace:
    """Reusable conservative occupancy for independent multi-query planning.

    Owns derived arrays; changes to the caller's grid cannot stale the cache.
    No construction routes or graphs enter this object.
    """
    def __init__(self, grid, origin, voxel, safety):
        grid = np.asarray(grid)
        origin = np.asarray(origin, dtype=float)
        if grid.ndim != 3 or min(grid.shape) < 2 or not np.isfinite(grid).all():
            raise ValueError('Expected a finite 3D occupancy grid')
        if origin.shape != (3,) or not np.isfinite(origin).all():
            raise ValueError('Expected a finite 3D grid origin')
        if not np.isfinite(voxel) or voxel <= 0 or not np.isfinite(safety) or safety <= 0:
            raise ValueError('Voxel size and safety must be finite and positive')
        self.origin, self.voxel, self.safety = origin.copy(), float(voxel), float(safety)
        self.shape = grid.shape
        began = time.perf_counter()
        # Treat space outside the supplied grid as occupied, even if a caller
        # provides an all-free boundary. This also makes EDT well-defined.
        padded = np.pad(grid > 0, 1, constant_values=False)
        self.clearance = ndimage.distance_transform_edt(padded, sampling=voxel)[1:-1, 1:-1, 1:-1].copy() - voxel*np.sqrt(3)/2
        self.safe = self.clearance > safety + voxel/2
        self.labels, self.components = ndimage.label(self.safe)
        self.seconds = time.perf_counter() - began
        for array in [self.origin, self.clearance, self.safe, self.labels]:
            array.flags.writeable = False

    def plan(self, mesh, start, goal, max_expansions=500000):
        return _plan_in_space(mesh, self, start, goal, max_expansions)


def plan_navigation(mesh, grid, origin, voxel, start, goal, safety, max_expansions=500000):
    """Return an independently found and mesh-certified start-to-goal witness."""
    space = NavigationSpace(grid, origin, voxel, safety)
    report = space.plan(mesh, start, goal, max_expansions)
    report['seconds'] += space.seconds
    return report


def _plan_in_space(mesh, space, start, goal, max_expansions):
    began = time.perf_counter()
    origin, voxel, safety = space.origin, space.voxel, space.safety
    start, goal = np.asarray(start, dtype=float), np.asarray(goal, dtype=float)
    if start.shape != (3,) or goal.shape != (3,) or not np.isfinite([start, goal]).all():
        raise ValueError('Endpoints must be finite 3D points')
    if isinstance(max_expansions, bool) or int(max_expansions) != max_expansions or max_expansions < 1:
        raise ValueError('Search budget must be a positive integer')
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
    if np.any(a < 0) or np.any(b < 0) or np.any(a >= space.shape) or np.any(b >= space.shape):
        return finish('endpoint_outside_grid')
    clearance, safe = space.clearance, space.safe
    if not safe[tuple(a)] or not safe[tuple(b)]:
        return finish('endpoint_not_in_conservative_robot_space')
    if space.labels[tuple(a)] != space.labels[tuple(b)]:
        return finish('no_connection_in_conservative_grid')
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
