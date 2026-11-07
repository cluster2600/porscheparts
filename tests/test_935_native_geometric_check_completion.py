"""A terminal diagnostic is distinct from a passed mesh or a truncated log."""
import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1]/'docs/research/935-native-geometric-check-20261107/source/check_recovered_mesh.py'
spec = importlib.util.spec_from_file_location('native_check_completion', SOURCE)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class NativeCheckCompletionTests(unittest.TestCase):
    def test_normal_and_rejected_terminal_diagnostics_are_complete(self):
        self.assertTrue(worker.completed({'exit_code': 0, 'timeout': False}, 'Mesh OK.\nEnd\n'))
        self.assertTrue(worker.completed({'exit_code': 1, 'timeout': False}, 'Failed 2 mesh checks.\nEnd\n'))

    def test_timeout_or_signal_cannot_be_promoted_by_a_terminal_marker(self):
        self.assertFalse(worker.completed({'exit_code': 0, 'timeout': True}, 'Mesh OK.\nEnd\n'))
        for code in (-15, 137, 255):
            with self.subTest(code=code):
                self.assertFalse(worker.completed({'exit_code': code, 'timeout': False}, 'Mesh OK.\nEnd\n'))

    def test_success_status_and_statistics_do_not_replace_the_end_marker(self):
        for text in ('Mesh stats\n12981388 cells\n', 'Mesh OK.\n', 'End of topology checks\n'):
            with self.subTest(text=text):
                self.assertFalse(worker.completed({'exit_code': 0, 'timeout': False}, text))


if __name__ == '__main__':
    unittest.main()
