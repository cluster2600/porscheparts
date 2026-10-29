#!/usr/bin/env python3
"""Inspect external OpenUSD fixtures; this is not SimReady runtime certification."""
import argparse
import json
import os
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdUtils

from fetch import DEFAULT_CACHE, HERE, verify


def inspect(cache, asset):
    for record in asset['files']:
        verify(cache / record['path'], record)
    source = cache / asset['root_usd']
    layers, dependencies, unresolved = UsdUtils.ComputeAllDependencies(str(source))
    stage = Usd.Stage.Open(str(source))
    if not stage or not stage.GetDefaultPrim():
        raise ValueError(f'Invalid default prim: {source}')
    errors = [str(error) for error in stage.GetCompositionErrors()]
    meshes = [prim for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies())
              if prim.IsA(UsdGeom.Mesh)]
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render', 'proxy'])
    box = bounds.ComputeWorldBound(stage.GetDefaultPrim()).ComputeAlignedRange()
    upstream_failures = []
    for layer in layers:
        metadata = layer.customLayerData.get('SimReady_Metadata', {})
        validation = metadata.get('validation', {})
        for date, features in validation.get('validated_features', {}).items():
            for name, result in features.items():
                if result.get('passed') is False:
                    upstream_failures.append({'layer': Path(layer.identifier).name,
                                              'date': date, 'feature': name,
                                              'requirements': result.get('failing requirements')})
    variants = []
    # Session-layer selections never edit the original NVIDIA files.
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        root = stage.GetDefaultPrim()
        for name in root.GetVariantSets().GetNames():
            variant = root.GetVariantSet(name)
            original = variant.GetVariantSelection()
            for choice in variant.GetVariantNames():
                variant.SetVariantSelection(choice)
                variants.append({'set': name, 'choice': choice,
                                 'composition_errors': [str(e) for e in stage.GetCompositionErrors()],
                                 'rigid_body_count': sum(p.HasAPI(UsdPhysics.RigidBodyAPI)
                                                         for p in Usd.PrimRange.Stage(
                                                             stage, Usd.TraverseInstanceProxies()))})
            if original:
                variant.SetVariantSelection(original)
            else:
                variant.ClearVariantSelection()
    result = {'id': asset['id'], 'default_prim': str(stage.GetDefaultPrim().GetPath()),
              'meters_per_unit': UsdGeom.GetStageMetersPerUnit(stage),
              'up_axis': str(UsdGeom.GetStageUpAxis(stage)),
              'mesh_count': len(meshes), 'layer_count': len(layers),
              'dependency_count': len(dependencies), 'unresolved_dependencies': list(unresolved),
              'composition_errors': errors, 'variants': variants,
              'bounds_min': list(box.GetMin()), 'bounds_max': list(box.GetMax()),
              'upstream_historical_failures': upstream_failures,
              'simready_runtime_validation': 'not_run',
              'porsche_fitment_verified': False, 'manufacturing_authorized': False}
    result['usd_inspection_passed'] = bool(meshes) and not box.IsEmpty() and not (
        unresolved or errors or any(v['composition_errors'] for v in variants))
    return result


def gallery(cache, assets, results):
    target = cache / 'reference-gallery.usda'
    stage = Usd.Stage.CreateNew(str(target)) if not target.exists() else Usd.Stage.Open(str(target))
    stage.GetRootLayer().Clear()
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(stage, '/ExternalReferences')
    stage.SetDefaultPrim(root.GetPrim())
    root.GetPrim().SetCustomData({'purpose': 'external_pipeline_fixtures',
                                'porsche_fitment_verified': False,
                                'manufacturing_authorized': False})
    cursor = 0.0
    for asset, result in zip(assets, results):
        if result['meters_per_unit'] != 1 or result['up_axis'] != 'Z':
            raise ValueError('Gallery expects the inspected metre/Z-up reference packages')
        xform = UsdGeom.Xform.Define(stage, '/ExternalReferences/' + asset['id'])
        model = stage.DefinePrim(str(xform.GetPath()) + '/Model')
        model.GetReferences().AddReference(os.path.relpath(cache / asset['root_usd'], cache))
        lo, hi = result['bounds_min'], result['bounds_max']
        xform.AddTranslateOp().Set(Gf.Vec3d(cursor - lo[0], -lo[1], -lo[2]))
        cursor += hi[0] - lo[0] + 0.25
    stage.GetRootLayer().Save()
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    lock = json.loads((HERE / 'assets.lock.json').read_text())
    results = [inspect(args.cache, asset) for asset in lock['assets']]
    report = {'repository': lock['repository'], 'revision': lock['revision'],
              'openusd_version': list(Usd.GetVersion()), 'assets': results,
              'all_usd_inspections_passed': all(r['usd_inspection_passed'] for r in results),
              'simready_runtime_validation': 'not_run', 'manufacturing_authorized': False}
    (args.cache / 'inspection.json').write_text(json.dumps(report, indent=2) + '\n')
    if not report['all_usd_inspections_passed']:
        raise SystemExit('OpenUSD inspection failed; see inspection.json')
    target = gallery(args.cache, lock['assets'], results)
    stage = Usd.Stage.Open(str(target))
    layers, dependencies, unresolved = UsdUtils.ComputeAllDependencies(str(target))
    report['gallery_inspection'] = {
        'composition_errors': [str(e) for e in stage.GetCompositionErrors()],
        'unresolved_dependencies': list(unresolved), 'layer_count': len(layers),
        'dependency_count': len(dependencies)}
    (args.cache / 'inspection.json').write_text(json.dumps(report, indent=2) + '\n')
    if unresolved or stage.GetCompositionErrors():
        raise SystemExit('Gallery inspection failed; see inspection.json')
    print(target)
    print('OpenUSD inspection passed; SimReady runtime validation not run')


if __name__ == '__main__':
    main()
