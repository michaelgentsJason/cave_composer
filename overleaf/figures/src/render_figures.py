"""Editable architectural drafts using figures4papers scientific-figure-making.

Style reference: D:/Desktop/作图/figures4papers/scientific-figure-making/
SKILL.md and references/design-theory.md, api.md. All geometry is schematic.
No policy results or simulator screenshots are synthesized.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Polygon,FancyArrowPatch,Rectangle

OUT=Path(__file__).resolve().parents[1]/'generated'
PALETTE={'blue':'#0F4D92','teal':'#42949E','violet':'#9A4D8E','rock':'#C9B297','gray':'#767676','red':'#B64342'}

def apply_publication_style():
    plt.rcParams.update({'font.family':['Arial','DejaVu Sans'],'font.size':8,'axes.spines.top':False,
        'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42,'ps.fonttype':42,
        'legend.frameon':False,'text.color':'#273444','svg.hashsalt':'cavern-v01'})

def canvas(height=3.25):
    fig=plt.figure(figsize=(7.16,height),facecolor='white');ax=fig.add_axes([.025,.04,.95,.92]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off');return fig,ax

def label(ax,x,y,text,weight='normal',size=8,color='#273444',ha='center'):
    return ax.text(x,y,text,ha=ha,va='center',fontsize=size,fontweight=weight,color=color,linespacing=1.35)

def arrow(ax,a,b,color=None,style='solid',connection='arc3,rad=0'):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=8,lw=.8,
        linestyle=style,color=color or PALETTE['gray'],connectionstyle=connection))

def box(ax,x,y,w,h,text,style='solid',color='#d0d5da',fill='white',size=8):
    ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,facecolor=fill,edgecolor=color,lw=.75,ls=style))
    label(ax,x,y,text,size=size)

def skeleton(ax,x,y,s=.1,kind='branch'):
    p=np.array([[-.8,-.3],[-.5,.2],[-.1,.15],[.15,-.2],[.6,.2],[.85,.45]])
    ax.plot(x+p[:,0]*s,y+p[:,1]*s,color=PALETTE['teal'],lw=1.5)
    if kind!='winding':
        q=np.array([[-.5,.2],[-.35,.65],[.25,.8],[.6,.2]]) if kind=='loop' else np.array([[-.1,.15],[.15,.7],[.6,.8]])
        ax.plot(x+q[:,0]*s,y+q[:,1]*s,color=PALETTE['teal'],lw=1.5)

def save(fig,name):
    OUT.mkdir(parents=True,exist_ok=True)
    for ext in ['svg','pdf','png']:
        metadata={'Creator':'CAVERN diagram renderer','Author':''} if ext=='pdf' else None
        if ext=='svg':metadata={'Creator':'CAVERN diagram renderer','Date':None}
        fig.savefig(OUT/(name+'.'+ext),dpi=300,facecolor='white',metadata=metadata)
    plt.close(fig)

def method():
    fig,ax=canvas(3.8)
    for x,t in [(0.12,'(a) Conditions + structure'),(.40,'(b) Protected geometry'),(.69,'(c) Task verification'),(.92,'(d) Delivery')]:label(ax,x,.96,t,'bold',8)
    label(ax,.12,.81,'Config / seed\nRobot radius + margin')
    skeleton(ax,.12,.67,.1,'loop');label(ax,.12,.53,'Routes + chambers')
    arrow(ax,(.23,.68),(.28,.68))
    # Irregular closed section with a deliberately protected inner region.
    t=np.linspace(0,2*np.pi,110);radius=1+.14*np.sin(3*t)+.12*np.cos(7*t)
    wall=np.column_stack([.4+.103*radius*np.cos(t),.70+.16*radius*np.sin(t)])
    ax.add_patch(Polygon(wall,facecolor=PALETTE['rock'],edgecolor='#8a7762',lw=.7))
    inner=np.column_stack([.4+.080*radius*np.cos(t),.70+.126*radius*np.sin(t)])
    ax.add_patch(Polygon(inner,facecolor='white',edgecolor='none'))
    ax.add_patch(Circle((.4,.7),.046,facecolor='#DDF2F3',edgecolor=PALETTE['teal'],lw=.6))
    ax.add_patch(Circle((.4,.7),.017,facecolor='#6b7784',edgecolor='none'))
    ax.add_patch(Circle((.4,.7),.027,facecolor='none',edgecolor='#53606c',lw=.6,ls='dashed'))
    label(ax,.4,.49,'Irregular sections +\nlocal solids + roughness')
    label(ax,.4,.39,'Visual / collision meshes')
    label(ax,.4,.335,'Seeded surface materials',size=7.5)
    # Exact inputs; construction is not connected to search as a solution.
    arrow(ax,(.50,.78),(.585,.78));label(ax,.55,.75,'Occupancy',size=7.5)
    box(ax,.69,.78,.20,.105,'Independent 3D A*')
    label(ax,.69,.88,'S/G + radius')
    arrow(ax,(.69,.845),(.69,.837))
    arrow(ax,(.69,.72),(.69,.61),color=PALETTE['violet'],style='dashed')
    box(ax,.69,.55,.20,.115,'Both final meshes\nInside + clearance')
    arrow(ax,(.50,.40),(.59,.51));label(ax,.55,.365,'Meshes',size=7.5)
    # Endpoint sampling is shown separately above the main geometry row.
    label(ax,.12,.905,'Sample S/G coordinates',size=7.5)
    ax.plot([.235,.64],[.905,.905],color='#aaaaaa',lw=.65)
    arrow(ax,(.64,.905),(.65,.84))
    arrow(ax,(.80,.55),(.85,.55));label(ax,.86,.64,'Accept',size=7.5)
    box(ax,.925,.55,.14,.16,'Textured assets\n+ task packs',size=7.5)
    arrow(ax,(.69,.487),(.69,.38),color=PALETTE['red'],style='dashed');label(ax,.72,.33,'Failures retained',size=7.5,color=PALETTE['red'])
    # One compact mechanism and a separate modification branch.
    ax.plot([0,1],[.255,.255],color='#d9dde2',lw=.6)
    label(ax,.23,.205,'Protected generation; checked polylines','bold',8)
    label(ax,.23,.12,r'$\rho_g = r+m+2.1\Delta_c$'+'\n'+r'$\widehat d_{\min}-h/2-\epsilon>r+m$',size=9)
    label(ax,.23,.035,'Solid teal: construction   Dashed violet: searched path',size=7)
    arrow(ax,(.93,.46),(.93,.21))
    box(ax,.835,.175,.30,.075,'Optional portals / export / props',size=7.5)
    arrow(ax,(.83,.135),(.83,.10))
    label(ax,.82,.06,'Check changed surfaces; separate records',size=7.5)
    save(fig,'cave_composer_method')

def framework():
    fig,ax=canvas(3.35)
    xs=[.085,.28,.475,.685,.91]
    for x,t in zip(xs,['Generated tasks','Offline assets','Interactive platform','Different caves','Baseline runs']):label(ax,x,.94,t,'bold')
    box(ax,.085,.73,.15,.18,'Cave\nComposer',color=PALETTE['blue'])
    box(ax,.28,.73,.16,.18,'Blender\nprepare / inspect')
    box(ax,.475,.73,.17,.18,'Isaac Lab\nIsaac Sim',style='dashed')
    for a,b in zip(xs[:3],xs[1:4]):arrow(ax,(a+.085,.73),(b-.09,.73))
    for y,k in [(.84,'winding'),(.73,'branch'),(.62,'loop')]:skeleton(ax,.685,y,.06,k)
    box(ax,.91,.83,.16,.10,'FlashSAC',style='dashed')
    box(ax,.91,.64,.16,.10,'Recurrent PPO',style='dashed')
    arrow(ax,(.765,.76),(.824,.83));arrow(ax,(.765,.70),(.824,.64))
    label(ax,.91,.49,'One shared policy\nper baseline run',size=7.5)
    arrow(ax,(.91,.435),(.91,.37));box(ax,.91,.31,.17,.11,'Freeze checkpoint',style='dashed',size=7.5)
    label(ax,.47,.50,'Actor profile: pending\nMaps / paths: privileged',size=7.5)
    ax.plot([0,.77],[.41,.41],color='#d9dde2',lw=.6)
    box(ax,.70,.30,.20,.105,'Planned generated tests\nFull-exit tasks',style='dashed',size=7.5)
    box(ax,.70,.105,.20,.105,'Candidate real local tasks\nEligibility pending',style='dashed',size=7.5)
    arrow(ax,(.82,.31),(.804,.31));arrow(ax,(.9,.25),(.81,.105))
    label(ax,.21,.33,'Real-source acquisition / reconstruction','bold',8)
    box(ax,.08,.20,.15,.10,'AC1 / Insight9',size=7.5)
    box(ax,.265,.20,.155,.10,'Metashape',size=8)
    box(ax,.46,.20,.16,.13,'Source-role\naudit',color=PALETTE['blue'])
    arrow(ax,(.158,.2),(.182,.2));arrow(ax,(.346,.2),(.376,.2));arrow(ax,(.545,.18),(.594,.105))
    label(ax,.29,.075,'Downloaded scans enter the same audit.\nPrior/development use excludes untouched OOD.',size=7.5)
    label(ax,.60,.015,'Dashed: execution evidence pending. Final OOD has no training feedback.',size=7)
    save(fig,'cavern_framework')

if __name__=='__main__':
    apply_publication_style();method();framework()
    (OUT/'figure_provenance.json').write_text(json.dumps({'skill':'figures4papers/scientific-figure-making',
        'outputs':'editable SVG, vector PDF, 300 dpi PNG','data_kind':'architectural schematics',
        'simulator_screenshots_used':False,'policy_results_used':False},indent=2))
