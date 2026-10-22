"""
Live test: partial modify of Composites and Layer Combinations via Create*(overwriteExisting).
Usage: python test_partial_composite_layercomb.py --port <port>
"""
import sys, json
sys.path.insert(0, r'D:\ONEDRIVE\Documents\CODE PLUGINS\tapir-partial-attr-modify\archicad-addon\Examples')
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

def is_error(item):
    return 'error' in item

def get_comp(guid):
    r = run('GetComposites', {'attributeIds': [{'attributeId': {'guid': guid}}]})
    items = r[list(r.keys())[0]]
    c = items[0]
    return c.get('composite', c)

prod = aclib.RunCommand('API.GetProductInfo', {})
print('Archicad', prod.get('version'), 'on port', aclib.port)

bm = run('GetAttributesByType', {'attributeType': 'BuildingMaterial'})['attributes']
lt = run('GetAttributesByType', {'attributeType': 'Line'})['attributes']
bmIds = [a['attributeId'] for a in bm]
ltIds = [a['attributeId'] for a in lt]

def skin(t, i, th): return {'type': t, 'buildingMaterialId': {'attributeId': bmIds[i]}, 'framePen': 1, 'thickness': th}
def sep(i, pen): return {'lineTypeId': {'attributeId': ltIds[i]}, 'linePen': pen}

