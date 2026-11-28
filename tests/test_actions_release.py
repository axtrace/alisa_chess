"""Exercise the publish sequence with a fake yc client, including rollout guards."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'publish_function', Path(__file__).resolve().parents[1] / '.github/scripts/publish-function.py'
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


@pytest.fixture
def pipeline(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path('dist').mkdir()
    Path('dist/function.zip').write_bytes(b'checked-artifact')
    for name, value in {
        'GITHUB_ACTIONS': 'true',
        'GITHUB_SHA': 'a' * 40,
        'GITHUB_RUN_ID': '20',
        'GITHUB_STEP_SUMMARY': 'summary',
        'DEPLOY_FOLDER': release.FOLDER,
        'DEPLOY_BUCKET': 'private',
        'DEPLOYER_ID': 'deployer',
    }.items():
        monkeypatch.setenv(name, value)

    def configure(target):
        monkeypatch.setenv('TARGET', target)
        fid, entry, gib, timeout, tag = release.TARGETS[target]
        state = {
            'id': 'before',
            'function_id': fid,
            'entrypoint': entry,
            'runtime': 'python314',
            'execution_timeout': timeout,
            'resources': {'memory': str(gib * 1024**3)},
            'concurrency': '1',
            'log_options': {'folder_id': release.FOLDER},
            'status': 'ACTIVE',
            'tags': ['$latest'],
            'environment': release.expected_environment(
                target, {'SHARED_DIALOGS_ALLOWED_OWNER': 'dialogs:' + 'f' * 64}
            ),
        }
        if tag:
            state['tags'].append(tag)
            state['service_account_id'] = release.RUNTIME_SA
        calls = []

        def fake_yc(*args):
            calls.append(args)
            if args[:4] == ('serverless', 'function', 'version', 'get-by-tag'):
                assert args[5] == fid and args[7] in state['tags']
                return dict(state)
            if args[:3] == ('storage', 's3api', 'put-object'):
                assert f'github-actions/{target}/' in args[args.index('--key') + 1]
                return {}
            assert args[:4] == ('serverless', 'function', 'version', 'create')
            assert args[args.index('--function-id') + 1] == fid
            assert args[args.index('--entrypoint') + 1] == entry
            assert ('--service-account-id' in args) == bool(tag)
            assert ('--tags' in args) == bool(tag)
            state.update(id='after', description=args[args.index('--description') + 1])
            return {}

        monkeypatch.setattr(release, 'yc', fake_yc)
        return calls, state

    return configure


@pytest.mark.parametrize('target', ['testing', 'api-testing', 'production'])
def test_publish_verified_target_and_retry(pipeline, target):
    calls, state = pipeline(target)
    release.publish()
    release.publish()
    assert sum('create' in call for call in calls) == 1
    assert sum('put-object' in call for call in calls) == 1
    assert state['id'] == 'after'
    assert 'a' * 40 in Path('summary').read_text()


def test_wrong_pilot_configuration_stops_before_upload(pipeline):
    calls, state = pipeline('testing')
    state['environment']['SHARED_DIALOGS_SKILL_ID'] = 'another-skill'
    with pytest.raises(RuntimeError, match='configuration'):
        release.publish()
    assert len(calls) == 1


def test_publish_preserves_explicit_anonymous_allowlist(pipeline):
    _, state = pipeline('testing')
    owner = 'dialogs-application:' + 'b' * 64
    state['environment']['SHARED_DIALOGS_ALLOWED_APPLICATION_OWNER'] = owner
    release.publish()
    assert state['environment']['SHARED_DIALOGS_ALLOWED_APPLICATION_OWNER'] == owner


def test_publish_does_not_enroll_anonymous_applications():
    environment = release.expected_environment('testing', {'SHARED_DIALOGS_ALLOWED_OWNER': 'dialogs:' + 'f' * 64})
    assert 'SHARED_DIALOGS_ALLOWED_APPLICATION_OWNER' not in environment
    with pytest.raises(ValueError, match='anonymous application'):
        release.expected_environment('testing', {**environment, 'SHARED_DIALOGS_ALLOWED_APPLICATION_OWNER': '*all*'})
