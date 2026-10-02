"""Meaningful dataset leakage, grounding and future-training preflight checks."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'training/qwen-metal-additive-20261002'

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

VERIFY=module('verify_grounded',PACKAGE/'verify_grounded.py')
sys.modules['verify_grounded']=VERIFY
PREPARE=module('metal_grounded_prepare',PACKAGE/'prepare_grounded.py')
EVALUATE=module('metal_grounded_evaluate',PACKAGE/'evaluate_grounded.py')
TRAIN=module('metal_grounded_train',PACKAGE/'train_pilot.py')

class GroundedMetalTest(unittest.TestCase):
    def test_registered_pilot_and_all_translations_stay_in_source_partition(self):
        result=VERIFY.verify(PACKAGE,PACKAGE/'grounded-v3')
        self.assertEqual(result['counts']['sft_tokens'],{'train':53,'valid':16,'test':21})
        self.assertEqual(result['evaluation_count'],8)
        manifest=VERIFY.load(PACKAGE/'grounded-v3/manifest.json')
        self.assertEqual(len(manifest['source_assignment']),10)
        self.assertFalse(manifest['training_run'])
        provenance=VERIFY.rows(PACKAGE/'grounded-v3/provenance.jsonl')
        titanium=[r for r in provenance if r.get('case_id')=='ground-014']
        self.assertEqual({r['language'] for r in titanium},set(PREPARE.SYSTEM))
        self.assertEqual({r['split'] for r in titanium},{'test'})

    def test_changed_evidence_or_unsupported_quote_is_rejected(self):
        case=VERIFY.load(PACKAGE/'grounded-input/cases.json')[0]
        p=next(r for r in VERIFY.rows(PACKAGE/'grounded-v3/passages.jsonl') if r['source_id']==case['source_id'] and r['paragraph']==case['paragraph'])
        bad=copy.deepcopy(case);bad['evidence_quotes']=['An invented experimental observation.']
        with self.assertRaisesRegex(ValueError,'Supporting quotation missing'):
            PREPARE.validate_case(bad,p)
        bad=copy.deepcopy(case);bad['passage_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Case passage changed'):
            PREPARE.validate_case(bad,p)

    def test_notation_keeps_exponents_and_chemical_subscripts(self):
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            self.skipTest('Optional formatter HTML dependency not installed')
        html='<section id="Sec1"><h2>Thermal properties</h2><div class="html-p">A specimen has a rate of 10<sup>6</sup> K/s and contains Cu<sub>2</sub>O; this deliberately long scientific paragraph describes the study conditions without a formula image.</div></section>'
        accepted,_=PREPARE.extract_scientific(BeautifulSoup(html,'html.parser'),'fixture')
        self.assertIn('10⁶ K/s',accepted[0]['text'])
        self.assertIn('Cu₂O',accepted[0]['text'])
        self.assertNotIn('10 6',accepted[0]['text'])

    def test_preflight_rejects_a_different_model_revision_without_ml_imports(self):
        config=VERIFY.load(PACKAGE/'lora-pilot.json');config['revision']='unregistered'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config.json';path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError,'profile mismatch'):
                TRAIN.preflight(path)

    def test_corrupted_export_cannot_be_loaded_for_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'export';shutil.copytree(PACKAGE/'grounded-v3',output)
            path=output/'sft_tokens/train.jsonl';data=VERIFY.rows(path)
            data[0]['labels'][0]=data[0]['input_ids'][0]
            path.write_text(''.join(json.dumps(r)+'\n' for r in data))
            with self.assertRaisesRegex(ValueError,'Changed output'):
                VERIFY.verify(PACKAGE,output)

    def test_prediction_audit_requires_full_coverage_and_never_invents_scientific_scores(self):
        export=PACKAGE/'grounded-v3'
        questions=VERIFY.rows(export/'evaluation/questions.jsonl')
        predictions=[{'id':r['id'],'response':'A response without a source citation.'} for r in questions]
        report,worksheet=EVALUATE.evaluate(export,predictions)
        self.assertEqual(report['citation_presence_rate'],0)
        self.assertIsNone(report['manual_mean_scores'])
        self.assertFalse(report['complete_manual_review'])
        with self.assertRaisesRegex(ValueError,'Incomplete evaluation coverage'):
            EVALUATE.evaluate(export,predictions[:-1])
        with self.assertRaisesRegex(ValueError,'Duplicate/unknown'):
            EVALUATE.evaluate(export,predictions+[predictions[0]])
        reviews=[{**r,'scores':dict.fromkeys(EVALUATE.FIELDS,2),'reviewer':'independent-reviewer-id'} for r in worksheet]
        reviews[0]['prediction_sha256']='wrong-prediction'
        with self.assertRaisesRegex(ValueError,'different prediction'):
            EVALUATE.evaluate(export,predictions,reviews)

    def test_near_duplicate_detector_handles_repeated_prose(self):
        a='Thermal conductivity depends on powder packing and contact between adjacent particles.'
        self.assertEqual(PREPARE.shingle_similarity(a,a),1)
        self.assertEqual(PREPARE.shingle_similarity(a,'Inspection uncertainty requires calibration of a tomographic sensor.'),0)

if __name__=='__main__':
    unittest.main()
