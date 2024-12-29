import pygame,sys #sys是python的标准库，提供Python运行时环境变量的操控
import threading
import json
import copy
import nbtrd
import python_nbt.nbt as nbt
import tkinter as tk
import os
from queue import Queue

comm=Queue(32)#两个线程通信用 cmd2display
com_dis2cmd=Queue(32)#display2cmd
def display_thread():
    selmode=''
    selgate=''
    # pygame.init()  #内部各功能模块进行初始化创建及变量设置，默认调用
    # pygame.display.set_caption("MCrs")  #设置显示窗口的标题内容，是一个字符串类型
    size = width,height = 800,600  #设置游戏窗口大小，分别是宽度和高度
    BLOCK_RENDERW=20
    #tkinter内嵌pygame 以便于加gui
    tkroot=tk.Tk()
    frame=tk.Frame(tkroot,width=width,height=height)
    frame.pack()
    os.environ['SDL_WINDOWID'] = str(frame.winfo_id())
    os.environ['SDL_VIDEODRIVER'] = 'windib'
    tkroot.update()
    #菜单栏# 创建顶层菜单
    menubar = tk.Menu(tkroot)

    # 添加菜单项
    
    filemenu=tk.Menu(menubar)
    filemenu.add_command(label='Open')
    filemenu.add_command(label='Save')
    filemenu.add_command(label='New')

    editmenu=tk.Menu(menubar)
    gatemenu=tk.Menu(editmenu)
    gatemenu.add_command(label='And',accelerator='shift+a',command=lambda :put_gate('and'))
    gatemenu.add_command(label='Or',accelerator='shift+o' ,command=lambda :put_gate('or'))
    gatemenu.add_command(label='Not',accelerator='shift+n',command=lambda :put_gate('not'))

    editmenu.add_cascade(label='Add Gate',menu=gatemenu)
    # 将下拉菜单添加到顶层菜单项
    menubar.add_cascade(label='Files', menu=filemenu)
    menubar.add_cascade(label='Edit', menu=editmenu)

    # 显示菜单
    tkroot.config(menu=menubar)

    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode(size)  #初始化显示窗口
    
    def draw_gate(gate,rect):
        pygame.draw.rect(screen,(100,100,100),(rect[0],rect[1],rect[0]+rect[2],rect[1]+rect[3]),\
                         width=3)
        font=pygame.font.SysFont('arial',15)
        screen.blit(font.render(gate,True,(255,255,255)),vadd(rect,(10,10)))
    def deal_sel(curpos:tuple[int,int]):
        nonlocal selgate,selmode
        '''
        处理鼠标模式（放置门etc)
        '''
        blkpos=(int(curpos[0]/BLOCK_RENDERW),int(curpos[1]/BLOCK_RENDERW))
        if selmode=='gate':
            com_dis2cmd.put('gate '+selgate+" %d,%d"%(blkpos[0],blkpos[1]))
        #清空状态
        selmode=''
    
    #鼠标模式:=gate为放置门电路
    def put_gate(type:str):
        nonlocal selmode,selgate
        '''
        在界面中放置门
        '''
        selgate=type
        selmode='gate'
    while True:  #无限循环，直到Python运行时退出结束
        
        if not comm.empty():
            #有来自cmd的消息
            data:list=comm.get()
            #解析
            if data[0]=='setblock':
                rect=[e*BLOCK_RENDERW for e in data[1]]
                pygame.draw.rect(screen,(255,255,255),(rect[0],rect[1],rect[0]+BLOCK_RENDERW,rect[1]+BLOCK_RENDERW))
            elif data[0]=='q':
                return
            elif data[0]=='update':
                pygame.display.update()
            elif data[0]=='gate':
                # rect=[e*BLOCK_RENDERW for e in data[2]]
                # pygame.draw.rect(screen,(100,100,100),(rect[0],rect[1],rect[0]+rect[2],rect[1]+rect[3]),\
                #                  width=3)
                # font=pygame.font.SysFont('arial',15)
                # screen.blit(font.render(data[1],True,(255,255,255)),vadd(rect,(10,10)))
                draw_gate(data[1],rect)
                #TODO 绘制端口位置


        for event in pygame.event.get():  #从Pygame的事件队列中取出事件，并从队列中删除该事件
            if event.type == pygame.QUIT:  #获得事件类型，并逐类响应
                return
            elif event.type==pygame.MOUSEMOTION:
                curpos=pygame.mouse.get_pos()
                if selmode=='gate':
                    draw_gate(selgate,curpos+tuple(gates[selgate]['size']))
            elif event.type==pygame.MOUSEBUTTONDOWN:
                deal_sel(pygame.mouse.get_pos())
        pygame.display.update()  #对显示窗口进行更新，默认窗口全部重绘
        tkroot.update()


helper="help\t\
    setblock <x,z> <block>\
        \tsave <path>\
        \tload <path>\
        \tgate [and/not/or] <x,z>\
        \tline <x1,z1> <v/h> <len>"
def within(v,bot,up)->bool:
    return bot<=v<up
def inarea(point,pos,size)->bool:
    return within(point[0],pos[0],pos[0]+size[0]) and within(point[1],pos[1],pos[1]+size[1])
