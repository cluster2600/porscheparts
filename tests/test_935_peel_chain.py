"""Cell deletions must keep their identity in the original numerical parent."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np


SOURCE = Path(__file__).resolve().parents[1]/'docs/research/935-current-peel-admission-20261107/source/check_peel_chain.py'
spec = importlib.util.spec_from_file_location('peel_chain_contract', SOURCE)
chain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chain)


class PeelChainTests(unittest.TestCase):
    def test_two_generation_deletions_keep_original_cell_identity(self):
        first = chain.kept_rows(5, np.array([1, 3]))
        final = first[chain.kept_rows(len(first), np.array([1]))]
        np.testing.assert_array_equal(first, [0, 2, 4])
        np.testing.assert_array_equal(final, [0, 4])

    def test_refuses_duplicate_ambiguous_and_out_of_range_indices(self):
        for removed in (np.array([1, 1]), np.array([-1]), np.array([5]),
                        np.array([1.5]), np.array([True]), np.array([[1]]),
                        np.array([2**64-1], dtype=np.uint64)):
            with self.subTest(removed=removed.tolist()):
                with self.assertRaises(AssertionError):
                    chain.kept_rows(5, removed)


if __name__ == '__main__':
    unittest.main()
