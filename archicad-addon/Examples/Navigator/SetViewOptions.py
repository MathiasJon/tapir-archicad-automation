"""Switches the fill handles of the current plan window with SetViewOptions, changes a GDL parameter of
the library part options on top of the window's combination, then restores the original options.

Run it with a floor plan, section or elevation window in front.
"""
import aclib

original = aclib.RunTapirCommand ('GetViewOptions')
showFillHandles = original['viewOptions']['onScreenViewOptions']['showFillHandles']

# Only the given option changes, the others keep their value.
aclib.PrintJson (aclib.RunTapirCommand ('SetViewOptions', {
    'viewOptions': {'onScreenViewOptions': {'showFillHandles': not showFillHandles}}
}))

# The library part options (gdlOptions) are changed by option set and parameter name. With a
# combination given, it is applied first and the change on top of it: the window then uses Custom
# options, which can be saved into a combination in the Model View Options dialog.
gdlOptions = original['viewOptions']['gdlOptions']
if gdlOptions and original['modelViewOptionName']:
    optionSet = gdlOptions[0]
    parameter = next ((p for p in optionSet['parameters'] if p['type'] == 'Boolean'), None)
    if parameter is not None:
        aclib.PrintJson (aclib.RunTapirCommand ('SetViewOptions', {
            'modelViewOptionName': original['modelViewOptionName'],
            'viewOptions': {'gdlOptions': [
                {'guid': optionSet['guid'], 'parameters': [{'name': parameter['name'], 'value': not parameter['value']}]}
            ]}
        }))

# Restore the original options. The combination is given by name, because Archicad may renumber
# the combinations when the options of a window change.
if original['modelViewOptionName']:
    aclib.PrintJson (aclib.RunTapirCommand ('SetViewOptions', {
        'modelViewOptionName': original['modelViewOptionName'],
        'viewOptions': {'onScreenViewOptions': original['viewOptions']['onScreenViewOptions']}
    }))
else:
    aclib.PrintJson (aclib.RunTapirCommand ('SetViewOptions', {
        'viewOptions': {
            'modelViewOptions': original['viewOptions']['modelViewOptions'],
            'onScreenViewOptions': original['viewOptions']['onScreenViewOptions']
        }
    }))
