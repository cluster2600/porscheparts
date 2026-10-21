def entities(raw,kind):
    mapping=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(raw,kind,mapping)
    return [mapping.FindKey(i) for i in range(1,mapping.Extent()+1)]


def bbox(raw):
    box=Bnd_Box();BRepBndLib.Add_s(raw,box,False)
    return None if box.IsVoid() else list(box.Get())


def inspect_native(raw):
    if raw is None or raw.IsNull():
        return dict(native_null=True,counts=dict(solids=0,faces=0,edges=0,vertices=0),
                    native_topologically_empty=True,bounds_mm=None)
    parts={name:entities(raw,kind) for name,kind in [('solids',TopAbs_SOLID),('faces',TopAbs_FACE),('edges',TopAbs_EDGE),('vertices',TopAbs_VERTEX)]}
    result=dict(native_null=False,native_type=str(raw.ShapeType()),native_valid=BRepCheck_Analyzer(raw).IsValid(),
                counts={key:len(value) for key,value in parts.items()},bounds_mm=bbox(raw),solids=[],tolerances_mm={})
    for solid in parts['solids']:
        result['solids'].append(dict(native_valid=BRepCheck_Analyzer(solid).IsValid(),bounds_mm=bbox(solid)))
    result['volume_integrals_not_called_here']=True
    casts={'faces':TopoDS.Face_s,'edges':TopoDS.Edge_s,'vertices':TopoDS.Vertex_s}
    for kind,cast in casts.items():
        tolerances=[BRep_Tool.Tolerance_s(cast(item)) for item in parts[kind]]
        result['tolerances_mm'][kind]=dict(count=len(tolerances),minimum=min(tolerances) if tolerances else None,
                                        maximum=max(tolerances) if tolerances else None)
    areas=[];types={}
    for face in parts['faces']:
        face=TopoDS.Face_s(face);props=GProp_GProps();BRepGProp.SurfaceProperties_s(face,props)
        areas.append(props.Mass());key=str(BRepAdaptor_Surface(face,True).GetType());types[key]=types.get(key,0)+1
    result['surface_area_sum_mm2']=sum(areas)
    result['surface_types']=types
    result['degenerated_edge_count']=sum(BRep_Tool.Degenerated_s(TopoDS.Edge_s(edge)) for edge in parts['edges'])
    result['native_topologically_empty']=all(not values for values in parts.values())
    result['highest_topological_dimension']=next((dim for name,dim in [('solids',3),('faces',2),('edges',1),('vertices',0)] if parts[name]),None)
    return result

