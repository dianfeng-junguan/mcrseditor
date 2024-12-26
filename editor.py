'''
用来做设计图的程序
'''
import sys
import json
print('editor')
comps={}
cons=[]
helpstr="cmds:\n\
    and/not/or [name]\n\
    con/connect [c1] [c2]\n\
    br/break [c1] [c2]\n\
    save [path]\n\
    open [path]\n\
    help\n\
    show\n\
    q/exit"
def solve(cmd:str)->int:
    '''
    解析命令
    cmds:
    and/not/or [name]
    con/connect [c1] [c2]
    br/break [c1] [c2]
    save [path]
    open [path]
    help
    show
    '''
    global comps
    args=cmd.strip().split(' ')
    first=args[0].lower()
    if first in ['and','not','or']:
        if args[1] in comps:
            print('%s already exists, overwriting previous one...'%(args[1]))
        comps[args[1]]={'type':args[0],'in':[],'out':[]}
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
        outs:list=comps[a]['out']
        ins:list=comps[b]['in']
        if not b in outs:
            outs.append(b)
        if not a in ins:
            ins.append(a)
    elif first=='show':
        print('components:')
        for c in comps.keys():
            print(c,comps[c]['type'],end='\t')
        print('\nconnections:')
        for c,v in comps.items():
            v:dict
            for wv in v['out']:
                print('%s->%s, '%(c,wv),end='')
            print()
            # for wv in v['in']:
            #     print('%s->%s, '%(wv,c),end='')
            # print()
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
        outs:list=comps[a]['out']
        ins:list=comps[b]['in']
        if b in outs:
            outs.remove(b)
        if a in ins:
            ins.remove(a)
    elif first=='help':
        print(helpstr)
    elif first=='save':
        js=json.dumps(comps,indent=2)
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
            comps=json.loads(js)
        print('loaded')
    elif first in ['q','exit']:
        return True
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