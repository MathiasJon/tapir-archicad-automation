"""
Live maintainer review of blocked PRs #953/#1024/#1026 (attribute folders), #916 (ActivateLayerCombination),
#1178 (SetGraphicOverrideRuleGroupOrder), #1365 (SetPropertyValueOfAttributes).
Usage: python -I test_maintainer_review.py --port <port> [section ...]
"""
import sys, json
sys.path.insert(0, r'D:\ONEDRIVE\Documents\CODE PLUGINS\tapir-maintainer-review\archicad-addon\Examples')
import aclib

sections = [a for a in sys.argv[1:] if not a.startswith('--') and not a.isdigit()] or ['folders', 'activate', 'order', 'props']

def run(cmd, params=None):
    return aclib.RunTapirCommand(cmd, params or {}, debug=False)

passes = fails = 0
def check(label, expected, got):
    global passes, fails
    ok = (got == expected)
    passes += ok
    fails += (not ok)
    print(f'  [{"PASS" if ok else "FAIL"}] {label}' + ('' if ok else f'  expected={expected!r} got={got!r}'))

def succ(r): return bool(r) and r.get('success') is True

def attrs(t): return run('GetAttributesByType', {'attributeType': t})['attributes']
def by_name(t, name): return next((a for a in attrs(t) if a['name'] == name), None)

print('Archicad', aclib.RunCommand('API.GetProductInfo', {}).get('version'), 'on port', aclib.port)

# ---------------------------------------------------------------- folders
if 'folders' in sections:
    print('\n== #953 / #1024 / #1026 attribute folders + folderPath')
    F = lambda t, *p: {'attributeType': t, 'path': list(p)}
    r = run('CreateAttributeFolders', {'attributeFolders': [F('Layer', 'ZZT', 'A', 'B'), F('Layer', 'ZZT', 'C'), F('Layer', 'ZZT', 'A'), F('BuildingMaterial', 'ZZT BM')]})
    check('create nested folders (4 results, all success incl. already-existing parent)', [True] * 4, [succ(x) for x in r['executionResults']])
    r = run('CreateAttributeFolders', {'attributeFolders': [F('Layer', 'ZZT', 'A', 'B')]})
    check('re-create existing folder reports success', True, succ(r['executionResults'][0]))
    r = run('CreateAttributeFolders', {'attributeFolders': [F('Layer', 'ZZT', ''), F('Layer', ' bad ')]})
    check('illegal paths rejected (empty name / surrounding spaces)', [False, False], [succ(x) for x in r['executionResults']])

    r = run('CreateLayers', {'layerDataArray': [{'name': 'ZZT_L1'}, {'name': 'ZZT_L2'}, {'name': 'ZZT_L3'}], 'overwriteExisting': True})
    L1, L2, L3 = [x['attributeId'] for x in r['attributeIds']]
    r = run('MoveAttributesAndFolders', {'attributeIds': [{'attributeId': L1}], 'targetFolder': F('Layer', 'ZZT', 'A', 'B')})
    check('move L1 into ZZT/A/B', True, succ(r['attributeExecutionResults'][0]))
    r = run('MoveAttributesAndFolders', {'attributeIds': [{'attributeId': L2}], 'targetFolder': F('Layer', 'ZZT', 'C')})
    check('move L2 into ZZT/C', True, succ(r['attributeExecutionResults'][0]))

    def path_of(name, t='Layer'):
        a = by_name(t, name)
        return a and a.get('folderPath')
    check('#1026 folderPath nested (L1)', ['ZZT', 'A', 'B'], path_of('ZZT_L1'))
    check('#1026 folderPath one level (L2)', ['ZZT', 'C'], path_of('ZZT_L2'))
    check('#1026 folderPath root (L3)', [], path_of('ZZT_L3'))
    others = [a['folderPath'] for a in attrs('Layer') if not a['name'].startswith('ZZT')]
    check('#1026 every other layer still reports a list', True, all(isinstance(p, list) for p in others))

    r = run('RenameAttributeFolders', {'attributeFolders': [{'attributeType': 'Layer', 'path': ['ZZT', 'C'], 'newName': 'D'}]})
    check('#1024 rename ZZT/C -> D', True, succ(r['executionResults'][0]))
    check('#1026 path follows the rename', ['ZZT', 'D'], path_of('ZZT_L2'))
    r = run('RenameAttributeFolders', {'attributeFolders': [{'attributeType': 'Layer', 'path': [], 'newName': 'X'}]})
    check('#1024 renaming the root folder is rejected', False, succ(r['executionResults'][0]))

    r = run('MoveAttributesAndFolders', {'attributeFolders': [F('Layer', 'ZZT', 'D')], 'targetFolder': F('Layer', 'ZZT', 'A')})
    check('#1024 move folder D into A', True, succ(r['folderExecutionResults'][0]))
    check('#1026 path follows the folder move', ['ZZT', 'A', 'D'], path_of('ZZT_L2'))
    r = run('MoveAttributesAndFolders', {'attributeIds': [{'attributeId': L3}], 'targetFolder': F('BuildingMaterial', 'ZZT BM')})
    check('#1024 moving a Layer into a BuildingMaterial folder is rejected', False, succ(r['attributeExecutionResults'][0]))
    r = run('MoveAttributesAndFolders', {'attributeIds': [{'attributeId': L1}], 'targetFolder': F('Layer')})
    check('#1024 empty target path = root', True, succ(r['attributeExecutionResults'][0]))
    check('#1026 L1 back in root', [], path_of('ZZT_L1'))

    r = run('DeleteAttributeFolders', {'attributeFolders': [F('Layer'), F('Layer', 'ZZT'), F('BuildingMaterial', 'ZZT BM')]})
    check('#953 delete root rejected, ZZT and ZZT BM deleted', [False, True, True], [succ(x) for x in r['executionResults']])
    check('#953 layer inside a deleted folder is deleted too (L2)', None, by_name('Layer', 'ZZT_L2'))
    check('#953 layer in root survives (L1)', True, by_name('Layer', 'ZZT_L1') is not None)
    run('DeleteAttributes', {'attributesToDelete': [{'attributeType': 'Layer', 'attributeId': x} for x in (L1, L3)]})

