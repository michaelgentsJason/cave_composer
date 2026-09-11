"""Fresh checks of delivered triangles, never reuse a pre-export certificate."""
import hashlib
from pathlib import Path
import numpy as np
import trimesh
from .planning import certify_polyline
from .portals import surface_path_certificate


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def verify_delivered_task(files, points, safety, *, closed=True):
    """Files must already be in metres/Z-up, with all instance transforms applied.

    Open-surface results attest distance only; callers must also bind a closed
    reference, valid portal cuts and crossing paths before accepting an episode.
    """
    if set(files) != {'visual', 'collision'}:
        raise ValueError('Both delivered meshes are required')
    reports = {}
    for kind, filename in files.items():
        mesh = trimesh.load(Path(filename), force='mesh', process=False)
        if not isinstance(mesh, trimesh.Trimesh): raise ValueError('Expected triangles')
        imported_vertices = len(mesh.vertices)
        # OBJ's distinct UV/normal indices split vertices on import. Reconstruct
        # geometric incidence using EXACT coordinate equality, without moving,
        # deleting, filling, or approximating any delivered triangle.
        vertices, inverse = np.unique(mesh.vertices, axis=0, return_inverse=True)
        mesh = trimesh.Trimesh(vertices, inverse[mesh.faces], process=False)
        certificate = (certify_polyline if closed else surface_path_certificate)(mesh, points, safety)
        reports[kind] = {'file_sha256': sha256(filename), 'triangles': len(mesh.faces),
                         'imported_vertices': imported_vertices, 'geometric_vertices': len(vertices),
                         'seam_protocol': 'exact-position index welding; delivered triangles unchanged',
                         'certificate': certificate}
    return {'status': 'PASS' if all(r['certificate']['status']=='PASS' for r in reports.values()) else 'FAIL',
            'protocol': 'closed_reference' if closed else 'open_surface_distance_only',
            'path_sha256': hashlib.sha256(np.asarray(points,dtype='<f8').tobytes()).hexdigest(),
            'required_radius': safety, 'meshes': reports}
