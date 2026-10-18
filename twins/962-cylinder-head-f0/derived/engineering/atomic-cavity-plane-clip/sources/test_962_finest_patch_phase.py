"""The phase companion preserves evidence and restores frozen metadata state."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json

PATH = Path(__file__).resolve().parents[1]/'twins/962-cylinder-head-f0/source/run_finest_patch_phase.py'
SPEC = importlib.util.spec_from_file_location('patch_phase_test', PATH)
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


class PatchPhaseGuards(unittest.TestCase):
    def test_unreviewed_authority_or_changed_controls_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = Path(tmp)/'child'
            card = dict(input_sha256={}, root_authorized=False, root_and_peer_review_complete=True,
                        phase='head', image_id=M.B.IMAGE, automatic_retry=False, limits={})
            child.write_text(json.dumps(card))
            with self.assertRaisesRegex(ValueError, 'Reviewed fixed phase'):
                M.validated_child(child, M.B.digest(child))
            card['root_authorized'] = True; child.write_text(json.dumps(card))
            with self.assertRaisesRegex(ValueError, 'phase controls changed'):
                M.validated_child(child, M.B.digest(child))

    def test_input_drift_refuses_before_output_and_native_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); source = root/'input'; source.write_bytes(b'original')
            pins = {'input': M.B.digest(source)}; child = root/'child'; child.write_text('{}')
            source.write_bytes(b'changed'); output = root/'work/962-engineering/new'
            with patch.object(M, 'ROOT', root), patch.object(M, 'validated_child', return_value=({}, pins)), \
                    patch.object(M.B, 'execute') as native:
                with self.assertRaisesRegex(ValueError, 'Input drift'):
                    M.run(child, M.B.digest(child), output)
            native.assert_not_called(); self.assertFalse(output.exists())

    def test_native_observer_failure_restores_format_and_records_no_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); child = root/'child'; child.write_text('{}')
            card = dict(phase='head', jobs=[dict(label='test', entrypoint='/finest-endpoint',
                arguments=['/input.bin', '/out/native'], read_only_mounts={}, expected_returncodes=[0, 3])])
            output = root/'work/962-engineering/new'
            with patch.object(M, 'ROOT', root), patch.object(M, 'validated_child', return_value=(card, {})), \
                    patch.object(M.B, 'execute', side_effect=TimeoutError('observer')):
                self.assertEqual(M.run(child, M.B.digest(child), output), 2)
            self.assertEqual(M.B.INSPECT, M.M.ORIGINAL_FORMAT)
            result = json.loads((output/'phase-summary.json').read_text())
            self.assertFalse(result['procedural_phase_finished'])
            self.assertFalse(result['head_surface_admitted'])
            self.assertEqual(result['error'], 'TimeoutError: observer')


if __name__ == '__main__':
    unittest.main()
