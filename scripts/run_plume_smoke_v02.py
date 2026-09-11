"""Use pinned upstream code; external interface smoke is NOT matched yield."""
import argparse,json,sys,random
from pathlib import Path
from types import SimpleNamespace

def main(mode,attempt):
    root=Path(__file__).resolve().parents[1]/'outputs/c1_pilot_v02/external/plume'
    upstream=root/'upstream';sys.path.insert(0,str(upstream/'src'))
    import config
    values={key:SimpleNamespace(value=value.value) for key,value in config.Config.__members__.items()}
    # Separate value holders avoid Enum True/False aliases changing unrelated flags.
    overrides={'PLUME_DIR':str(root/(mode+'_'+attempt)).replace('\\','/'),'NB_NODES':10,'GENERATION_SIZE':(40,40,20),
        'MAX_RADIUS_NODE':3.0,'OPEN_VISUALIZATION':False,'GENERATE_GRAPH_IMAGE':False,'ANIMATE':False,
        'GENERATE_MESH':True,'BAKE_TEXTURE':False,'HIGH_POLY':False,'SLICE_MESH':False,'DEBUG':False,
        'GPU_ACCELERATION':False,'MESH_FORMAT':'obj'}
    for k,v in overrides.items():values[k]=SimpleNamespace(value=v)
    config.Config=SimpleNamespace(**values)
    dest=root/(mode+'_'+attempt);dest.mkdir(exist_ok=True)
    (dest/'settings.json').write_text(json.dumps({'overrides':overrides,'seed':88010,
        'scope':'Native graph or supported external graph smoke; fixed upstream skin aperture is not matched to Composer.'},indent=2))
    random.seed(88010)
    import numpy as np
    np.random.seed(88010)
    from graph import Graph
    graph=Graph('smoke',0,2)
    if mode=='native':
        from algorithm import Algorithm
        graph.add_node(node_id_p=0,coordinates_p=[0.,0.,0.],radius_p=random.uniform(1.,3.),active_p=True)
        Algorithm(graph_p=graph,loop_closure_probability_p=10).algorithm('gaussian_perlin')
        for node in graph.nodes.values():node.set_edges(list(dict.fromkeys(e for e in node.get_edges() if e is not None)))
    else:
        nav=json.loads((root.parents[1]/'scenes/request_00/full/navigation/centerline.json').read_text())['routes'][0]
        pts=np.asarray(nav['points']);idx=list(range(0,len(pts),8))
        if idx[-1]!=len(pts)-1:idx.append(len(pts)-1)
        for i,j in enumerate(idx):graph.add_node(i,parent_p=i-1 if i else None,coordinates_p=pts[j].tolist(),radius_p=2.6)
    # Same None/duplicate removal as upstream Generator.post_processing_graph.
    for node in graph.nodes.values():node.set_edges(list(dict.fromkeys(e for e in node.get_edges() if e is not None)))
    graph.create_adjency_matrix(graph.nb_nodes);graph.save_graph()
    if mode=='external_graph':
        from blender import MeshGeneration
        MeshGeneration('smoke',0,str(dest/'data/smoke/0').replace('\\','/'))
    print('PLUME_SMOKE_COMPLETE',mode,flush=True)

if __name__=='__main__':
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['native','external_graph'],required=True)
    parser.add_argument('--attempt',default='postprocessed')
    args=parser.parse_args(argv);main(args.mode,args.attempt)
