"""Construct support free intervals from actual triangular-prism unions."""
import time
import numpy as np
import shapely
import trimesh
from pyslm.support import GridBlockSupport, geometry, utils
from pyslm.support.support import _triangulate_exact_projected_domain
from prismatic_envelopes import projected_prism_union

GRID_PARAMETERS = ['gridSpacing','numSkinMeshSubdivideIterations','supportTeethHeight',
    'supportTeethTopLength','supportTeethBottomLength','supportTeethBaseInterval',
    'supportTeethUpperPenetration','supportWallThickness','useSupportSkin','useSupportBorder',
    'useLowerSupportTeeth','useUpperSupportTeeth','supportBorderDistance','trussWidth','trussAngle','mergeMesh']


def polygon_parts(geometry):
    if isinstance(geometry, shapely.Polygon):
        return [geometry] if not geometry.is_empty else []
    return [part for item in getattr(geometry,'geoms',[]) for part in polygon_parts(item)]


def identify(part,generator,overhang_angle):
    """Retain every free vertical interval below every real overhang triangle."""
    started=time.monotonic()
    regions=utils.getOverhangMesh(part,overhang_angle,True)
    coverage=dict(algorithm='actual_triangle_prism_union_intersect_exact_XY_mask_minus_complete_part',
        overhang_subregions=len(regions),expected_regions=0,generated_regions=0,
        complete_region_omissions=0,region_projection_admission_passed=False,
        edge_gap_mm=generator.outerSupportEdgeGap,minimum_projected_area_mm2=generator.minimumAreaThreshold,
        configured_area_exclusions=[],regions=[],source_prism_unions=[])
    blocks=[]
    for source_index,source in enumerate(regions):
        projection=shapely.union_all(shapely.polygons(source.triangles[:,:,:2]))
        if not projection.is_valid:
            raise ValueError('Invalid projected overhang triangle union')
        mask=projection.buffer(-generator.outerSupportEdgeGap)
        polygons=polygon_parts(mask)
        retained=[]
        for polygon in polygons:
            if polygon.area<generator.minimumAreaThreshold:
                coverage['configured_area_exclusions'].append(dict(source_index=source_index,
                    area_mm2=polygon.area,stage='explicit_edge_gap_then_minimum_projected_area'))
            else: retained.append(polygon)
        if not retained:
            coverage['configured_area_exclusions'].append(dict(source_index=source_index,
                original_projected_area_mm2=projection.area,buffered_area_mm2=mask.area,
                stage='no_polygon_above_configured_minimum_area'))
            continue
        prism_union,prism_receipt=projected_prism_union(source)
        coverage['source_prism_unions'].append(dict(source_index=source_index,**prism_receipt))
        for polygon in retained:
            coverage['expected_regions']+=1
            (xy,faces),tri_receipt=_triangulate_exact_projected_domain(polygon,generator.triangulationSpacing)
            height=prism_union.bounds[1,2]+generator.upperProjectionOffset
            planar=trimesh.Trimesh(np.column_stack([xy,np.full(len(xy),height)]),faces,process=False)
            mask_volume=geometry.extrudeFace(planar,height=0.)
            source_volume=geometry.boolIntersect(prism_union,mask_volume)
            free_volume=geometry.boolDiff(source_volume,part.geometry)
            if (not free_volume.is_watertight or not free_volume.is_winding_consistent or
                    free_volume.volume<=0 or not np.isfinite(free_volume.vertices).all()):
                raise ValueError('A required free support volume is invalid or empty')
            block=GridBlockSupport(part,free_volume,source,True)
            for name in GRID_PARAMETERS:setattr(block,name,getattr(generator,'_'+name))
            row=dict(index=len(blocks),source_index=source_index,area_mm2=polygon.area,
                bounds_xy_mm=list(polygon.bounds),source_projected_area_mm2=projection.area,
                edge_gap_excluded_area_mm2=projection.difference(mask).area,
                mask_triangulation=tri_receipt,real_triangle_union_volume_before_part_cut_mm3=source_volume.volume,
                free_support_volume_mm3=free_volume.volume,generated=True,
                all_vertical_intervals_retained=True,body_subtracted_in_same_coordinates=True)
            coverage['regions'].append(row);blocks.append(block);coverage['generated_regions']+=1
    if coverage['generated_regions']!=coverage['expected_regions'] or not blocks:
        raise ValueError('A required projected support region was omitted')
    coverage['region_projection_admission_passed']=True
    coverage['elapsed_seconds']=time.monotonic()-started
    generator.projectionCoverage=coverage
    return blocks
