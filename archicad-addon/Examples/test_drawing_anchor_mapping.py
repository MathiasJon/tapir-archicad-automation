"""
Where does Archicad really draw model elements on a layout?

Ground truth: three solid RGB squares (red, green, blue) are placed in the model, on a
dedicated empty story, at known coordinates. Each scenario places one Drawing of a view
of that story on a test layout, saves the layout window as an image and measures where
the three colors really are. Two more squares (magenta, cyan) are placed directly on the
layout at known layout coordinates to check the pixel -> layout mapping of the image.

From the three measured centers a similarity transform layout = t + s * R(theta) * model
is fitted: s is the real scale, theta the real rotation and t the layout position of the
model origin. Those are compared with what GetDetailsOfElements reports for the Drawing
(pos, anchorPoint, useOwnOrigoAsAnchor, offset, angle, ratio, drawingScale, modelOffset,
bounds) and with GetDrawingContentBoxes, for views with and without a saved zoom and a
rotation, and for different anchors / angles / ratios. A last part changes the model
content (adds an element far away) and updates the Drawings, to see whether the same
model point moves on the layout.

Run:  uv run --with pillow --with numpy python test_drawing_anchor_mapping.py --port <port>
The project is left modified (test story, views, layout): close it without saving.
"""
import json
import math
import os
import sys
import tempfile

import numpy as np
from PIL import Image

import aclib

OUT_DIR = os.path.join(tempfile.gettempdir(), 'tapir_anchor_test')
os.makedirs(OUT_DIR, exist_ok=True)

STORY_NAME = 'TAPIR_ANCHOR_TEST'
SQUARE = 2.0  # model meters
MARKERS = {   # color -> model center
    'red':   ((1.0, 0.0, 0.0), (10.0, 5.0)),
    'green': ((0.0, 1.0, 0.0), (30.0, 5.0)),
    'blue':  ((0.0, 0.0, 1.0), (10.0, 20.0)),
}
LAYOUT_W, LAYOUT_H = 0.841, 0.594   # A1, meters on the layout
CALIB = {     # color -> layout center (meters), size 10 mm
    'magenta': ((1.0, 0.0, 1.0), (0.05, 0.05)),
    'cyan':    ((0.0, 1.0, 1.0), (0.79, 0.54)),
}
CALIB_SIZE = 0.010

results = []


def run(cmd, params=None):
    r = aclib.RunTapirCommand(cmd, params or {}, debug=False)
    if r is None:
        raise RuntimeError('%s returned nothing' % cmd)
    return r


def square(center, size):
    cx, cy = center
    h = size / 2
    return [{'x': cx - h, 'y': cy - h}, {'x': cx + h, 'y': cy - h},
            {'x': cx + h, 'y': cy + h}, {'x': cx - h, 'y': cy + h}]


def rgb(c):
    return {'red': c[0], 'green': c[1], 'blue': c[2]}


def walk(item):
    for child in item.get('children', []):
        nav = child['navigatorItem']
        yield nav
        yield from walk(nav)


def tree(map_id):
    return run('GetNavigatorItemTree', {'navigatorMapId': map_id})['navigatorItemTree']


# ---------------------------------------------------------------- setup ----------------
def setup_story():
    info = run('GetStories')
    stories = info['stories']
    for s in stories:
        if s['name'] == STORY_NAME:
            return s['index']
    top = stories[-1]
    new_index = top['index'] + 1
    to_set = [{'index': s['index'], 'dispOnSections': s['dispOnSections'],
               'level': s['level'], 'name': s['name']} for s in stories]
    to_set.append({'index': new_index, 'dispOnSections': False,
                   'level': top['level'] + 50.0, 'name': STORY_NAME})
    run('SetStories', {'stories': to_set})
    return new_index


def find_story_item(story_index):
    for nav in walk(tree('ProjectMap')):
        if nav.get('type') == 'StoryItem' and STORY_NAME in nav.get('name', ''):
            return nav
    raise RuntimeError('story item not found')


def place_model_markers(story_index, extra=False):
    data = []
    items = MARKERS.items() if not extra else [('grey', ((0.5, 0.5, 0.5), (70.0, 45.0)))]
    for _, (color, center) in items:
        data.append({'floorInd': story_index, 'coordinates': square(center, SQUARE),
                     'contourPenIndex': 1, 'foregroundColor': rgb(color), 'backgroundColor': rgb(color)})
    r = run('CreateHatches', {'hatchesData': data})
    return [e for e in r['elements'] if 'elementId' in e]


