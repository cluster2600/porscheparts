"""UNRUN offline fixtures for the exact T003 one_model implementation.

Only a later separately authorized call may load the two verified source buffers.
No Z3, Session, run_fixed_toys, owner, subprocess or native input is called here.
"""
import hashlib
from pathlib import Path
import types
import unittest


E = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering')
TRANSPORT = E / 'head-star-current24-qfnra-toy-transport-prep-003/check_toy_sessions.py'
TRANSPORT_SHA = '3619b5316cf23398ed479ebf724a1159bb816ce3bafb85ad93c40b67b7df4990'
PROTOCOL = E / 'head-star-current24-coupled-qfnra-prep-001/qfnra_protocol.py'
PROTOCOL_SHA = '9b5885a35bfbc681c0354e937b9f57621b3d8137adc25b4e2ba455e86ce59785'
NAME = 'c001_n1_x'
ALIASES = ['toy_rational_assert_0']
REAL = '(define-fun c001_n1_x () Real (/ 3.0 2.0))'
BOOL = '(define-fun toy_rational_assert_0 () Bool (= c001_n1_x (/ 3.0 2.0)))'
CAPTURED_MODEL = '(\n  (define-fun c001_n1_x () Real\n    (/ 3.0 2.0))\n  (define-fun toy_rational_assert_0 () Bool\n    (= c001_n1_x (/ 3.0 2.0)))\n)\n'
EXPECTED_VALUE = dict(kind='rational', numerator='3', denominator='2')


def load_exact_source(path, digest, size, namespace):
    raw = path.read_bytes()
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Fixture source identity changed: ' + str(path))
    module = types.ModuleType(namespace)
    module.__file__ = str(path)
    # Future authorized fixture execution only; exact buffers, no cached pyc.
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def model(*definitions):
    return '(\n' + '\n'.join(definitions) + '\n)\n'


class OneModelFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = load_exact_source(PROTOCOL, PROTOCOL_SHA, 12459, 'offline_protocol_exact')
        cls.transport = load_exact_source(TRANSPORT, TRANSPORT_SHA, 22291, 'offline_transport003_exact')

    def value(self, text, aliases=None):
        return self.transport.one_model(self.protocol, text, NAME, ALIASES if aliases is None else aliases)

    def refuse(self, text):
        with self.assertRaises(self.transport.ToyRefusal):
            self.value(text)

    def test_captured_rational_model(self):
        self.assertEqual(self.value(CAPTURED_MODEL), EXPECTED_VALUE)

    def test_model_prefix_and_reordered_definitions(self):
        text = '(model\n' + BOOL + '\n' + REAL + '\n)'
        self.assertEqual(self.value(text), EXPECTED_VALUE)

    def test_two_exact_known_aliases(self):
        second = '(define-fun toy_rational_assert_1 () Bool (> c001_n1_x 0))'
        self.assertEqual(self.value(model(second, REAL, BOOL), ALIASES + ['toy_rational_assert_1']), EXPECTED_VALUE)

    def test_extra_definition(self):
        for extra in ['(define-fun foreign_real () Real 0)', '(define-fun foreign_bool () Bool true)']:
            with self.subTest(extra=extra):
                self.refuse(model(REAL, BOOL, extra))

    def test_missing_definition(self):
        for retained in [REAL, BOOL]:
            with self.subTest(retained=retained):
                self.refuse(model(retained))

    def test_duplicate_definition(self):
        for duplicated in [REAL, BOOL]:
            with self.subTest(duplicated=duplicated):
                self.refuse(model(duplicated, duplicated))

    def test_unknown_name_at_exact_count(self):
        for real, boolean in [(REAL.replace(NAME, 'foreign_real'), BOOL),
                              (REAL, BOOL.replace(ALIASES[0], 'foreign_bool'))]:
            with self.subTest(real=real, boolean=boolean):
                self.refuse(model(real, boolean))

    def test_wrong_sort(self):
        for real, boolean in [(REAL.replace('() Real', '() Bool'), BOOL),
                              (REAL, BOOL.replace('() Bool', '() Real'))]:
            with self.subTest(real=real, boolean=boolean):
                self.refuse(model(real, boolean))

    def test_wrong_arity(self):
        for real, boolean in [(REAL.replace('() Real', '((arg Real)) Real'), BOOL),
                              (REAL, BOOL.replace('() Bool', '((arg Real)) Bool'))]:
            with self.subTest(real=real, boolean=boolean):
                self.refuse(model(real, boolean))


if __name__ == '__main__':
    unittest.main()
