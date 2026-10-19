"""Restore original short, tooth-free horizontal interfaces after native Clipper quantization."""
import numpy as np
import pyclipr
import shapely
from shapely.geometry import Polygon,LineString


def restore_short_horizontal_interfaces(material,domain,cycle_length,interfaces=None):
    """Only move an existing horizontal boundary back to its original source Z.

    Native generateSliceGeometry retains the source edge when it fits in one
    tooth cycle. Its final Clipper has a default fixed scale. An interface whose
    source Z falls just above the encoded lattice can otherwise lose all contact.
    This is an explicit coordinate restoration, not an expanded contact test.
    """
    scale=float(pyclipr.Clipper().scaleFactor);half_step=.5/scale
    if material.is_empty:
        return material,dict(method='no_material_to_restore',native_clipper_scale_per_mm=scale,
            maximum_allowed_displacement_mm=half_step,native_tooth_cycle_length_mm=cycle_length,
            restored_edges=[],maximum_displacement_mm=0.,source_geometry_unchanged=True)
    candidates=[]
    polygons=[domain] if domain.geom_type=='Polygon' else list(domain.geoms)
    for polygon in shapely.orient_polygons(polygons):
        upper=[];lower=[]
        if interfaces is not None:
            upper=[LineString(path) for path in interfaces['upper']];lower=[LineString(path) for path in interfaces['lower']]
        else:
            for ring in [polygon.exterior,*polygon.interiors]:
                p=np.asarray(ring.coords)
                for a,b in zip(p[:-1],p[1:]):
                    if b[0]<a[0]:upper.append(LineString([a,b]))
                    elif b[0]>a[0]:lower.append(LineString([a,b]))
        for kind,segments in [('upper',upper),('lower',lower)]:
            merged=shapely.line_merge(shapely.union_all(segments))
            paths=[merged] if merged.geom_type=='LineString' else list(getattr(merged,'geoms',[]))
            for path in paths:
                p=np.asarray(path.coords)
                if path.length>0 and path.length<=cycle_length and np.ptp(p[:,1])==0:
                    z=float(p[0,1]);encoded=float(np.round(z*scale)/scale)
                    if z!=encoded and abs(z-encoded)<=half_step:
                        candidates.append(dict(kind=kind,source_z_mm=z,native_z_mm=encoded,
                            abscissa_interval_mm=[float(p[:,0].min()),float(p[:,0].max())],source_interface_length_mm=path.length))
    used=[]
    def ring(points):
        p=np.asarray(points).copy();original=p.copy()
        for candidate in candidates:
            left,right=candidate['abscissa_interval_mm'];z=candidate['native_z_mm']
            for i in range(len(p)-1):
                a,b=original[i],original[i+1]
                if a[1]==b[1]==z and min(max(a[0],b[0]),right)>max(min(a[0],b[0]),left):
                    # Restore the actual existing edge, retaining its X encoding.
                    p[i,1]=candidate['source_z_mm'];p[i+1,1]=candidate['source_z_mm']
                    used.append(dict(candidate,source_boundary_edge_2d_mm=[a.tolist(),b.tolist()],
                        displacement_mm=abs(candidate['source_z_mm']-z)))
        p[-1]=p[0]
        return p
    parts=[material] if material.geom_type=='Polygon' else list(material.geoms)
    result=shapely.union_all([Polygon(ring(p.exterior.coords),[ring(r.coords) for r in p.interiors]) for p in parts])
    if result.is_empty or not result.is_valid:raise ValueError('Restoring a native short interface produced invalid material')
    return result,dict(method='restore_existing_horizontal_short_tooth_free_interface_to_source_Z',
        native_clipper_scale_per_mm=scale,maximum_allowed_displacement_mm=half_step,
        native_tooth_cycle_length_mm=cycle_length,restored_edges=used,
        maximum_displacement_mm=max([r['displacement_mm'] for r in used],default=0.),
        source_geometry_unchanged=True)
