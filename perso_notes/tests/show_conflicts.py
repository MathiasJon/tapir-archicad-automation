import re, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')
files = [f for f in subprocess.run(['git', 'diff', '--name-only', '--diff-filter=U'], capture_output=True, text=True).stdout.split() if f]
for f in files:
    t = open(f, encoding='utf-8', newline='').read()
    for i, m in enumerate(re.finditer(r'<<<<<<< [^\r\n]*\r?\n(.*?)=======\r?\n(.*?)>>>>>>> [^\r\n]*\r?\n', t, re.S)):
        line = t[:m.start()].count('\n') + 1
        o, th = m.group(1).splitlines(), m.group(2).splitlines()
        print(f'### {f}:{line} block {i}  ours={len(o)} lines  theirs={len(th)} lines')
        show = lambda L: '\n'.join(L[:6] + (['   ...'] + L[-4:] if len(L) > 10 else L[6:]))
        print('  OURS:\n' + show(o)); print('  THEIRS:\n' + show(th))