def vadd(a,b)->list:
    c=[]
    for i in range(min(len(a),len(b))):
        c.append(a[i]+b[i])
    return c
def overlap(rect1,rect2)->bool:
    pos=rect1[:2]
    size=rect1[2:]
    return inarea(pos,rect2[:2],rect2[2:]) or inarea(vadd(pos,[0,size[1]]),rect2[:2],rect2[2:]) or\
              inarea(vadd(pos,[size[0],0]),rect2[:2],rect2[2:]) or inarea(vadd(pos,[size[0],size[1]]),rect2[:2],rect2[2:])
def available(pos,size)->bool:
    for i in blkmap:
        if overlap(pos+size,i['rect']) or overlap(i['rect'],pos+size):
            return False
    return True


blkmap=[]
conn=[]
curf=''
def solve(cmd:str):
    global blkmap,conn,curf
    args=cmd.strip().lower().split(' ')
    if args[0]=='help':
        print(helper)
    elif args[0] =='gate':
        pos=list(map(int,args[2].split(',')))
        gt=gates[args[1]]
        if not available(pos,gt['size']):
            print('failed placing gate: place not enough')
            return
        blkmap.append({"type":args[1],"rect":pos+gt['size']})
        comm.put(['gate',args[1],pos+gt['size']])
    elif args[0] in ['q','exit','quit']:
        comm.put('q')
        sys.exit()
    elif args[0]=='save':
        if len(args)<2:
            args.append(curf)
        with open(args[1],'w') as f:
            json.dump({'components':blkmap,'connections':conn},f)
    elif args[0]=='open':
        with open(args[1],'r') as f:
            d=json.load(f)
            blkmap=d['components']
            conn=d['connections']
        curf=args[1]
        for gt in blkmap:
            for x in range(gt['rect'][2]):
                for y in range(gt['rect'][3]):
                    comm.put(['setblock',vadd(gt['rect'][:2],(x,y))])
    elif args[0]=='line':
        p1=list(map(int,args[1].split(',')))
        direc=args[2]
        llen=int(args[3])
        rect=copy.deepcopy(p1)
        if direc=='v':#竖直方向
            rect+=(0,llen)
        elif direc=='h':
            rect+=(llen,0)
        else:
            print('unrecognized direction')
        conn.append(rect)
        for l in range(max(rect[2:])):
            comm.put(['setblock',vadd(p1,(l if direc=='h' else 0, l if direc=='v' else 0))])
    elif args[0]=='export':
        #生成nbt
        nbtgates={"and":nbt.read_from_nbt_file('lib/nbt/and_2_1.nbt'),\
                  "or":nbt.read_from_nbt_file('lib/nbt/or_2_1.nbt'),\
                    "not":nbt.read_from_nbt_file('lib/nbt/not_1_1.nbt')}
        struct=nbtrd.structure()
        #{'components':blkmap,'connections':conn}
        #blkmap:{"type":args[1],"rect":pos+gt['size']}
        all_palette=[]
        all_palette=[struct.create_blockstate("minecraft:stone"),struct.create_blockstate("minecraft:redstone_wire",nbt.NBTTagCompound())]
        all_palette[1]['Properties']['power']=nbt.NBTTagInt(0)
        all_palette[1]['Properties']['north']=nbt.NBTTagString('none')
        all_palette[1]['Properties']['south']=nbt.NBTTagString('none')
        all_palette[1]['Properties']['east']= nbt.NBTTagString('none')
        all_palette[1]['Properties']['west']= nbt.NBTTagString('none')
        struct.add_to_palette(nbtrd.blocks.BLOCK_STONE,struct.create_blockstate("minecraft:stone"))
        struct.add_to_palette(nbtrd.blocks.BLOCK_REDSTONE,all_palette[1])
        for sub in blkmap:
            '''
            获取nbt
            获取nbt.blocks
            获取palette
            获取palette对应方块名对应id
            setblock
            '''
            schemanbt:nbt.NBTTagCompound=nbtgates[sub['type']]
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
                rx=sub['rect'][0]+bx
                ry=1+by
                #sub['rect'][1]
                rz=sub['rect'][2]+bz
                struct.setblock(rx,ry,rz,newi)
        for lc in conn:
            #连接线
            rx,rz=lc[0],lc[1]
            for l in range(max(lc[2:])):
                struct.setblock(rx,1,rz,1)
                struct.setblock(rx,0,rz,0)
                if lc[3]:
                    rx+=1
                else:
                    rz+=1
        with open(args[1],'wb') as f:
            nbt.write_to_nbt_file(f,struct.get_nbt())
        print('done')

#加载门电路库
with open('gates.json','r') as f:
    global gates
    gates=json.load(f)
if len(sys.argv)>1:
    with open(sys.argv[1],'r') as f:
        cmds=f.readlines()
    for l in cmds:
        solve(l)
    comm.put(['q'])
    sys.exit()

if __name__=='__main__':
    #设置pygame线程
    displayth=threading.Thread(target=display_thread,daemon=True)
    displayth.start()
    while True:
        # cmd=input('cmd:')
        if not com_dis2cmd.empty():
            solve(com_dis2cmd.get())

