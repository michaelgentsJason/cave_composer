"""Read-only material inventory. Never load, rewrite, or export source geometry."""
from pathlib import Path
import argparse,json,struct
from PIL import Image


def inspect(path):
    path=Path(path); result={'path':str(path.resolve()),'format':path.suffix.lower(),'bytes':path.stat().st_size}
    if path.suffix.lower()=='.mtl':
        lines=path.read_text(errors='replace').splitlines()
        maps=[l.split(maxsplit=1) for l in lines if l.strip().startswith(('map_','bump '))]
        result['maps']=maps
        result['classification']='likely baked photogrammetry atlas' if any('photo' in l.lower() for l in lines) else 'undetermined; inspect UVs/images'
        result['has_explicit_roughness_map']=any(k in ('map_Pr','map_roughness') for k,v in maps)
        result['has_explicit_normal_map']=any(k in ('map_Bump','bump','norm') for k,v in maps)
    elif path.suffix.lower() in ('.glb','.gltf'):
        if path.suffix.lower()=='.glb':
            with path.open('rb') as f:
                magic,version,size=struct.unpack('<III',f.read(12)); n,kind=struct.unpack('<II',f.read(8)); data=json.loads(f.read(n))
        else: data=json.loads(path.read_text())
        result.update(materials=data.get('materials',[]),images=data.get('images',[]),textures=data.get('textures',[]))
        result['classification']='PBR container; atlas versus tileable cannot be proven from container alone'
    elif path.suffix.lower() in ('.jpg','.jpeg','.png'):
        with Image.open(path) as im: result.update(dimensions=im.size,mode=im.mode)
        result['classification']='image; photographic lighting and texture semantics require visual inspection'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); p.add_argument('--output',required=True); a=p.parse_args()
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps([inspect(x) for x in a.paths],indent=2),encoding='utf-8')
