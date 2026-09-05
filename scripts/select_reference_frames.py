"""Read-only sampling and inspection sheet for a CAVERS RGB sequence collection."""
from pathlib import Path
import argparse,json
import numpy as np
from scipy.ndimage import laplace
from PIL import Image,ImageDraw,ImageFont

p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
records=[]
for seq in sorted(root.glob('rec_handheld_*/RS_COLOR/data')):
    paths=sorted(seq.glob('*.png'),key=lambda p:int(p.stem.rsplit('_',1)[-1]))
    if not paths:continue
    candidates=[]
    for idx in np.linspace(0,len(paths)-1,min(45,len(paths)),dtype=int):
        with Image.open(paths[idx]) as im:
            im.thumbnail((384,216));rgb=np.asarray(im,dtype=float)/255
        gray=rgb.mean(2);dark=float((gray<.06).mean());clip=float((gray>.94).mean())
        score=float(np.var(laplace(gray)))*(1-dark)*max(.05,1-clip*5)
        candidates.append({'path':str(paths[idx]),'sequence':seq.parents[1].name,'score':score,'dark_fraction':dark,'clipped_fraction':clip,'mean_rgb':rgb.mean((0,1)).tolist()})
    # Choose four separated temporal regions to avoid four nearly identical frames.
    for group in np.array_split(np.arange(len(candidates)),4):
        records.append(max([candidates[i] for i in group],key=lambda r:r['score']))
cols=4;w=480;h=300
sheet=Image.new('RGB',(cols*w,((len(records)+cols-1)//cols)*h),(17,27,36));draw=ImageDraw.Draw(sheet)
for i,r in enumerate(records):
    with Image.open(r['path']) as im:
        im=im.convert('RGB');im.thumbnail((w,260));x=(i%cols)*w;y=(i//cols)*h;sheet.paste(im,(x,y))
    draw.text((x+8,y+264),f"{i:02d}  {Path(r['path']).parents[2].name} / {Path(r['path']).name}",fill=(231,237,243))
    draw.text((x+8,y+280),f"dark {r['dark_fraction']:.2f} | clipped {r['clipped_fraction']:.2f}",fill=(167,185,195))
sheet.save(out/'cavers_contact.jpg',quality=92)
(out/'candidate_frames.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(len(records),'frames reviewed in',out/'cavers_contact.jpg')
