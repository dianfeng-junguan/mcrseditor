'''
一级处理json文件，和具体的mc门电路做对应，以及摆放电路
'''
import sys
import json
import glob
import pathseek
import nbtrd
import python_nbt.nbt as nbt
import multiprocessing
if len(sys.argv)<3:
    print('lacks args')
    sys.exit(-1)
# try:
#     with open('libs.json','r') as f:
#         global libs
#         libs=json.load(f)
# except Exception:
#     print('failed loading libs.json')
#     sys.exit(-1)
def task_path(x1,y1,z1,x2,y2,z2,mp:pathseek.Map,q:multiprocessing.Queue):
    li=mp.path_astar(x1,y1,z1,x2,y2,z2)
    q.put(li)
    
def vec_add(l1,l2)->list:
    res=[]
    for i in range(len(l1)):
        res.append(l1[i]+l2[i])
    return res
def translate_dir(dir:str)->list:
    if dir.strip().lower()=='x+':
        return [1,0,0]
    elif dir.strip().lower()=='x-':
        return [-1,0,0]
    elif dir.strip().lower()=='y-':
        return [0,1,0]
    elif dir.strip().lower()=='y+':
        return [0,-1,0]
    elif dir.strip().lower()=='z+':
        return [0,0,1]
    elif dir.strip().lower()=='z-':
        return [0,0,-1]
    return None
