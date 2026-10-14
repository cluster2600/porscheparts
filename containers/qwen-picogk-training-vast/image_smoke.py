"""Contrôles CPU sans modèle, CUDA, données privées ni entraînement."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def main():
    inputs = json.loads((HERE/'inputs.json').read_text())
    for name, expected in inputs['image_files_sha256'].items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest() == expected, name
    spec = importlib.util.spec_from_file_location('qwen_image_training', HERE/'train.py')
    trainer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trainer)
    assert 'mlx.core' not in sys.modules
    checks = 0
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder).resolve()
        trainer.ROOT = root
        corpus = root/'train.jsonl'
        payload = (json.dumps({'messages': [{'role': 'user', 'content': 'Synthetic request'},
                   {'role': 'assistant', 'content': 'Synthetic response'}]})+'\n').encode()
        corpus.write_bytes(payload)
        expected = hashlib.sha256(payload).hexdigest()
        assert trainer.supplemental_corpus(corpus, expected) == (payload, 1)
        assert trainer.workspace_input(corpus) == corpus
        checks += 2
        for bad_path, bad_hash in ((corpus, 'wrong'), (corpus, None), (None, expected)):
            try: trainer.supplemental_corpus(bad_path, bad_hash)
            except ValueError: checks += 1
            else: raise AssertionError('Invalid corpus accepted.')
        corpus.write_bytes(b'{"messages":[]}\n')
        try: trainer.supplemental_corpus(corpus, hashlib.sha256(corpus.read_bytes()).hexdigest())
        except ValueError: checks += 1
        else: raise AssertionError('Empty chat accepted.')
        cli = ('import sys; from pathlib import Path; sys.path.insert(0,sys.argv.pop(1)); '
               'import train; train.ROOT=Path(sys.argv.pop(1)); train.main()')
        result = subprocess.run([sys.executable, '-c', cli, str(HERE), str(root),
                  '--name', 'rejected', '--iters', '1', '--corpus', str(corpus),
                  '--corpus-sha256', 'wrong', '--base-profile', str(root/'missing-profile.json')],
                  capture_output=True, text=True, timeout=30)
        assert result.returncode == 2 and 'corpus SHA-256 mismatch' in result.stderr, result.stderr
        assert not (root/'runs').exists()
        checks += 1
        corpus.unlink()
        corpus.symlink_to(HERE/'train.py')
        for path in (corpus, HERE/'train.py'):
            try: trainer.workspace_input(path)
            except ValueError: checks += 1
            else: raise AssertionError('Escaping input accepted.')
        final = root/'evaluation/final.json'
        final.parent.mkdir()
        final.write_text('{}')
        try: trainer.workspace_input(final)
        except ValueError: checks += 1
        else: raise AssertionError('Final task accepted for training.')
        profile = root/'base.json'
        profile.write_text('{}')
        try: trainer.base_runtime.verify_base(root, profile, expected_profile_sha256=trainer.PROFILE_SHA256)
        except ValueError as error:
            assert 'SHA-256 mismatch' in str(error)
            checks += 1
        else: raise AssertionError('Changed base profile accepted.')
        dangling = root/'model7b-manifest.json'
        dangling.symlink_to(root.parent/'never-write-here.json')
        cli = ('import importlib.util,sys; from pathlib import Path; '
               's=importlib.util.spec_from_file_location("download",sys.argv[1]); '
               'd=importlib.util.module_from_spec(s); s.loader.exec_module(d); '
               'd.ROOT=Path(sys.argv[2]); d.DESTINATION=d.ROOT/"model7b"; '
               'sys.argv=[sys.argv[1]]; d.main()')
        result = subprocess.run([sys.executable, '-c', cli, str(HERE/'download-model7b.py'), str(root)],
                                capture_output=True, text=True, timeout=30)
        assert result.returncode != 0 and 'Preserve the existing manifest' in result.stderr, result.stderr
        assert dangling.is_symlink() and not (root.parent/'never-write-here.json').exists()
        checks += 1
    result = subprocess.run([sys.executable, '-O', str(HERE/'download-model7b.py')],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and 'optimization must remain disabled' in result.stderr, result.stderr
    checks += 1
    for script in ('train.py', 'download-model7b.py'):
        result = subprocess.run([sys.executable, str(HERE/script), '--help'],
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        checks += 1
    print(json.dumps({'status': 'passed', 'checks': checks, 'model_loaded': False,
                      'gpu_tested': False, 'training_started': False}))


if __name__ == '__main__':
    main()
