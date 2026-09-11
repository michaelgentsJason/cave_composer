"""Verify a frozen release and stage two unchanged representative Isaac inputs.

This adapter does not regenerate, transform, or alter any source geometry.
Run the existing isaac_cave_smoke_v02.py against the newly staged directory.
"""
import argparse
import json
import shutil
from pathlib import Path
from check_c2_release_v02 import check


def stage(release, output):
    release,output=release.resolve(),output.resolve()
    if output.exists():raise FileExistsError('Use a new runtime input directory')
    if output.is_relative_to(release):raise ValueError('Do not write into the frozen release')
    receipt=check(release)
    manifest=json.loads((release/'manifest.json').read_text(encoding='utf-8'))
    selected=['request_00_full','request_01_full']
    for sid in selected:
        item=next(s for s in manifest['scenes'] if s['scene_id']==sid)
        shutil.copytree(release/item['open_bundle'],output/'open_assets'/sid)
        shutil.copytree(release/item['closed_tasks'],output/'task_packs'/sid)
    receipt.update(staged_scenes=selected,source_release=str(release),
        scope='Unchanged copies; direct USD adapter smoke only, no policy or Lab')
    (output/'staging_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(stage(args.release,args.output),indent=2))
