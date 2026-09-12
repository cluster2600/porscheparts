#!/usr/bin/env python3
"""Container-only worker: generated code and independent audit are separate runs.

This worker MUST run in disposable network-less, non-root, resource-bounded
containers. Its AST screen is defence in depth, NOT a Python security sandbox.
Generated code must never run on the host or in the inference service.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def screen(source):
    if len(source.encode()) > 100000:
        raise ValueError('generated_code_too_large')
    tree = ast.parse(source)
    nodes = list(ast.walk(tree))
    if len(nodes) > 5000:
        raise ValueError('generated_AST_too_large')
    forbidden = (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith,
                 ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda,
                 ast.Try, ast.Global, ast.Nonlocal, ast.Delete)
    names = {'exec', 'eval', 'compile', 'open', 'input', 'getattr', 'setattr',
             'globals', 'locals', 'vars', 'dir', '__import__', 'breakpoint', 'exit', 'quit'}
    for node in nodes:
        if isinstance(node, forbidden):
            raise ValueError('unsupported_generated_control_flow')
        if isinstance(node, ast.Import) and any(alias.name not in {'cadquery', 'math'} for alias in node.names):
            raise ValueError('unsupported_generated_import')
        if isinstance(node, ast.ImportFrom) and (node.module not in {'cadquery', 'math'} or node.level):
            raise ValueError('unsupported_generated_import')
        if isinstance(node, ast.Attribute) and node.attr.startswith('_'):
            raise ValueError('private_generated_attribute_forbidden')
        if isinstance(node, ast.Name) and (node.id in names or node.id.startswith('__')):
            raise ValueError('unsafe_generated_name')
    return tree


def execute(args):
    import cadquery as cq
    import math
    source = args.input.read_text()
    tree = screen(source)
    state = {'cq': cq, 'cadquery': cq, 'math': math}
    # This execution is permitted only inside the disposable isolated container.
    exec(compile(tree, '<untrusted-specialist-CAD>', 'exec'), state)
    candidates = [(key, value) for key, value in state.items()
                  if isinstance(value, (cq.Workplane, cq.Shape))]
    if not candidates:
        raise ValueError('no_CadQuery_result')
    name, result = candidates[-1]
    if isinstance(result, cq.Workplane):
        solids = result.solids().vals()
        if not solids:
            raise ValueError('no_generated_solids')
        result = cq.Compound.makeCompound(solids) if len(solids) != 1 else solids[0]
    result.exportBrep(str(args.output / 'candidate.brep'))
    (args.output / 'producer.json').write_text(json.dumps({
        'untrusted_producer_receipt': True, 'generated_code_sha256': digest(args.input),
        'selected_variable': name, 'cad_coordinates_to_normalized': 0.01,
        'candidate_sha256': digest(args.output / 'candidate.brep'),
    }, indent=2) + '\n')


def audit(args):
    import cadquery as cq
    import OCP
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepTools import BRepTools
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Shape
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
    if args.input.stat().st_size > 50_000_000:
        raise ValueError('candidate_BRep_size_limit')
    before = digest(args.input)
    native = TopoDS_Shape()
    if not BRepTools.Read_s(native, str(args.input), BRep_Builder()) or native.IsNull():
        raise ValueError('native_BRep_read_failed')
    analyzer = BRepCheck_Analyzer(native, True)
    analyzer.SetExactMethod(True)
    counts = {}
    for label, kind in [('solids', TopAbs_SOLID), ('shells', TopAbs_SHELL), ('faces', TopAbs_FACE),
                        ('edges', TopAbs_EDGE), ('vertices', TopAbs_VERTEX)]:
        items = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(native, kind, items)
        counts[label] = items.Extent()
    shape = cq.Shape.cast(native)
    normalized = shape.scale(0.01)
    bbox = normalized.BoundingBox()
    normalized.exportStl(str(args.output / 'candidate-normalized.stl'),
                         tolerance=0.001, angularTolerance=0.1)
    report = {
        'schema': 'specialist-CAD-independent-native-audit/v1',
        'source_sha256': before, 'source_unchanged': digest(args.input) == before,
        'worker_sha256': digest(__file__), 'cadquery_version': cq.__version__,
        'OCP_version': OCP.__version__, 'BRep_valid': bool(analyzer.IsValid()),
        'topology': counts, 'CAD_to_normalized_scale': 0.01,
        'normalized_bounds': [[bbox.xmin, bbox.ymin, bbox.zmin], [bbox.xmax, bbox.ymax, bbox.zmax]],
        'normalized_surface_area': normalized.Area(),
        'candidate_volume_normalized_cubed': normalized.Volume(),
        'reference_volume_comparison_allowed': False,
        'stl_sha256': digest(args.output / 'candidate-normalized.stl'),
        'mesh_tolerance_normalized': 0.001, 'mesh_angular_tolerance_rad': 0.1,
        'self_intersections_independently_tested': False,
        'manufacturing_release': False,
    }
    (args.output / 'native-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'BRep_valid': report['BRep_valid'], 'topology': counts}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['execute', 'audit'], required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not Path('/.dockerenv').exists():
        raise RuntimeError('container_only_worker')
    args.output.mkdir(exist_ok=True)
    {'execute': execute, 'audit': audit}[args.stage](args)


if __name__ == '__main__':
    main()
