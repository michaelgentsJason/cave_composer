"""Opt-in, seeded structural modifiers of the positive-inside void field.

These are controllable geometric primitives, not a fitted speleogenesis model.
The caller must apply its protected-passage union AFTER every solid modifier.
"""
import hashlib
import numpy as np


KINDS = {'ceiling_drop', 'floor_rise', 'wall_intrusion', 'overhang', 'side_cavity', 'rockfall'}


def sample_morphology(spec, seed, difficulty):
    """Named batch prior; every sampled value remains in the saved config."""
    rng=np.random.default_rng(np.random.SeedSequence([int(seed),947]))
    scale={'easy':.5,'medium':.8,'hard':1.}[difficulty]
    width,height=spec['corridor']['width'],spec['corridor']['height']
    kinds=['side_cavity','overhang','ceiling_drop','rockfall']
    if difficulty=='hard':kinds+=['floor_rise','wall_intrusion']
    locations=np.linspace(.2,.82,len(kinds))+rng.uniform(-.025,.025,len(kinds))
    features=[]
    for i,(kind,at) in enumerate(zip(kinds,locations)):
        f={'id':f'{kind}_{i}','kind':kind,'at':float(at),'length':float(rng.uniform(2.5,4.5)),
           'span':float(min(width,height)*rng.uniform(.35,.7)),
           'depth':float(min(width,height)*rng.uniform(.25,.5)),
           'strength':scale,'side':int(rng.choice([-1,1]))}
        if kind=='rockfall':f['count']=int(rng.integers(3,8))
        features.append(f)
    return {'cross_section':{'amplitude':float(rng.uniform(.2,.34)*scale),
                            'eccentricity':float(rng.uniform(.12,.22)*scale),
                            'length_scale':float(rng.uniform(6,12))},
            'roughness':{'contrast':float(rng.uniform(.6,.95)*scale),'length_scale':float(rng.uniform(6,14))},
            'features':features}


def validate_morphology(config, number, route_ids):
    if not isinstance(config, dict) or set(config)-{'cross_section', 'roughness', 'features'}:
        raise ValueError('Unknown morphology parameters')
    ranges = {'cross_section': {'amplitude':(0,.4), 'eccentricity':(0,.3), 'length_scale':(2,40)},
              'roughness': {'contrast':(0,1), 'length_scale':(2,40)}}
    for group, limits in ranges.items():
        item=config.get(group,{})
        if not isinstance(item,dict) or set(item)-set(limits):
            raise ValueError('Unknown morphology.'+group+' parameters')
        for key,value in item.items(): number(value,'morphology.'+group+'.'+key,*limits[key])
    features=config.get('features',[])
    if not isinstance(features,list) or len(features)>40:
        raise ValueError('morphology.features must be a list of at most 40 features')
    ids=set()
    for f in features:
        if not isinstance(f,dict) or set(f)-{'id','kind','route','at','length','span','depth','strength','side','count'}:
            raise ValueError('Unknown structural feature parameters')
        if not isinstance(f.get('id'),str) or not f['id'] or f['id'] in ids:
            raise ValueError('Structural features require unique nonempty IDs')
        ids.add(f['id'])
        if f.get('kind') not in KINDS or f.get('route','main') not in route_ids:
            raise ValueError('Unknown feature kind or route')
        for key,limits in {'at':(.08,.92),'length':(1,12),'span':(.4,10),'depth':(.2,4)}.items():
            number(f.get(key),'feature.'+key,*limits)
        number(f.get('strength',1),'feature.strength',0,1)
        if isinstance(f.get('side',1),bool) or f.get('side',1) not in [-1,1]:
            raise ValueError('feature.side must be -1 or 1')
        count=f.get('count',5); number(count,'feature.count',1,12)
        if int(count)!=count:raise ValueError('feature.count must be an integer')
        if 'count' in f and f['kind']!='rockfall':raise ValueError('count applies only to rockfall')


