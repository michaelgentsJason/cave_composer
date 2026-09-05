import runpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
runpy.run_module('cave_composer.blender_render',run_name='__main__')
