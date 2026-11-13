import importlib.util
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'twins/962-cylinder-head-f0/source/physics_witness/exact_end181_forces.py'
spec = importlib.util.spec_from_file_location('exact_end181', SOURCE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ExactEnd181Tests(unittest.TestCase):
    def test_closed_form_thermal_extension_and_shear_controls(self):
        audit.controls()

    def test_unbound_capture_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'native-execution.json').write_text('{}')
            output = root/'result.json'
            with self.assertRaises(AssertionError):
                audit.main(root, output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
