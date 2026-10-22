"""
Live test: ModifyGraphicOverrideCombinations + CreateGraphicOverrideRuleGroups.
Usage: python -I test_override_modify_create.py --port <port>
"""
import sys
sys.path.insert(0, r'D:\ONEDRIVE\Documents\CODE PLUGINS\tapir-override-modify-create\archicad-addon\Examples')
import aclib

def run(cmd, params=None):
    return aclib.RunTapirCommand(cmd, params or {}, debug=False)

passes = fails = 0
def check(label, expected, got):
    global passes, fails
    ok = (got == expected)
    passes += ok
    fails += (not ok)
    print(f'  [{"PASS" if ok else "FAIL"}] {label}' + ('' if ok else f'  expected={expected!r} got={got!r}'))

def ok(result):
    return result.get('success') is True

def get_comb(cid):
    for c in run('GetGraphicOverrideCombinations')['graphicOverrideCombinations']:
        if c['graphicOverrideCombinationId'] == cid:
            return c
    return None

def get_group(name):
    for g in run('GetGraphicOverrideRuleGroups')['graphicOverrideRuleGroups']:
        if g['name'] == name:
            return g
    return None

print('Archicad', aclib.RunCommand('API.GetProductInfo', {}).get('version'), 'on port', aclib.port)
combIds, ruleIds, groups = [], [], []
try:
    print('\n== ModifyGraphicOverrideCombinations')
    r = run('CreateGraphicOverrideRules', {'graphicOverrideRules': [
        {'name': 'ZZT Rule A', 'ruleGroupName': 'ZZT Group Rules'},
        {'name': 'ZZT Rule B', 'ruleGroupName': 'ZZT Group Rules'}]})
    ruleIds = [x for x in r['graphicOverrideRuleIds'] if 'error' not in x]
    groups.append('ZZT Group Rules')
    check('2 rules created', 2, len(ruleIds))
    rA, rB = ruleIds
    r = run('CreateGraphicOverrideCombinations', {'graphicOverrideCombinations': [
        {'name': 'ZZT Comb 1', 'graphicOverrideRuleIds': [rA]},
        {'name': 'ZZT Comb Other', 'graphicOverrideRuleIds': []}]})
    combIds = [x for x in r['graphicOverrideCombinationIds'] if 'error' not in x]
    check('2 combinations created', 2, len(combIds))
    c1 = combIds[0]['graphicOverrideCombinationId']

    r = run('ModifyGraphicOverrideCombinations', {'graphicOverrideCombinations': [{'graphicOverrideCombinationId': c1, 'name': 'ZZT Comb 1 Renamed'}]})
    check('rename only succeeds', True, ok(r['executionResults'][0]))
    c = get_comb(c1)
    check('name changed', 'ZZT Comb 1 Renamed', c['name'])
    check('rules kept after rename', [rA], c['graphicOverrideRuleIds'])

    r = run('ModifyGraphicOverrideCombinations', {'graphicOverrideCombinations': [{'graphicOverrideCombinationId': c1, 'graphicOverrideRuleIds': [rB, rA]}]})
    check('rules only succeeds', True, ok(r['executionResults'][0]))
    c = get_comb(c1)
    check('name kept after rules change', 'ZZT Comb 1 Renamed', c['name'])
    check('rules replaced, order kept', [rB, rA], c['graphicOverrideRuleIds'])

    r = run('ModifyGraphicOverrideCombinations', {'graphicOverrideCombinations': [{'graphicOverrideCombinationId': c1, 'name': 'ZZT Comb 1 Both', 'graphicOverrideRuleIds': []}]})
    check('name + empty rules succeeds', True, ok(r['executionResults'][0]))
    c = get_comb(c1)
    check('name changed (both)', 'ZZT Comb 1 Both', c['name'])
    check('rules emptied', [], c['graphicOverrideRuleIds'])

    r = run('ModifyGraphicOverrideCombinations', {'graphicOverrideCombinations': [
        {'graphicOverrideCombinationId': {'guid': '00000000-1111-2222-3333-444444444444'}, 'name': 'ZZT Nope'},
        {'graphicOverrideCombinationId': c1, 'name': 'ZZT Comb Other'},
        {'graphicOverrideCombinationId': c1, 'name': ''},
        {'graphicOverrideCombinationId': c1, 'graphicOverrideRuleIds': [{'graphicOverrideRuleId': {'guid': '00000000-1111-2222-3333-444444444444'}}]}]})
    res = r['executionResults']
    check('unknown combination rejected', False, ok(res[0]))
    check('duplicate name rejected', False, ok(res[1]))
    check('empty name rejected', False, ok(res[2]))
    check('unknown rule rejected', False, ok(res[3]))
    c = get_comb(c1)
    check('combination untouched after errors', ('ZZT Comb 1 Both', []), (c['name'], c['graphicOverrideRuleIds']))
    print('  sample error:', res[1])

    print('\n== CreateGraphicOverrideRuleGroups')
    r = run('CreateGraphicOverrideRuleGroups', {'ruleGroupNames': ['ZZT Empty Group 1', 'ZZT Empty Group 2', 'ZZT Empty Group 1', '', 'ZZT Group Rules']})
    res = r['executionResults']
    groups += ['ZZT Empty Group 1', 'ZZT Empty Group 2']
    check('group 1 created', True, ok(res[0]))
    check('group 2 created', True, ok(res[1]))
    check('duplicate name in same call rejected', False, ok(res[2]))
    check('empty name rejected', False, ok(res[3]))
    check('existing group name rejected', False, ok(res[4]))
    g = get_group('ZZT Empty Group 1')
    check('group 1 listed and empty', [], g and g['graphicOverrideRuleIds'])
    check('group 2 listed', True, get_group('ZZT Empty Group 2') is not None)

    r = run('CreateGraphicOverrideRules', {'graphicOverrideRules': [{'name': 'ZZT Rule In New Group', 'ruleGroupName': 'ZZT Empty Group 2'}]})
    newRule = r['graphicOverrideRuleIds'][0]
    if 'error' not in newRule:
        ruleIds.append(newRule)
    check('rule created in the new group', [newRule], get_group('ZZT Empty Group 2')['graphicOverrideRuleIds'])
finally:
    if combIds:
        run('DeleteGraphicOverrideCombinations', {'graphicOverrideCombinationIds': combIds})
    if ruleIds:
        run('DeleteGraphicOverrideRules', {'graphicOverrideRuleIds': ruleIds})
    if groups:
        run('DeleteGraphicOverrideRuleGroups', {'ruleGroupNames': groups, 'deleteRules': True})
    left = [g['name'] for g in run('GetGraphicOverrideRuleGroups')['graphicOverrideRuleGroups'] if g['name'].startswith('ZZT')]
    left += [c['name'] for c in run('GetGraphicOverrideCombinations')['graphicOverrideCombinations'] if c['name'].startswith('ZZT')]
    print('\ncleanup leftovers:', left)
    print(f'\nRESULT: {passes} passed, {fails} failed')
