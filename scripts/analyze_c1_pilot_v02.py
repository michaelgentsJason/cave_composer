"""Raw paired pilot summaries and editable quantitative/geometry figures."""
from pathlib import Path
import argparse,json,sys,csv,platform
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import trimesh
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cave_composer.delivery_validation import sha256
ROOT=Path('outputs/c1_pilot_v02');FIG=Path('overleaf/figures/generated/c1_v02')
OUTPUT=Path('outputs/c1_analysis_new');TABLE=OUTPUT/'generator.tex'
COLORS={'full':'#168c9e','no_protection':'#b64282','restricted':'#677885'}
LABELS={'full':'Composer','no_protection':'No protection','restricted':'Restricted'}

def save(fig,name):
    for ext in ['svg','pdf','png']:fig.savefig(FIG/(name+'.'+ext),dpi=300,bbox_inches='tight',facecolor='white')
    plt.close(fig)

def load_records():
    rechecks=json.loads((ROOT/'delivery_recheck.json').read_text())['results'];records=[]
    for check in rechecks:
        r=json.loads((ROOT/check['original_result']).read_text());r['final_delivered_check']=check.get('delivered_check')
        r['accepted']=check['accepted'];r['recheck_seconds']=check['seconds'];records.append(r)
    return records

def write_table(groups):
    """The manuscript table uses the same corrected denominator as the plots."""
    lines=[r'\begin{table}[t]',r'\centering',
        r'\caption{Descriptive generation pilot, after declared OBJ seam recheck. Costs include failed attempts and both delivery checks. PLUME comparison was blocked.}',
        r'\label{tab:generator}',r'\small',r'\begin{tabular}{lccc}',r'\toprule',
        r'Condition & Normal & Stress & s / accepted \\',r'\midrule']
    for arm,label in LABELS.items():
        normal=next(g for g in groups if g['arm']==arm and g['stratum']=='normal')
        stress=next(g for g in groups if g['arm']==arm and g['stratum']=='stress')
        accepted=normal['final_passes']+stress['final_passes']
        cost=(normal['pilot_total_seconds']+stress['pilot_total_seconds'])/accepted if accepted else None
        value=f'{cost:.2f}' if cost is not None else r'\missing'
        lines.append(f"{label} & {normal['final_passes']}/{normal['requested']} & {stress['final_passes']}/{stress['requested']} & {value} "+r'\\')
    lines.extend([r'PLUME & \missing & \missing & \missing \\',r'\bottomrule',r'\end{tabular}',r'\end{table}'])
    target=TABLE
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return target

