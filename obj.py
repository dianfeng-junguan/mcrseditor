'''
一级处理json文件，和具体的mc门电路做对应，以及摆放电路
'''
import sys
import json
import glob
import pathseek
import nbtrd
import python_nbt.nbt as nbt
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
def overlap(p1:tuple,s1:tuple,p2:tuple,s2:tuple)->bool:
    return ()
px=0
for k,v in comps.items():
    v:dict
    typ=v['type']
    #in:input c out:output c
    id=typ+'_'+str(v['in'])+'_'+str(v['out'])
    path='lib/'+id+'.json'
    if len(glob.glob(path))==0:
        print('error: gate not found:',id)
        sys.exit(-1)
    if not id in used_gates.keys():
        used_gates[id]={'path':path}
        with open(path,'r') as f:
            used_gates[id]['data']=json.load(f)
    v['type']=id
    #place gate
    size:list=used_gates[id]['data']['size']
    #需要一个布局算法
    #按x排列
    gatemap[k]={'id':id,'gate':used_gates[id]['data']['path'],'pos':[px,0,0],'in':v['in']\
                ,'out':v['out']}
    port_rest[k]={'in':v['in'],'out':v['out']}
    px+=size[0]+5
mp=pathseek.Map(px,48,48)
struct=nbtrd.structure(px,48,48)
struct.add_to_palette(nbtrd.blocks.BLOCK_STONE,struct.create_blockstate("minecraft:stone"))
print(used_gates)
'''
TODO
1.计算所需大小生成structure
2.加注释
3.路径方块放置
4.部件放置到结构中
'''
for g in gatemap.values():
    #TODO 完成这个函数
    for x in range(used_gates[g['id']]['data']['size'][0]):
        for y in range(used_gates[g['id']]['data']['size'][1]):
            for z in range(used_gates[g['id']]['data']['size'][2]):
                rx=g['pos'][0]+x
                ry=g['pos'][1]+y
                rz=g['pos'][2]+z
                mp.add_obstacle(rx,ry,rz)
                struct.setblock(rx,ry,rz,nbtrd.blocks.BLOCK_STONE)
def vec_add(l1,l2)->list:
    res=[]
    for i in range(len(l1)):
        res.append(l1[i]+l2[i])
    return res
#now connect
for con in cons:
    a,b=con[0],con[1]
    aid,bid=gatemap[a]['id'],gatemap[b]['id']
    outs,ins=used_gates[aid]['data']['out'],used_gates[aid]['data']['in']
    touse_a,touse_b=port_rest[a]['out']-1,port_rest[b]['in']-1
    port_rest[a]['out']-=1
    port_rest[b]['in']-=1
    outp=vec_add(used_gates[aid]['data']['out'][touse_a],gatemap[a]['pos'])
    inp=vec_add(used_gates[bid]['data']['in'][touse_b],gatemap[b]['pos'])

    #寻路连接
    print(outp,'to',inp)
    conpath=mp.path_bfs(outp[0],outp[1],outp[2],inp[0],inp[1],inp[2])
    for i in conpath:
        struct.setblock(i[0],i[1],i[2],nbtrd.blocks.BLOCK_STONE)
    print(conpath)
    #TODO 按路径放置方块
print(gatemap)
nbt.write_to_nbt_file(sys.argv[2],struct.get_nbt())
print('done')

# print('used:',used_gates)


    