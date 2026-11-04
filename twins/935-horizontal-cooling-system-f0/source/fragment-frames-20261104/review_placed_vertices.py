#!/usr/bin/env python3
"""Independently review all ordered CAD vertices after same-scan placement."""
import argparse,hashlib,json
from pathlib import Path
import FreeCAD as App
import Part
import numpy as np


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()


def vertices(shape):
 return np.array([[v.Point.x,v.Point.y,v.Point.z] for v in shape.Vertexes],dtype=float)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('shaft',type=Path);p.add_argument('support',type=Path);p.add_argument('transform',type=Path);p.add_argument('placed',type=Path);p.add_argument('output',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[4]/'work'
 if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()): raise SystemExit('fresh private work output required')
 expected=('8d78c70ae3f2a43bc5f4cadb0e43980c4b3b853465b0806060d738b58074c89b','3246d98fca2c5df2bdbe2b8457be3f87fa6ffba2b98f46de97886417969c0d00','11039619a1e206090b28ee919faaf4d2f96107d47a63809a9f77a39811cf0d04','30e837b39fb5b36a73b828aa98c9706c350a5f8702442bda10bbd03f35fe11e0')
 if tuple(sha(x) for x in (a.shaft,a.support,a.transform,a.placed))!=expected: raise ValueError('input hash mismatch')
 matrix=np.asarray(json.loads(a.transform.read_text())['shaft_cad_to_support_cad'],float)
 if matrix.shape!=(4,4) or not np.isfinite(matrix).all(): raise ValueError('invalid transform')
 shaft=Part.read(str(a.shaft.resolve()));support=Part.read(str(a.support.resolve()));doc=App.openDocument(str(a.placed.resolve()))
 try:
  s=doc.getObject('shaft_open_candidate_transformed');t=doc.getObject('support_open_candidate')
  if s is None or t is None or len(s.Shape.Solids) or len(t.Shape.Solids):raise ValueError('missing open fragments')
  source,placed=vertices(shaft),vertices(s.Shape); source_support,placed_support=vertices(support),vertices(t.Shape)
  if source.shape!=(1584,3) or placed.shape!=source.shape or source_support.shape!=(8,3) or placed_support.shape!=source_support.shape: raise ValueError('unexpected vertex counts')
  err=float(np.max(np.abs(source@matrix[:3,:3].T+matrix[:3,3]-placed))); err_support=float(np.max(np.abs(source_support-placed_support)))
  if not np.isfinite([err,err_support]).all() or max(err,err_support)>1e-8: raise ValueError('vertex placement mismatch')
 finally: App.closeDocument(doc.Name)
 result={'status':'all_ordered_brep_vertices_checked_not_fit_validation','input_sha256':expected,'shaft_vertex_count':len(source),'shaft_max_coordinate_error_source_units':err,'support_vertex_count':len(source_support),'support_max_coordinate_error_source_units':err_support,'freecad_version':App.Version()[:3],'scale_verified':False,'physical_registration_verified':False,'mating_interface_verified':False,'manufacturing_authorized':False}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
