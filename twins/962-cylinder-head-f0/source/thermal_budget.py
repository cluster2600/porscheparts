"""Algebraic TEC energy budget from explicit assumptions; not module sizing."""
import argparse
import json
import math


def calculate(cold_load_w, assumed_cop, assumed_bus_v, assumed_dc_efficiency, auxiliaries_w):
    values = dict(cold_load_w=cold_load_w, assumed_cop=assumed_cop,
                  assumed_bus_v=assumed_bus_v, assumed_dc_efficiency=assumed_dc_efficiency,
                  auxiliaries_w=auxiliaries_w)
    if any(type(v) not in (int, float) for v in values.values()):
        raise ValueError("Inputs must be finite numbers, not booleans or strings")
    try:
        if not all(math.isfinite(v) for v in values.values()):
            raise ValueError("Inputs must be finite")
        if cold_load_w < 0 or auxiliaries_w < 0 or assumed_cop <= 0 or assumed_bus_v <= 0 or not 0 < assumed_dc_efficiency <= 1:
            raise ValueError("Loads must be nonnegative, COP/voltage positive, efficiency in (0, 1]")
        tec_power = cold_load_w / assumed_cop
        hot_side = cold_load_w + tec_power
        bus_power = tec_power / assumed_dc_efficiency + auxiliaries_w
        result = dict(tec_electrical_input_w=tec_power, tec_hot_side_rejection_w=hot_side,
                      bus_input_w=bus_power, converter_loss_w=tec_power / assumed_dc_efficiency - tec_power,
                      bus_current_a=bus_power / assumed_bus_v,
                      total_added_ambient_rejection_w=cold_load_w + bus_power)
        if not all(math.isfinite(v) for v in result.values()):
            raise ValueError("Budget overflow")
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Budget overflow") from exc
    return dict(status="assumption_only_no_hardware_sizing", hardware_qualified=False,
                assumptions=values, results=result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cold-load-w", type=float, required=True)
    parser.add_argument("--assumed-cop", type=float, required=True)
    parser.add_argument("--assumed-bus-v", type=float, required=True)
    parser.add_argument("--assumed-dc-efficiency", type=float, required=True)
    parser.add_argument("--auxiliaries-w", type=float, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(calculate(args.cold_load_w, args.assumed_cop, args.assumed_bus_v,
                                   args.assumed_dc_efficiency, args.auxiliaries_w), indent=2, allow_nan=False))
    except ValueError as exc:
        parser.error(str(exc))
