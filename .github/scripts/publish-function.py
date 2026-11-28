"""Publish the verified artifact from the current Actions run to an existing function."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

# Function ID, entrypoint, memory (GiB), timeout and named tag.
TARGETS = {
    'testing': ('d4e8q2rnrsp61kcn3n2c', 'shared_alice_serverless.handler', 2, '5s', 'shared-pilot'),
    'api-testing': ('d4ejp5195b9ehust1eed', 'app_serverless.handler', 1, '30s', 'api-testing'),
    'production': ('d4enqm5nkmh02evh4rv8', 'alice_serverless.handler', 8, '5s', None),
}
FOLDER = 'b1gft06jh7u3p9509dqb'
RUNTIME_SA = 'aje3s4fcje2i3312p0tq'
YDB = {
    'CHESS_STORAGE': 'ydb',
    'YDB_ENDPOINT': 'grpcs://ydb.serverless.yandexcloud.net:2135',
    'YDB_DATABASE': '/ru-central1/b1gtsmd34503k985ndgb/etnkf4jq5020ksn7e0go',
    'YDB_TABLE_PREFIX': 'test_chess_',
    'YDB_METADATA_CREDENTIALS': '1',
}


def yc(*args):
    value = subprocess.check_output(['yc', *args, '--folder-id', FOLDER, '--format', 'json'], text=True)
    return json.loads(value) if value.strip() else None


def expected_environment(target, current):
    if target == 'production':
        return {'DEBUG': 'True', 'COUNT': '1'}
    if target == 'api-testing':
        return YDB
    # Enrollment is managed on the private pilot. Never print or widen the allowlist.
    owner = current.get('SHARED_DIALOGS_ALLOWED_OWNER', '')
    if not re.fullmatch(r'dialogs:[0-9a-f]{64}', owner):
        raise ValueError('Missing or invalid tester allowlist on the current testing version')
    environment = {
        **YDB,
        'DEBUG': 'True',
        'COUNT': '1',
        'LOG_LEVEL': 'WARNING',
        'SHARED_GAMES_ENABLED': 'true',
        'SHARED_ALICE_AUTH': 'dialogs_iam',
        'SHARED_DIALOGS_ALLOWED_OWNER': owner,
        'SHARED_DIALOGS_SKILL_ID': '462df9a1-7fb1-41d4-8082-810aad12ce69',
        'SHARED_DIALOGS_FUNCTION_ID': TARGETS['testing'][0],
    }
    # Отдельный допуск анонимного приложения сохраняется только если уже задан.
    application = current.get('SHARED_DIALOGS_ALLOWED_APPLICATION_OWNER')
    if application is not None:
        if not re.fullmatch(r'dialogs-application:[0-9a-f]{64}', application):
            raise ValueError('Invalid anonymous application allowlist')
        environment['SHARED_DIALOGS_ALLOWED_APPLICATION_OWNER'] = application
    return environment


def publish():
    target = os.environ['TARGET']
    fid, entry, memory, timeout, tag = TARGETS[target]
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('DEPLOY_FOLDER') != FOLDER:
        raise ValueError('Publication requires GitHub Actions and the configured folder')
    bundle = Path('dist/function.zip')
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    sha = os.environ['GITHUB_SHA']
    run_id = os.environ['GITHUB_RUN_ID']
    desc = f'GitHub Actions {run_id} commit {sha} zip-sha256 {digest}'
    bucket = os.environ['DEPLOY_BUCKET']
    key = f'github-actions/{target}/{sha}/{digest}.zip'

    def active(active_tag):
        return yc('serverless', 'function', 'version', 'get-by-tag', '--function-id', fid, '--tag', active_tag)

    current = active('$latest')
    sa = RUNTIME_SA if target != 'production' else None
    environment = expected_environment(target, current.get('environment', {}))
    expected = {
        'function_id': fid,
        'entrypoint': entry,
        'runtime': 'python314',
        'execution_timeout': timeout,
        'resources': {'memory': str(memory * 1024**3)},
        'concurrency': '1',
        'environment': environment,
        'service_account_id': sa,
        'log_options': {'folder_id': FOLDER},
        'status': 'ACTIVE',
    }

    def verify(version):
        mismatches = [name for name, value in expected.items() if version.get(name) != value]
        if mismatches or (tag and tag not in version.get('tags', [])):
            raise RuntimeError(f'Unexpected {target} version configuration: {mismatches} (also check tags)')

    verify(current)
    if current.get('description') != desc:
        acl = ['--grant-full-control', f'id="{os.environ["DEPLOYER_ID"]}"']
        if sa:
            acl += ['--grant-read', f'id="{sa}"']
        yc('storage', 's3api', 'put-object', '--bucket', bucket, '--key', key, '--body', str(bundle.resolve()), *acl)
        flags = ['--service-account-id', sa] if sa else []
        if tag:
            flags += ['--tags', tag]
        yc(
            'serverless',
            'function',
            'version',
            'create',
            '--function-id',
            fid,
            '--runtime',
            'python314',
            '--entrypoint',
            entry,
            '--memory',
            f'{memory}GB',
            '--execution-timeout',
            timeout,
            '--concurrency',
            '1',
            '--log-folder-id',
            FOLDER,
            '--environment',
            ','.join(f'{k}={v}' for k, v in environment.items()),
            '--package-bucket-name',
            bucket,
            '--package-object-name',
            key,
            '--package-sha256',
            digest,
            '--description',
            desc,
            *flags,
        )
    published = active('$latest')
    verify(published)
    if published.get('description') != desc or (tag and active(tag)['id'] != published['id']):
        raise RuntimeError('Published version or active tag does not match this run')
    with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as summary:
        summary.write(
            f'**{target}** · `{entry}`\n\nCommit `{sha}` · ZIP SHA-256 `{digest}`\n\n'
            f'Active version `{published["id"]}` · tags `{", ".join(published["tags"])}`\n'
        )


if __name__ == '__main__':
    publish()
