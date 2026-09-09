"""Read-only CAVERS observation profile and conservative source-group registry."""
import argparse
import csv
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cave_composer.bundle import atomic_json, file_sha256
from cave_composer.reference_data import audit_reference_registry, depth_observation_statistics, quantiles


def profile(root, output, frames=24):
    root, output = Path(root).resolve(), Path(output).resolve()
    if frames < 2 or output.exists() or root in output.parents or output in root.parents:
        raise ValueError('Use >=2 frames and a new output separate from the read-only dataset')
    reference = root/'rec_handheld_4_metashape'
    calibration = reference/'calibration/rs_color_opencv.xml'
    associations = reference/'associations/rgb_depth_pairs.csv'
    qc_file = reference/'qc/preprocessing_summary.json'
    qc = json.loads(qc_file.read_text())
    if qc['aligned_depth_unit'] != 'm' or qc['aligned_depth_type'] != 'Z in camera_color_optical_frame':
        raise ValueError('Unverified depth scale/convention')
    xml = ET.parse(calibration).getroot()
    K = np.fromstring(xml.find('Camera_Matrix/data').text, sep=' ').reshape(3, 3)
    distortion = np.fromstring(xml.find('Distortion_Coefficients/data').text, sep=' ')
    if np.any(distortion != 0):
        raise ValueError('This profile expects rectified depth with zero distortion')
    size = (int(xml.find('image_Width').text), int(xml.find('image_Height').text))
    rows = list(csv.DictReader(associations.open(encoding='utf-8-sig')))
    accepted = [row for row in rows if row['accepted'] == '1']
    indices = np.unique(np.linspace(0, len(accepted)-1, min(frames, len(accepted)), dtype=int))
    hashes = {p.relative_to(root).as_posix(): file_sha256(p) for p in [calibration, associations, qc_file]}
    records = []
    for index in indices:
        row = accepted[index]
        if row['depth_unit'] != 'm' or row['depth_type'] != 'z_in_rgb_optical_frame':
            raise ValueError('Mixed depth conventions')
        file = reference/'depth_aligned_to_rgb'/row['aligned_depth_filename']
        before = file_sha256(file)
        with Image.open(file) as im:
            if im.size != size or im.mode != 'F':
                raise ValueError('Expected calibrated full-resolution float32 depth')
            record = depth_observation_statistics(np.asarray(im), K)
        if before != file_sha256(file):
            raise ValueError('Reference changed while reading')
        relative = file.relative_to(root).as_posix()
        hashes[relative] = before
        record.update(file=relative, sha256=before, rgb_source_index=int(row['rgb_source_index']))
        records.append(record)
    registry = {'schema_version': 1, 'assets': [
        {'id': 'cavers_all_recordings_and_derivatives', 'source_group': 'Cueva_de_la_Victoria_Malaga',
         'group_confirmed': True, 'role': 'prior', 'used_for_development': True,
         'group_evidence': 'https://zenodo.org/records/19367714',
         'content_sha256': list(hashes.values()),
         'reason': 'Official dataset collected at Cueva de la Victoria; prior appearance use of rec_handheld_4/5 and inspection of other sequences. Separate rooms/recordings do not constitute independent caves.'}],
        'final_test_selection': 'PENDING: no independent cave assets designated or consumed',
        'disallowed_split': 'Random frames or recording names do not establish independent cave-level test separation.'}
    audit = audit_reference_registry(registry)
    summary = {'schema_version': 1, 'source': 'CAVERS rec_handheld_4 metric aligned depth',
        'selected_frames': len(records), 'accepted_frames_available': len(accepted),
        'sampling': 'uniform over accepted frame order, no view-quality cherry-picking',
        'intrinsics': K.tolist(), 'resolution': list(size), 'records': records,
        'distribution_of_frame_median_depth_m': quantiles([r['optical_depth_m']['p50'] for r in records if r['optical_depth_m']]),
        'distribution_of_frame_p95_range_m': quantiles([r['range_m']['p95'] for r in records if r['range_m']]),
        'source_sha256': hashes, 'original_files_unchanged': all(file_sha256(root/p) == h for p, h in hashes.items()),
        'scope': 'Offline reference observations; depth is not a policy input. Not a cave-width distribution or recovered physical material.',
        'metric_geometry_prior_status': 'PENDING: independent scaled cave mesh plus surveyed/annotated route needed; do not fit corridor widths to forward depth.'}
    output.mkdir(parents=True)
    atomic_json(output/'observation_statistics.json', summary)
    atomic_json(output/'reference_registry.json', registry)
    atomic_json(output/'split_audit.json', audit)
    print(json.dumps({'frames': len(records), 'median_depth_distribution_m': summary['distribution_of_frame_median_depth_m'],
                      'split_audit': audit}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--frames', type=int, default=24)
    args = parser.parse_args()
    profile(args.dataset, args.output, args.frames)
