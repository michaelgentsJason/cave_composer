"""Use two visually selected CAVERS rock-only ROIs; all source files read-only."""
from pathlib import Path
import sys,argparse,json,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image,ImageDraw
from cave_composer.materials import infer_image_prior,write_material
from cave_composer.appearance import restyle

p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--source-scene',required=True);p.add_argument('--output',required=True);p.add_argument('--blender');a=p.parse_args()
root=Path(a.dataset); out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
selections=[('rec_handheld_4',2575,[340,140,700,430]),('rec_handheld_5',1929,[630,200,660,400])]
priors=[]
for seq,idx,roi in selections:
    source=root/seq/'RS_COLOR/data'/f'RS_COLOR_{idx}.png'
    prior=infer_image_prior(source,out/f'{seq}_{idx}_prior.json',roi)
    prior['dataset']='CAVERS';prior['selection']='rock-only flowstone ROI, visually reviewed; lamp cores and black void excluded'
    priors.append(prior)
palette=np.mean([p['palette'] for p in priors],axis=0).tolist()
material={'style':'cavers_flowstone','seed':100,'palette':palette,'roughness':0.87,'detail_anisotropy':1.8,
          'prior_source':'CAVERS rec_handheld_4 frame 2575 + rec_handheld_5 frame 1929; selected rock ROIs'}
(out/'cavers_style.json').write_text(json.dumps(material,indent=2))
(out/'experiment.json').write_text(json.dumps({'priors':priors,'material':material,'anisotropy':'1.8 is a visually chosen flowstone-style parameter, not calibrated physical inference','roughness':'default; not estimated','original_files_unchanged':all(hashlib.sha256(Path(p['prior_source']).read_bytes()).hexdigest()==p['source_sha256'] for p in priors),'limitations':['Lighting remains in observed colors','Camera noise is not copied as surface texture','No metric normal/roughness recovered','Keep CAVERS out of strict untouched OOD if its appearance informs training']},indent=2))
scene=restyle(a.source_scene,material,out/'cave_b_cavers',a.blender)
images=[Path(a.source_scene)/'previews/inside_01.png',scene/'previews/inside_01.png']
sheet=Image.new('RGB',(1600,550),(16,28,40));draw=ImageDraw.Draw(sheet)
for i,path in enumerate(images):
    im=Image.open(path).convert('RGB');im.thumbnail((800,500));sheet.paste(im,(i*800,40))
    draw.text((i*800+20,14),['Procedural limestone baseline','CAVERS rock-palette prior / IDENTICAL geometry'][i],fill=(231,237,244))
sheet.save(out/'appearance_comparison.jpg',quality=93)
print(scene)
