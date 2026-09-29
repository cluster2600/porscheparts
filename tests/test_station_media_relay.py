import importlib.util
from pathlib import Path
import struct
import socket
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch


path = Path(__file__).parents[1] / 'deploy/vast/station/media-relay.py'
spec = importlib.util.spec_from_file_location('station_media_relay', path)
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


class MediaFramingTests(unittest.TestCase):
    def test_lifetime_policy_must_be_explicit_and_exclusive(self):
        for arguments in ([], ['--deadline', '1'], ['--deadline', '1', '--persistent']):
            result = subprocess.run([sys.executable, str(path), 'server', *arguments], capture_output=True, timeout=3)
            self.assertEqual(result.returncode, 2)

    def test_persistent_server_stops_on_sigterm(self):
        # An ephemeral loopback port avoids the live station's relay port.
        command = (
            'import runpy,sys; '
            f'module=runpy.run_path({str(path)!r}); '
            'module["main"].__globals__["TCP_PORT"]=0; '
            'sys.argv=["relay", "server", "--persistent"]; '
            'raise SystemExit(module["main"]())'
        )
        process = subprocess.Popen([sys.executable, '-u', '-c', command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            ready = process.stdout.readline()
            self.assertIn('"event": "listening"', ready)
            self.assertIn('"deadline": null', ready)
        finally:
            process.terminate()
            output, errors = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 130, errors)
        self.assertIn('"event": "interrupted"', output)

    def test_fragmented_and_coalesced_maximum_datagrams(self):
        expected = [(49152, b'x' * 65507), (50000, b'abc')]
        wire = b''.join(relay.HEADER.pack(port, len(data)) + data for port, data in expected)
        buffer, received = bytearray(), []
        for offset in range(0, len(wire), 137):
            buffer.extend(wire[offset:offset + 137])
            received.extend(relay.frames(buffer))
        self.assertEqual(received, expected)
        self.assertFalse(buffer)

    def test_invalid_headers_are_rejected_before_payload(self):
        for port, size in ((0, 5), (1, 0), (1, 65508)):
            with self.subTest(port=port, size=size), self.assertRaises(ValueError):
                list(relay.frames(bytearray(struct.pack('!HH', port, size))))

    def test_continuously_progressing_partial_frames_do_not_time_out(self):
        errors, clock = [], [0]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as target, socket.socket() as listener:
            target.bind(('127.0.0.1', 0))
            target.settimeout(2)
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            with socket.create_connection(listener.getsockname()) as sender:
                receiver, _ = listener.accept()
                def serve():
                    try:
                        with receiver:
                            relay.relay(receiver, 'server', time.time() + 20)
                    except Exception as error:
                        errors.append(error)
                with patch.object(relay, 'UDP_PORT', target.getsockname()[1]), patch.object(relay.time, 'monotonic', side_effect=lambda: clock[0]), patch.object(relay, 'report'):
                    worker = threading.Thread(target=serve)
                    worker.start()
                    frame = relay.HEADER.pack(49152, 3) + b'abc'
                    try:
                        sender.sendall(frame[:2])
                        for index in range(7):
                            clock[0] = index * 2
                            sender.sendall(frame[2:] + frame[:2])
                            self.assertEqual(target.recv(10), b'abc')
                            time.sleep(.02)
                        sender.sendall(frame[2:])
                        self.assertEqual(target.recv(10), b'abc')
                    finally:
                        sender.shutdown(socket.SHUT_RDWR)
                        worker.join(timeout=3)
                    self.assertFalse(worker.is_alive())
                    self.assertFalse(errors)


if __name__ == '__main__':
    unittest.main()
