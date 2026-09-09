"""Draw whole-cave XY projections from portable geometry and saved navigation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import atomic_json
from cave_composer.routes import build_routes
from cave_composer.spec import load_spec
from scripts.asset_gallery import write_gallery


def render(folder):
    config = load_spec(json.loads((folder / 'config.json').read_text(encoding='utf-8')))
    routes = build_routes(config)
    nav = json.loads((folder / 'navigation_z_up.json').read_text(encoding='utf-8'))
    portals = json.loads((folder / 'portal_validation.json').read_text(encoding='utf-8'))['portals']
    path = np.asarray(nav['points'])
    with np.load(folder / 'reference_visual.npz') as mesh:
        vertices, faces = mesh['vertices'], mesh['faces']
        triangles = vertices[faces, :2]
        limits = np.vstack([vertices[:, :2], path[:, :2]])
    with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 11}):
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
        fig.subplots_adjust(left=.02, right=.98, top=.97, bottom=.04)
        ax.add_collection(PolyCollection(triangles, facecolors='#dce5e3', edgecolors='none',
                                         antialiased=False, rasterized=True))
        for i, route in enumerate(routes):
            p = route['points']
            ax.plot(p[:, 0], p[:, 1], color='#168c9e' if i == 0 else '#5274b8' if route['join_end'] is not None else '#bb7c26', lw=2.5,
                    solid_capstyle='round', zorder=3)
        ax.plot(path[:, 0], path[:, 1], color='#b64282', lw=1.8, ls=(0, (4, 3)), zorder=4)
        for portal, marker, color, label, offset in zip(
                portals, ['o', 'D'], ['#397b58', '#be6445'], ['Entrance', 'Exit'], [(-7, -22), (7, -22)]):
            x, y = portal['center'][:2]
            ax.scatter(x, y, marker=marker, s=75, c=color, edgecolors='white', linewidths=1.5, zorder=6)
            ax.annotate(label, (x, y), xytext=offset, textcoords='offset points',
                        ha='right' if label == 'Entrance' else 'left', color=color, weight='bold')
        low, high = limits.min(axis=0), limits.max(axis=0)
        span = high - low
        pad = max(float(span.max()) * .12, 5.)
        ax.set_xlim(low[0] - pad, high[0] + pad)
        ax.set_ylim(low[1] - pad, high[1] + pad)
        ax.set_aspect('equal', adjustable='box')
        ax.axis('off')
        length = 10 if span.max() >= 30 else 5
        x, y = low[0], low[1] - pad * .68
        ax.plot([x, x + length], [y, y], color='#273444', lw=2)
        ax.plot([x, x], [y - .3, y + .3], color='#273444', lw=1)
        ax.plot([x + length, x + length], [y - .3, y + .3], color='#273444', lw=1)
        ax.text(x + length / 2, y - .8, f'{length} m', ha='center', va='top', color='#273444')
        ax.text(.99, .02, 'XY projection', transform=ax.transAxes, ha='right', color='#71828b', fontsize=10)
        fig.savefig(folder / 'overview_route.png', dpi=150, facecolor='white')
        plt.close(fig)
        main = routes[0]
        fig, ax = plt.subplots(figsize=(10, 2.4), facecolor='white')
        fig.subplots_adjust(left=.08, right=.97, bottom=.26, top=.80)
        ax.plot(main['s'], main['points'][:, 2], color='#168c9e', lw=2)
        ax.set(xlabel='Distance along main passage / m', ylabel='Z / m', title='Main passage elevation')
        if np.ptp(main['points'][:, 2]) < .5:
            level = float(np.mean(main['points'][:, 2]))
            ax.set_ylim(level-1, level+1)
        ax.spines[['top','right']].set_visible(False)
        ax.grid(alpha=.2)
        fig.savefig(folder / 'overview_profile.png', dpi=150, facecolor='white')
        plt.close(fig)
    atomic_json(folder / 'overview_route.json', {
        'view': 'XY orthographic projection of exported reference mesh; not a free-space topology certificate',
        'units': 'metres', 'routes_source': 'local config.json / build_routes',
        'verified_path_source': 'navigation_z_up.json', 'portals_source': 'portal_validation.json',
        'main_route_length_m': float(routes[0]['s'][-1]),
        'route_elevation_range_m': float(np.ptp(np.concatenate([r['points'][:, 2] for r in routes]))),
        'source_sha256': {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                          for name in ['config.json', 'navigation_z_up.json', 'reference_visual.npz', 'portal_validation.json']}})


def main(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'batch_manifest.json').read_text(encoding='utf-8'))
    for a in manifest['assets']:
        render(root / a['folder'])
        print(a['name'], 'overview complete', flush=True)
    write_gallery(root, manifest['assets'], manifest['targets'])
    atomic_json(root / 'checksums.json', {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in sorted(root.rglob('*')) if p.is_file() and p != root / 'checksums.json'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='exports/caves_difficulty_v01')
    main(parser.parse_args().root)
