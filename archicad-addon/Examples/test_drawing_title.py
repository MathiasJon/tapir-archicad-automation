import json
import aclib

print ('Switching to a layout window...')
lb = aclib.RunCommand ('API.GetNavigatorItemTree', {'navigatorTreeId': {'type': 'LayoutBook'}})

def find_first_layout (item):
    navItem = item.get ('navigatorItem', item)
    if navItem.get ('type') == 'LayoutItem':
        return navItem['navigatorItemId']
    for c in navItem.get ('children', []):
        found = find_first_layout (c)
        if found:
            return found
    return None

layoutNavId = find_first_layout (lb['navigatorTree']['rootItem'])
if layoutNavId is None:
    print ('No layout found - cannot test.')
    raise SystemExit

aclib.RunTapirCommand ('ChangeWindow', {'windowType': 'Layout', 'navigatorItemId': layoutNavId}, debug=False)

print ('Looking for Drawing elements in the project...')
resp = aclib.RunTapirCommand ('GetElementsByType', {'elementType': 'Drawing'}, debug=False)
drawings = resp['elements'] if resp else []
print ('Found {} drawing(s).'.format (len (drawings)))

if not drawings:
    print ('No drawings in this project - cannot test.')
    raise SystemExit

drawingId = drawings[0]['elementId']
print ('Using drawing: {}'.format (drawingId))

beforeResp = aclib.RunTapirCommand ('GetDetailsOfElements', {'elements': [{'elementId': drawingId}]}, debug=False)
beforeDetails = beforeResp['detailsOfElements'][0]['details']
print ('Before: nameType={}, customName={}, numberingType={}, customNumber={}, isInNumbering={}'.format (
    beforeDetails.get ('nameType'), beforeDetails.get ('customName'),
    beforeDetails.get ('numberingType'), beforeDetails.get ('customNumber'),
    beforeDetails.get ('isInNumbering')))

setResp = aclib.RunTapirCommand ('SetDetailsOfElements', {
    'elementsWithDetails': [{
        'elementId': drawingId,
        'details': {
            'typeSpecificDetails': {
                'nameType': 'CustomName',
                'customName': 'PLAN DE VENTE TEST',
                'numberingType': 'CustomNumber',
                'customNumber': '99',
                'isInNumbering': False
            }
        }
    }]
}, debug=False)
print ('SetDetailsOfElements response: {}'.format (json.dumps (setResp)))

afterResp = aclib.RunTapirCommand ('GetDetailsOfElements', {'elements': [{'elementId': drawingId}]}, debug=False)
afterDetails = afterResp['detailsOfElements'][0]['details']
print ('After: nameType={}, customName={}, numberingType={}, customNumber={}, isInNumbering={}'.format (
    afterDetails.get ('nameType'), afterDetails.get ('customName'),
    afterDetails.get ('numberingType'), afterDetails.get ('customNumber'),
    afterDetails.get ('isInNumbering')))

ok = (afterDetails.get ('nameType') == 'CustomName' and afterDetails.get ('customName') == 'PLAN DE VENTE TEST'
      and afterDetails.get ('numberingType') == 'CustomNumber' and afterDetails.get ('customNumber') == '99'
      and afterDetails.get ('isInNumbering') is False)
print ('\n{}'.format ('WRITE TEST PASSED' if ok else 'WRITE TEST FAILED'))
