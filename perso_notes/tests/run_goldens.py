import sys, os, subprocess, time, json, urllib.request
REPO = r'D:\ONEDRIVE\Documents\CODE PLUGINS\tapir-maintainer-review\archicad-addon'
sys.path.insert(0, os.path.join(REPO, 'Test'))
import output_masks
PLA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TestProject.pla')
def post(body, timeout=10):
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:19723', data=json.dumps(body).encode()), timeout=timeout))
    except Exception as e:
        return {'exc': str(e)}
def ready():
    r = post({'command': 'API.GetProductInfo'}, 3)
    return r.get('succeeded') is True
def reopen():
    clicker = subprocess.Popen(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'click_open.ps1'], stdout=subprocess.PIPE, text=True)
    post({'command': 'API.ExecuteAddOnCommand', 'parameters': {'addOnCommandId': {'commandNamespace': 'TapirCommand', 'commandName': 'OpenProject'}, 'addOnCommandParameters': {'projectFilePath': PLA}}}, 120)
    clicker.wait(60)
    for _ in range(60):
        if ready(): return True
        time.sleep(2)
    return False
for name in sys.argv[1:]:
    assert reopen(), 'Archicad not ready'
    out = subprocess.run(['python', os.path.join(REPO, 'Examples', name), 'silent'], capture_output=True, timeout=120, cwd=os.path.join(REPO, 'Examples')).stdout
    out = output_masks.Mask('\n'.join(out.decode('utf-8', 'replace').split('\r\n')))
    gold = os.path.join(REPO, 'Test', 'ExpectedOutputs', name + '.output')
    if os.path.isfile(gold):
        exp = open(gold, encoding='utf-8').read()
        status = 'MATCH' if out == exp else 'DIFF'
    else:
        status = 'NO GOLDEN'
    open(name + '.actual', 'w', encoding='utf-8').write(out)
    print(f'{name:50} {status}', flush=True)
