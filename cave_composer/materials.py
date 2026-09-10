"""Portable dry-rock albedo and optional image-to-palette prior, separate from geometry."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

PALETTES = {
    "limestone": [[0.19,0.18,0.155],[0.39,0.365,0.30],[0.63,0.60,0.51]],
    "sandstone": [[0.20,0.135,0.08],[0.46,0.31,0.19],[0.72,0.56,0.37]],
    "basalt": [[0.08,0.085,0.09],[0.22,0.235,0.24],[0.43,0.44,0.43]],
}


def write_material(spec, directory):
    if 'texture_library' in spec:
        from .reference_material import write_reference_material
        return write_reference_material(spec,directory)
    directory = Path(directory); directory.mkdir(parents=True,exist_ok=True)
    palette = np.array(spec.get("palette", PALETTES.get(spec["style"],PALETTES["limestone"])))
    rng = np.random.default_rng(int(spec["seed"]))
    n = 1024
    y,x = np.meshgrid(np.arange(n)/n*2*np.pi,np.arange(n)/n*2*np.pi,indexing="ij")
    value = np.zeros((n,n))
    # Periodic filtered random fields avoid the visible plaid of separable sine products.
    for sigma,amp in [(70,0.07),(27,0.06),(9,0.045),(3,0.025),(0.6,0.015)]:
        anisotropy=spec.get('detail_anisotropy',1.0)
        band=gaussian_filter(rng.normal(size=(n,n)),(sigma*anisotropy,sigma),mode='wrap')
        value += amp*(band-band.mean())/max(band.std(),1e-8)
    value = np.clip(0.5+value,0,1)
    low = np.minimum(value*2,1)[...,None]
    high = np.maximum(value*2-1,0)[...,None]
    rgb = (palette[0]*(1-low)+palette[1]*low)*(1-high)+palette[2]*high
    Image.fromarray(np.uint8(np.clip(rgb,0,1)*255)).save(directory/"rock_albedo.png")
    (directory/"material.json").write_text(json.dumps({**spec,"palette":palette.tolist(),"water_baked":False,"texture_period_metres":spec.get('texture_period_metres',4),"method":"periodic multiscale procedural albedo; box/planar projection"},indent=2),encoding="utf-8")
    return palette


def infer_image_prior(path, output, roi=None):
    path=Path(path)
    original=Image.open(path).convert("RGB")
    if roi is not None:
        if len(roi)!=4 or min(roi)<0 or roi[2]<=0 or roi[3]<=0 or roi[0]+roi[2]>original.width or roi[1]+roi[3]>original.height:
            raise ValueError('ROI must be x, y, width, height inside the image')
        im=original.crop((roi[0],roi[1],roi[0]+roi[2],roi[1]+roi[3]))
    else: im=original.copy()
    im.thumbnail((512,512))
    a=np.asarray(im,dtype=float)/255
    valid=a[(a.mean(2)>0.06)&(a.mean(2)<0.95)]
    if len(valid)<100: raise ValueError("Insufficient nonblack/nonwhite texture pixels")
    # Quantiles summarize observed RGB only; illumination/roughness are not identifiable.
    palette=np.quantile(valid,[0.15,0.5,0.85],axis=0)
    gray=a.mean(2)
    result={"schema_version":1,"style":"reference_palette","palette":palette.tolist(),
            "seed":100,"roughness":0.87,"prior_source":str(path.resolve()),
            "source_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "image_dimensions":original.size,"roi_xywh":roi,"high_frequency_proxy":float(np.abs(np.diff(gray,axis=0)).mean()),
            "roughness_inferred":False,"normal_inferred":False,
            "limitations":["RGB palette includes capture illumination and atlas padding", "No geometry or UV atlas transfer", "Roughness default; not measured", "Using held-out OOD scans for priors is appearance leakage"]}
    Path(output).write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result
