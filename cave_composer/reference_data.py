"""Source-group split checks and explicitly scoped reference measurements."""
import numpy as np
import trimesh


def audit_reference_registry(registry):
    """Fail closed on unknown grouping or any prior/dev use of a test group."""
    records = registry['assets']
    errors, groups, hashes, ids = [], {}, {}, set()
    allowed = {'prior', 'train', 'validation', 'test', 'quarantine'}
    for record in records:
        identity, role = record['id'], record['role']
        if identity in ids:
            errors.append('duplicate_id:'+identity)
        ids.add(identity)
        if role not in allowed:
            errors.append('unknown_role:'+identity)
        group = record.get('source_group')
        if not group:
            errors.append('missing_source_group:'+identity)
        groups.setdefault(group, []).append(record)
        if role == 'test' and (not record.get('group_confirmed') or record.get('used_for_development')):
            errors.append('test_not_untouched:'+identity)
        for fingerprint in record.get('content_sha256', []):
            hashes.setdefault(fingerprint, set()).add(role)
    for group, members in groups.items():
        roles = {r['role'] for r in members}
        if 'test' in roles and len(roles) > 1:
            errors.append('test_group_overlap:'+str(group))
        if 'validation' in roles and roles & {'prior', 'train'}:
            errors.append('validation_group_overlap:'+str(group))
        if any(r.get('used_for_development') for r in members) and 'test' in roles:
            errors.append('test_group_used_for_development:'+str(group))
    for fingerprint, roles in hashes.items():
        if 'test' in roles and len(roles) > 1:
            errors.append('duplicate_content_across_test:'+fingerprint)
    tests = sum(r['role'] == 'test' for r in records)
    return {'status': 'FAIL' if errors else 'PASS', 'errors': sorted(set(errors)),
            'groups': len(groups), 'test_assets': tests,
            'untouched_test_ready': not errors and tests > 0,
            'scope': 'Metadata/group and exact content-hash checks, not proof against unrecorded derivatives or undeclared prior exposure.'}


def quantiles(values):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    return None if not len(values) else dict(zip(['p05', 'p25', 'p50', 'p75', 'p95'], map(float, np.quantile(values, [.05, .25, .5, .75, .95]))))


def depth_observation_statistics(depth, K):
    """Metric optical Z observations, never interpreted as complete cave width."""
    depth = np.asarray(depth, dtype=float)
    K = np.asarray(K, dtype=float)
    if depth.ndim != 2 or K.shape != (3, 3) or not np.isfinite(K).all() or min(K[0, 0], K[1, 1]) <= 0:
        raise ValueError('Depth image and finite camera intrinsics required')
    valid = np.isfinite(depth) & (depth > 0)
    y, x = np.indices(depth.shape)
    rays = np.sqrt(1+((x-K[0, 2])/K[0, 0])**2+((y-K[1, 2])/K[1, 1])**2)
    h, w = depth.shape
    center = depth[h//3:2*h//3, w//3:2*w//3]
    return {'valid_fraction': float(valid.mean()), 'optical_depth_m': quantiles(depth[valid]),
            'range_m': quantiles((depth*rays)[valid]),
            'central_optical_depth_m': quantiles(center[np.isfinite(center)&(center>0)]),
            'scope': 'Visible surface distances conditional on the recorded camera pose/FOV and depth validity; not cave width, free-space clearance, or physical rock roughness.'}


def cross_section_statistics(mesh, points, junction_positions=None, junction_radius=3.):
    """Measure first-hit side/up wall spans along an explicitly supplied route.

    Works with annotated metric reference meshes too; those annotations are
    required and are never inferred from unscaled photographs.
    """
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 3 or not np.isfinite(p).all():
        raise ValueError('At least three finite metric route points required')
    tangent = p[2:]-p[:-2]
    horizontal = np.linalg.norm(tangent[:, :2], axis=1)
    usable = horizontal > 1e-6
    centers = p[1:-1][usable]
    t = tangent[usable]
    side = np.column_stack([-t[:, 1], t[:, 0], np.zeros(len(t))])
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    up = np.tile([0., 0., 1.], (len(t), 1))
    directions = np.stack([side, -side, up, -up], axis=1).reshape(-1, 3)
    origins = np.repeat(centers, 4, axis=0)
    hits, rays, _ = mesh.ray.intersects_location(origins, directions, multiple_hits=False)
    distances = np.full(len(origins), np.nan)
    distances[rays] = np.linalg.norm(hits-origins[rays], axis=1)
    distances = distances.reshape(-1, 4)
    inside = mesh.contains(centers) if mesh.is_watertight else np.zeros(len(centers), dtype=bool)
    complete = np.isfinite(distances).all(axis=1) & inside
    widths = distances[complete, 0]+distances[complete, 1]
    heights = distances[complete, 2]+distances[complete, 3]
    ordinary = np.ones(len(centers), dtype=bool)
    if junction_positions is not None and len(junction_positions):
        junctions = np.asarray(junction_positions, dtype=float)
        ordinary = np.min(np.linalg.norm(centers[:, None, :]-junctions[None, :, :], axis=2), axis=1) > junction_radius
    ordinary = ordinary[complete]
    return {'samples_requested': len(p)-2, 'samples_complete_inside': int(complete.sum()),
            'width_m': quantiles(widths), 'height_m': quantiles(heights),
            'width_height_ratio': quantiles(widths/heights),
            'nonjunction_profile': {'exclusion_radius_m': junction_radius,
                'samples': int(ordinary.sum()), 'transverse_span_m': quantiles(widths[ordinary]),
                'vertical_span_m': quantiles(heights[ordinary])},
            'scope': 'First-hit horizontal transverse and world-vertical spans at supplied route samples; not maximal inscribed diameter; requires watertight metric mesh.'}
