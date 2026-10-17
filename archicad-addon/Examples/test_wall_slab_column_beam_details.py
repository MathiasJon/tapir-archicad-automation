import aclib

elements = aclib.RunTapirCommand ('GetAllElements', {})['elements']
detailsOfElements = aclib.RunTapirCommand ('GetDetailsOfElements', {'elements': elements})['detailsOfElements']

wallGuid = None
slabGuid = None
columnGuid = None
beamGuid = None
for i in range (len (elements)):
    elementType = detailsOfElements[i]['type']
    guid = elements[i]['elementId']['guid']
    if elementType == 'Wall' and wallGuid is None:
        wallGuid = guid
    elif elementType == 'Slab' and slabGuid is None:
        slabGuid = guid
    elif elementType == 'Column' and columnGuid is None:
        columnGuid = guid
    elif elementType == 'Beam' and beamGuid is None:
        beamGuid = guid

surfaces = aclib.RunTapirCommand ('GetAttributesByType', {'attributeType': 'Surface'}, debug = False)['attributes']
fills = aclib.RunTapirCommand ('GetAttributesByType', {'attributeType': 'Fill'}, debug = False)['attributes']
surfaceId = surfaces[0]['attributeId']
fillId = fills[0]['attributeId']

if wallGuid is not None:
    aclib.RunTapirCommand ('ModifyWalls', {
        'wallsWithDetails': [{
            'elementId': {'guid': wallGuid},
            'referenceLineLocation': 'Center',
            'slantAlpha': 1.4,
            'zoneRel': 'ReduceArea',
            'visibility': {
                'showOnHome': True,
                'showAllAbove': False,
                'showAllBelow': False,
                'showRelAbove': 0,
                'showRelBelow': 0
            },
            'referenceMaterial': {'overridden': True, 'attributeId': surfaceId},
            'cutFillPen': {'overridden': True, 'penIndex': 5}
        }]
    })

if slabGuid is not None:
    aclib.RunTapirCommand ('ModifySlabs', {
        'slabsWithDetails': [{
            'elementId': {'guid': slabGuid},
            'referencePlaneLocation': 'CoreBottom',
            'topMaterial': {'overridden': True, 'attributeId': surfaceId},
            'cutFillPen': {'overridden': True, 'penIndex': 6},
            'floorFill': {
                'use': True,
                'foregroundPen': 3,
                'backgroundPen': 1,
                'fillId': fillId,
                'use3DHatching': False,
                'orientation': {
                    'type': 'Global',
                    'origin': {'x': 0.0, 'y': 0.0},
                    'matrix00': 1.0,
                    'matrix10': 0.0,
                    'matrix01': 0.0,
                    'matrix11': 1.0,
                    'innerRadius': 0.0
                }
            }
        }]
    })

if columnGuid is not None:
    aclib.RunTapirCommand ('ModifyColumns', {
        'columnsWithDetails': [{
            'elementId': {'guid': columnGuid},
            'isSlanted': False,
            'wrapping': True,
            'cutFillPen': {'overridden': True, 'penIndex': 4},
            'coverFill': {
                'use': True,
                'useFromSurface': False,
                'orientationComesFrom3D': False,
                'fillId': fillId,
                'foregroundPen': 2,
                'backgroundPen': 1,
                'transformationType': 'Global',
                'transformation': {
                    'origin': {'x': 0.0, 'y': 0.0},
                    'xAxis': {'x': 1.0, 'y': 0.0},
                    'yAxis': {'x': 0.0, 'y': 1.0}
                }
            }
        }]
    })

if beamGuid is not None:
    aclib.RunTapirCommand ('ModifyBeams', {
        'beamsWithDetails': [{
            'elementId': {'guid': beamGuid},
            'isSlanted': False,
            'anchorPoint': 'Center',
            'cutFillPen': {'overridden': True, 'penIndex': 7},
            'holes': [
                {'type': 'Rectangular', 'showContour': True, 'centerX': 0.5, 'centerZ': 0.1, 'width': 0.2, 'height': 0.15}
            ],
            'coverFill': {
                'use': True,
                'useFromSurface': False,
                'orientationComesFrom3D': False,
                'fillId': fillId,
                'foregroundPen': 2,
                'backgroundPen': 1,
                'transformationType': 'Global',
                'transformation': {
                    'origin': {'x': 0.0, 'y': 0.0},
                    'xAxis': {'x': 1.0, 'y': 0.0},
                    'yAxis': {'x': 0.0, 'y': 1.0}
                }
            }
        }]
    })

changedGuids = [g for g in [wallGuid, slabGuid, columnGuid, beamGuid] if g is not None]
detailsOfElements = aclib.RunTapirCommand ('GetDetailsOfElements', {'elements': [{'elementId': {'guid': g}} for g in changedGuids]})['detailsOfElements']
