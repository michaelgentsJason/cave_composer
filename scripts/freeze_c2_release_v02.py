"""Copy, verify and freeze a portable paired interface pilot with fixed episodes."""
from pathlib import Path
import argparse,json,sys,shutil
import numpy as np,trimesh
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.tasks import load_task_pack
from cave_composer.bundle import verify_portal_export
from cave_composer.delivery_validation import sha256,verify_delivered_task
from cave_composer.exit_tasks import certify_exit_trace
from cave_composer.portals import surface_path_certificate
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_textured_exports import load_world_mesh
SOURCE=Path('outputs/c2_pretraining_v02');TARGET=Path('exports/cavern_pretraining_v02')
PILOT=Path('outputs/c1_pilot_v02')

def dump(path,data):path.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
def npzmesh(path):
    d=np.load(path);return trimesh.Trimesh(d['vertices'],d['faces'],process=False)

def main():
    if TARGET.exists():raise FileExistsError(TARGET)
    TARGET.mkdir(parents=True);scenes=[];episodes=[];verification=[];pair_metrics={}
    for item in json.loads((SOURCE/'preparation.json').read_text())['scenes']:
        sid=item['scene_id'];dest=TARGET/'assets'/sid;dest.mkdir(parents=True)
        for from_,to_ in [('task_packs','closed_tasks'),('open_assets_inset005','open'),('portable_inset005','portable')]:
            shutil.copytree(SOURCE/from_/sid,dest/to_)
        contract,accepted=load_task_pack(dest/'closed_tasks');portal=verify_portal_export(dest/'open')
        refs={k:npzmesh(dest/'closed_tasks'/k/'mesh.npz') for k in ['visual','collision']}
        surfaces={k:npzmesh(dest/'open'/k/'mesh.npz') for k in refs}
        for kind in refs:
            if sha256(dest/'closed_tasks'/kind/'mesh.npz')!=portal['source_files'][kind+'/mesh.npz']:raise ValueError('Closed reference binding mismatch')
        visual_glb=load_world_mesh(dest/'portable'/(sid+'.glb'));visual_obj=load_world_mesh(dest/'portable'/(sid+'.obj'))
        vrec={'scene_id':sid,'closed_reference_binding':True,'tasks':[]}
        for ep in accepted:
            task=json.loads((dest/'closed_tasks/tasks'/(ep['id']+'.json')).read_text());points=task['planning']['points']
            checks={'open_obj_dual_mesh':verify_delivered_task({k:dest/'open'/k/f'cave_{k}.obj' for k in refs},points,.55,closed=False),
                    'portable_visual_glb':surface_path_certificate(visual_glb,points,.55),
                    'portable_visual_obj':surface_path_certificate(visual_obj,points,.55)}
            if not all(c['status']=='PASS' for c in checks.values()):raise ValueError('Internal task invalid on delivered derivative')
            vrec['tasks'].append({'id':ep['id'],'checks':checks})
            episodes.append({'episode_id':sid+'/'+ep['id'],'scene_id':sid,'base_group':item['base_group'],'condition':item['condition'],
                'split':item['split'],'task_kind':'interior_pair','reset':ep['start'],'goal':ep['goal'],
                'primary_matched_schedule':ep['id']=='task_0000','witness_record':f'assets/{sid}/closed_tasks/tasks/'+ep['id']+'.json'})
            if ep['id']=='task_0000':pair_metrics.setdefault(item['base_group'],{})[item['condition']]=task['planning']['metrics']
        through=json.loads((dest/'open/navigation/portal_path.json').read_text())
        witness=certify_exit_trace(through['points'],refs,surfaces,portal)
        if witness['status']!='PASS':raise ValueError('Full-exit witness failed: '+sid)
        yaw=np.arctan2(portal['portals'][0]['inward'][1],portal['portals'][0]['inward'][0])
        episodes.append({'episode_id':sid+'/full_exit_0000','scene_id':sid,'base_group':item['base_group'],'condition':item['condition'],
            'split':item['split'],'task_kind':'full_exit','reset':{'position_m':through['start'],'orientation_wxyz':[float(np.cos(yaw/2)),0,0,float(np.sin(yaw/2))]},
            'goal':{'position_m':through['goal'],'tolerance_m':.5},'primary_matched_schedule':True,
            'witness_record':f'assets/{sid}/open/navigation/portal_path.json','termination_protocol':'ordered physical aperture crossings + goal; closed interior and open swept-distance audit; collision/budget precedence in platform'})
        vrec['full_exit_witness']=witness;verification.append(vrec)
        scenes.append({'scene_id':sid,'base_group':item['base_group'],'condition':item['condition'],'split':item['split'],
                       'closed_tasks':f'assets/{sid}/closed_tasks','open_bundle':f'assets/{sid}/open',
                       'visual_glb':f'assets/{sid}/portable/{sid}.glb','visual_obj':f'assets/{sid}/portable/{sid}.obj',
                       'collision_obj':f'assets/{sid}/open/collision/cave_collision.obj',
                       'units':'metres','obj_frame':'right-handed Z-up','glb_frame':'right-handed Y-up',
                       'glb_to_zup':[[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]],
                       'collider':'static nonconvex triangles; approximation none, never convexHull',
                       'rig':f'assets/{sid}/closed_tasks/stereo_rig.json'})
        print(sid,'copied and freshly checked',flush=True)
    pairs=[]
    for base,conditions in pair_metrics.items():
        a,b=conditions['full'],conditions['restricted']
        pairs.append({'base_group':base,'full':a,'restricted':b,
            'path_length_difference_m':a['path_length_m']-b['path_length_m'],
            'clearance_lower_bound_difference_m':a['continuous_clearance_lower_bound_m']-b['continuous_clearance_lower_bound_m']})
    profile=json.loads(Path('research_workspace/contracts/platform_proposal_v01.json').read_text())
    profile['delivery_scope']='New pilot for interface acceptance. Existing colleague training version is not changed.'
    profile['primary_sampling']='Only primary_matched_schedule=true; uniform over caves in selected condition/split, then its two primary tasks. Auxiliary task_0001 excluded from primary comparison.'
    profile['material_condition']='Same seeded limestone style, albedo/normal bake settings, lighting/randomization convention in both arms; no water model.'
    profile['primary_budget']={'proposal_max_steps':1500,'proposal_max_seconds':120,'control_rate_hz':'UNCONFIRMED','equal_between_conditions':True}
    dump(TARGET/'platform_profile.json',profile);dump(TARGET/'episodes.json',{'episodes':episodes});dump(TARGET/'verification.json',verification)
    dump(TARGET/'matched_conditions.json',{'pairs':pairs,'matching':'Same base route, nominal width/height, robot, first interior S/G, material seed, scene count and primary request count.',
        'limitation':'Realized clearance and auxiliary task class differ. This pilot is not a fully clearance-matched causal training comparison; report the pair table and calibrate a separate preregistered training study.'})
    (TARGET/'README.md').write_text('''# CAVERN pretraining interface pilot v02

8 generated assets: 4 full / 4 restricted. Per condition: 2 train, 1 development,
1 ID new-geometry test. The same base group stays in one split across arms.
24 fixed tasks: 16 interior + 8 physical full-exit. The primary paired list has
16 tasks (one common interior request and one full-exit per scene); 8 auxiliary
interior tasks are retained but excluded from the main matched sampler.

Each asset includes closed references, both open meshes, textured GLB and
OBJ+MTL+PNG, explicit transforms, stereo rig, and fresh geometric records.
Use OBJ Z-up directly, or apply the recorded GLB Y-up to Z-up transform once.
Static collision must use triangles with approximation=none, never a solid
convex hull. One sample runtime uses two actual assets; this does not certify
all scenes, Isaac Lab, vehicle dynamics, a policy, or the colleague's pipeline.

The platform/action/goal proposal remains UNCONFIRMED. Actor observations are
not the task JSON: maps, planned witnesses, poses and validation files are
privileged. Any relative-goal channel using ground-truth pose must be declared
localization-assisted. Current sensor selection is stereo RGB.

Before use: run `python scripts/check_c2_release_v02.py --release
exports/cavern_pretraining_v02` from the repository. Run the provided Isaac
smoke script in the colleague's EXISTING environment and return raw receipts.
Do not edit this frozen package in place. Record dataset/manifest SHA, scene
assignment, actual rig/actor/action/controller config, seeds, checkpoint SHA,
fixed episode IDs, timestamps, pose traces and termination reasons. No policy
results have been generated here. An internal goal is not a physical exit.
''',encoding='utf-8')
    manifest={'dataset_id':'cavern_pretraining_v02','status':'offline_geometric_interface_pilot','approved_for_training':False,
        'scenes':scenes,'episodes':'episodes.json','profile':'platform_profile.json','source_groups':'base_group locks both conditions and all episodes',
        'source_preregistration_sha256':sha256(PILOT/'preregistration.json'),
        'final_portal_inset_m':.05,'initial_export_attempts':str(SOURCE/'portable_export_runs.json'),
        'runtime_scope':'Two representative final open NPZ meshes via direct USD adapter only; full Lab/vehicle/training integration pending',
        'files':{p.relative_to(TARGET).as_posix():sha256(p) for p in sorted(TARGET.rglob('*')) if p.is_file()}}
    dump(TARGET/'manifest.json',manifest);dump(TARGET/'manifest_digest.json',{'sha256':sha256(TARGET/'manifest.json')})
    print('Frozen',len(scenes),'scenes',len(episodes),'episodes')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--output',type=Path,default=TARGET)
    parser.add_argument('--pilot',type=Path,default=PILOT)
    args=parser.parse_args();SOURCE=args.source;TARGET=args.output;PILOT=args.pilot;main()
