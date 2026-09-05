from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def topology_preview(routes,graph,visibility,directory,name):
    directory=Path(directory)
    with plt.rc_context({'font.family':'DejaVu Sans','figure.facecolor':'#101c28','axes.facecolor':'#101c28','text.color':'#e3eaf1','axes.labelcolor':'#c3d0de','xtick.color':'#98abba','ytick.color':'#98abba','axes.edgecolor':'#4a5c6b','grid.color':'#344653'}):
        fig=plt.figure(figsize=(14,8),layout='constrained')
        ax=fig.add_subplot(121)
        for i,r in enumerate(routes):
            p=r['points']; ax.plot(*p[:,:2].T,color='#54d6c7' if i==0 else '#f2b45e',lw=2.5,label='Main route' if i==0 else r['id'])
        p=routes[0]['points']; ax.scatter(*p[6,:2],c='#8be58b',s=70,label='Spawn'); ax.scatter(*p[-7,:2],c='#fa8a89',s=70,label='Goal')
        for nid in graph['junctions']:
            q=graph['nodes'][nid]['position']; ax.scatter(*q[:2],c='#f8dc72',s=80,marker='D')
        for ch in graph['chambers']: ax.scatter(*ch['position'][:2],c='#b7a0ee',s=190,marker='o',alpha=0.6)
        for r in routes:
            for e in r['events']:
                if e['type']=='turn':
                    q=r['points'][(e['start_index']+e['end_index'])//2]; ax.annotate(f" {e['angle_degrees']:g}°",q[:2],xytext=(5,8),textcoords='offset points',fontsize=9)
        ax.set_aspect('equal',adjustable='datalim'); ax.margins(0.14); ax.grid(alpha=0.35)
        ax.set(xlabel='X / m',ylabel='Y / m',title='Navigation structure · plan view'); ax.legend(loc='upper left',facecolor='#182938',labelcolor='#e3eaf1',fontsize=8)
        ax2=fig.add_subplot(222)
        for r in routes: ax2.plot(r['s'],r['points'][:,2],lw=2)
        ax2.set(xlabel='Route arc length / m',ylabel='Elevation / m',title='Vertical profile'); ax2.grid(alpha=0.4)
        ax3=fig.add_subplot(224)
        ax3.plot(visibility['s_metres'],visibility['forward_ray_metres'],color='#54d6c7',label='Forward tangent ray')
        ax3.plot(visibility['s_metres'],visibility['visible_route_arc_metres'],color='#f2b45e',label='Visible route arc (90° FOV)')
        ax3.set(xlabel='Main route arc length / m',ylabel='Distance / m',title='Geometric look-ahead · no water model'); ax3.grid(alpha=0.4); ax3.legend(facecolor='#182938',labelcolor='#e3eaf1',fontsize=8)
        fig.suptitle(name.replace('_',' ').upper(),fontsize=17,fontweight='bold')
        fig.savefig(directory/'topology.png',dpi=140); plt.close(fig)
