import re, subprocess
def show(stage, f):
    return subprocess.run(['git', 'show', f':{stage}:{f}'], capture_output=True).stdout.decode('utf-8')
def write(f, t):
    open(f, 'w', encoding='utf-8', newline='').write(t)
def keep_both(f):
    t = open(f, encoding='utf-8', newline='').read()
    write(f, re.sub(r'<<<<<<< [^\r\n]*\r?\n(.*?)=======\r?\n(.*?)>>>>>>> [^\r\n]*\r?\n', lambda m: m.group(1) + m.group(2), t, flags=re.S))
def extract(text, start_pat, end_pat):
    s = re.search(start_pat, text).start()
    m = re.compile(end_pat, re.S).search(text, s + 1)
    return text[s:m.start() if m else len(text)]
def insert_after(f, block, anchor_pat, base=None):
    ours = base if base is not None else show(2, f)
    a = re.compile(anchor_pat, re.S).search(ours)
    write(f, ours[:a.end()] + block + ours[a.end():])
    print(f, 'inserted', block.count('\n'), 'lines')

def stack_with_shared_tail(f, tail_end_line):
    """Both sides appended new code at the same spot and share the lines after the conflict up to tail_end_line:
    ours + shared tail + blank line + theirs (+ the shared tail again, already in place after the conflict)."""
    t = open(f, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in t else '\n'
    m = re.search(r'<<<<<<< [^\r\n]*\r?\n(.*?)=======\r?\n(.*?)>>>>>>> [^\r\n]*\r?\n', t, re.S)
    after = t[m.end():]
    lines = after.split(nl)
    idx = next(i for i, l in enumerate(lines) if l == tail_end_line)
    tail = nl.join(lines[:idx + 1]) + nl
    write(f, t[:m.start()] + m.group(1) + tail + nl + m.group(2) + after)