# ---------------------------------------------------------------- activate
if 'activate' in sections:
    print('\n== #916 ActivateLayerCombination')
    layers = attrs('Layer')
    target = next(l for l in layers[1:] if not l['name'].startswith('ZZT'))
    getLayer = lambda: run('GetLayers', {'attributeIds': [{'attributeId': target['attributeId']}]})
    print('  target layer:', target['name'], '| GetLayers sample:', json.dumps(getLayer())[:200])
    r = run('CreateLayerCombinations', {'layerCombinationDataArray': [
        {'name': 'ZZT LC hide', 'layers': [{'attributeId': target['attributeId'], 'isHidden': True}]},
        {'name': 'ZZT LC show', 'layers': [{'attributeId': target['attributeId'], 'isHidden': False}]}], 'overwriteExisting': True})
    lcHide, lcShow = [x['attributeId'] for x in r['attributeIds']]
    def hidden():
        g = getLayer()
        item = g[list(g.keys())[0]][0]
        item = item.get('layer', item)
        return item.get('isHidden')
    r = run('ActivateLayerCombination', {'attributeId': lcHide})
    check('activate "hide" succeeds', True, succ(r))
    check('target layer now hidden in the current window', True, hidden())
    r = run('ActivateLayerCombination', {'attributeId': lcShow})
    check('activate "show" succeeds', True, succ(r))
    check('target layer now visible', False, hidden())
    r = run('ActivateLayerCombination', {'attributeId': target['attributeId']})
    check('a Layer guid is rejected', False, succ(r))
    print('  error message:', r)
    r = run('ActivateLayerCombination', {'attributeId': {'guid': '00000000-1111-2222-3333-444444444444'}})
    check('an unknown guid is rejected', False, succ(r))
    run('DeleteAttributes', {'attributesToDelete': [{'attributeType': 'LayerCombination', 'attributeId': x} for x in (lcHide, lcShow)]})

