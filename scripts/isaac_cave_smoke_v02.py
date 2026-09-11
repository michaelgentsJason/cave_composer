"""No learner: two real cave instances, USD static triangles, reset and stereo RGB.

Run inside an EXISTING Isaac Sim 5.0 Python environment. No Isaac Lab claim.
Outputs are written before shutdown so a renderer shutdown stall stays visible.
"""
from pathlib import Path
import argparse,json,time,traceback,hashlib
parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--open-folder',default='open_assets')
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
report={'status':'RUNNING','engine':'Isaac Sim 5.0.0.0','isaaclab_tested':False,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'lighting':{'sphere_intensity':15000,'sphere_exposure':8,'radius_m':.15,'scope':'diagnostic lighting, not calibrated underwater optics'},
        'scope':'static triangle import, transform/reset, scene queries and RGB; no vehicle, controller or RL'}
def save():
    (args.output/'runtime_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
save();start=time.perf_counter()
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'width':320,'height':240,'multi_gpu':False})
report['startup_seconds']=time.perf_counter()-start;save();print('CAVE_APP_READY',flush=True)
try:
    import numpy as np
    from PIL import Image
    from pxr import UsdGeom,UsdPhysics,UsdShade,UsdLux,Sdf,Gf
    import omni.usd,omni.replicator.core as rep
    from omni.physx import get_physx_scene_query_interface
    from isaacsim.core.api import World
    world=World(stage_units_in_meters=1.0,physics_dt=1/60,rendering_dt=1/60)
    stage=omni.usd.get_context().get_stage();UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z)
    records=[];annotators=[]
    for i,sid in enumerate(['request_00_full','request_01_full']):
        directory=args.root/args.open_folder/sid;origin=np.array([0.,i*80.,0.]);base=f'/World/envs/env_{i}'
        parent=UsdGeom.Xform.Define(stage,base);parent.AddTranslateOp().Set(Gf.Vec3d(*origin))
        for kind in ['visual','collision']:
            path=directory/kind/'mesh.npz';data=np.load(path);points=data['vertices'];faces=data['faces']
            mesh=UsdGeom.Mesh.Define(stage,base+'/'+kind)
            mesh.CreatePointsAttr(points.tolist());mesh.CreateFaceVertexCountsAttr([3]*len(faces));mesh.CreateFaceVertexIndicesAttr(faces.reshape(-1).tolist())
            mesh.CreateSubdivisionSchemeAttr('none');mesh.CreateDoubleSidedAttr(True)
            if kind=='collision':
                UsdPhysics.CollisionAPI.Apply(mesh.GetPrim()).CreateCollisionEnabledAttr(True)
                UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim()).CreateApproximationAttr('none')
                mesh.CreateVisibilityAttr('invisible')
                wall=points[faces[len(faces)//2]].mean(0)+origin
            else:
                # Explicit UV mapping and local texture; no fabricated sensor image.
                uv=UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.vertex)
                uv.Set((points[:,:2]/2.).tolist())
                mat=UsdShade.Material.Define(stage,base+'/rock_material')
                shader=UsdShade.Shader.Define(stage,base+'/rock_material/surface');shader.CreateIdAttr('UsdPreviewSurface')
                shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.85)
                tex=UsdShade.Shader.Define(stage,base+'/rock_material/texture');tex.CreateIdAttr('UsdUVTexture')
                texture=(directory/'materials/rock_albedo.png').resolve()
                tex.CreateInput('file',Sdf.ValueTypeNames.Asset).Set(str(texture))
                tex.CreateInput('wrapS',Sdf.ValueTypeNames.Token).Set('repeat');tex.CreateInput('wrapT',Sdf.ValueTypeNames.Token).Set('repeat')
                reader=UsdShade.Shader.Define(stage,base+'/rock_material/uv');reader.CreateIdAttr('UsdPrimvarReader_float2')
                reader.CreateInput('varname',Sdf.ValueTypeNames.Token).Set('st')
                tex.CreateInput('st',Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(),'result')
                shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).ConnectToSource(tex.ConnectableAPI(),'rgb')
                mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface');UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(mat)
        task=json.loads((args.root/'task_packs'/sid/'tasks/task_0000.json').read_text())
        ep=json.loads((args.root/'task_packs'/sid/'episodes.json').read_text())['episodes'][0]
        rig=json.loads((args.root/'task_packs'/sid/'stereo_rig.json').read_text())
        width,height=rig['resolution'];baseline=rig['baseline_m'];q=ep['start']['orientation_wxyz']
        pose=np.array(ep['start']['position_m'])+origin
        yaw=2*np.arctan2(q[3],q[0]);direction=np.array([np.cos(yaw),np.sin(yaw),0.]);side=np.array([-np.sin(yaw),np.cos(yaw),0.])
        body=UsdGeom.Xform.Define(stage,base+'/reset_body');body.AddTranslateOp().Set(Gf.Vec3d(*(pose-origin)))
        body.AddOrientOp().Set(Gf.Quatf(float(q[0]),Gf.Vec3f(*q[1:])))
        # Check resetting an environment-local object restores the agreed world pose.
        reset_world=np.array(UsdGeom.Xformable(body).ComputeLocalToWorldTransform(0).ExtractTranslation())
        rec={'scene_id':sid,'namespace':base,'origin':origin.tolist(),'reset_world':reset_world.tolist(),
             'reset_expected':pose.tolist(),'reset_transform_ok':bool(np.allclose(reset_world,pose)),
             'reset_orientation_wxyz':q,'camera_K':rig['cameras']['left']['K'],
             'collider_approximation':'none (static nonconvex triangle mesh)','images':[],
             'visual_sha256':hashlib.sha256((directory/'visual/mesh.npz').read_bytes()).hexdigest(),
             'collision_sha256':hashlib.sha256((directory/'collision/mesh.npz').read_bytes()).hexdigest(),
             'wall_probe':wall.tolist(),'free_probe':pose.tolist()}
        lamp=UsdLux.SphereLight.Define(stage,base+'/lamp');lamp.CreateIntensityAttr(15000);lamp.CreateRadiusAttr(.15)
        lamp.CreateExposureAttr(8)
        UsdGeom.Xformable(lamp).AddTranslateOp().Set(Gf.Vec3d(*(pose-origin+direction*.3)))
        for eye,sign in [('left',1),('right',-1)]:
            eye_pose=pose+sign*baseline/2*side;cam_path=base+'/'+eye
            cam=UsdGeom.Camera.Define(stage,cam_path);cam.CreateFocalLengthAttr(rig['cameras'][eye]['K'][0][0]/width*36)
            cam.CreateHorizontalApertureAttr(36);cam.CreateVerticalApertureAttr(36*height/width)
            cam.CreateClippingRangeAttr(Gf.Vec2f(.03,100.))
            local_eye=eye_pose-origin;matrix=Gf.Matrix4d().SetLookAt(Gf.Vec3d(*local_eye),Gf.Vec3d(*(local_eye+direction)),Gf.Vec3d(0,0,1)).GetInverse()
            UsdGeom.Xformable(cam).AddTransformOp().Set(matrix)
            product=rep.create.render_product(cam_path,(width,height));ann=rep.AnnotatorRegistry.get_annotator('rgb');ann.attach([product])
            annotators.append((ann,rec,eye,eye_pose.tolist()))
        records.append(rec)
    world.reset();report['reset_completed']=True;save()
    for _ in range(24):world.step(render=True)
    query=get_physx_scene_query_interface()
    for rec in records:
        for label,radius in [('free_probe',.55),('wall_probe',.12)]:
            hits=[]
            def callback(hit):hits.append(str(hit.collision));return True
            count=query.overlap_sphere(radius,tuple(rec[label]),callback,False)
            rec[label+'_hits']={'count':int(count),'colliders':hits}
        rec['collision_probes_ok']=(rec['free_probe_hits']['count']==0 and rec['wall_probe_hits']['count']>0
                                    and all(h.startswith(rec['namespace']+'/') for h in rec['wall_probe_hits']['colliders']))
    for ann,rec,eye,pose in annotators:
        data=ann.get_data();array=np.asarray(data)
        filename=rec['scene_id']+'_'+eye+'.png'
        valid=array.ndim==3 and array.shape[:2]==(height,width) and array.shape[2]>=3
        if valid:Image.fromarray(array[:,:,:3].astype(np.uint8)).save(args.output/filename)
        rec['images'].append({'eye':eye,'file':filename,'shape':list(array.shape),'rgb_valid':bool(valid),
                              'std':float(array[:,:,:3].std()) if valid else None,'pose_world':pose})
    report.update(scenes=records,baseline_m=baseline,resolution=[width,height],physics_steps=24,rendering_dt=1/60,
                  status='PASS' if all(r['reset_transform_ok'] and r['collision_probes_ok'] and all(im['rgb_valid'] and im['std']>1 for im in r['images']) for r in records) else 'FAIL',
                  seconds_before_shutdown=time.perf_counter()-start)
    stage.GetRootLayer().Export(str((args.output/'two_caves.usda').resolve()))
    save();print('CAVE_SMOKE_TESTS_FINISHED',report['status'],flush=True)
except Exception as exc:
    report.update(status='ERROR',error=repr(exc),traceback=traceback.format_exc());save();traceback.print_exc()
finally:
    app.close(wait_for_replicator=False)
