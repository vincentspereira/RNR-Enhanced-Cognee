"""Fleet selection and fail-closed collision checks; no account creation."""
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = runpy.run_path(str(ROOT / 'integrations/hermes/deployment/stage_launch_named_fleet.py'),run_name='fleet_stage_test')


def plans():
    rows = []
    for index in range(42):
        ident = f'{index:016x}'
        rows.append(dict(profile_id=ident,source_user='vincentspereira',source_profile=f'/home/vincentspereira/.hermes/profiles/invented_{index}',
            proposed_user='ecbot_'+ident,proposed_home='/var/lib/enhanced-cognee-profiles/'+ident,proposed_uid=None,
            enabled=False,admission='pending',gates={'os_boundary':False},existing_binding=None))
    rows.append(dict(source_user='vincentspereira',source_profile='/home/vincentspereira/.hermes',profile_id='main'))
    return rows


def test_only_remaining_named_profiles_selected():
    selected = HELPER['selection'](plans(),'0'*16)
    assert len(selected) == 41
    assert all(row['profile_id'] != '0'*16 for row in selected)
    assert all(Path(row['source_profile']).parent.name == 'profiles' for row in selected)


@pytest.mark.parametrize('field,value',[('proposed_user','root'),('proposed_home','/unrelated'),('proposed_uid',0),
    ('enabled',True),('admission','admitted'),('gates',{'os_boundary':True})])
def test_modified_or_active_plan_refused(field,value):
    rows = plans()
    rows[1][field] = value
    with pytest.raises(ValueError):
        HELPER['selection'](rows,'0'*16)


def test_unaccounted_profile_and_duplicate_id_refused():
    rows = plans()
    with pytest.raises(ValueError):
        HELPER['selection'](rows[1:],'0'*16)
    rows[1]['profile_id'] = rows[0]['profile_id']
    with pytest.raises(ValueError):
        HELPER['selection'](rows,'0'*16)


@pytest.mark.parametrize('collision',['user','group','home'])
def test_existing_local_work_never_reused_or_overwritten(monkeypatch,collision):
    rows = HELPER['selection'](plans(),'0'*16)
    def missing(_):
        raise KeyError('invented')
    monkeypatch.setattr(HELPER['pwd'],'getpwnam',lambda _:SimpleNamespace() if collision=='user' else missing(_))
    monkeypatch.setattr(HELPER['grp'],'getgrnam',lambda _:SimpleNamespace() if collision=='group' else missing(_))
    monkeypatch.setattr(HELPER['os'].path,'lexists',lambda _:collision=='home')
    with pytest.raises(ValueError):
        HELPER['no_collision'](rows)


def test_published_owner_components_remain_exact():
    import hashlib
    directory = ROOT / 'integrations/hermes/deployment'
    for name,digest in [('qualify_launch_isolated_accounts.py',HELPER['ACCOUNT_SHA']),('stage_launch_named_candidate.py',HELPER['STAGE_SHA'])]:
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
        helper = runpy.run_path(str(directory / 'qualify_launch_isolated_accounts.py'),run_name='bounded_public_test')
        helper['owner_program']((directory / name).read_bytes())
