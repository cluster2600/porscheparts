"""Exact Catmull-Rom to composite bicubic B-spline conversion; no surface fitting."""
import numpy as np

# Columns act on previous, start, end, next interpolation positions.
TRANSFORM=np.array([[0,1,0,0],[-1/6,1,1/6,0],[0,1/6,1,-1/6],[0,0,1,0]],dtype=float)

def profile_bspline(profile):
    """Exact, geometrically closed composite cubic for a loft-end cap."""
    profile=np.asarray(profile,float)
    if profile.ndim!=2 or profile.shape[1]!=3 or len(profile)<3 or not np.isfinite(profile).all():
        raise ValueError('Expected at least three finite profile control points')
    count=len(profile);poles=np.empty((3*count+1,3))
    for i in range(count):
        neighbours=np.array([profile[(i+j-1)%count] for j in range(4)])
        poles[3*i:3*i+4]=TRANSFORM@neighbours
    return {'poles_mm':poles,'knots':np.arange(count+1,dtype=float),'multiplicities':[4]+[3]*(count-1)+[4],'degree':3}

def component_bspline(component):
    sections=np.asarray(component['sections_mm'],float);nu=len(sections)-1;nv=len(sections[0])-int(not component['closed_profile']);grid=np.empty((3*nu+1,3*nv+1,3))
    def point(i,j):
        i=min(max(i,0),len(sections)-1);j=j%len(sections[0]) if component['closed_profile'] else min(max(j,0),len(sections[0])-1)
        return sections[i,j]
    for i in range(nu):
        for j in range(nv):
            p=np.array([[point(i+a-1,j+b-1) for b in range(4)] for a in range(4)])
            patch=np.einsum('ai,ijc,bj->abc',TRANSFORM,p,TRANSFORM)
            grid[3*i:3*i+4,3*j:3*j+4]=patch
    start,end=component.get('v_range',[0,nv])
    if int(start)!=start or int(end)!=end or not 0<=start<end<=nv:
        raise ValueError('Expected an increasing whole-segment canonical v_range')
    start,end=int(start),int(end)
    if component['closed_profile'] and [start,end]!=[0,nv]:
        raise ValueError('Closed profiles cannot be cropped without a new boundary contract')
    grid=grid[:,3*start:3*end+1]
    return {'poles_mm':grid,'u_knots':np.arange(nu+1,dtype=float),'v_knots':np.arange(start,end+1,dtype=float),'u_multiplicities':[4]+[3]*(nu-1)+[4],'v_multiplicities':[4]+[3]*(end-start-1)+[4],'degree_u':3,'degree_v':3,'closed_profile':component['closed_profile']}

def occ_surface(component):
    from OCP.gp import gp_Pnt
    from OCP.TColgp import TColgp_Array2OfPnt
    from OCP.TColStd import TColStd_Array1OfReal,TColStd_Array1OfInteger
    from OCP.Geom import Geom_BSplineSurface
    d=component_bspline(component);poles=d['poles_mm'];array=TColgp_Array2OfPnt(1,len(poles),1,len(poles[0]))
    for i in range(len(poles)):
        for j in range(len(poles[0])):array.SetValue(i+1,j+1,gp_Pnt(*poles[i,j]))
    def real(values):
        a=TColStd_Array1OfReal(1,len(values))
        for i,x in enumerate(values):a.SetValue(i+1,float(x))
        return a
    def integer(values):
        a=TColStd_Array1OfInteger(1,len(values))
        for i,x in enumerate(values):a.SetValue(i+1,int(x))
        return a
    surface=Geom_BSplineSurface(array,real(d['u_knots']),real(d['v_knots']),integer(d['u_multiplicities']),integer(d['v_multiplicities']),3,3,False,False)
    # The joined Bezier representation declares C0, although uniform Catmull-Rom
    # has matching first derivatives. Remove exactly redundant knots so OCCT can
    # recognise C1 regularity when constructing the physical normal offsets.
    for i in range(surface.NbUKnots()-1,1,-1):
        if not surface.RemoveUKnot(i,2,1e-9):
            raise ValueError('Canonical U junction did not preserve C1 continuity')
    for i in range(surface.NbVKnots()-1,1,-1):
        if not surface.RemoveVKnot(i,2,1e-9):
            raise ValueError('Canonical V junction did not preserve C1 continuity')
    if component['closed_profile']:
        if not surface.IsVClosed():
            raise ValueError('Canonical closed profile did not close in BRep geometry')
        surface.SetVPeriodic()
    return surface

def occ_face(component):
    from build123d import Face
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    if component['type']=='planar_profile_cap':
        return occ_cap_face(component)
    surface=occ_surface(component)
    return Face(BRepBuilderAPI_MakeFace(surface,1e-7).Face())

def occ_cap_face(component):
    """Build a planar face with the exact closed Catmull-Rom loft-end boundary."""
    from build123d import Edge,Face,Wire
    from OCP.gp import gp_Pnt
    from OCP.TColgp import TColgp_Array1OfPnt
    from OCP.TColStd import TColStd_Array1OfReal,TColStd_Array1OfInteger
    from OCP.Geom import Geom_BSplineCurve
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    d=profile_bspline(component['profile_mm']);poles=TColgp_Array1OfPnt(1,len(d['poles_mm']))
    for i,p in enumerate(d['poles_mm']):poles.SetValue(i+1,gp_Pnt(*p))
    knots=TColStd_Array1OfReal(1,len(d['knots']));mults=TColStd_Array1OfInteger(1,len(d['multiplicities']))
    for i,x in enumerate(d['knots']):knots.SetValue(i+1,float(x))
    for i,x in enumerate(d['multiplicities']):mults.SetValue(i+1,int(x))
    curve=Geom_BSplineCurve(poles,knots,mults,3,False)
    curve.SetPeriodic()
    face=Face(Wire([Edge(BRepBuilderAPI_MakeEdge(curve).Edge())]))
    direction=np.asarray(component['normal_direction'],float)
    if direction.shape!=(3,) or not np.isfinite(direction).all() or np.linalg.norm(direction)<1e-12:
        raise ValueError('Expected a finite, nonzero cap normal direction')
    if np.dot(np.asarray(tuple(face.normal_at())),direction)<0:face.wrapped.Reverse()
    return face
