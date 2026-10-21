"""Union real triangular downward prisms without assuming a single-valued height field."""
import numpy as np
import manifold3d
import trimesh


def projected_prism_union(surface, lower_z=0., upper_offset=0.):
    faces=np.array([[0,1,2],[3,5,4],[0,3,4],[0,4,1],
                    [1,4,5],[1,5,2],[2,5,3],[2,3,0]],dtype=np.uint64)
    prisms=[]
    expected_sum=0.
    for triangle in surface.triangles:
        top=np.array(triangle,dtype=np.float64,copy=True)
        top[:,2]+=upper_offset
        determinant=np.cross(top[1,:2]-top[0,:2],top[2,:2]-top[0,:2])
        if determinant==0:
            raise ValueError('A vertical triangle cannot define a downward support prism')
        if determinant<0: top=top[[0,2,1]]
        if np.any(top[:,2]<=lower_z):
            raise ValueError('Support prism must lie above its lower plane')
        lower=top.copy();lower[:,2]=lower_z
        mesh=manifold3d.Mesh64(vert_properties=np.vstack([top,lower]),tri_verts=faces.copy())
        prism=manifold3d.Manifold(mesh)
        if prism.status()!=manifold3d.Error.NoError:
            raise ValueError('Native Manifold rejected a triangular prism')
        expected_sum+=abs(determinant)/2*(top[:,2].mean()-lower_z)
        prisms.append(prism)
    union=manifold3d.Manifold.batch_boolean(prisms,manifold3d.OpType.Add)
    if union.status()!=manifold3d.Error.NoError:
        raise ValueError('Native triangular-prism union failed')
    result=union.to_mesh64()
    mesh=trimesh.Trimesh(result.vert_properties[:,:3],result.tri_verts,process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
        raise ValueError('Triangular-prism union did not produce a closed positive volume')
    return mesh,dict(triangular_prisms=len(prisms),sum_prism_volumes_mm3=expected_sum,
                     union_volume_mm3=mesh.volume,boolean_precision='Manifold Mesh64')


def prism_boundary_chain(surface):
    """Cancel paired internal side quads algebraically, retaining the same prism winding sum.

    This is a boundary chain, possibly self-intersecting, for exact winding-number
    Boolean input. It is not admitted as an embedded free support volume.
    """
    vertices=np.asarray(surface.vertices,dtype=np.float64)
    lower=vertices.copy();lower[:,2]=0.
    top=np.asarray(surface.faces,dtype=np.int64)[:,[0,2,1]]
    if np.any(np.cross(surface.triangles[:,1,:2]-surface.triangles[:,0,:2],
                       surface.triangles[:,2,:2]-surface.triangles[:,0,:2])>=0):
        raise ValueError('Boundary chain requires consistently downward overhang faces')
    edges=np.stack([top[:,[0,1]],top[:,[1,2]],top[:,[2,0]]],axis=1).reshape(-1,2)
    _,inverse,counts=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
    if np.any(counts>2):raise ValueError('Overhang source has a nonmanifold edge')
    boundary=edges[counts[inverse]==1]
    n=len(vertices);a,b=boundary.T
    side=np.stack([np.column_stack([a,a+n,b+n]),np.column_stack([a,b+n,b])],axis=1).reshape(-1,3)
    faces=np.vstack([top,np.asarray(surface.faces)+n,side])
    chain=trimesh.Trimesh(np.vstack([vertices,lower]),faces,process=False)
    expected=float(np.sum(abs(np.cross(surface.triangles[:,1,:2]-surface.triangles[:,0,:2],
                          surface.triangles[:,2,:2]-surface.triangles[:,0,:2]))/2*
                          surface.triangles[:,:,2].mean(axis=1)))
    tolerance=128*np.finfo(float).eps*max(1.,expected)*len(surface.faces)
    if not chain.is_watertight or not chain.is_winding_consistent or abs(chain.volume-expected)>tolerance:
        raise ValueError('Cancelled boundary chain differs from the real prism sum')
    return chain,dict(source_triangles=len(surface.faces),boundary_chain_triangles=len(faces),
        internal_side_quads_cancelled=int(np.sum(counts==2)),boundary_side_quads=len(boundary),
        sum_prism_volumes_mm3=expected,boundary_chain_signed_volume_mm3=chain.volume,
        numerical_volume_tolerance_mm3=tolerance,coordinate_displacement_mm=0.,
        interpretation='oriented boundary chain for exact winding Boolean; not an embedded volume')


def reduce_exact_horizontal_patches(surface):
    """Retriangulate only exactly horizontal patches, preserving every boundary edge.

    No plane-fit tolerance, vertex displacement, welding tolerance, or shape
    simplification is used.  The new XY triangulation must use original vertices.
    """
    import shapely
    vertices=np.asarray(surface.vertices,dtype=np.float64)
    triangles=surface.triangles
    flat=np.ptp(triangles[:,:,2],axis=1)==0
    retained=[surface.faces[~flat]];rows=[]
    def boundary(faces):
        edges=np.stack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]],axis=1).reshape(-1,2)
        edges,counts=np.unique(np.sort(edges,axis=1),axis=0,return_counts=True)
        if np.any(counts>2):raise ValueError('Horizontal source patch has a nonmanifold edge')
        return edges[counts==1]
    coordinate_index={tuple(point):i for i,point in enumerate(vertices)}
    if len(coordinate_index)!=len(vertices):raise ValueError('Source has duplicate XYZ vertex identities')
    for height in np.unique(triangles[flat,0,2]):
        selected=np.flatnonzero(flat&(triangles[:,0,2]==height))
        old=surface.faces[selected]
        polygons=shapely.polygons(triangles[selected,:,:2])
        domain=shapely.union_all(polygons)
        new_triangles=shapely.get_parts(shapely.constrained_delaunay_triangles(domain))
        xy=np.asarray([np.asarray(t.exterior.coords)[:3] for t in new_triangles])
        new=np.asarray([[coordinate_index[tuple([p[0],p[1],height])] for p in triangle]
                       for triangle in xy],dtype=np.int64)
        # The source is a downward overhang.  Orient the replacement likewise.
        normal=np.cross(vertices[new[:,1],:2]-vertices[new[:,0],:2],vertices[new[:,2],:2]-vertices[new[:,0],:2])
        new[normal>0]=new[normal>0][:,[0,2,1]]
        if not np.array_equal(boundary(old),boundary(new)):
            raise ValueError('Horizontal retriangulation changed an original boundary edge')
        delta=domain.symmetric_difference(shapely.union_all(new_triangles)).area
        area_old=float(np.sum(shapely.area(polygons)));area_new=float(np.sum(shapely.area(new_triangles)))
        bound=128*np.finfo(float).eps*max(1.,area_old)*len(old)
        if delta!=0 or abs(area_old-area_new)>bound:
            raise ValueError('Horizontal retriangulation changed the original domain')
        retained.append(new)
        rows.append(dict(height_mm=float(height),source_triangles=len(old),replacement_triangles=len(new),
            boundary_edges=len(boundary(old)),boundary_edges_exactly_equal=True,symmetric_difference_area_mm2=delta,
            source_area_mm2=area_old,replacement_area_mm2=area_new,numerical_area_tolerance_mm2=bound))
    result=trimesh.Trimesh(vertices.copy(),np.vstack(retained),process=False)
    return result,dict(source_triangles=len(surface.faces),replacement_triangles=len(result.faces),
        exact_horizontal_faces=int(flat.sum()),coordinate_displacement_mm=0.,all_new_vertices_from_source=True,
        algorithm='strict_constant_Z_patch_constrained_Delaunay_original_boundary_edges',patches=rows)
