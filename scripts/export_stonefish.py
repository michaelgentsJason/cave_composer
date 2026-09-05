import sys,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.stonefish import export_stonefish
p=argparse.ArgumentParser(); p.add_argument('scenes',nargs='+'); p.add_argument('--depth',type=float,default=20); p.add_argument('--jerlov',type=float,default=.2); a=p.parse_args()
for scene in a.scenes: print(export_stonefish(scene,a.depth,a.jerlov))
