"""Exact source/deck deltas and retained analytic gates; no solver."""
import ast
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'carrier-wholepart-release-feasibility-001'


class Checks(unittest.TestCase):
    def test_preparer_only_changes_output_card(self):
        old=(OLD/'prepare.py').read_text()
        self.assertEqual(old.count("'*NODE FILE'"),1)
        self.assertEqual((HERE/'prepare.py').read_text(),old.replace("'*NODE FILE'","'*NODE OUTPUT,DOUBLE'"))
    def test_four_actual_deck_lines_only(self):
        old=(OLD/'prepared-001/wholepart-release.inp').read_bytes();new=(HERE/'prepared-001/wholepart-release.inp').read_bytes()
        self.assertEqual(old.count(b'*NODE FILE'),4)
        self.assertEqual(new,old.replace(b'*NODE FILE',b'*NODE OUTPUT,DOUBLE'))
        cards=[line for line in new.splitlines()if line.startswith((b'*NODE FILE',b'*NODE OUTPUT',b'*EL FILE',b'*EL OUTPUT',b'*CONTACT FILE',b'*CONTACT OUTPUT',b'*TRANSFORM'))]
        self.assertEqual(cards,[b'*NODE OUTPUT,DOUBLE']*4)
        for name in ('mesh.inp','quadratic-temperature.inc'):self.assertEqual((HERE/'prepared-001'/name).read_bytes(),(OLD/'prepared-001'/name).read_bytes())
    def test_execution_supervisor_caller_unchanged(self):
        self.assertEqual((HERE/'run.py').read_bytes(),(OLD/'run.py').read_bytes())
    def test_numeric_helpers_and_analytic_gate_unchanged(self):
        old=ast.parse((OLD/'assess.py').read_text());new=ast.parse((HERE/'assess.py').read_text())
        for name in ('circle','metrics'):
            get=lambda tree:next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
            self.assertEqual(ast.dump(get(old)),ast.dump(get(new)))
        gate=lambda tree:[ast.dump(n.value)for n in ast.walk(tree)if isinstance(n,ast.keyword)and n.arg=='analytic_pass']
        self.assertEqual(gate(old),gate(new));self.assertEqual(len(gate(new)),1)


if __name__=='__main__':unittest.main()
