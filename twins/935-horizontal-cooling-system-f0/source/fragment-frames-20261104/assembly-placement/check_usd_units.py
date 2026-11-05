#!/usr/bin/env python3
"""Check explicit SI metadata for a conditional 935 inspection stage."""
import argparse
from pathlib import Path


def validate(stage):
    """Reject USD fallback units; this cannot calibrate the underlying scan."""
    from pxr import UsdGeom

    if stage is None:
        raise ValueError('USD stage did not open')
    if not stage.HasAuthoredMetadata('metersPerUnit'):
        raise ValueError('Root stage must explicitly author metersPerUnit')
    value = UsdGeom.GetStageMetersPerUnit(stage)
    if value != 1.0:
        raise ValueError(f'Expected one metre per stage unit, got {value}')
    return {'meters_per_unit': value, 'source_scale_verified': False}


def main():
    from pxr import Usd

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    args = parser.parse_args()
    print(validate(Usd.Stage.Open(str(args.scene))))


if __name__ == '__main__':
    main()
