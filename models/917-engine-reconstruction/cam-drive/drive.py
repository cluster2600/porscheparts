"""Hypothetical positive 2:1 cam drive; dimensions are not measured interfaces."""
import math

MODULE = 1.5
PRESSURE = math.radians(20)
BACKLASH = .4
TEETH = (27, 48, 54)
WIDTH = 12


def involute(angle):
    return math.tan(angle)-angle


def profile(teeth, samples=20):
    if teeth not in TEETH or samples < 8:
        raise ValueError('Unsupported gear or insufficient flank sampling')
    pitch=MODULE*teeth/2; base=pitch*math.cos(PRESSURE)
    root=pitch-1.25*MODULE; tip=pitch+MODULE
    half=math.pi/(2*teeth)-BACKLASH/(4*pitch)
    def flank(r):
        return half+involute(PRESSURE)-involute(math.acos(min(1,base/r)))
    lower=max(root,base); points=[]
    for tooth in range(teeth):
        centre=math.tau*tooth/teeth
        radii=([root] if root<lower else [])+[lower+(tip-lower)*i/samples for i in range(samples+1)]
        for r in radii:
            angle=centre-flank(r);points.append([r*math.cos(angle),r*math.sin(angle)])
        for i in range(1,9):
            angle=centre-flank(tip)+2*flank(tip)*i/8
            points.append([tip*math.cos(angle),tip*math.sin(angle)])
        for r in reversed(radii[:-1]):
            angle=centre+flank(r);points.append([r*math.cos(angle),r*math.sin(angle)])
        a=centre+flank(root);b=centre+math.tau/teeth-flank(root)
        for i in range(1,8):
            angle=a+(b-a)*i/8;points.append([root*math.cos(angle),root*math.sin(angle)])
    return points


def web_tip_radius(root,rib):
    # Keep rounded rib tips inside the root circle, including their beam radius.
    return root-rib-.3


def contact_ratio(a,b):
    r1=MODULE*a/2;r2=MODULE*b/2
    path=sum(math.sqrt((r+MODULE)**2-(r*math.cos(PRESSURE))**2) for r in (r1,r2))
    return (path-(r1+r2)*math.sin(PRESSURE))/(math.pi*MODULE*math.cos(PRESSURE))


def train(target,idlers):
    if idlers % 2 != 1:
        raise ValueError('Odd idler count required for positive cam rotation')
    counts=[TEETH[0]]+[TEETH[1]]*idlers+[TEETH[2]]
    lengths=[MODULE*(a+b)/2 for a,b in zip(counts,counts[1:])]
    total=sum(lengths); distance=math.hypot(*target)
    signs=[1 if i<len(lengths)//2 else -1 for i in range(len(lengths))]
    imbalance=sum(s*l for s,l in zip(signs,lengths))
    if not abs(imbalance)<distance<total:
        return None
    q=math.acos(math.sqrt((distance**2-imbalance**2)/(total**2-imbalance**2)))
    direction=math.atan2(target[1],target[0])-math.atan2(imbalance*math.sin(q),total*math.cos(q))
    centres=[[0.,0.]]
    for length,sign in zip(lengths,signs):
        centres.append([centres[-1][0]+length*math.cos(direction+sign*q),
                        centres[-1][1]+length*math.sin(direction+sign*q)])
    phases=[0.]
    for i,(a,b) in enumerate(zip(centres,centres[1:])):
        angle=math.atan2(b[1]-a[1],b[0]-a[0]);za=counts[i];zb=counts[i+1]
        phases.append((zb*(angle+math.pi)-math.pi+za*(angle-phases[-1]))/zb)
    clearance=min(math.dist(centres[i],centres[j])-MODULE*(counts[i]+counts[j])/2-2*MODULE
                  for i in range(len(counts)) for j in range(i+2,len(counts)))
    if clearance<=0:
        return None
    return {'centres_yz_mm':centres,'teeth':counts,'phase_rad':phases,
            'speed_ratio_to_crank':[(-1)**i*counts[0]/n for i,n in enumerate(counts)],
            'nonadjacent_tip_envelope_gap_mm':clearance,
            'contact_ratios':[contact_ratio(a,b) for a,b in zip(counts,counts[1:])]}


def layout(cam_centres):
    rows=[]; search=[]
    for name,target in sorted(cam_centres.items()):
        # Solve in the positive bank, then reflect the layout; tooth phases are recomputed.
        bank=1 if target[0]>0 else -1
        candidates=[]
        for count in (1,3,5,7):
            candidate=train([abs(target[0]),target[1]],count)
            search.append({'cam':name,'idlers':count,'accepted':candidate is not None})
            if candidate is not None:candidates.append((count,candidate))
        if not candidates:raise ValueError('No reachable nonintersecting cam train')
        count,candidate=min(candidates,key=lambda p:p[0])
        centres=[[bank*y,z] for y,z in candidate['centres_yz_mm']]
        phases=[0.]
        for i,(a,b) in enumerate(zip(centres,centres[1:])):
            angle=math.atan2(b[1]-a[1],b[0]-a[0]);za=candidate['teeth'][i];zb=candidate['teeth'][i+1]
            phases.append((zb*(angle+math.pi)-math.pi+za*(angle-phases[-1]))/zb)
        candidate.update({'cam':name,'bank':bank,'centres_yz_mm':centres,'phase_rad':phases,
                          'plane_x_mm':400 if name.endswith('intake') else 424,'idler_count':count})
        rows.append(candidate)
    # The two branches share one crank gear in each axial plane.
    for a,b in ((rows[0],rows[2]),(rows[1],rows[3])):
        if a['plane_x_mm']!=b['plane_x_mm']:raise ValueError('Wrong paired axial planes')
        for i in range(1,len(a['teeth'])):
            for j in range(1,len(b['teeth'])):
                gap=math.dist(a['centres_yz_mm'][i],b['centres_yz_mm'][j])-MODULE*(a['teeth'][i]+b['teeth'][j])/2-2*MODULE
                if gap<=0:raise ValueError('Opposite bank tip envelopes intersect')
    return {'module_mm':MODULE,'pressure_angle_deg':20,'total_circular_backlash_mm':BACKLASH,
            'face_width_mm':WIDTH,'search':search,'trains':rows,'manufacturing_authorized':False,
            'engine_start_authorized':False,'material_qualified':False,'dynamic_timing_validated':False}