VIEW_FOLDER = None


def create_view(story_item, name, rotation_deg=0.0, zoom=None):
    global VIEW_FOLDER
    if VIEW_FOLDER is None:
        VIEW_FOLDER = run('CreateViewMapFolder', {'folderName': 'TAPIR_ANCHOR_VIEWS'})['navigatorItemId']
    r = run('CreateViewsInViewMap', {'viewsData': [{'navigatorItemId': story_item['navigatorItemId'],
                                                    'parentNavigatorItemId': VIEW_FOLDER, 'name': name}]})
    nav_id = r['navigatorItems'][0]['navigatorItemId']
    if zoom is not None:
        run('SetViewSettings', {'navigatorItemIdsWithViewSettings': [
            {'navigatorItemId': nav_id, 'viewSettings': {'saveZoom': True, 'ignoreSavedZoom': False, 'zoom': zoom}}]})
    if rotation_deg:
        run('SetViewRotation', {'navigatorItemIdsWithRotation': [
            {'navigatorItemId': nav_id, 'rotation': math.radians(rotation_deg)}]})
    settings = run('GetViewSettings', {'navigatorItemIds': [{'navigatorItemId': nav_id}]})
    return nav_id, settings


def create_layout():
    r = run('CreateLayout', {'layoutsData': [{'layoutName': 'TAPIR_ANCHOR_LAYOUT', 'masterLayoutName': 'TAPIR_ANCHOR_MASTER',
                                              'paperWidth': LAYOUT_W * 1000, 'paperHeight': LAYOUT_H * 1000}]})
    return r['databases'][0]['databaseId']


def activate_layout(layout_db):
    run('ChangeWindow', {'databaseId': layout_db})


def place_layout_calibration():
    data = [{'coordinates': square(center, CALIB_SIZE), 'contourPenIndex': 1,
             'foregroundColor': rgb(color), 'backgroundColor': rgb(color)} for color, center in CALIB.values()]
    return [e for e in run('CreateHatches', {'hatchesData': data})['elements'] if 'elementId' in e]


# ---------------------------------------------------------------- measure --------------
def capture(layout_db, tag, box=None):
    activate_layout(layout_db)
    run('SetZoom', {'zoomBox': box or {'xMin': 0.0, 'yMin': 0.0, 'xMax': LAYOUT_W, 'yMax': LAYOUT_H}})
    path = os.path.join(OUT_DIR, tag + '.png')
    r = run('SaveCurrentWindowAsImage', {'imageFilePath': path})
    img = np.asarray(Image.open(path).convert('RGB')).astype(int)
    zoom, rot = r['zoom'], r.get('rotation', 0.0)
    h, w, _ = img.shape

    def px_to_layout(px, py):
        x = zoom['xMin'] + (px + 0.5) / w * (zoom['xMax'] - zoom['xMin'])
        y = zoom['yMax'] - (py + 0.5) / h * (zoom['yMax'] - zoom['yMin'])
        return x, y

    def find(color):
        target = np.array([round(c * 255) for c in color])
        mask = np.all(np.abs(img - target) <= 40, axis=2)
        n = int(mask.sum())
        if n == 0:
            return None
        ys, xs = np.nonzero(mask)
        cx, cy = px_to_layout(xs.mean(), ys.mean())
        return {'x': cx, 'y': cy, 'pixels': n}

    found = {name: find(color) for name, (color, _) in list(MARKERS.items()) + list(CALIB.items())}
    calib_err = []
    for name, (_, center) in CALIB.items():
        f = found[name]
        calib_err.append(None if f is None else math.hypot(f['x'] - center[0], f['y'] - center[1]))
    return found, {'zoom': zoom, 'rotation': rot, 'size': [w, h], 'calibErrors': calib_err, 'image': path}


def fit_similarity(model_pts, layout_pts):
    """layout = t + s R(theta) model, least squares (complex numbers)."""
    m = np.array([complex(*p) for p in model_pts])
    l = np.array([complex(*p) for p in layout_pts])
    mc, lc = m.mean(), l.mean()
    a = np.sum((l - lc) * np.conj(m - mc)) / np.sum(np.abs(m - mc) ** 2)
    t = lc - a * mc
    resid = np.abs(l - (t + a * m)).max()
    return {'scale': abs(a), 'thetaDeg': math.degrees(np.angle(a)), 'origin': {'x': t.real, 'y': t.imag},
            'maxResidual': float(resid)}


