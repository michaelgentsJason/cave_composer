"""Validate collaborator receipts and copy only into a fresh intake folder."""
import argparse,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.handoff import read,write_new,validate_results,contained
from cave_composer.bundle import file_sha256

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--episodes',required=True)
    p.add_argument('--results',required=True);p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    output=Path(a.output)
    if output.exists():raise FileExistsError('Never overwrite received results')
    run=read(a.run);episodes=read(a.episodes)['episodes'];rows=[json.loads(line) for line in Path(a.results).read_text(encoding='utf-8').splitlines() if line.strip()]
    if run.get('episode_manifest_sha256')!=file_sha256(a.episodes):raise ValueError('Fixed episode file hash mismatch')
    report=validate_results(rows,run,episodes,a.root)
    output.mkdir(parents=True)
    for src,name in [(a.run,'run.json'),(a.episodes,'episodes.json'),(a.results,'results.jsonl')]:shutil.copyfile(src,output/name)
    for row in rows:
        if row['outcome']!='not_run':
            dest=contained(output/'trajectories',row['trajectory']);dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(contained(a.root,row['trajectory']),dest)
    write_new(output/'intake_check.json',report);print(json.dumps(report,indent=2))