def export_as_nbt_and_json(input_path,output_path):
    with open(input_path,'r') as f:
        global data
        data=json.load(f)

    used_gates={}
    #link gates
    #collect used gates
    comps:dict=data['components']
    gatemap={}
    cons=data['connections']
    port_rest={}#num of in/out unused
    #
    for_uipy={'components':[],'connections':[]}
    def overlap(p1:tuple,s1:tuple,p2:tuple,s2:tuple)->bool:
        return ()
    px=10
    pz=10
    sz=[10,48,10]
    c=0
    lnc=int(len(comps)**0.5)
    for k,v in comps.items():
        v:dict
        typ=v['type']
        #in:input c out:output c
        #寻找相应的门
        id=typ#+'_'+str(v['in'])+'_'+str(v['out'])
        path='lib/'+id+'.json'
        if len(glob.glob(path))==0:
            print('error: gate not found:',id)
            sys.exit(-1)
        if not id in used_gates.keys():
            used_gates[id]={'path':path}
            with open(path,'r') as f:
                used_gates[id]['data']=json.load(f)
                used_gates[id]['nbt']=nbt.read_from_nbt_file(open(used_gates[id]['data']['path'],'rb'))
        v['type']=id
        #place gate
        size:list=used_gates[id]['data']['size']
        #需要一个布局算法
        #方阵排列
        gatemap[k]={'id':id,'gate':used_gates[id]['data']['path'],'pos':[px,0,pz],'in':v['in']\
                    ,'out':v['out']}
        #export to ui.py project file format
        if typ!='port':
            for_uipy['components'].append({'type':typ,'rect':[px,pz,size[0],size[2]]})
        port_rest[k]={'in':v['in'],'out':v['out']}
        c+=1
        sz[1]=max(sz[1],size[1])
        if c%lnc==0:
            px=4
            pz+=size[2]+10
            sz[2]=max(sz[2],pz)
        else:
            px+=size[0]+10
            sz[0]=max(sz[0],px)
    mp=pathseek.Map(48,48,48)
    struct=nbtrd.structure(48,48,48)
    all_palette=[struct.create_blockstate("minecraft:stone"),struct.create_blockstate("minecraft:redstone_wire",nbt.NBTTagCompound())]
    all_palette[1]['Properties']['power']=nbt.NBTTagInt(0)
    all_palette[1]['Properties']['north']=nbt.NBTTagString('none')
    all_palette[1]['Properties']['south']=nbt.NBTTagString('none')
    all_palette[1]['Properties']['east']= nbt.NBTTagString('none')
    all_palette[1]['Properties']['west']= nbt.NBTTagString('none')
    struct.add_to_palette(nbtrd.blocks.BLOCK_STONE,struct.create_blockstate("minecraft:stone"))
    struct.add_to_palette(nbtrd.blocks.BLOCK_REDSTONE,all_palette[1])
    for e in gatemap.values():
        print(e['id'],':',e['pos'])
    '''
    TODO
    1.计算所需大小生成structure
    2.加注释
    3.路径方块放置
    4.部件放置到结构中
    '''
    for g in gatemap.values():
        '''
        获取nbt
        获取nbt.blocks
        获取palette
        获取palette对应方块名对应id
        setblock
        '''
        schemanbt:nbt.NBTTagCompound=used_gates[g['id']]['nbt']
        blks:nbt.NBTTagList=schemanbt['blocks']
        pal:nbt.NBTTagList=schemanbt['palette']
        base=len(all_palette)
        for pv in range(len(pal)):
            all_palette.append(pal[pv])
            struct.add_to_palette(pv+base,pal[pv])
        for b in blks:
            b:nbt.NBTTagCompound
            bpos:nbt.NBTTagList=b['pos']
            #pos
            bx,by,bz=bpos[0].value,bpos[1].value,bpos[2].value
            #palette
            state=b['state'].value
            newi=state+base
            rx=g['pos'][0]+bx
            ry=g['pos'][1]+by
            rz=g['pos'][2]+bz
            mp.add_obstacle(rx,ry,rz)
            struct.setblock(rx,ry,rz,newi)
            
    max_concurrent=12
    queue=multiprocessing.Queue(12)
    pool=[]
    #now connect
    for con in cons:
        a,b=con[0],con[1]
        aid,bid=gatemap[a]['id'],gatemap[b]['id']
        outs,ins=used_gates[aid]['data']['out'],used_gates[aid]['data']['in']
        touse_a,touse_b=port_rest[a]['out']-1,port_rest[b]['in']-1
        port_rest[a]['out']-=1
        port_rest[b]['in']-=1
        outp=vec_add(used_gates[aid]['data']['out'][touse_a][:3],gatemap[a]['pos'])
        inp=vec_add(used_gates[bid]['data']['in'][touse_b][:3],gatemap[b]['pos'])

        #寻路连接
        print(aid,'to',bid,end=':')
        conpath=mp.path_astar(outp[0],outp[1],outp[2],inp[0],inp[1],inp[2])
        print('ok')
        prev_line=[conpath[0]]
        prev_d=''
        for i in conpath:#[0,1,0],
            #四周都需要为空，不能有其他红石线连接
            for d in [[0,0,0],[0,-1,0],[1,0,0],[-1,0,0],[0,0,1],[0,0,-1]]:
                iv=vec_add(i,d)
                mp.add_obstacle(iv[0],iv[1],iv[2])
            # mp.add_obstacle(i[0],i[1]-1,i[2])
            struct.setblock(i[0],i[1],i[2],nbtrd.blocks.BLOCK_REDSTONE)
            struct.setblock(i[0],i[1]-1,i[2],nbtrd.blocks.BLOCK_STONE)
            #compose into horizontal and vertical parts
            deltav=[i[0]-prev_line[-1][0],i[2]-prev_line[-1][2]]
            nowdir='h' if deltav[1]!=0 else 'v'
            if prev_d=='':
                prev_d=nowdir
            elif nowdir!=prev_d:
                #should pack prev_line
                for_uipy['connections'].append(prev_line[0]+prev_line[-1])
                prev_line=[]
                prev_d=nowdir
            prev_line.append(i)
        #分配任务
        # pool.append(multiprocessing.Process(target=task_path,args=\
        #                                     [outp[0],outp[1],outp[2],inp[0],inp[1],inp[2],mp,queue],daemon=True))
    # done=0
    # working=0
    # p=0
    # while done<len(pool):
    #     if working<max_concurrent and p<len(pool):
    #         pool[p].start()
    #         p+=1
    #         working+=1
    #     else:
    #         recv=queue.get()
    #         if len(recv)>0:
    #             conpath=recv#mp.path_bfs(outp[0],outp[1],outp[2],inp[0],inp[1],inp[2])
    #             print(conpath)
    #             working-=1
    #             done+=1
    #             for i in conpath:
    #                 struct.setblock(i[0],i[1],i[2],nbtrd.blocks.BLOCK_REDSTONE)
    #                 struct.setblock(i[0],i[1]-1,i[2],nbtrd.blocks.BLOCK_STONE)
        #TODO 按路径放置方块

    # print(gatemap)
    with open(output_path.split('.')[0]+'.ui.json','w') as f:
        json.dump(for_uipy,f,indent=2)
    nbt.write_to_nbt_file(sys.argv[2],struct.get_nbt())
    print('done')

