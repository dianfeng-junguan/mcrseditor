'''
用来做设计图的程序
'''
import sys
import json
print('editor')
comps={}
cons=[]
helpstr="cmds:\n\
    port [name]\n\
    and/not/or [name]\n\
    con/connect [c1] [c2]\n\
    br/break [c1] [c2]\n\
    save [path]\n\
    open [path]\n\
    help\n\
    show\n\
    export [path] :export as circuit.py project file\n\
    q/exit"
def solve(cmd:str)->int:
    '''
    解析命令
    '''
    global comps,cons
    args=cmd.strip().split(' ')
    first=args[0].lower()
    if first in ['and','not','or','port']:
        if args[1] in comps:
            print('%s already exists, overwriting previous one...'%(args[1]))
        comps[args[1]]={'type':args[0],'in':0,'out':0}
    elif first in ['con','connect']:
        #连接
        if len(args)<3:
            print('need at least 2 args.')
            return False
        a=args[1]
        b=args[2]
        if not a in comps.keys() or not b in comps.keys():
            print('one or two component(s) not found')
            return False
        if not (a,b) in cons:
            #有向连接，out->in
            cons.append((a,b))
            comps[a]['out']+=1
            comps[b]['in']+=1
    elif first=='show':
        print('components:')
        for c in comps.keys():
            print(c,comps[c]['type'],end='\t')
        print('\nconnections:')
        for tup in cons:
            print('%s->%s, '%(tup[0],tup[1]),end='')
            print()
    elif first in ['br','break']:
        #断开
        if len(args)<3:
            print('need at least 2 args.')
            return False
        a=args[1]
        b=args[2]
        if not a in comps.keys() or not b in comps.keys():
            print('one or two component(s) not found')
            return False
        if (a,b) in cons:
            #有向连接，out->in
            cons.remove((a,b))
            comps[a]['out']-=1
            comps[b]['in']-=1
    elif first=='help':
        print(helpstr)
    elif first=='save':
        js=json.dumps({'components':comps,'connections':cons},indent=2)
        if len(args)<2:
            print('need path')
            return False
        with open(args[1],'w') as f:
            f.write(js)
        print('saved')
    elif first=='open':
        if len(args)<2:
            print('need path')
            return False
        with open(args[1],'r') as f:
            js=f.read()
            data=json.loads(js)
            comps=data['components']
            cons=data['connections']
        print('loaded')
    elif first in ['q','exit']:
        return True
    elif first =='export':
        print('coming up')
    else:
        print('unknown cmd')

        

if len(sys.argv)>1:
    lines:str
    with open(sys.argv[1],'r') as f:
        lines=f.readlines()
    for l in lines:
        solve(l)
else:
    r=False
    while not r:
        l=input('cmd:')
        r=solve(l)