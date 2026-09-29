"""Bounded firmware state model. No hardware, radio or cryptography implementation."""
import argparse
import hashlib
import json
from pathlib import Path
import time

MAX_BYTES = 256 * 1024
MAX_PIXELS = 4096
MAX_FRAMES = 60
CHUNK_BYTES = 128
WATCHDOG_SECONDS = 2.0


def integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("integer out of range")
    return value


def pack(document):
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValueError("unsupported document")
    integer(document["version"], 1, 1)
    width = integer(document.get("width"), 1, MAX_PIXELS)
    height = integer(document.get("height"), 1, MAX_PIXELS)
    if width * height > MAX_PIXELS or document.get("format") != "mono8":
        raise ValueError("unsupported geometry or format")
    frames = document.get("frames")
    if not isinstance(frames, list) or not 1 <= len(frames) <= MAX_FRAMES:
        raise ValueError("invalid frame count")
    payload, durations = bytearray(), []
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("invalid frame")
        durations.append(integer(frame.get("duration_ms"), 100, 10000))
        pixels = frame.get("pixels")
        if not isinstance(pixels, list) or len(pixels) != width * height:
            raise ValueError("invalid pixel count")
        payload.extend(integer(pixel, 0, 255) for pixel in pixels)
    if len(payload) > MAX_BYTES:
        raise ValueError("payload too large")
    return width, height, tuple(durations), bytes(payload)


class Panel:
    """Authentication and local arming are trusted test inputs, not BLE commands."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.active = None
        self.fault()

    def fault(self):
        self.authenticated = False
        self.armed = False
        self.playing = False
        self.pending = None
        self.last_seen = None

    def connect(self, authenticated=False):
        self.fault()
        if authenticated is not True:
            raise PermissionError("authenticated transport required")
        self.authenticated = True
        self.last_seen = self.clock()

    def tick(self):
        if self.last_seen is not None and self.clock() - self.last_seen >= WATCHDOG_SECONDS:
            self.fault()

    def require_link(self):
        self.tick()
        if not self.authenticated:
            raise PermissionError("session closed")

    def heartbeat(self):
        self.require_link()
        self.last_seen = self.clock()

    def arm_local(self):
        self.require_link()
        self.armed = True

    def stop(self):
        self.playing = False
        self.armed = False
        self.pending = None

    def begin(self, width, height, durations, size, digest):
        self.require_link()
        self.stop()
        integer(width, 1, MAX_PIXELS)
        integer(height, 1, MAX_PIXELS)
        if width * height > MAX_PIXELS or not isinstance(durations, (tuple, list)):
            raise ValueError("invalid metadata")
        integer(len(durations), 1, MAX_FRAMES)
        durations = tuple(integer(value, 100, 10000) for value in durations)
        integer(size, 1, MAX_BYTES)
        if size != width * height * len(durations):
            raise ValueError("invalid size")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid digest")
        self.pending = (width, height, durations, size, digest, bytearray())

    def data(self, offset, chunk):
        self.require_link()
        try:
            if self.pending is None:
                raise ValueError("no transfer")
            size, buffer = self.pending[3], self.pending[5]
            integer(offset, 0, size)
            if not isinstance(chunk, bytes) or not 1 <= len(chunk) <= CHUNK_BYTES:
                raise ValueError("invalid chunk")
            if offset != len(buffer) or len(buffer) + len(chunk) > size:
                raise ValueError("invalid offset or overflow")
            buffer.extend(chunk)
            return len(buffer)
        except ValueError:
            self.stop()
            raise

    def commit(self):
        self.require_link()
        if self.pending is None:
            raise ValueError("no transfer")
        width, height, durations, size, digest, buffer = self.pending
        self.pending = None
        if len(buffer) != size or hashlib.sha256(buffer).hexdigest() != digest:
            self.stop()
            raise ValueError("incomplete or corrupt transfer")
        self.active = (width, height, durations, bytes(buffer))

    def play(self):
        self.require_link()
        if not self.armed or self.active is None or self.pending is not None:
            raise PermissionError("local arm and committed content required")
        self.playing = True
        self.started = self.clock()

    def render(self):
        self.tick()
        if self.active is None:
            return b""
        width, height, durations, payload = self.active
        size = width * height
        if not self.playing:
            return bytes(size)
        elapsed = int((self.clock() - self.started) * 1000) % sum(durations)
        for index, duration in enumerate(durations):
            if elapsed < duration:
                return payload[index * size:(index + 1) * size]
            elapsed -= duration
        raise AssertionError("unreachable frame")


def upload(panel, document):
    width, height, durations, payload = pack(document)
    panel.begin(width, height, durations, len(payload), hashlib.sha256(payload).hexdigest())
    for offset in range(0, len(payload), CHUNK_BYTES):
        panel.data(offset, payload[offset:offset + CHUNK_BYTES])
    panel.commit()


def gif_document(path):
    # Optional host-side decoder; never imported by the firmware state model.
    from PIL import Image, ImageOps
    import warnings

    if Path(path).stat().st_size > 5 * 1024 * 1024:
        raise ValueError("GIF file too large")
    frames = []
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as source:
            if source.format != "GIF" or source.width * source.height > 1_000_000:
                raise ValueError("unsupported source")
            for index in range(MAX_FRAMES + 1):
                try:
                    source.seek(index)
                except EOFError:
                    break
                if index == MAX_FRAMES:
                    raise ValueError("too many GIF frames")
                if source.width * source.height > 1_000_000:
                    raise ValueError("GIF frame too large")
                rgba = source.convert("RGBA")
                black = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
                black.alpha_composite(rgba)
                fitted = ImageOps.contain(black.convert("L"), (16, 8), Image.Resampling.LANCZOS)
                canvas = Image.new("L", (16, 8), 0)
                canvas.paste(fitted, ((16 - fitted.width) // 2, (8 - fitted.height) // 2))
                duration = max(100, min(10000, int(source.info.get("duration", 100))))
                frames.append({"duration_ms": duration, "pixels": list(canvas.getdata())})
    document = {"version": 1, "width": 16, "height": 8, "format": "mono8", "frames": frames}
    pack(document)
    return document


def demo_document():
    return {"version": 1, "width": 16, "height": 8, "format": "mono8", "frames": [
        {"duration_ms": 200, "pixels": [255 if (x + shift) % 8 == y else 0
                                       for y in range(8) for x in range(16)]}
        for shift in (0, 1)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--input", type=Path)
    inputs.add_argument("--gif", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and not args.gif:
        parser.error("--output requires --gif")
    if args.gif:
        document = gif_document(args.gif)
        if args.output:
            # Exclusive create avoids overwriting user files.
            with args.output.open("x", encoding="utf-8") as output:
                json.dump(document, output)
    elif args.input:
        with args.input.open("rb") as source:
            raw = source.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError("JSON file too large")
        document = json.loads(raw)
    else:
        document = demo_document()
    now = [0.0]
    panel = Panel(clock=lambda: now[0])
    panel.connect(authenticated=True)
    upload(panel, document)
    panel.arm_local()
    panel.play()
    width, height, durations, _ = panel.active
    for duration in durations:
        panel.heartbeat()
        pixels = panel.render()
        print("SIMULATION ONLY")
        for y in range(height):
            print("".join("#" if value > 127 else "." for value in pixels[y * width:(y + 1) * width]))
        # Virtual time with regular trusted heartbeat, including long frames.
        remaining = duration / 1000
        while remaining > 0:
            step = min(remaining, 0.5)
            now[0] += step
            panel.heartbeat()
            remaining -= step
    panel.fault()
    assert not any(panel.render())


if __name__ == "__main__":
    main()
