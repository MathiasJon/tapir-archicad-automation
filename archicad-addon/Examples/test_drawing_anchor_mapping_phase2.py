"""
Phase 2 of test_drawing_anchor_mapping.py (run it first, same session, project not reopened):
unclipped Drawings, anchors changed after creation, a model content change that extends the
drawing to the bottom left, and modelOffset on a clipped Drawing.

Run:  uv run --with pillow --with numpy python test_drawing_anchor_mapping_phase2.py --port <port>
"""
import json
import math
import os

import test_drawing_anchor_mapping as t

run = t.run


def find_view(name):
    for nav in t.walk(t.tree('PublicViewMap')):
        if nav.get('name') == name:
            return nav['navigatorItemId']
    raise RuntimeError('view %s not found' % name)


def find_layout_db():
    for nav in t.walk(t.tree('LayoutBook')):
        if nav.get('type') == 'LayoutItem' and nav.get('name') == 'TAPIR_ANCHOR_LAYOUT':
            r = run('GetDatabaseIdFromNavigatorItemId', {'navigatorItemIds': [{'navigatorItemId': nav['navigatorItemId']}]})
            return r['databases'][0]['databaseId']
    raise RuntimeError('layout not found')


def find_story():
    for s in run('GetStories')['stories']:
        if s['name'] == t.STORY_NAME:
            return s['index']


def set_drawing(drawing, **fields):
    r = run('SetDetailsOfElements', {'elementsWithDetails': [
        {'elementId': drawing['elementId'], 'details': {'typeSpecificDetails': fields}}]})
    return r['executionResults'][0]


def node_of_bounds(b, anchor):
    xs = {'Left': b['xMin'], 'Center': (b['xMin'] + b['xMax']) / 2, 'Right': b['xMax']}
    ys = {'Bottom': b['yMin'], 'Middle': (b['yMin'] + b['yMax']) / 2, 'Top': b['yMax']}
    if anchor == 'Center':
        return xs['Center'], ys['Middle']
    for v in ('Top', 'Middle', 'Bottom'):
        if anchor.startswith(v):
            h = anchor[len(v):]
            return xs[{'Left': 'Left', 'Center': 'Center', 'Right': 'Right'}[h]], ys[v]
    raise ValueError(anchor)


def summary(rec):
    d, fit = rec['details'], rec['fit']
    line = '  -> '
    if fit:
        o = fit['origin']
        line += 'origin-pos=(%.1f, %.1f) mm  origin-offset=(%.1f, %.1f) mm' % (
            (o['x'] - d['pos']['x']) * 1000, (o['y'] - d['pos']['y']) * 1000,
            (o['x'] - d['offset']['x']) * 1000, (o['y'] - d['offset']['y']) * 1000)
    if not d['useOwnOrigoAsAnchor']:
        nx, ny = node_of_bounds(d['bounds'], d['anchorPoint'])
        line += '  pos-anchorNode(bounds)=(%.1f, %.1f) mm' % ((d['pos']['x'] - nx) * 1000, (d['pos']['y'] - ny) * 1000)
    print(line)


def main():
    story = find_story()
    layout_db = find_layout_db()
    views = {n: find_view('TAPIR_ANCHOR_' + n) for n in ('plain', 'rot30')}
    pos = {'x': 0.40, 'y': 0.30}
    leftovers = run('GetElementsByType', {'elementType': 'Drawing', 'databases': [{'databaseId': layout_db}]})['elements']
    if leftovers:
        print('deleting %d leftover Drawings on the test layout' % len(leftovers))
        run('DeleteElements', {'elements': leftovers})

    drawings = []
    for vname, nav in views.items():
        for mode in ('BottomLeft', 'Center', 'TopRight', 'origo'):
            r = run('CreateDrawings', {'drawingsData': [{'navigatorItemId': nav, 'layoutDatabaseId': t.find_layout_db() if False else layout_db,
                                                          'name': 'P2_%s_%s' % (vname, mode), 'position': pos}]})['elements'][0]
            # unclipped first, then the anchor, then the position (each in its own call)
            print('\n### %s %s' % (vname, mode))
            print('  clip off:', set_drawing(r, isCutWithFrame=False))
            if mode == 'origo':
                print('  anchor:  ', set_drawing(r, useOwnOrigoAsAnchor=True))
            else:
                print('  anchor:  ', set_drawing(r, useOwnOrigoAsAnchor=False, anchorPoint=mode))
            print('  pos:     ', set_drawing(r, pos=pos))
            drawings.append((vname, mode, r))

    def measure_all(phase):
        for vname, mode, r in drawings:
            # hide the others off the sheet while measuring this one
            others = [(o, t.details_of([o])[0]['pos']) for _, _, o in drawings if o is not r]
            for o, p in others:
                set_drawing(o, pos={'x': p['x'] + 10.0, 'y': p['y']})
            rec = t.measure_drawing(r, layout_db, '%s_%s_%s' % (phase, vname, mode),
                                    {'view': vname, 'placement': mode, 'phase': phase})
            summary(rec)
            for o, p in others:
                set_drawing(o, pos=p)

    measure_all('p2before')

    # content change: an element far to the bottom left of the markers
    grey = run('CreateHatches', {'hatchesData': [{'floorInd': story, 'coordinates': t.square((-30.0, -20.0), t.SQUARE),
                                                  'contourPenIndex': 1, 'foregroundColor': t.rgb((0.5, 0.5, 0.5)),
                                                  'backgroundColor': t.rgb((0.5, 0.5, 0.5))}]})['elements']
    print('\nadded far element', grey)
    print('UpdateDrawings', run('UpdateDrawings', {'elements': [r for _, _, r in drawings]}))
    measure_all('p2afterChange')
    run('DeleteElements', {'elements': grey})
    run('UpdateDrawings', {'elements': [r for _, _, r in drawings]})
    run('DeleteElements', {'elements': [r for _, _, r in drawings]})

    # modelOffset on a clipped origo drawing
    for mo in ({'x': 0.0, 'y': 0.0}, {'x': 5.0, 'y': 3.0}):
        clip = [{'x': 0.1, 'y': 0.1}, {'x': 0.6, 'y': 0.1}, {'x': 0.6, 'y': 0.5}, {'x': 0.1, 'y': 0.5}]
        r = run('CreateDrawings', {'drawingsData': [{'navigatorItemId': views['plain'], 'layoutDatabaseId': layout_db,
                                                      'name': 'P2_mo', 'position': pos, 'modelOffset': mo,
                                                      'clipPolygon': clip}]})['elements'][0]
        rec = t.measure_drawing(r, layout_db, 'p2_modelOffset_%g_%g' % (mo['x'], mo['y']), {'modelOffset': mo})
        summary(rec)
        run('DeleteElements', {'elements': [r]})

    with open(os.path.join(t.OUT_DIR, 'results_phase2.json'), 'w') as f:
        json.dump(t.results, f, indent=1)


if __name__ == '__main__':
    main()
