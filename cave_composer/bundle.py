"""Atomic metadata and integrity checks shared by scene and dataset workflows."""
from contextlib import contextmanager
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import uuid


def atomic_json(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with temporary.open('w', encoding='utf-8', newline='\n') as stream:
            json.dump(data, stream, indent=2, allow_nan=False, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def file_sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else _stream_digest(stream)


def _stream_digest(stream):
    result = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        result.update(block)
    return result.hexdigest()


def environment_signature():
    return {
        'python': platform.python_version(),
        'dependencies': {name: importlib.metadata.version(name) for name in
                         ['numpy', 'scipy', 'scikit-image', 'trimesh', 'rtree', 'Pillow', 'PyYAML', 'matplotlib']},
        # Normalize line endings so the same checkout has the same identity on Windows/Linux.
        'source_sha256': {p.name: hashlib.sha256(p.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
                          for p in sorted(Path(__file__).parent.glob('*.py'))},
    }


def bundle_checksums(folder):
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): file_sha256(p)
            for p in sorted(folder.rglob('*')) if p.is_file() and p != folder/'metadata/checksums.json'}


def verify_bundle(folder):
    """Check complete file inventory, contents and the persisted generation outcome."""
    folder = Path(folder)
    required = ['.cave_composer_bundle', 'metadata/checksums.json', 'metadata/run.json',
                'metadata/provenance.json', 'metadata/validation.json', 'metadata/metrics.json',
                'metadata/config.json', 'visual/cave_visual.obj', 'collision/cave_collision.obj',
                'visual/mesh.npz', 'collision/mesh.npz', 'materials/rock_albedo.png',
                'navigation/centerline.json', 'navigation/navigation_graph.json',
                'navigation/spawn_points.json', 'navigation/goals.json', 'previews/topology.png']
    missing = [name for name in required if not (folder/name).is_file()]
    if missing:
        raise ValueError(f'Incomplete bundle {folder}: {missing}')
    recorded = json.loads((folder/'metadata/checksums.json').read_text(encoding='utf-8'))
    actual = bundle_checksums(folder)
    changed = sorted(key for key in set(recorded) | set(actual) if recorded.get(key) != actual.get(key))
    if changed:
        raise ValueError(f'Bundle integrity mismatch in {folder}: {changed[:8]}')
    run = json.loads((folder/'metadata/run.json').read_text(encoding='utf-8'))
    config = json.loads((folder/'metadata/config.json').read_text(encoding='utf-8'))
    config_sha = hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if config_sha != run['config_sha256']:
        raise ValueError(f'Bundle config differs from the generation request: {folder}')
    validation = json.loads((folder/'metadata/validation.json').read_text(encoding='utf-8'))
    if run['status'] != 'COMPLETE' or validation['status'] != 'VALID' or not all(validation['checks'].values()):
        raise ValueError(f'Bundle is not a completed VALID scene: {folder}')
    if run['render']:
        for name in ['overview.png', 'inside_01.png', 'inside_02.png', 'render_info.json']:
            if not (folder/'previews'/name).is_file():
                raise ValueError(f'Missing rendered preview: {folder/name}')
        if validation.get('intersection_audit', {}).get('status') != 'PASS':
            raise ValueError(f'Missing successful intersection audit: {folder}')
    if run['save_blend'] and not (folder/'cave.blend').is_file():
        raise ValueError(f'Missing saved Blender scene: {folder}')
    return run


@contextmanager
def dataset_lock(root):
    """An OS-managed lock releases on process death; no stale PID removal is needed."""
    path = Path(root)/'.dataset.lock'
    with path.open('a+b') as stream:
        if path.stat().st_size == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(f'Another dataset process holds {path}') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