def details_of(elements):
    d = run('GetDetailsOfElements', {'elements': elements})['detailsOfElements']
    out = []
    for item in d:
        det = item.get('details', item)
        out.append(det.get('typeSpecificDetails', det))
    return out


def measure_drawing(drawing, layout_db, tag, extra_info):
    det = details_of([drawing])[0]
    box = run('GetDrawingContentBoxes', {'elements': [drawing]})['contentBoxes'][0]
    b = det['bounds']
    pad = 0.02
    found, img_info = capture(layout_db, tag, {'xMin': b['xMin'] - pad, 'yMin': b['yMin'] - pad,
                                               'xMax': b['xMax'] + pad, 'yMax': b['yMax'] + pad})
    names = [n for n in MARKERS if found.get(n)]
    fit = None
    if len(names) >= 2:
        fit = fit_similarity([MARKERS[n][1] for n in names], [(found[n]['x'], found[n]['y']) for n in names])
    rec = {'tag': tag, **extra_info, 'details': det, 'contentBox': box, 'found': found, 'image': img_info, 'fit': fit}
    results.append(rec)
    report(rec)
    return rec


def report(rec):
    d, fit = rec['details'], rec['fit']
    print('\n=== %s' % rec['tag'])
    print('  details: pos=(%.4f, %.4f) useOwnOrigo=%s anchor=%s offset=(%.4f, %.4f) angle=%.2f deg ratio=%s drawingScale=%s modelOffset=(%.3f, %.3f) cut=%s'
          % (d['pos']['x'], d['pos']['y'], d.get('useOwnOrigoAsAnchor'), d.get('anchorPoint'),
             d.get('offset', {}).get('x', float('nan')), d.get('offset', {}).get('y', float('nan')),
             math.degrees(d['angle']), d['ratio'], d['drawingScale'], d['modelOffset']['x'], d['modelOffset']['y'],
             d['isCutWithFrame']))
    b = d['bounds']
    print('  bounds:     x %.4f..%.4f  y %.4f..%.4f' % (b['xMin'], b['xMax'], b['yMin'], b['yMax']))
    cb = rec['contentBox'].get('contentBox')
    if cb:
        print('  contentBox: x %.4f..%.4f  y %.4f..%.4f' % (cb['xMin'], cb['xMax'], cb['yMin'], cb['yMax']))
    print('  calibration errors (mm): %s' % ['-' if e is None else '%.2f' % (e * 1000) for e in rec['image']['calibErrors']])
    for n in MARKERS:
        f = rec['found'].get(n)
        print('  %-5s %s' % (n, 'NOT VISIBLE' if f is None else '(%.4f, %.4f) %d px' % (f['x'], f['y'], f['pixels'])))
    if fit:
        print('  FIT: scale=%.6f (1:%.1f) theta=%.3f deg  model origin on layout=(%.4f, %.4f)  residual=%.2f mm'
              % (fit['scale'], 1 / fit['scale'], fit['thetaDeg'], fit['origin']['x'], fit['origin']['y'], fit['maxResidual'] * 1000))
        print('  origin - pos = (%.2f, %.2f) mm' % ((fit['origin']['x'] - d['pos']['x']) * 1000, (fit['origin']['y'] - d['pos']['y']) * 1000))


# ---------------------------------------------------------------- scenarios ------------
PLACEMENTS = [
    ('default',      {}),
    ('origo',        {'useOwnOrigoAsAnchor': True}),
    ('BL',           {'useOwnOrigoAsAnchor': False, 'anchorPoint': 'BottomLeft'}),
    ('TR',           {'useOwnOrigoAsAnchor': False, 'anchorPoint': 'TopRight'}),
    ('origo_a20_r05', {'useOwnOrigoAsAnchor': True, 'angle': math.radians(20), 'scale': 0.5}),
]
POS = {'x': 0.40, 'y': 0.30}


