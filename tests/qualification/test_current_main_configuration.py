"""Current definitions are preserved; only reviewed settings/references change."""
import copy
from pathlib import Path
import runpy

import pytest

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
CURRENT=runpy.run_path(str(FOLDER/'current_main_configuration.py'))
DEST=Path('/var/lib/enhanced-cognee-profiles/'+'a'*16+'/ec-main-operational-restore-invented')


def config(count=6):
    rows={'filesystem':dict(command='npx',args=['-y','@modelcontextprotocol/server-filesystem',CURRENT['SOURCE_WORKSPACE']])}
    rows.update({f'invented-{i}':dict(url=f'https://example.invalid/mcp/{i}',headers={'Authorization':'invented-private-value'},
        env={'INVENTED_SETTING':'preserve'},opaque_options={'nested':['invented',i]}) for i in range(count-1)})
    return dict(model={'provider':'zai','default':'glm-5.3-flash','base_url':'https://open.bigmodel.cn/api/coding/paas/v4'},
        gateway={'multiplex_profiles':True},platforms={'whatsapp':{'enabled':True}},mcp_servers=rows,
        unrelated={'private_instructions':'invented preserve-only text','source_path':'/home/vincentspereira/invented-data'})


@pytest.mark.parametrize('count',[1,4,6,7,128])
def test_every_current_definition_is_preserved_without_a_fixed_four_server_assumption(count):
    original=config(count);saved=copy.deepcopy(original)
    updated=CURRENT['transform'](original,DEST)
    assert original==saved and len(updated['mcp_servers'])==count
    expected=copy.deepcopy(original)
    expected['mcp_servers']['filesystem']['args'][-1]=str(DEST/'workspace')
    expected['memory']={'provider':'enhanced_cognee'}
    assert updated==expected
    restored=DEST.with_name('ec-main-operational-restore-second1')
    rebased=CURRENT['rebase'](updated,DEST,restored)
    expected['mcp_servers']['filesystem']['args'][-1]=str(restored/'workspace')
    assert rebased==expected


@pytest.mark.parametrize('damage',['wrong_command','wrong_package','duplicate_path','ambiguous_server','missing_root',
 'other_memory','routed_profile','standalone','too_many','cycle','nonfinite','nonstring_key'])
def test_scope_or_ambiguous_configuration_is_refused_without_changing_source(damage):
    value=config()
    server=value['mcp_servers']['filesystem']
    if damage=='wrong_command':server['command']='python'
    if damage=='wrong_package':server['args'][1]='unreviewed-package'
    if damage=='duplicate_path':server['args'].append(CURRENT['SOURCE_WORKSPACE'])
    if damage=='ambiguous_server':value['mcp_servers']['another-filesystem']=copy.deepcopy(server)
    if damage=='missing_root':server['args'][-1]='/unreviewed/root'
    if damage=='other_memory':value['memory']={'provider':'unreviewed'}
    if damage=='routed_profile':value['gateway']['profile_routes']=['invented-route']
    if damage=='standalone':value['gateway']['multiplex_profiles']=False
    if damage=='too_many':value=config(129)
    if damage=='cycle':value['recursive']=value
    if damage=='nonfinite':value['opaque']=float('nan')
    if damage=='nonstring_key':value['opaque']={1:'invented'}
    with pytest.raises(ValueError):CURRENT['transform'](value,DEST)


@pytest.mark.parametrize('raw',[
    b'mcp_servers: {}\nmcp_servers: {}\n',b'outer:\n  token: invented-one\n  token: invented-two\n',
    b'!!python/object:object {}',b'1: invented\n',b'x: .nan\n',b'x: &loop [*loop]\n',b'x: 2026-10-27\n'])
def test_duplicate_or_executable_or_ambiguous_yaml_never_loses_a_definition_silently(raw):
    with pytest.raises(ValueError):CURRENT['load'](raw)


def test_standard_yaml_and_shared_noncyclic_aliases_remain_supported():
    assert CURRENT['load'](b'x: &value [a, b]\ny: *value\n')=={'x':['a','b'],'y':['a','b']}


@pytest.mark.parametrize('path',['/home/vincentspereira/.hermes','/var/lib/enhanced-cognee-profiles/bad/ec-main-operational-restore-invented',
    '/var/lib/enhanced-cognee-profiles/'+'a'*16+'/.hermes','/tmp/ec-main-operational-restore-invented'])
def test_caller_cannot_select_an_original_or_active_profile(path):
    with pytest.raises(ValueError):CURRENT['transform'](config(),Path(path))
