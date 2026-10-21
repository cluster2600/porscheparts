"""Adapt native PySLM full-sheet return paths to its native PolyTree consumer."""
import types
import pyclipr
from pyslm.hatching import BaseHatcher
from pyslm.support import GridBlockSupport


def as_tree(result):
    if not isinstance(result,list):return result
    clipper=pyclipr.Clipper();clipper.scaleFactor=int(BaseHatcher.CLIPPER_SCALEFACTOR)
    clipper.addPaths(result,pyclipr.Subject,False)
    return clipper.execute2(pyclipr.Union,pyclipr.FillRule.NonZero)


def full_slice_geometry(self,section):
    return as_tree(GridBlockSupport.generateSliceGeometry(self,section))


def enable(block):
    block.generateTrussGrid=False
    block.generateSliceGeometry=types.MethodType(full_slice_geometry,block)
    return block
