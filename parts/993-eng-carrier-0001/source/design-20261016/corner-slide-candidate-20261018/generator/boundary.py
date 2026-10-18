"""Actual native boundary support records for the original exact Z=4 pad plane."""
import math

def require(value,message):
    if not value:raise ValueError(message)
def planar_curve(row):
    kind=row['curve_type']
    if kind.endswith('GeomAbs_Line'):return row['location_mm'][2]==4. and row['direction'][2]==0.
    if kind.endswith('GeomAbs_Circle')or kind.endswith('GeomAbs_Ellipse'):return row['location_mm'][2]==4. and row['axis_direction']in ([0.,0.,1.],[0.,0.,-1.])
    if kind.endswith('GeomAbs_BezierCurve')or kind.endswith('GeomAbs_BSplineCurve'):
        return bool(row['poles_mm'])and len(row['weights'])==len(row['poles_mm'])and all(len(p)==3 and p[2]==4. and all(math.isfinite(x)for x in p)for p in row['poles_mm'])and all(math.isfinite(w)and w>0 for w in row['weights'])
    return False

def validate(summary,records):
    require(summary.get('native_valid')is True and summary['counts']['solids']==0 and not summary['solids']and summary['material_solid_volume_mm3']==0,'Common has a Solid or an invalid/null native result')
    require(summary['highest_topological_dimension']in (None,0,1,2),'Common dimension is unresolved or volumetric')
    require(all(len(records[key])==summary['counts'][key]and [r['index']for r in records[key]]==list(range(len(records[key])))for key in ['faces','edges','vertices']),'Complete native contact topology records required')
    require(all(all(type(i)is int and 0<=i<len(records['edges'])for i in face['edge_indices'])for face in records['faces'])and all(all(type(i)is int and 0<=i<len(records['vertices'])for i in edge['vertex_indices'])for edge in records['edges']),'Native support incidence index outside complete map')
    for face in records['faces']:
        require(face['surface_type'].endswith('GeomAbs_Plane')and face['location_mm'][2]==4. and face['axis_direction']in ([0.,0.,1.],[0.,0.,-1.]),'Boundary face is not the exact original pad plane Z4')
    owned_edges={i for face in records['faces']for i in face['edge_indices']}
    for edge in records['edges']:
        if edge['index']not in owned_edges:require(planar_curve(edge),'Orphan boundary edge has unresolved/non-pad native support')
    owned_vertices={i for edge in records['edges']for i in edge['vertex_indices']}
    for vertex in records['vertices']:
        if vertex['index']not in owned_vertices:require(vertex['point_mm'][2]==4.,'Orphan contact vertex is not exactly at Z4')
    return dict(no_Solid_intersection=True,all_nonempty_contact_on_recorded_exact_pad_support_Z4=True,zero_positive_3D_material_intersection=True,new_geometric_epsilon_used=False)

def native_records(shape):
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve,BRepAdaptor_Surface
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
    from OCP.TopExp import TopExp,TopExp_Explorer
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS
    maps={}
    for name,kind in [('faces',TopAbs_FACE),('edges',TopAbs_EDGE),('vertices',TopAbs_VERTEX)]:
        value=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(shape,kind,value);maps[name]=value
    def children(parent,kind,index):
        explorer=TopExp_Explorer(parent,kind);ids=[]
        while explorer.More():ids.append(index.FindIndex(explorer.Current())-1);explorer.Next()
        require(all(i>=0 for i in ids),'Contact topology incidence unresolved');return sorted(set(ids))
    result=dict(faces=[],edges=[],vertices=[])
    for i in range(1,maps['faces'].Extent()+1):
        face=TopoDS.Face_s(maps['faces'].FindKey(i));surface=BRepAdaptor_Surface(face,True);row=dict(index=i-1,surface_type=str(surface.GetType()),native_tolerance_mm=BRep_Tool.Tolerance_s(face),edge_indices=children(face,TopAbs_EDGE,maps['edges']))
        if row['surface_type'].endswith('GeomAbs_Plane'):
            plane=surface.Plane();row.update(location_mm=list(plane.Location().Coord()),axis_direction=list(plane.Axis().Direction().Coord()))
        result['faces'].append(row)
    for i in range(1,maps['edges'].Extent()+1):
        edge=TopoDS.Edge_s(maps['edges'].FindKey(i));curve=BRepAdaptor_Curve(edge);kind=str(curve.GetType());row=dict(index=i-1,curve_type=kind,parameter_domain=[curve.FirstParameter(),curve.LastParameter()],native_tolerance_mm=BRep_Tool.Tolerance_s(edge),vertex_indices=children(edge,TopAbs_VERTEX,maps['vertices']))
        if kind.endswith('GeomAbs_Line'):
            line=curve.Line();row.update(location_mm=list(line.Location().Coord()),direction=list(line.Direction().Coord()))
        elif kind.endswith('GeomAbs_Circle')or kind.endswith('GeomAbs_Ellipse'):
            conic=curve.Circle()if kind.endswith('GeomAbs_Circle')else curve.Ellipse();row.update(location_mm=list(conic.Location().Coord()),axis_direction=list(conic.Axis().Direction().Coord()))
        elif kind.endswith('GeomAbs_BezierCurve')or kind.endswith('GeomAbs_BSplineCurve'):
            value=curve.Bezier()if kind.endswith('GeomAbs_BezierCurve')else curve.BSpline();row.update(degree=value.Degree(),poles_mm=[list(value.Pole(j).Coord())for j in range(1,value.NbPoles()+1)],weights=[value.Weight(j)for j in range(1,value.NbPoles()+1)])
            if kind.endswith('GeomAbs_BSplineCurve'):row.update(knots=[value.Knot(j)for j in range(1,value.NbKnots()+1)],multiplicities=[value.Multiplicity(j)for j in range(1,value.NbKnots()+1)])
        result['edges'].append(row)
    for i in range(1,maps['vertices'].Extent()+1):
        vertex=TopoDS.Vertex_s(maps['vertices'].FindKey(i));result['vertices'].append(dict(index=i-1,point_mm=list(BRep_Tool.Pnt_s(vertex).Coord()),native_tolerance_mm=BRep_Tool.Tolerance_s(vertex)))
    return result
