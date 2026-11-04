#!/usr/bin/env python3
"""Verify the authored 935 inspection timeline after USD layer composition."""
import argparse
from pathlib import Path


def validate(stage):
    """Check this inspection animation, not its physical speed or coupling."""
    from pxr import Usd, UsdGeom

    if stage is None:
        raise ValueError("USD stage did not open")
    metadata = (stage.GetStartTimeCode(), stage.GetEndTimeCode(),
                stage.GetTimeCodesPerSecond(), stage.GetFramesPerSecond())
    if metadata != (0, 240, 60, 60):
        raise ValueError(f"Unexpected composed timeline: {metadata}")
    rotor = stage.GetPrimAtPath('/World/rotor_candidate')
    if not rotor or not rotor.IsA(UsdGeom.Xformable):
        raise ValueError("Rotor transform is missing")
    ops = UsdGeom.Xformable(rotor).GetOrderedXformOps()
    spins = [op for op in ops if op.GetOpName() == 'xformOp:rotateZ']
    if len(spins) != 1:
        raise ValueError("Expected one rotor Z rotation")
    for frame in range(241):
        value = spins[0].Get(Usd.TimeCode(frame))
        if value is None or abs(float(value) - 1.5 * frame) > 1e-9:
            raise ValueError(f"Unexpected rotor angle at frame {frame}: {value}")
    return {'checked_frames': 241, 'time_codes_per_second': 60,
            'frames_per_second': 60, 'physical_speed_verified': False}


def main():
    from pxr import Usd
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    args = parser.parse_args()
    print(validate(Usd.Stage.Open(str(args.scene))))


if __name__ == '__main__':
    main()