class Morphology:
    def __init__(self, config, field, seed):
        self.config=config
        self.section=config.get('cross_section',{})
        self.roughness=config.get('roughness',{})
        self.phase=np.random.default_rng(np.random.SeedSequence([int(seed),271])).uniform(-np.pi,np.pi,8)
        self.field=field
        self.primitives=[]
        self.records=[]
        self.end_s=np.concatenate([np.full(len(r['points'])-1,r['s'][-1]) for r in field.routes])
        route_offsets={};offset=0
        for r in field.routes:
            route_offsets[r['id']]=(r,offset);offset+=len(r['points'])-1
        for feature in config.get('features',[]):
            strength=feature.get('strength',1)
            if strength==0:continue
            r,offset=route_offsets[feature.get('route','main')]
            distance=feature['at']*r['s'][-1]
            j=min(len(r['points'])-2,max(0,int(np.searchsorted(r['s'],distance)-1)))
            idx=offset+j
            center=r['points'][j]+field.tangent[idx]*(distance-r['s'][j])
            basis=np.column_stack([field.tangent[idx],field.side[idx],field.up[idx]])
            half=feature['length']/2;span=feature['span']/2;depth=feature['depth']*strength
            w,h=field.w[idx],field.h[idx];side=feature.get('side',1)
            kind=feature['kind'];group=[]
            def add(local,radii,solid=True,power=2.4):
                primitive={'center':(center+basis@np.array(local)).tolist(),'radii':list(radii),
                           'basis':basis.tolist(),'solid':solid,'power':power,'feature_id':feature['id']}
                self.primitives.append(primitive);group.append(primitive)
            if kind=='ceiling_drop':add([0,0,h],[half,span,depth])
            elif kind=='floor_rise':add([0,0,-h],[half,span,depth])
            elif kind=='wall_intrusion':add([0,side*w,0],[half,depth,span])
            elif kind=='overhang':add([0,side*w,h*.3],[half,depth,span],power=3.5)
            elif kind=='side_cavity':
                # Overlap the source wall so the pocket has an actual mouth.
                add([0,side*w*.83,.15*h],[half,depth,span],False,2.2)
            elif kind=='rockfall':
                token=int.from_bytes(hashlib.sha256(feature['id'].encode()).digest()[:4],'little')
                rng=np.random.default_rng(np.random.SeedSequence([int(seed),733,token]))
                for _ in range(feature.get('count',5)):
                    size=rng.uniform(.55,1,3)*[min(half,.9),min(span,.85),depth]
                    add([rng.uniform(-half,half),side*rng.uniform(.25,.85)*min(w,span*2),
                         -h+size[2]*rng.uniform(.2,.65)],size,True,1.65)
            self.records.append({'spec':feature,'position':center.tolist(),'primitives':group})

    def section_coordinates(self,u,v,idx,tclip):
        cfg=self.section;amplitude=cfg.get('amplitude',0);ecc=cfg.get('eccentricity',0)
        if amplitude==0 and ecc==0:return u,v,1.
        f=self.field;s=f.s[idx]+tclip-f.lengths[idx]/2
        # Leave terminal neighborhoods intact for deterministic portal export.
        fade=np.clip(np.minimum(s,self.end_s[idx]-s)/3,0,1)
        phase=s/cfg.get('length_scale',8)*2*np.pi
        uc=u-ecc*f.w[idx]*np.sin(phase*.63+self.phase[0])*fade
        vc=v-ecc*f.h[idx]*np.sin(phase*.87+self.phase[1])*fade
        angle=amplitude*np.sin(phase*.43+self.phase[2])
        cu=uc*np.cos(angle)+vc*np.sin(angle);cv=-uc*np.sin(angle)+vc*np.cos(angle)
        theta=np.arctan2(cv/f.h[idx],cu/f.w[idx])
        lobes=.65*np.cos(3*theta+phase*.7+self.phase[3])+.35*np.cos(5*theta-phase*.4+self.phase[4])
        return cu,cv,1+amplitude*fade*lobes

    def roughness_multiplier(self,points):
        contrast=self.roughness.get('contrast',0)
        if contrast==0:return 1.
        # A continuous world-space envelope: no nearest-route discontinuities at junctions.
        q=np.asarray(points)/self.roughness.get('length_scale',8)
        phase=q@np.array([.81,.47,.35])*2*np.pi+self.phase[5]
        band=np.tanh(2*(np.sin(phase)+.35*np.sin(phase*.43+self.phase[6])))
        return 1+contrast*band

    def apply_features(self,points,base,solid):
        for p in self.primitives:
            if p['solid']!=solid:continue
            radii=np.array(p['radii'])
            local=(points-np.array(p['center']))@np.array(p['basis'])
            rho=np.sum(np.abs(local/radii)**p['power'],axis=1)**(1/p['power'])
            level=(1-rho)*radii.min()
            base=np.minimum(base,-level) if solid else np.maximum(base,level)
        return base

    def extra_bounds(self):
        bounds=[]
        for p in self.primitives:
            extent=np.abs(np.array(p['basis']))@np.array(p['radii'])
            bounds.extend([np.array(p['center'])-extent-2,np.array(p['center'])+extent+2])
        return bounds

    def report(self):
        return {'version':1,'config':self.config,'features':self.records,
                'solid_primitive_count':sum(p['solid'] for p in self.primitives),
                'void_primitive_count':sum(not p['solid'] for p in self.primitives),
                'protection':('All modifiers precede the final protected-passage union; intrusive features may be clipped.'
                              if self.field.protect_passage else 'EXPERIMENTAL: protected-passage union disabled.'),
                'scope':'Parameterized structural variation; not a fitted real-cave distribution or erosion simulation.'}
