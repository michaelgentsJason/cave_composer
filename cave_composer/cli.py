import argparse,json
from . import generate


def main():
    p=argparse.ArgumentParser(description='Generate a validated, metric-scale cave scene bundle.')
    p.add_argument('--config',required=True); p.add_argument('--seed',type=int,default=42); p.add_argument('--output')
    p.add_argument('--render',action='store_true'); p.add_argument('--blender'); p.add_argument('--save-blend',action='store_true')
    a=p.parse_args(); print(json.dumps(generate(a.config,a.seed,a.output,render=a.render,blender=a.blender,save_blend=a.save_blend),indent=2))


if __name__=='__main__': main()