def main():
    product = aclib.RunCommand('API.GetProductInfo', {})
    print('Archicad', product)

    story_index = setup_story()
    story_item = find_story_item(story_index)
    run('ChangeWindow', {'windowType': 'FloorPlan', 'storyIndex': story_index})
    markers = place_model_markers(story_index)
    print('markers', len(markers), 'on story', story_index, story_item.get('name'))

    views = [
        ('plain', 0.0, None),
        ('zoomIn', 0.0, {'xMin': 5.0, 'yMin': 0.0, 'xMax': 35.0, 'yMax': 10.0}),     # red + green only
        ('zoomOut', 0.0, {'xMin': -40.0, 'yMin': -30.0, 'xMax': 80.0, 'yMax': 60.0}),
        ('rot30', 30.0, None),
        ('rot90', 90.0, None),
        ('rot30zoom', 30.0, {'xMin': 5.0, 'yMin': 0.0, 'xMax': 35.0, 'yMax': 25.0}),
    ]
    view_ids = {}
    for name, rot, zoom in views:
        nav_id, settings = create_view(story_item, 'TAPIR_ANCHOR_' + name, rot, zoom)
        view_ids[name] = nav_id
        print('view', name, json.dumps(settings)[:400])

    layout_db = create_layout()
    activate_layout(layout_db)
    calib = place_layout_calibration()
    print('calibration squares', len(calib))

    # 1. Matrix: every view x every placement, created WITHOUT making the view current first.
    for vname, _, _ in views:
        for pname, extra in PLACEMENTS:
            item = {'navigatorItemId': view_ids[vname], 'layoutDatabaseId': layout_db,
                    'name': 'T_%s_%s' % (vname, pname), 'position': POS, **extra}
            r = run('CreateDrawings', {'drawingsData': [item]})['elements'][0]
            if 'elementId' not in r:
                print('CreateDrawings failed', vname, pname, r)
                continue
            measure_drawing(r, layout_db, '%s_%s' % (vname, pname), {'view': vname, 'placement': pname, 'gotoFirst': False})
            run('DeleteElements', {'elements': [r]})

    # 2. Same 'origo' placement after making the view current first (stale transform, #645).
    for vname, _, _ in views:
        run('ChangeWindow', {'navigatorItemId': view_ids[vname]})
        item = {'navigatorItemId': view_ids[vname], 'layoutDatabaseId': layout_db,
                'name': 'G_%s' % vname, 'position': POS, 'useOwnOrigoAsAnchor': True}
        r = run('CreateDrawings', {'drawingsData': [item]})['elements'][0]
        if 'elementId' in r:
            measure_drawing(r, layout_db, 'goto_%s_origo' % vname, {'view': vname, 'placement': 'origo', 'gotoFirst': True})
            run('DeleteElements', {'elements': [r]})

    # 3. Content change: does the same model point move on the layout after an update?
    kept = []
    for pname, extra in PLACEMENTS[:4]:
        item = {'navigatorItemId': view_ids['plain'], 'layoutDatabaseId': layout_db,
                'name': 'C_%s' % pname, 'position': POS, **extra}
        r = run('CreateDrawings', {'drawingsData': [item]})['elements'][0]
        kept.append((pname, r))
    extra_hatch = place_model_markers(story_index, extra=True)
    run('UpdateDrawings', {'elements': [r for _, r in kept]})
    for pname, r in kept:
        others = [o for _, o in kept if o is not r]
        # hide the others by moving them off the paper while measuring this one
        moved = []
        for o in others:
            od = details_of([o])[0]
            moved.append((o, od['pos']))
            run('SetDetailsOfElements', {'elementsWithDetails': [{'elementId': o['elementId'], 'details': {'typeSpecificDetails': {'pos': {'x': od['pos']['x'] + 5.0, 'y': od['pos']['y']}}}}]})
        measure_drawing(r, layout_db, 'afterChange_%s' % pname, {'view': 'plain', 'placement': pname, 'afterContentChange': True})
        for o, p in moved:
            run('SetDetailsOfElements', {'elementsWithDetails': [{'elementId': o['elementId'], 'details': {'typeSpecificDetails': {'pos': p}}}]})

    with open(os.path.join(OUT_DIR, 'results.json'), 'w') as f:
        json.dump(results, f, indent=1)
    print('\nResults written to', os.path.join(OUT_DIR, 'results.json'))


if __name__ == '__main__':
    main()
