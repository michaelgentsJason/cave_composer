import argparse,json
from . import generate


def main():
    p=argparse.ArgumentParser(description='Generate a validated, metric-scale cave scene bundle.')
    p.add_argument('--config',required=True); p.add_argument('--seed',type=int,default=42); p.add_argument('--output')
    p.add_argument('--render',action='store_true'); p.add_argument('--blender'); p.add_argument('--save-blend',action='store_true')
    a=p.parse_args(); print(json.dumps(generate(a.config,a.seed,a.output,render=a.render,blender=a.blender,save_blend=a.save_blend),indent=2))


if __name__=='__main__': main()


def dataset_main():
    from .dataset import generate_dataset
    p=argparse.ArgumentParser(description='Generate, resume and review a deterministic cave dataset.')
    p.add_argument('--distribution',required=True)
    p.add_argument('--num-scenes',type=int,default=100)
    p.add_argument('--workers',type=int,default=1)
    p.add_argument('--output',default='outputs/dataset')
    p.add_argument('--render',action='store_true')
    p.add_argument('--blender')
    p.add_argument('--save-blend',action='store_true')
    p.add_argument('--resume',action='store_true')
    p.add_argument('--retry-failed',action='store_true')
    args=p.parse_args()
    manifest=generate_dataset(args.distribution,args.num_scenes,args.workers,args.output,
                              args.render,args.blender,args.save_blend,args.resume,args.retry_failed)
    print(f"Dataset: {manifest['valid']} VALID / {manifest['invalid']} failed / {manifest['pending']} pending")
    print(f"Quality report: {__import__('pathlib').Path(args.output).resolve()/'index.html'}")
    raise SystemExit(0 if manifest['invalid']==0 and manifest['pending']==0 else 2)
