import sys,argparse,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.materials import infer_image_prior,write_material

p=argparse.ArgumentParser(); p.add_argument('--image',required=True); p.add_argument('--output',required=True); a=p.parse_args()
folder=Path(a.output); folder.mkdir(parents=True,exist_ok=True)
prior=infer_image_prior(a.image,folder/'prior.json')
write_material(prior,folder/'materials')
print(json.dumps(prior,indent=2))
