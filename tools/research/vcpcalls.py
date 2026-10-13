# For each call to set/getVCP, find the enclosing function and the last immediate loaded into %esi.
import sys, re
func = None
window = []
res = {}
for line in open(sys.argv[1]):
    m = re.match(r'^[0-9a-f]+ <(.*)>:$', line)
    if m:
        func = m.group(1); window = []; continue
    window.append(line)
    if len(window) > 25: window.pop(0)
    m = re.search(r'call\s+\S+ <(\S*::(?:set|get)VCP)\(', line) or re.search(r'call\s+\S+ <DpModelModuleInterface::((?:set|get)VCP)', line)
    if m:
        imm = None
        for w in reversed(window[:-1]):
            mm = re.search(r'mov\s+\$0x([0-9a-f]+),%esi', w)
            if mm: imm = int(mm.group(1), 16); break
            if re.search(r',%esi$|,%rsi$', w.strip()): imm = 'reg'; break
        f = re.sub(r'\(.*', '', func)
        res.setdefault(f, set()).add((m.group(1).split('::')[-1], hex(imm) if isinstance(imm, int) else imm))
for f in sorted(res):
    print(f, sorted(res[f], key=str))
