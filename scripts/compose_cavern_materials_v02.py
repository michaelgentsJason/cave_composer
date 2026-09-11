"""Figures4papers-style editable compositions of recorded renders; no AI imagery."""
from pathlib import Path
import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.delivery_validation import sha256
OUT=Path('overleaf/figures/generated/c1_v02');R=Path('outputs/c1_pilot_v02/renders')
def save(fig,name):
    for ext in ['pdf','svg','png']:fig.savefig(OUT/(name+'.'+ext),dpi=300,bbox_inches='tight',facecolor='white')
    plt.close(fig)
def main():
    plt.rcParams.update({'font.family':'Arial','font.size':8,'axes.titlesize':9,'svg.fonttype':'none','pdf.fonttype':42})
    inputs=[];fig,axes=plt.subplots(2,3,figsize=(7.15,3.15),layout='constrained')
    for j,base in enumerate(['request_00','request_01','request_02']):
        record=json.loads(Path(f'outputs/c1_pilot_v02/results/{j*3:02d}.json').read_text());summary=record['geometry']['meshes']['visual']['summary']
        for i,mode in enumerate(['clay','textured']):
            p=R/f'{base}_overview_{mode}.png';inputs.append(p);axes[i,j].imshow(Image.open(p));axes[i,j].axis('off')
            if i==0:axes[i,j].set_title(['Winding','Branching','Chamber + slope'][j])
            if i==1:axes[i,j].text(.5,-.05,f"Section span {summary['width_mean_m']:.2f} × {summary['height_mean_m']:.2f} m",ha='center',transform=axes[i,j].transAxes,fontsize=7.5)
    for i,label in enumerate(['Clay','Textured']):
        axes[i,0].text(-.035,.5,label,rotation=90,ha='right',va='center',transform=axes[i,0].transAxes,fontsize=8)
    save(fig,'fixed_cave_cases')
    fig,axes=plt.subplots(2,3,figsize=(7.15,3.1),layout='constrained')
    for j,base in enumerate(['request_00','request_01','request_02']):
        for i,mode in enumerate(['clay','textured']):
            p=R/f'{base}_interior_{mode}.png';inputs.append(p);axes[i,j].imshow(Image.open(p));axes[i,j].axis('off')
            if i==0:axes[i,j].set_title(base.replace('_',' '))
    save(fig,'fixed_cave_interiors')
    runtime=Path('outputs/cavern_round_v02/isaac_runtime/final_rig_and_portals')
    receipt=json.loads((runtime/'runtime_receipt.json').read_text());inputs.append(runtime/'runtime_receipt.json')
    if receipt['status']=='PASS':
        fig,axes=plt.subplots(2,2,figsize=(7.15,4.1),layout='constrained')
        for i,s in enumerate(receipt['scenes']):
            for j,im in enumerate(s['images']):
                p=runtime/im['file'];inputs.append(p);axes[i,j].imshow(Image.open(p));axes[i,j].axis('off');axes[i,j].set_title(f"{s['scene_id']} · {im['eye'].capitalize()} RGB")
        save(fig,'isaac_stereo_actual')
    # Preparation illustrations only: reused existing exports, no final scan read.
    fig,axes=plt.subplots(1,2,figsize=(7.15,2.8),layout='constrained')
    for ax,source in zip(axes,['zhaoqing','catacombs']):
        p=Path('exports/metashape_crops_v01')/(source+'_split_overview.png');inputs.append(p)
        ax.imshow(Image.open(p));ax.axis('off');ax.set_title(source.capitalize()+' · prior crop preparation')
    save(fig,'real_source_preparation')
    inputs.extend([R/'provenance.json',Path('exports/metashape_crops_v01/manifest.json')])
    (OUT/'composition_provenance.json').write_text(json.dumps({'command':'.venv/Scripts/python.exe scripts/compose_cavern_materials_v02.py',
        'script_sha256':sha256(__file__),'inputs':{str(p):sha256(p) for p in inputs},
        'fixed_cave_cases':'C1: actual matched-scale Blender inspection cutaways, full source roofs remain intact. Section means include junctions/chambers.',
        'fixed_cave_interiors':'C1: identical lens/lighting/route-fraction camera convention and flat normals; real triangle geometry in clay/textured modes.',
        'isaac_stereo_actual':'C2: actual Isaac Sim 5.0 frames at fixed episode resets; not a policy or underwater-physics result.',
        'real_source_preparation':'C3: old Metashape crop preparation images, metric scale and untouched eligibility unresolved; not a newly selected final test schedule.',
        'source_geometry_for_generator_tuning':False},indent=2))
if __name__=='__main__':main()