def main():
    FIG.mkdir(parents=True,exist_ok=True);records=load_records();summaries=[];rows=[]
    for r in records:
        request=r['request'];stages={s['name']:s.get('seconds',0) for s in r.get('run',{}).get('stages',[])}
        reason=(None if r['accepted'] else r.get('planning',{}).get('reason') or r.get('exception',{}).get('message') or r.get('reason') or 'delivered_mesh_rejected')
        rows.append({'base_id':request['base_id'],'arm':request['arm'],'stratum':request['stratum'],'attempts':1,'retries':0,
                     'accepted':r['accepted'],'reason':reason,'generation_s':r.get('generation_wall_seconds'),
                     'geometry_s':stages.get('geometry'),'legacy_validation_s':stages.get('validation'),
                     'independent_search_and_checks_s':stages.get('independent_navigation'),'material_export_s':stages.get('material_and_export'),
                     'inspection_and_total_s':r['wall_seconds_including_measurement']+r['recheck_seconds'],
                     'path_length_m':r.get('planning',{}).get('length_metres'),
                     'delivered_clearance_m':min(v['certificate']['continuous_clearance_lower_bound'] for v in r['final_delivered_check']['meshes'].values()) if r.get('final_delivered_check') else None})
    for stratum in ['normal','stress']:
        for arm in COLORS:
            selected=[(r,row) for r,row in zip(records,rows) if r['request']['stratum']==stratum and r['request']['arm']==arm]
            accepted=sum(row['accepted'] for r,row in selected);total=sum(row['inspection_and_total_s'] for r,row in selected)
            summaries.append({'stratum':stratum,'arm':arm,'requested':len(selected),'attempts':len(selected),'retries':0,
                'first_geometric_passes':accepted,'final_passes':accepted,'pilot_total_seconds':total,
                'seconds_per_accepted_cave':total/accepted if accepted else None,
                'failures':[row['reason'] for _,row in selected if not row['accepted']],
                'requested_semantic_branch_cases':sum(r.get('geometry',{}).get('requested',{}).get('branches',0)>0 for r,_ in selected),
                'accepted_semantic_branch_cases':sum(r.get('geometry',{}).get('requested',{}).get('branches',0)>0 and row['accepted'] for r,row in selected),
                'requested_semantic_chamber_cases':sum(r.get('geometry',{}).get('requested',{}).get('chambers',0)>0 for r,_ in selected)})
    report={'scope':'Six paired base requests, 18 single attempts; descriptive pilot, no significance or generalization claim.',
            'source_preregistration_sha256':sha256(ROOT/'preregistration.json'),'hardware':platform.platform(),
            'timing_scope':'Shared workstation wall time includes initial OBJ import check, corrected seam-incidence check, and geometry measurement. Not isolated throughput.',
            'first_pass_definition':'One geometry per request/arm, checked with corrected import adapter; initial UV-seam representation failures remain in results/*.json.',
            'coverage_scope':'Recorded semantic structures and local final-mesh section proxies; not exact free-space branch/loop certification.',
            'rows':rows,'groups':summaries,'external_plume_paired_result':None,'policy_results':None}
    (OUTPUT/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    table=write_table(summaries)
    with (OUTPUT/'results.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    plt.rcParams.update({'font.family':'Arial','font.size':8,'axes.titlesize':9,'axes.labelsize':8,
        'svg.fonttype':'none','pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(7.15,2.15),layout='constrained')
    for j,arm in enumerate(COLORS):
        groups=[g for g in summaries if g['arm']==arm]
        x=np.arange(2)+(j-1)*.24
        axes[0].bar(x,[g['final_passes']/g['requested'] for g in groups],width=.22,color=COLORS[arm],label=LABELS[arm])
        for xx,g in zip(x,groups):axes[0].text(xx,g['final_passes']/g['requested']+.025,f"{g['final_passes']}/{g['requested']}",ha='center',fontsize=7)
        normal=[r for r in records if r['request']['arm']==arm and r['request']['stratum']=='normal']
        axes[1].scatter([r['geometry']['requested']['width_m'] for r in normal],
                        [r['geometry']['meshes']['visual']['summary']['width_mean_m'] for r in normal],s=22,color=COLORS[arm],marker=['o','x','s'][j])
        axes[2].bar(x,[g['seconds_per_accepted_cave'] or 0 for g in groups],width=.22,color=COLORS[arm])
        for xx,g in zip(x,groups):
            if g['seconds_per_accepted_cave'] is None:axes[2].text(xx,.6,'n/a',ha='center',fontsize=7)
    axes[0].set(xticks=[0,1],xticklabels=['Normal','Stress'],ylim=(0,1.2),ylabel='Accepted / requested',title='(a) Independent task yield')
    axes[1].plot([4.8,6.5],[4.8,6.5],color='.7',ls='--',lw=.8)
    axes[1].set(xlabel='Nominal width (m)',ylabel='Mean section span (m)',title='(b) Spans include junctions')
    axes[2].set(xticks=[0,1],xticklabels=['Normal','Stress'],ylabel='Pilot seconds / accepted cave',title='(c) Cost includes failures')
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=3,frameon=False)
    save(fig,'pilot_quantitative')
    # Fixed stress request, both actual meshes. No failed search is drawn as a path.
    pair=[next(r for r in records if r['request']['base_id']=='request_04' and r['request']['arm']==arm) for arm in ['full','no_protection']]
    fig,axes=plt.subplots(2,2,figsize=(7.15,4.1),layout='constrained')
    nav=json.loads((ROOT/pair[0]['request']['scene']/'navigation/centerline.json').read_text())['routes'][0]
    center=np.array(nav['points']);selected=round((len(center)-1)*.55)
    p=center[selected];t=center[selected+1]-center[selected-1];t/=np.linalg.norm(t)
    side=np.cross([0,0,1],t);side/=np.linalg.norm(side);up=np.cross(t,side);basis=np.column_stack([side,up])
    for j,r in enumerate(pair):
        folder=ROOT/r['request']['scene'];mesh=trimesh.load(folder/'visual/cave_visual.obj',force='mesh',process=True)
        cloud=mesh.triangles_center;axes[0,j].scatter(cloud[::2,0],cloud[::2,1],s=.2,c='.65',rasterized=True)
        axes[0,j].plot(center[:,0],center[:,1],c='#168c9e',lw=1,label='Construction')
        planned=r.get('planning',{});s=np.array(planned['start']);g=np.array(planned['goal'])
        axes[0,j].scatter([s[0]],[s[1]],s=22,c='#168c9e' if planned['status']=='PASS' else '#a65454',marker='o');axes[0,j].scatter([g[0]],[g[1]],s=28,c='#b64282' if planned['status']=='PASS' else '#a65454',marker='D')
        if planned.get('points'):
            path=np.array(planned['points']);axes[0,j].plot(path[:,0],path[:,1],c='#b64282',ls='--',lw=1.2,label='Searched')
        axes[0,j].text(.02,.03,'A* accepted' if planned['status']=='PASS' else 'A*: S/G outside conservative free set',transform=axes[0,j].transAxes,fontsize=7,color='#273444')
        axes[0,j].set(aspect='equal',title=LABELS[r['request']['arm']],xlabel='X (m)',ylabel='Y (m)')
        section=mesh.section(plane_origin=p,plane_normal=t);curves=section.discrete if section else []
        for curve in curves:
            xy=(curve-p)@basis;axes[1,j].plot(*xy.T,c=COLORS[r['request']['arm']],lw=1)
        axes[1,j].add_patch(plt.Circle((0,0),.55,fill=False,color='#273444',ls='--',lw=1))
        if not curves:axes[1,j].text(.02,.9,'No cavity contour on this plane',transform=axes[1,j].transAxes,fontsize=7)
        axes[1,j].set(aspect='equal',xlim=(-2,2),ylim=(-2,2),xlabel='Lateral (m)',ylabel='Vertical (m)',title='Local section at 55% route distance')
    save(fig,'protection_actual_geometry')
    inputs=[ROOT/'preregistration.json',ROOT/'delivery_recheck.json',OUTPUT/'summary.json',*sorted((ROOT/'results').glob('*.json'))]
    if (ROOT/'endpoint_audit.json').exists():inputs.append(ROOT/'endpoint_audit.json')
    provenance={'script':str(Path(__file__)),'script_sha256':sha256(__file__),
        'inputs':{str(p):sha256(p) for p in inputs},'command':'.venv/Scripts/python.exe scripts/analyze_c1_pilot_v02.py',
        'figures':{'pilot_quantitative':'C1.6 descriptive paired pilot','protection_actual_geometry':'C1.6 and C1.7 actual mesh section and independent search status'},
        'style_skill':'figures4papers/scientific-figure-making','images':'Only actual geometry and raw pilot records; no policy trajectory or generative imagery.'}
    provenance['generated_table']={'path':str(table),'sha256':sha256(table),'source':'summary.json groups, exact-position seam recheck'}
    (FIG/'provenance.json').write_text(json.dumps(provenance,indent=2))
    print(json.dumps(summaries,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT,help='Recorded pilot inputs (read-only)')
    parser.add_argument('--output',type=Path,default=OUTPUT,help='Fresh analysis directory; refuses overwrite')
    args=parser.parse_args();ROOT=args.root;OUTPUT=args.output
    if OUTPUT.resolve()==ROOT.resolve() or OUTPUT.resolve().is_relative_to(ROOT.resolve()):
        parser.error('Analysis output must be outside the recorded pilot')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    FIG=OUTPUT/'figures';TABLE=OUTPUT/'generator.tex'
    main()
