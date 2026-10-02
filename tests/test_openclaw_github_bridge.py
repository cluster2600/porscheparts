import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

path = Path(__file__).parents[1] / 'deploy/openbao/openclaw-github.py'
spec = importlib.util.spec_from_file_location('github_bridge', path)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
REPO = 'cluster2600/porscheparts'


class GithubBridgeTests(unittest.TestCase):
    def test_private_repository_credentials_never_enter_json_output(self):
        auth = Mock()
        auth.login.return_value = 'stub-session'
        auth.read_github_token.return_value = 'stub-source-credential'
        metadata = dict(full_name=REPO, id=bridge.REPOSITORIES[REPO],
                        temp_clone_token='stub-temporary-credential',
                        permissions={'pull': True, 'push': True})
        output = io.StringIO()
        with patch.object(bridge, 'load_auth', return_value=auth), patch.object(bridge, 'github_get', return_value=metadata):
            bridge.dispatch(dict(action='check', repo=REPO), output)
        result = json.loads(output.getvalue())
        self.assertEqual(result['full_name'], REPO)
        self.assertNotIn('temp_clone_token', result)
        nested = [dict(head=dict(repo=metadata), download_url='https://example.invalid/?token=stub', content='data')]
        cleaned = bridge.public_result(nested)
        self.assertNotIn('download_url', cleaned[0])
        self.assertNotIn('temp_clone_token', cleaned[0]['head']['repo'])
        self.assertEqual(cleaned[0]['content'], 'data')

    def test_allowed_repository_ids_and_read_routes(self):
        self.assertEqual(bridge.REPOSITORIES['cluster2600/porschefanatics.com'], 1336775701)
        self.assertEqual(bridge.validate_request(dict(action='file', repo=REPO, target='docs/a b.md', ref='codex/test')),
                         (REPO, 'repos/' + REPO + '/contents/docs/a%20b.md?ref=codex%2Ftest'))
        self.assertEqual(bridge.validate_request(dict(action='pr', repo=REPO, target='92'))[1], 'repos/' + REPO + '/pulls/92')

    def test_invalid_input_is_rejected_before_authentication(self):
        invalid = [dict(action='repo', repo='cluster2600/other'), dict(action='api', repo=REPO),
                   dict(action='repo', repo=REPO, token='not-a-secret'),
                   dict(action='pr', repo=REPO, target='1;command')]
        invalid += [dict(action='file', repo=REPO, target=value) for value in
                    ('../secret', '/absolute', 'a/../b', 'a//b', 'a/./b', 'a%2fb', 'a\\b', 'a\nb')]
        with patch.object(bridge, 'load_auth') as auth:
            for request in invalid:
                with self.subTest(request=request), self.assertRaises(ValueError):
                    bridge.dispatch(request, io.StringIO())
            auth.assert_not_called()

    def test_git_credential_accepts_only_two_exact_https_paths(self):
        for repo in bridge.REPOSITORIES:
            request = bridge.credential_request('get', io.StringIO(
                f'capability[]=authtype\nprotocol=https\nhost=github.com\npath={repo}.git\n'
                'wwwauth[]=Basic realm="GitHub"\nwwwauth[]=ignored challenge\n\n'))
            self.assertEqual(bridge.validate_request(request)[0], repo)
        for protocol, host, path in [('http', 'github.com', REPO), ('https', 'github.com:443', REPO),
                                    ('https', 'github.com', REPO + '/other'), ('https', 'evil.test', REPO)]:
            with self.assertRaises(ValueError):
                bridge.credential_request('get', io.StringIO(f'protocol={protocol}\nhost={host}\npath={path}\n'))
        self.assertIsNone(bridge.credential_request('store', io.StringIO('password=stub')))
        self.assertIsNone(bridge.credential_request('erase', io.StringIO('')))

    def test_stub_credential_output_is_git_protocol_and_session_is_revoked(self):
        auth = Mock()
        auth.login.return_value = 'stub-session'
        auth.read_github_token.return_value = 'stub-credential-not-a-secret'
        metadata = dict(full_name=REPO, id=bridge.REPOSITORIES[REPO])
        request = dict(action='credential', operation='get', protocol='https', host='github.com', path=REPO + '.git')
        output = io.StringIO()
        with patch.object(bridge, 'load_auth', return_value=auth), patch.object(bridge, 'github_get', return_value=metadata):
            bridge.dispatch(request, output)
        self.assertEqual(output.getvalue(), 'username=x-access-token\npassword=stub-credential-not-a-secret\n\n')
        auth.revoke_token.assert_called_once_with('stub-session')

    def test_repository_identity_mismatch_releases_no_credential(self):
        auth = Mock()
        auth.login.return_value = 'stub-session'
        auth.read_github_token.return_value = 'stub-credential-not-a-secret'
        request = dict(action='credential', operation='get', protocol='https', host='github.com', path=REPO)
        output = io.StringIO()
        with patch.object(bridge, 'load_auth', return_value=auth), patch.object(bridge, 'github_get', return_value=dict(full_name=REPO, id=1)):
            with self.assertRaises(RuntimeError):
                bridge.dispatch(request, output)
        self.assertEqual(output.getvalue(), '')
        auth.revoke_token.assert_called_once_with('stub-session')


if __name__ == '__main__':
    unittest.main()
