"""Explicit stereo RGB calibration contract, independent of a simulator."""
import numpy as np


def stereo_rgb_rig(width=1280, height=720, fx=675.5555555556, baseline=.12):
    """Rectified parallel pinholes. Defaults are a provisional simulation rig."""
    if isinstance(width, bool) or isinstance(height, bool) or int(width) != width or int(height) != height or min(width, height) < 16:
        raise ValueError('Image dimensions must be integers >=16')
    if not np.isfinite([fx, baseline]).all() or fx <= 0 or baseline <= 0:
        raise ValueError('Positive focal length and baseline required')
    rotation = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]], dtype=float)
    cameras = {}
    for name, side in [('left', 1), ('right', -1)]:
        transform = np.eye(4)
        transform[:3, :3] = rotation
        transform[1, 3] = side*baseline/2
        cameras[name] = {'K': [[fx, 0., width/2], [0., fx, height/2], [0., 0., 1.]],
                         'T_body_from_optical': transform.tolist(), 'distortion': [0., 0., 0., 0., 0.]}
    return {'schema_version': 1, 'modality': 'stereo_rgb', 'resolution': [width, height],
            'baseline_m': baseline, 'rectified': True, 'synchronized': True,
            'body_axes': 'X forward, Y left, Z up', 'optical_axes': 'X right, Y down, Z forward',
            'pixel_convention': 'continuous image-edge coordinates, principal point W/2,H/2',
            'cameras': cameras, 'calibration_status': 'provisional simulation values; not measured hardware calibration',
            'actor_sensor_keys': ['rgb_left', 'rgb_right'],
            'excluded_actor_sensor_keys': ['depth', 'disparity_ground_truth', 'occupancy', 'planned_path', 'navigation_graph']}


def project_body_points(rig, points, camera):
    """Project metric body-frame points to pixels and optical depth for auditing."""
    points = np.asarray(points, dtype=float)
    transform = np.asarray(rig['cameras'][camera]['T_body_from_optical'])
    optical = (points-transform[:3, 3]) @ transform[:3, :3]
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all() or np.any(optical[:, 2] <= 0):
        raise ValueError('Expected finite points in front of camera')
    image = optical @ np.asarray(rig['cameras'][camera]['K']).T
    return image[:, :2]/image[:, 2:], optical[:, 2]