if __name__=="__main__":
    with open(sys.argv[1],'r') as f:
        global data
        data=json.load(f)

    used_gates={}
    #link gates
    #collect used gates
    comps:dict=data['components']
    gatemap={}
    cons=data['connections']
    port_rest={}#num of in/out unused
    #
    for_uipy={'components':[],'connections':[]}
    def overlap(p1:tuple,s1:tuple,p2:tuple,s2:tuple)->bool:
        return ()
    px=10
    pz=10
    sz=[10,48,10]
    c=0
    lnc=int(len(comps)**0.5)
    for k,v in comps.items():
        v:dict
        typ=v['type']
        #in:input c out:output c
        #寻找相应的门
        id=typ#+'_'+str(v['in'])+'_'+str(v['out'])
        path='lib/'+id+'.json'
        if len(glob.glob(path))==0:
            print('error: gate not found:',id)
            sys.exit(-1)
        if not id in used_gates.keys():
            used_gates[id]={'path':path}
            with open(path,'r') as f:
                used_gates[id]['data']=json.load(f)
                used_gates[id]['nbt']=nbt.read_from_nbt_file(open(used_gates[id]['data']['path'],'rb'))
        v['type']=id
        #place gate
        size:list=used_gates[id]['data']['size']
        #需要一个布局算法
        #方阵排列
        gatemap[k]={'id':id,'gate':used_gates[id]['data']['path'],'pos':[px,0,pz],'in':v['in']\
                    ,'out':v['out']}
        #export to ui.py project file format
        if typ!='port':
            for_uipy['components'].append({'type':typ,'rect':[px,pz,size[0],size[2]]})
        port_rest[k]={'in':v['in'],'out':v['out']}
        c+=1
        sz[1]=max(sz[1],size[1])
        if c%lnc==0:
            px=4
            pz+=size[2]+10
            sz[2]=max(sz[2],pz)
        else:
            px+=size[0]+10
            sz[0]=max(sz[0],px)
    mp=pathseek.Map(48,48,48)
    struct=nbtrd.structure(48,48,48)
    all_palette=[struct.create_blockstate("minecraft:stone"),struct.create_blockstate("minecraft:redstone_wire",nbt.NBTTagCompound())]
    all_palette[1]['Properties']['power']=nbt.NBTTagInt(0)
    all_palette[1]['Properties']['north']=nbt.NBTTagString('none')
    all_palette[1]['Properties']['south']=nbt.NBTTagString('none')
    all_palette[1]['Properties']['east']= nbt.NBTTagString('none')
    all_palette[1]['Properties']['west']= nbt.NBTTagString('none')
    struct.add_to_palette(nbtrd.blocks.BLOCK_STONE,struct.create_blockstate("minecraft:stone"))
    struct.add_to_palette(nbtrd.blocks.BLOCK_REDSTONE,all_palette[1])
    for e in gatemap.values():
        print(e['id'],':',e['pos'])
    '''
    TODO
    1.计算所需大小生成structure
    2.加注释
    3.路径方块放置
    4.部件放置到结构中
    '''
    for g in gatemap.values():
        '''
        获取nbt
        获取nbt.blocks
        获取palette
        获取palette对应方块名对应id
        setblock
        '''
        schemanbt:nbt.NBTTagCompound=used_gates[g['id']]['nbt']
        blks:nbt.NBTTagList=schemanbt['blocks']
        pal:nbt.NBTTagList=schemanbt['palette']
        base=len(all_palette)
        for pv in range(len(pal)):
            all_palette.append(pal[pv])
            struct.add_to_palette(pv+base,pal[pv])
        for b in blks:
            b:nbt.NBTTagCompound
            bpos:nbt.NBTTagList=b['pos']
            #pos
            bx,by,bz=bpos[0].value,bpos[1].value,bpos[2].value
            #palette
            state=b['state'].value
            newi=state+base
            rx=g['pos'][0]+bx
            ry=g['pos'][1]+by
            rz=g['pos'][2]+bz
            mp.add_obstacle(rx,ry,rz)
            struct.setblock(rx,ry,rz,newi)
            
    max_concurrent=12
    queue=multiprocessing.Queue(12)
    pool=[]
    #now connect
    for con in cons:
        a,b=con[0],con[1]
        aid,bid=gatemap[a]['id'],gatemap[b]['id']
        outs,ins=used_gates[aid]['data']['out'],used_gates[aid]['data']['in']
        touse_a,touse_b=port_rest[a]['out']-1,port_rest[b]['in']-1
        port_rest[a]['out']-=1
        port_rest[b]['in']-=1
        outp=vec_add(used_gates[aid]['data']['out'][touse_a][:3],gatemap[a]['pos'])
        inp=vec_add(used_gates[bid]['data']['in'][touse_b][:3],gatemap[b]['pos'])

        #寻路连接
        print(aid,'to',bid,end=':')
        conpath=mp.path_astar(outp[0],outp[1],outp[2],inp[0],inp[1],inp[2])
        print('ok')
        prev_line=[conpath[0]]
        prev_d=''
        for i in conpath:#[0,1,0],
            #四周都需要为空，不能有其他红石线连接
            for d in [[0,0,0],[0,-1,0],[1,0,0],[-1,0,0],[0,0,1],[0,0,-1]]:
                iv=vec_add(i,d)
                mp.add_obstacle(iv[0],iv[1],iv[2])
            # mp.add_obstacle(i[0],i[1]-1,i[2])
            struct.setblock(i[0],i[1],i[2],nbtrd.blocks.BLOCK_REDSTONE)
            struct.setblock(i[0],i[1]-1,i[2],nbtrd.blocks.BLOCK_STONE)
            #compose into horizontal and vertical parts
            deltav=[i[0]-prev_line[-1][0],i[2]-prev_line[-1][2]]
            nowdir='h' if deltav[1]!=0 else 'v'
            if prev_d=='':
                prev_d=nowdir
            elif nowdir!=prev_d:
                #should pack prev_line
                for_uipy['connections'].append(prev_line[0]+prev_line[-1])
                prev_line=[]
                prev_d=nowdir
            prev_line.append(i)
        #分配任务
        # pool.append(multiprocessing.Process(target=task_path,args=\
        #                                     [outp[0],outp[1],outp[2],inp[0],inp[1],inp[2],mp,queue],daemon=True))
    # done=0
    # working=0
    # p=0
    # while done<len(pool):
    #     if working<max_concurrent and p<len(pool):
    #         pool[p].start()
    #         p+=1
    #         working+=1
    #     else:
    #         recv=queue.get()
    #         if len(recv)>0:
    #             conpath=recv#mp.path_bfs(outp[0],outp[1],outp[2],inp[0],inp[1],inp[2])
    #             print(conpath)
    #             working-=1
    #             done+=1
    #             for i in conpath:
    #                 struct.setblock(i[0],i[1],i[2],nbtrd.blocks.BLOCK_REDSTONE)
    #                 struct.setblock(i[0],i[1]-1,i[2],nbtrd.blocks.BLOCK_STONE)
        #TODO 按路径放置方块

    # print(gatemap)
    with open(sys.argv[2].split('.')[0]+'.ui.json','w') as f:
        json.dump(for_uipy,f,indent=2)
    nbt.write_to_nbt_file(sys.argv[2],struct.get_nbt())
    print('done')

    # print('used:',used_gates)


        