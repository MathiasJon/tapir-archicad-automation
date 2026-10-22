import subprocess, re, sys
sys.stdout.reconfigure(encoding='utf-8')

def git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True, encoding='utf-8', errors='replace')

branches = [
    'origin/feature/partial-composite-layercomb-modify',
    'origin/feature/graphic-override-combination-modify-rulegroup-create',
    'origin/feature/graphic-overrides-fields',
    'origin/fix/section-elevation-commands',
    'upstream/claude/issue-1116-get-current-layer-combination',
    'upstream/claude/issue-1318-part2-attribute-property-status',
    'upstream/claude/issue-1318-part4-attribute-property-availability',
    'upstream/claude/issue-985-attribute-classifications',
    'upstream/claude/issue-988-consolidation-used-attributes',
    'upstream/claude/issue-1216-get-attributes-from-project',
    'upstream/claude/issue-1334-delete-attributes-batch',
    'upstream/claude/issue-948-attribute-creation-info',
    'upstream/claude/issue-1064-set-graphic-override-rule-order',
    'upstream/claude/issue-1162-rename-rule-groups',
]
conflict_re = re.compile(r'<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n', re.S)

def trivial(a, c):
    # Both sides only add command registrations (or one side is empty): keeping both is correct.
    ok = lambda s: not s.strip() or 'RegisterCommand' in s
    return ok(a) and ok(c)

for b in branches:
    git('merge', '--no-edit', '-q', b)
    unmerged = [f for f in git('diff', '--name-only', '--diff-filter=U').stdout.split() if f]
    if not unmerged:
        print(f'OK        {b}', flush=True)
        continue
    auto, manual = [], []
    for f in unmerged:
        txt = open(f, encoding='utf-8', newline='').read()
        blocks = conflict_re.findall(txt)
        if f.endswith('AddOnMain.cpp') and blocks and all(trivial(a, c) for a, c in blocks):
            open(f, 'w', encoding='utf-8', newline='').write(conflict_re.sub(lambda m: m.group(1) + m.group(2), txt))
            git('add', f)
            auto.append(f)
        else:
            manual.append(f)
    if manual:
        git('merge', '--abort')
        print(f'CONFLICT  {b}  -> {manual}', flush=True)
    else:
        git('commit', '--no-edit', '-q')
        print(f'AUTO-FIX  {b}  ({auto})', flush=True)
