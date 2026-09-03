import json,glob,re,os,collections
ROOT="/root/.claude/projects"
files=sorted(glob.glob(ROOT+"/**/*.jsonl",recursive=True))
PAT=re.compile(r"(?i)\b(i was wrong|was wrong|my (own )?(error|mistake|defect)|corrected|correction|does not reproduce|did not (plant|reach|fire|run)|never (ran|fired|reached|read|called|checked)|stale|wrong base|false (block|positive|negative|claim)|vacuous|silently|the plant (did|does) not|instrument (defect|failure)|i reported|i claimed|withdrawn|turns out|actually,? (the|it|this)|root cause)\b")
hits=collections.Counter(); ex=collections.defaultdict(list)
n=0
for f in files:
    try: fh=open(f,encoding="utf-8",errors="replace")
    except: continue
    for line in fh:
        n+=1
        if len(line)>400000: line=line[:400000]
        try: r=json.loads(line)
        except: continue
        m=r.get("message") or {}
        if m.get("role")!="assistant": continue
        c=m.get("content")
        if not isinstance(c,list): continue
        for b in c:
            if b.get("type") not in ("text","thinking"): continue
            for s in re.split(r"(?<=[.!?])\s+|\n",b.get("text") or b.get("thinking") or ""):
                s=s.strip()
                if 40<len(s)<400 and PAT.search(s):
                    k=PAT.search(s).group(1).lower()
                    hits[k]+=1
                    if len(ex[k])<400: ex[k].append((os.path.basename(f),s))
print("lines",n,"files",len(files))
out="/home/user/Keel/docs/ledger/blindspot/incidents.txt"
with open(out,"w") as o:
    for k,v in hits.most_common():
        o.write(f"\n===== {k}  ({v}) =====\n")
        for fn,s in ex[k]: o.write(f"[{fn}] {s}\n")
print("wrote",out, sum(hits.values()))
