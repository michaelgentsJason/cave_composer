import argparse
from cave_composer.dataset import generate_dataset

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--distribution',required=True); p.add_argument('--num-scenes',type=int,default=100); p.add_argument('--workers',type=int,default=1); p.add_argument('--output',default='outputs/dataset'); p.add_argument('--render',action='store_true'); p.add_argument('--blender')
    a=p.parse_args(); m=generate_dataset(a.distribution,a.num_scenes,a.workers,a.output,a.render,a.blender)
    print(f"Dataset: {m['valid']} VALID / {m['invalid']} INVALID")
    raise SystemExit(0 if m['invalid']==0 else 2)
