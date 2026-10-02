"""E0 host calculations and TLC5947 reference bytes; no hardware I/O."""
import argparse
import csv
import json
import math
from pathlib import Path

import panel_simulator

WIDTH, HEIGHT = 16, 8
DRIVERS, CHANNELS = 6, 24
PWM_MAX = 4095
FRAME_BYTES = DRIVERS * CHANNELS * 12 // 8


def encode_frame(pixels, pwm_cap=1024):
    """Row-major mono8 -> farthest chip first, OUT23 first, MSB first."""
    panel_simulator.integer(pwm_cap, 0, PWM_MAX)
    if not isinstance(pixels, (bytes, bytearray, list, tuple)) or len(pixels) != WIDTH * HEIGHT:
        raise ValueError("E0 requires exactly 128 mono8 pixels")
    values = [(panel_simulator.integer(p, 0, 255) * pwm_cap + 127) // 255
              for p in pixels]
    values += [0] * (DRIVERS * CHANNELS - len(values))
    packed = 0
    for value in reversed(values):
        packed = (packed << 12) | value
    return packed.to_bytes(FRAME_BYTES, "big")


def channel_map(pitch_mm=2.5):
    if type(pitch_mm) not in (int, float) or pitch_mm not in (2.5, 4.0):
        raise ValueError("E0 supports proposed pitches 2.5 or 4 mm only")
    for index in range(WIDTH * HEIGHT):
        x, y = index % WIDTH, index // WIDTH
        yield {"led": f"D{index + 1}", "x": x, "y": y,
               "center_x_mm": x * pitch_mm, "center_y_mm": y * pitch_mm,
               "anode_net": "VLED_3V3", "driver": f"U{1 + index // CHANNELS}",
               "output": index % CHANNELS, "dap_pin": 5 + index % CHANNELS,
               "status": "not_validated_for_manufacture"}


def finite(value, minimum, maximum):
    if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError("finite engineering input outside E0 bounds")
    return value


def estimate(rref_ohm=20000, supply_v=3.3, vf_min_v=1.7, vf_max_v=2.3):
    """Screen assumed corners, not a component guarantee or thermal simulation."""
    finite(rref_ohm, 1000, 100000)
    finite(supply_v, 3.0 / 0.97, 3.6 / 1.03)
    finite(vf_min_v, 0.1, 3.6)
    finite(vf_max_v, vf_min_v, 3.6)
    current_a = 41 * 1.20 / rref_ohm
    low_a, high_a = current_a * 0.90, current_a * 1.10
    if low_a < 0.002 or high_a > 0.005:
        raise ValueError("assumed current corners must stay within E0 2-5 mA range")
    v_low, v_high = supply_v * 0.97, supply_v * 1.03
    headroom = v_low - vf_max_v
    if headroom < 0.6:
        raise ValueError("less than assumed 0.6 V current-sink headroom")
    led_peak_a = WIDTH * HEIGHT * high_a
    logic_a = DRIVERS * 0.045 + 0.002
    bleed_a = v_high / 990  # 1 kohm, minus 1% tolerance
    source_a = led_peak_a + logic_a + bleed_a
    if source_a > 0.65:
        raise ValueError("assumed load exceeds E0 steady-current stop threshold")
    return {
        "status": "unvalidated_engineering_estimate_bench_only",
        "assumptions": {"rref_ohm": rref_ohm, "vref_typ_v": 1.20,
                        "supply_v": supply_v, "supply_tolerance": 0.03,
                        "total_current_margin_including_resistor": 0.10,
                        "vf_min_v": vf_min_v, "vf_max_v": vf_max_v,
                        "logic_allowance_per_driver_ma": 45,
                        "buffers_allowance_ma": 2, "bleeder_min_ohm": 990,
                        "mcu_power_included": False},
        "led_nominal_ma": current_a * 1000,
        "led_corners_ma": [low_a * 1000, high_a * 1000],
        "all_leds_peak_ma": led_peak_a * 1000,
        "coupon_source_peak_ma": source_a * 1000,
        "coupon_input_max_w": v_high * source_a,
        "full_driver_dissipation_w": CHANNELS * high_a * (v_high - vf_min_v) + v_high * 0.045,
        "headroom_min_v": headroom,
        "spi_frame_bytes": FRAME_BYTES,
        "spi_shift_ms_at_1mhz": FRAME_BYTES * 8 / 1000,
    }


def write_outputs(directory, document, pitch_mm=2.5, pwm_cap=1024, **power_inputs):
    width, height, durations, payload = panel_simulator.pack(document)
    if (width, height) != (WIDTH, HEIGHT):
        raise ValueError("E0 requires a 16x8 document")
    frames = [encode_frame(payload[i * WIDTH * HEIGHT:(i + 1) * WIDTH * HEIGHT], pwm_cap)
              for i in range(len(durations))]
    rows = list(channel_map(pitch_mm))
    report = estimate(**power_inputs)
    report.update({"pitch_mm": pitch_mm, "pwm_cap": pwm_cap,
                   "frame_durations_ms": list(durations)})
    # Refuse to overwrite an existing directory or any user artifacts.
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    with (directory / "channel-map.csv").open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (directory / "frames-spi.hex").open("x", encoding="ascii") as output:
        output.write("\n".join(frame.hex() for frame in frames) + "\n")
    with (directory / "estimate.json").open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--pitch-mm", type=float, choices=(2.5, 4.0), default=2.5)
    parser.add_argument("--pwm-cap", type=int, default=1024)
    parser.add_argument("--rref-ohm", type=float, default=20000)
    parser.add_argument("--supply-v", type=float, default=3.3)
    parser.add_argument("--vf-min-v", type=float, default=1.7)
    parser.add_argument("--vf-max-v", type=float, default=2.3)
    args = parser.parse_args()
    document = panel_simulator.demo_document()
    if args.input:
        with args.input.open("rb") as source:
            raw = source.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            parser.error("JSON file too large")
        document = json.loads(raw)
    report = write_outputs(args.output_dir, document, args.pitch_mm, args.pwm_cap,
                           rref_ohm=args.rref_ohm, supply_v=args.supply_v,
                           vf_min_v=args.vf_min_v, vf_max_v=args.vf_max_v)
    print("HOST ONLY: no hardware I/O; not validated for manufacture")
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
