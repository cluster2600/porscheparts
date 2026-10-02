#!/usr/bin/env python3
"""Explicit GitHub read commands and Git credential transport for two repositories."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
from urllib.parse import quote

REPOSITORIES = {
    'cluster2600/porscheparts': 1349420480,
    'cluster2600/porschefanatics.com': 1336775701,
}
AUTH_WRAPPER = Path('/Users/maxime/.local/bin/openbao-github')
AUTH_SHA256 = 'd71cf774a0f0cba1eb2e199db38438c11a5df71d68212ea37038d45820c5b052'
GH = '/opt/homebrew/bin/gh'
MAX_REQUEST = 16384
MAX_RESPONSE = 4 * 1024 * 1024
ACTIONS = ('check', 'repo', 'file', 'branches', 'prs', 'issues', 'pr', 'issue', 'runs', 'run')
REPO_FIELDS = ('id', 'full_name', 'private', 'default_branch', 'description',
               'html_url', 'visibility', 'archived', 'disabled', 'size', 'pushed_at', 'updated_at')


def public_result(value):
    # Private repository metadata and Contents responses can include temporary
    # access credentials. They are never needed for the CLI's JSON reads.
    if isinstance(value, dict):
        return {key: public_result(item) for key, item in value.items()
                if key not in ('temp_clone_token', 'download_url', 'access_token',
                               'refresh_token', 'token', 'client_secret')}
    if isinstance(value, list):
        return [public_result(item) for item in value]
    return value


def validate_request(request):
    if not isinstance(request, dict):
        raise ValueError('request must be an object')
    action = request.get('action')
    if action == 'credential':
        if set(request) != {'action', 'operation', 'protocol', 'host', 'path'}:
            raise ValueError('unexpected credential fields')
        if request['operation'] != 'get' or request['protocol'] != 'https' or request['host'] != 'github.com':
            raise ValueError('credential request is outside the allowlist')
        path = request['path']
        if not isinstance(path, str):
            raise ValueError('invalid repository path')
        repo = path[:-4] if path.endswith('.git') else path
        if repo not in REPOSITORIES:
            raise ValueError('repository is outside the allowlist')
        return repo, f'repos/{repo}'
    if action not in ACTIONS or set(request) - {'action', 'repo', 'target', 'ref'}:
        raise ValueError('action or fields are outside the allowlist')
    repo = request.get('repo')
    if repo not in REPOSITORIES:
        raise ValueError('repository is outside the allowlist')
    base = f'repos/{repo}'
    target, ref = request.get('target'), request.get('ref')
    if action == 'file':
        if not isinstance(target, str) or not 0 < len(target) <= 512:
            raise ValueError('file path is required')
        if any(part in ('', '.', '..') for part in target.split('/')) or not re.fullmatch(r'[A-Za-z0-9_./ -]+', target):
            raise ValueError('file path must be relative without traversal')
        if ref is not None and (not isinstance(ref, str) or not re.fullmatch(r'[A-Za-z0-9_./-]{1,160}', ref) or '..' in ref):
            raise ValueError('invalid ref')
        return repo, base + '/contents/' + quote(target, safe='/') + ('?ref=' + quote(ref, safe='') if ref else '')
    if ref is not None:
        raise ValueError('ref is only supported for file')
    if action in ('pr', 'issue', 'run'):
        if not isinstance(target, str) or not re.fullmatch(r'[1-9][0-9]{0,14}', target):
            raise ValueError('a positive numeric identifier is required')
        segment = {'pr': 'pulls', 'issue': 'issues', 'run': 'actions/runs'}[action]
        return repo, base + '/' + segment + '/' + target
    if target is not None:
        raise ValueError('unexpected target')
    suffix = {'check': '', 'repo': '', 'branches': '/branches?per_page=100',
              'prs': '/pulls?state=all&per_page=100', 'issues': '/issues?state=all&per_page=100',
              'runs': '/actions/runs?per_page=100'}[action]
    return repo, base + suffix


def load_auth():
    info = AUTH_WRAPPER.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise RuntimeError('unsafe authentication wrapper permissions')
    source = AUTH_WRAPPER.read_bytes()
    if hashlib.sha256(source).hexdigest() != AUTH_SHA256:
        raise RuntimeError('authentication wrapper hash mismatch')
    module = types.ModuleType('approved_github_auth')
    module.__file__ = str(AUTH_WRAPPER)
    exec(compile(source, str(AUTH_WRAPPER), 'exec'), module.__dict__)
    return module


def github_get(token, endpoint):
    # A fresh gh config avoids aliases, extensions, stored credentials and pagers.
    with tempfile.TemporaryDirectory(prefix='openclaw-github-config-') as directory:
        environment = {
            'HOME': str(Path.home()), 'PATH': '/usr/bin:/bin:/opt/homebrew/bin',
            'GH_TOKEN': token, 'GH_HOST': 'github.com', 'GH_CONFIG_DIR': directory,
            'GH_PROMPT_DISABLED': '1', 'GH_PAGER': 'cat', 'NO_COLOR': '1',
        }
        result = subprocess.run([GH, 'api', '--hostname', 'github.com', '--method', 'GET', endpoint],
                                env=environment, capture_output=True, timeout=40)
    if result.returncode or len(result.stdout) > MAX_RESPONSE:
        raise RuntimeError('GitHub read failed; diagnostics withheld')
    return json.loads(result.stdout)


def dispatch(request, output=sys.stdout):
    repo, endpoint = validate_request(request)  # Reject before any authentication.
    auth = load_auth()
    session = auth.login()
    try:
        token = auth.read_github_token(session)
        metadata = github_get(token, f'repos/{repo}')
        if metadata.get('full_name') != repo or metadata.get('id') != REPOSITORIES[repo]:
            raise RuntimeError('GitHub repository identity mismatch')
        if request['action'] == 'credential':
            # The caller must connect stdout directly to Git's credential pipe.
            output.write('username=x-access-token\npassword=' + token + '\n\n')
        else:
            if endpoint == f'repos/{repo}':
                result = {key: metadata[key] for key in REPO_FIELDS if key in metadata}
                result['permissions'] = {key: metadata.get('permissions', {}).get(key)
                                         for key in ('pull', 'push')}
            else:
                result = github_get(token, endpoint)
            json.dump(public_result(result), output, ensure_ascii=False)
            output.write('\n')
    finally:
        auth.revoke_token(session)


def ssh_request(request):
    validate_request(request)
    home = Path.home()
    command = ['ssh', '-T', '-i', str(home / '.ssh/id_openclaw_github'),
               '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'ForwardAgent=no', '-o', 'ConnectTimeout=8',
               '-o', 'HostKeyAlias=openclaw-github-mac',
               '-o', 'UserKnownHostsFile=' + str(home / '.ssh/openclaw_github_known_hosts'),
               '-p', '2220', 'maxime@127.0.0.1', 'openclaw-github']
    # Do not capture stdout: credential output belongs exclusively to Git.
    return subprocess.run(command, input=json.dumps(request).encode(), timeout=100).returncode


def credential_request(operation, stream):
    if operation in ('store', 'erase'):
        return None  # Never persist a credential.
    if operation != 'get':
        raise ValueError('unsupported credential operation')
    fields = {}
    body = stream.read(MAX_REQUEST + 1)
    if len(body) > MAX_REQUEST:
        raise ValueError('credential request too large')
    for line in body.splitlines():
        if not line:
            break
        key, separator, value = line.partition('=')
        # Git 2.53 supplies repeatable capability and HTTP challenge metadata.
        # These do not change the exact protocol/host/path credential scope.
        if separator and key in ('capability[]', 'wwwauth[]'):
            continue
        if not separator or key in fields or key not in ('protocol', 'host', 'path', 'username'):
            raise ValueError('invalid credential input')
        fields[key] = value
    request = dict(action='credential', operation='get', **{key: fields.get(key) for key in ('protocol', 'host', 'path')})
    validate_request(request)
    return request


def main():
    try:
        if sys.argv[1:] == ['--dispatch']:
            if os.environ.get('SSH_ORIGINAL_COMMAND', '') not in ('', 'openclaw-github'):
                raise ValueError('SSH command is outside the allowlist')
            body = sys.stdin.read(MAX_REQUEST + 1)
            if len(body) > MAX_REQUEST:
                raise ValueError('request too large')
            dispatch(json.loads(body))
            return 0
        if sys.argv[1:2] == ['credential']:
            if len(sys.argv) != 3:
                raise ValueError('credential operation is required')
            request = credential_request(sys.argv[2], sys.stdin)
            return ssh_request(request) if request else 0
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('action', choices=ACTIONS)
        parser.add_argument('repo', choices=tuple(REPOSITORIES))
        parser.add_argument('target', nargs='?')
        parser.add_argument('--ref')
        args = parser.parse_args()
        request = {key: value for key, value in vars(args).items() if value is not None}
        return ssh_request(request)
    except Exception:
        print('GitHub bridge request failed; check allowed repository, action and SSH service.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
