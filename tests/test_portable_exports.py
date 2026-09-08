import json
import struct

import numpy as np
import pytest

from cave_composer.bundle import atomic_json, bundle_checksums, verify_portal_export
from cave_composer.portable_mesh import clean_glb, clean_obj
from scripts.verify_textured_exports import portable_reference


def test_portable_reference_uses_local_files_and_config(tmp_path):
    np.savez(tmp_path/'reference_visual.npz', vertices=np.zeros((3, 3)), faces=[[0, 1, 2]])
    (tmp_path/'config.json').write_text(json.dumps({'robot': {'radius': .42, 'margin': .23}}))
    (tmp_path/'export_verification.json').write_text(json.dumps({
        'texture_resolution': 512, 'source_open_export': 'Z:/nonexistent/original/computer'}))
    vertices, faces, safety, resolution = portable_reference(tmp_path)
    assert vertices.shape == (3, 3) and faces == 1
    assert safety == pytest.approx(.65) and resolution == 512


@pytest.fixture
def portal(tmp_path):
    names = ['metadata/source_config.json', 'visual/mesh.npz', 'visual/cave_visual.obj',
             'visual/cave_visual.mtl', 'collision/mesh.npz', 'collision/cave_collision.obj',
             'navigation/centerline.json', 'navigation/portal_path.json',
             'materials/material.json', 'materials/rock_albedo.png']
    for name in names:
        p = tmp_path/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'fixture bytes')
    details = {'boundary_loops': [{}, {}], 'closed_reference_interior_certificate': {'status': 'PASS'},
               'crossing_certificate': {'status': 'PASS'}}
    atomic_json(tmp_path/'metadata/portal_validation.json', {
        'status': 'PASS', 'artifact_type': 'open_portal_export',
        'meshes': {'visual': details, 'collision': details}})
    atomic_json(tmp_path/'metadata/checksums.json', bundle_checksums(tmp_path))
    return tmp_path


def test_portal_reuse_allows_new_previews_but_rejects_changed_geometry(portal):
    (portal/'preview.txt').write_text('Additional inspection result')
    assert verify_portal_export(portal)['status'] == 'PASS'
    (portal/'visual/mesh.npz').write_bytes(b'changed')
    with pytest.raises(ValueError, match='integrity mismatch'):
        verify_portal_export(portal)


def test_portal_reuse_rejects_missing_certificate_even_with_current_hashes(portal):
    p = portal/'metadata/portal_validation.json'
    report = json.loads(p.read_text())
    report['meshes']['collision']['crossing_certificate']['status'] = 'FAIL'
    atomic_json(p, report)
    atomic_json(portal/'metadata/checksums.json', bundle_checksums(portal))
    with pytest.raises(ValueError, match='certificates'):
        verify_portal_export(portal)


def make_glb(path, shared=False):
    positions = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype='<f4').tobytes()
    indices = np.array([0, 1, 2, 0, 0, 1], dtype='<u4').tobytes()
    payload = b'preserved image payload  '
    binary = positions + indices + payload
    primitive = {'attributes': {'POSITION': 0}, 'indices': 1}
    data = {'asset': {'version': '2.0'}, 'buffers': [{'byteLength': len(binary)}],
            'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': len(positions)},
                            {'buffer': 0, 'byteOffset': len(positions), 'byteLength': len(indices)},
                            {'buffer': 0, 'byteOffset': len(positions) + len(indices), 'byteLength': len(payload)}],
            'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3'},
                          {'bufferView': 1, 'componentType': 5125, 'count': 6, 'type': 'SCALAR'}],
            'meshes': [{'primitives': [primitive, primitive] if shared else [primitive]}]}
    encoded = json.dumps(data).encode()
    encoded += b' ' * (-len(encoded) % 4)
    body = struct.pack('<II', len(encoded), 0x4E4F534A) + encoded
    body += struct.pack('<II', len(binary), 0x004E4942) + binary
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, len(body) + 12) + body)
    return positions, payload


def test_glb_cleanup_preserves_positions_and_image_payload(tmp_path):
    p = tmp_path/'mesh.glb'
    positions, payload = make_glb(p)
    result = clean_glb(p)
    raw = p.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    metadata = json.loads(raw[20:20 + size])
    binary = raw[28 + size:]
    assert result['triangles_after'] == 1 and metadata['accessors'][1]['count'] == 3
    assert binary[:len(positions)] == positions and binary.endswith(payload)
    assert clean_glb(p)['zero_area_triangles_removed'] == 0


def test_glb_shared_indices_rejected_without_mutation(tmp_path):
    p = tmp_path/'shared.glb'
    make_glb(p, shared=True)
    before = p.read_bytes()
    with pytest.raises(ValueError, match='Shared index'):
        clean_glb(p)
    assert p.read_bytes() == before


def test_obj_cleanup_preserves_uv_and_material_references(tmp_path):
    p = tmp_path/'mesh.obj'
    prefix = 'mtllib rock.mtl\nv 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nusemtl Rock\n'
    p.write_text(prefix + 'f 1/1 2/1 3/1\nf 1/1 1/1 2/1\n')
    assert clean_obj(p)['triangles_after'] == 1
    assert p.read_text() == prefix + 'f 1/1 2/1 3/1\n'


def test_obj_all_degenerate_rejected_without_mutation(tmp_path):
    p = tmp_path/'empty.obj'
    p.write_text('v 0 0 0\nf 1 1 1\n')
    before = p.read_bytes()
    with pytest.raises(ValueError, match='No nondegenerate'):
        clean_obj(p)
    assert p.read_bytes() == before
