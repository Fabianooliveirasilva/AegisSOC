import os,sys,base64,subprocess,tempfile,random
S=sys.argv[1]; exp=sys.argv[2]
random.seed(1234)
vecs=[[0]*32,[255]*32,list(range(32)),list(range(224,256)),
 [0xfb,0xff,0xbf]*10+[0xfb,0xff],  # maps to '-' '_' region
 [0xf8]*32,[0x3e<<2]*32,[0xff,0xef,0xbe]*10+[0xff,0xef],
 [1]*32,[128]*32,[0x7e]*32]
vecs+= [[0x3e<<2|0, 0]*16, [0x3f]*32]
while len(vecs)<40: vecs.append([random.randrange(256) for _ in range(32)])
bad=0;dash=0;us=0
for i,v in enumerate(vecs):
    d=tempfile.mkdtemp(dir=S+'/t')
    q=d+'/q'
    names=["postgres_superuser_password","postgres_owner_password","postgres_app_password","redis_password","bootstrap_admin_password"]
    lines=[v]+[[random.randrange(256) for _ in range(32)] for _ in range(4)]
    open(q,'w').write(''.join(' '.join('%3d'%b for b in l)+'\n' for l in lines))
    env=dict(os.environ,PATH=S+'/bin_q:'+os.environ['PATH'],FAKE_OD_Q=q)
    sec=d+'/sec'
    shell=os.environ.get('SH','sh')
    r=subprocess.run(shell.split()+[exp+'/scripts/setup-secrets','--ci',sec],env=env,capture_output=True,text=True)
    ok=r.returncode==0
    for n,l in zip(names,lines):
        ref=base64.urlsafe_b64encode(bytes(l)).decode().rstrip('=')
        got=open(sec+'/'+n).read() if os.path.exists(sec+'/'+n) else None
        if got!=ref: ok=False
    dash+= '-' in ref; us+='_' in ref
    if not ok: bad+=1; print("MISMATCH",i,v[:4],r.stderr[:200])
    if '-' in open(sec+'/postgres_superuser_password').read(): pass
print("vectors",len(vecs),"x5 secrets each; mismatches",bad)
