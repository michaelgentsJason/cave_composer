"""Remove zero-area export triangles after coordinate precision conversion.

UVs, normals, textures and positions are unchanged. Only degenerate triangle
indices are removed. This supports the non-sparse, indexed triangle GLBs
produced by this project's Blender exporter.
"""
import json
from pathlib import Path
import struct
import numpy as np


def clean_glb(path, area_epsilon=1e-12):
    if not np.isfinite(area_epsilon) or area_epsilon < 0:
        raise ValueError('Area threshold must be finite and nonnegative')
    path = Path(path)
    raw = path.read_bytes()
    magic, version, total = struct.unpack_from('<4sII', raw)
    if magic != b'glTF' or version != 2 or total != len(raw):
        raise ValueError('Invalid GLB header')
    size, tag = struct.unpack_from('<II', raw, 12)
    if tag != 0x4E4F534A:
        raise ValueError('Expected GLB JSON chunk')
    data = json.loads(raw[20:20 + size])
    if len(data.get('buffers', [])) != 1 or 'uri' in data['buffers'][0]:
        raise ValueError('Expected one embedded GLB buffer')
    indices = [p['indices'] for m in data['meshes'] for p in m['primitives']]
    if len(set(indices)) != len(indices):
        raise ValueError('Shared index accessors are unsupported; file was not changed')
    binary_size, tag = struct.unpack_from('<II', raw, 20 + size)
    if tag != 0x004E4942:
        raise ValueError('Expected GLB binary chunk')
    binary = bytearray(raw[28 + size:28 + size + binary_size])
    dtypes = {5121: '<u1', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
    def accessor(index, columns):
        spec = data['accessors'][index]
        if 'sparse' in spec:
            raise ValueError('Sparse accessor unsupported')
        view = data['bufferViews'][spec['bufferView']]
        offset = spec.get('byteOffset', 0) + view.get('byteOffset', 0)
        dtype = np.dtype(dtypes[spec['componentType']])
        stride = view.get('byteStride', columns * dtype.itemsize)
        array = np.ndarray((spec['count'], columns), dtype=dtype, buffer=binary,
                           offset=offset, strides=(stride, dtype.itemsize))
        return array, spec, view, offset
    removed, before = 0, 0
    for mesh in data['meshes']:
        for primitive in mesh['primitives']:
            if primitive.get('mode', 4) != 4:
                raise ValueError('Only triangle primitives supported')
            positions, _, _, _ = accessor(primitive['attributes']['POSITION'], 3)
            index, spec, view, offset = accessor(primitive['indices'], 1)
            if 'byteStride' in view:
                raise ValueError('Interleaved index buffers unsupported')
            faces = index.reshape(-1, 3).copy()
            triangles = positions[faces].astype(np.float64)
            area = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                           triangles[:, 2] - triangles[:, 0]), axis=1) / 2
            keep = area > area_epsilon
            before += len(faces)
            removed += int((~keep).sum())
            encoded = faces[keep].reshape(-1).astype(index.dtype)
            if not len(encoded):
                raise ValueError('All triangles degenerate')
            payload = encoded.tobytes()
            binary[offset:offset + len(payload)] = payload
            spec.update(count=len(encoded), min=[int(encoded.min())], max=[int(encoded.max())])
    encoded_json = json.dumps(data, separators=(',', ':')).encode('utf-8')
    encoded_json += b' ' * (-len(encoded_json) % 4)
    body = struct.pack('<II', len(encoded_json), 0x4E4F534A) + encoded_json
    body += struct.pack('<II', len(binary), 0x004E4942) + binary
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, len(body) + 12) + body)
    return {'triangles_before': before, 'zero_area_triangles_removed': removed, 'triangles_after': before - removed}


def clean_obj(path, area_epsilon=1e-12):
    if not np.isfinite(area_epsilon) or area_epsilon < 0:
        raise ValueError('Area threshold must be finite and nonnegative')
    path = Path(path)
    lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
    vertices = np.array([[float(x) for x in line.split()[1:4]] for line in lines if line.startswith('v ')])
    output, removed, before = [], 0, 0
    for line in lines:
        if line.startswith('f '):
            indices = [int(x.split('/')[0]) for x in line.split()[1:]]
            if len(indices) != 3 or min(indices) <= 0:
                raise ValueError('Expected positive-index OBJ triangles')
            tri = vertices[np.array(indices) - 1]
            before += 1
            if np.linalg.norm(np.cross(tri[1] - tri[0], tri[2] - tri[0])) / 2 <= area_epsilon:
                removed += 1
                continue
        output.append(line)
    if before == removed:
        raise ValueError('No nondegenerate OBJ triangles; file was not changed')
    path.write_text(''.join(output), encoding='utf-8', newline='\n')
    return {'triangles_before': before, 'zero_area_triangles_removed': removed, 'triangles_after': before - removed}