created = []
try:
    print('\n== Composite')
    r = run('CreateComposites', {'compositeDataArray': [{
        'name': 'ZZTest_Comp', 'useWith': ['Wall', 'Slab'],
        'skins': [skin('Finish', 0, 0.01), skin('Core', 1, 0.2), skin('Other', 2, 0.03)],
        'separators': [sep(0, 1), sep(1, 2), sep(0, 3), sep(1, 4)]}], 'overwriteExisting': True})
    item = r['attributeIds'][0]
    check('create succeeds', False, is_error(item))
    guid = item['attributeId']['guid']
    created.append(('Composite', guid))
    before = get_comp(guid)
    print('  initial:', json.dumps(before)[:400])

    # 1. rename only
    r = run('CreateComposites', {'compositeDataArray': [{'attributeId': {'guid': guid}, 'name': 'ZZTest_Comp_Renamed'}], 'overwriteExisting': True})
    check('rename-only accepted', False, is_error(r['attributeIds'][0]))
    after = get_comp(guid)
    check('name changed', 'ZZTest_Comp_Renamed', after.get('name'))
    for k in ('useWith', 'skins', 'separators'):
        check(f'{k} kept after rename', before.get(k), after.get(k))

    # 2. useWith only
    r = run('CreateComposites', {'compositeDataArray': [{'attributeId': {'guid': guid}, 'name': 'ZZTest_Comp_Renamed', 'useWith': ['Roof']}], 'overwriteExisting': True})
    after2 = get_comp(guid)
    check('useWith changed', ['Roof'], after2.get('useWith'))
    check('skins kept after useWith change', before.get('skins'), after2.get('skins'))
    check('separators kept after useWith change', before.get('separators'), after2.get('separators'))

    # 3. skins only, same count -> separators kept
    r = run('CreateComposites', {'compositeDataArray': [{'attributeId': {'guid': guid}, 'name': 'ZZTest_Comp_Renamed',
        'skins': [skin('Finish', 0, 0.02), skin('Core', 1, 0.25), skin('Other', 2, 0.04)]}], 'overwriteExisting': True})
    check('skins-only (same count) accepted', False, is_error(r['attributeIds'][0]))
    after3 = get_comp(guid)
    check('thicknesses changed', [0.02, 0.25, 0.04], [round(s['thickness'], 6) for s in after3['skins']])
    check('separators kept after skins change', before.get('separators'), after3.get('separators'))
    check('useWith still Roof', ['Roof'], after3.get('useWith'))

    # 4. skins only, different count -> error
    r = run('CreateComposites', {'compositeDataArray': [{'attributeId': {'guid': guid}, 'name': 'ZZTest_Comp_Renamed',
        'skins': [skin('Core', 1, 0.3)]}], 'overwriteExisting': True})
    check('skins-only (count change) rejected', True, is_error(r['attributeIds'][0]))
    check('composite untouched after rejection', after3.get('skins'), get_comp(guid).get('skins'))

    # 5. separators only
    r = run('CreateComposites', {'compositeDataArray': [{'attributeId': {'guid': guid}, 'name': 'ZZTest_Comp_Renamed',
        'separators': [sep(1, 5), sep(1, 6), sep(1, 7), sep(1, 8)]}], 'overwriteExisting': True})
    check('separators-only accepted', False, is_error(r['attributeIds'][0]))
    after5 = get_comp(guid)
    check('separator pens changed', [5, 6, 7, 8], [s['linePen'] for s in after5['separators']])
    check('skins kept after separators change', after3.get('skins'), after5.get('skins'))

    # 6. separators only with wrong count -> error
    r = run('CreateComposites', {'compositeDataArray': [{'attributeId': {'guid': guid}, 'name': 'ZZTest_Comp_Renamed',
        'separators': [sep(1, 5)]}], 'overwriteExisting': True})
    check('separators-only (wrong count) rejected', True, is_error(r['attributeIds'][0]))

    # 7. new composite without skins -> error
    r = run('CreateComposites', {'compositeDataArray': [{'name': 'ZZTest_Comp_NoSkins'}], 'overwriteExisting': False})
    check('new composite without skins rejected', True, is_error(r['attributeIds'][0]))
    if not is_error(r['attributeIds'][0]):
        created.append(('Composite', r['attributeIds'][0]['attributeId']['guid']))

    # 8. full overwrite still works (regression)
    r = run('CreateComposites', {'compositeDataArray': [{'attributeId': {'guid': guid}, 'name': 'ZZTest_Comp_Renamed', 'useWith': ['Wall'],
        'skins': [skin('Core', 1, 0.3)], 'separators': [sep(0, 1), sep(0, 2)]}], 'overwriteExisting': True})
    after8 = get_comp(guid)
    check('full overwrite: 1 skin', 1, len(after8['skins']))
    check('full overwrite: 2 separators', 2, len(after8['separators']))

    print('\n== Layer Combination')
    layers = run('GetAttributesByType', {'attributeType': 'Layer'})['attributes']
    target = layers[min(3, len(layers) - 1)]['attributeId']
    r = run('CreateLayerCombinations', {'layerCombinationDataArray': [{'name': 'ZZTest_LC',
        'layers': [{'attributeId': target, 'isHidden': True, 'isLocked': True, 'isWireframe': False, 'intersectionGroupNr': 5}]}], 'overwriteExisting': True})
    item = r['attributeIds'][0]
    check('create succeeds', False, is_error(item))
    lcGuid = item['attributeId']['guid']
    created.append(('LayerCombination', lcGuid))
    getLc = lambda: run('GetLayerCombinations', {'attributes': [{'attributeId': {'guid': lcGuid}}]})['layerCombinations'][0]['layerCombination']
    lcBefore = getLc()

    r = run('CreateLayerCombinations', {'layerCombinationDataArray': [{'attributeId': {'guid': lcGuid}, 'name': 'ZZTest_LC_Renamed'}], 'overwriteExisting': True})
    check('rename-only accepted', False, is_error(r['attributeIds'][0]))
    lcAfter = getLc()
    check('name changed', 'ZZTest_LC_Renamed', lcAfter.get('name'))
    check('layer stats kept', lcBefore.get('layers'), lcAfter.get('layers'))

    r = run('CreateLayerCombinations', {'layerCombinationDataArray': [{'name': 'ZZTest_LC_New'}], 'overwriteExisting': False})
    check('new combination without layers accepted', False, is_error(r['attributeIds'][0]))
    if not is_error(r['attributeIds'][0]):
        created.append(('LayerCombination', r['attributeIds'][0]['attributeId']['guid']))
finally:
    if created:
        run('DeleteAttributes', {'attributesToDelete': [{'attributeType': t, 'attributeId': {'guid': g}} for t, g in created]})
        print(f'\ncleanup: deleted {len(created)} test attributes')
    print(f'\nRESULT: {passes} passed, {fails} failed')