# ---------------------------------------------------------------- order
if 'order' in sections:
    print('\n== #1178 SetGraphicOverrideRuleGroupOrder')
    names = lambda: [g['name'] for g in run('GetGraphicOverrideRuleGroups')['graphicOverrideRuleGroups']]
    r = run('CreateGraphicOverrideRules', {'graphicOverrideRules': [{'name': f'ZZT R{i}', 'ruleGroupName': f'ZZT G{i}'} for i in (1, 2, 3)]})
    ruleIds = [x for x in r['graphicOverrideRuleIds'] if 'error' not in x]
    before = names()
    print('  groups before:', before)
    r = run('SetGraphicOverrideRuleGroupOrder', {'ruleGroupNames': ['ZZT G3', 'ZZT G1']})
    check('reorder succeeds', True, succ(r))
    after = names()
    rest = [n for n in before if n not in ('ZZT G3', 'ZZT G1')]
    check('listed groups first, others keep their relative order', ['ZZT G3', 'ZZT G1'] + rest, after)
    r = run('SetGraphicOverrideRuleGroupOrder', {'ruleGroupNames': ['ZZT G2', 'Nope']})
    check('unknown name rejected', False, succ(r))
    r = run('SetGraphicOverrideRuleGroupOrder', {'ruleGroupNames': ['ZZT G2', 'ZZT G2']})
    check('duplicate name rejected', False, succ(r))
    check('order untouched after rejections', after, names())
    run('DeleteGraphicOverrideRuleGroups', {'ruleGroupNames': ['ZZT G1', 'ZZT G2', 'ZZT G3'], 'deleteRules': True})

# ---------------------------------------------------------------- props
if 'props' in sections:
    print('\n== #1365 SetPropertyValueOfAttributes')
    bms = attrs('BuildingMaterial')
    ids = [{'attributeId': b['attributeId']} for b in bms]
    pid = aclib.RunCommand('API.GetPropertyIds', {'properties': [{'type': 'UserDefined', 'localizedName': ['Tapir Group', 'Tapir Custom']}]})['properties'][0]['propertyId']
    vals = run('GetPropertyValuesOfAttributes', {'attributeIds': ids, 'properties': [{'propertyId': pid}]})['propertyValuesForAttributes']
    withProp = [ids[i] for i in range(len(ids)) if 'error' not in vals[i]['propertyValues'][0]]
    without = [ids[i] for i in range(len(ids)) if 'error' in vals[i]['propertyValues'][0]]
    print(f'  {len(withProp)} materials with the property, {len(without)} without')
    def values(lst):
        v = run('GetPropertyValuesOfAttributes', {'attributeIds': lst, 'properties': [{'propertyId': pid}]})['propertyValuesForAttributes']
        return [x['propertyValues'][0].get('propertyValue', {}).get('value') for x in v]
    orig = values(withProp)
    r = run('SetPropertyValueOfAttributes', {'propertyId': pid, 'propertyValue': {'value': 'Audited'}, 'attributeIds': withProp})
    check('set on all materials with the property succeeds', True, succ(r))
    check('every listed material now reads "Audited"', ['Audited'] * len(withProp), values(withProp))
    if without:
        r = run('SetPropertyValueOfAttributes', {'propertyId': pid, 'propertyValue': {'value': 'Mixed'}, 'attributeIds': withProp[:2] + without[:1]})
        check('mixed list with a material lacking the property fails', False, succ(r))
        print('  error message:', r)
        check('...and changes no material (all or nothing)', ['Audited'] * 2, values(withProp[:2]))
    print('  ORIGINAL_VALUES_JSON=' + json.dumps(orig))

print(f'\nRESULT: {passes} passed, {fails} failed')
