"""Check declared source roles without opening real/OOD geometry or textures."""
import argparse
import json
from pathlib import Path
import yaml

def audit(registry):
    ids=set(); assets=set(); eligible=[]
    for source in registry['sources']:
        if source['group_id'] in ids:raise ValueError('Duplicate group')
        ids.add(source['group_id'])
        for asset in source['asset_ids']:
            if asset in assets:raise ValueError('Asset assigned to multiple groups')
            assets.add(asset)
        if source['untouched_final_eligible']:
            if source['identity_confirmed'] is not True or source['prior_or_development_used'] is not False:
                raise ValueError('Unknown or previously used source cannot be untouched OOD')
            if source['training_use'] != 'never_used_confirmed':raise ValueError('Training use unresolved')
            eligible.append(source['group_id'])
    return {'status':'adapter_checked','scope':'declared metadata consistency, not proof of source history',
            'groups':len(ids),'untouched_final_eligible':eligible,
            'c3_readiness':'blocked' if not eligible else 'requires_metric_scale_and_runtime_checks'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--registry',default='research_workspace/source_registry_v02.yaml')
    a=p.parse_args();print(json.dumps(audit(yaml.safe_load(Path(a.registry).read_text(encoding='utf-8'))),indent=2))
