import pygame,sys #sys是python的标准库，提供Python运行时环境变量的操控
import threading
import json
import copy
import nbtrd
import python_nbt.nbt as nbt
import tkinter as tk
import os
from tkinter import filedialog
from queue import Queue

comm=Queue(32)#两个线程通信用 cmd2display
com_dis2cmd=Queue(32)#display2cmd


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
def vsub(a,b)->list:
    return vadd(a,[-e for e in b])
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
def openf(given:str):
    global curf,blkmap,conn
    with open(given,'r') as f:
            d=json.load(f)
            blkmap=d['components']
            conn=d['connections']
    curf=given
def savef(path:str):
    with open(path,'w') as f:
        json.dump({'components':blkmap,'connections':conn},f)
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
        savef(args[1])
    elif args[0]=='open':
        openf(args[1])
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
        export(args[1])

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
def drawline(rect):
    pygame.draw.rect(buffer,(255,255,255),vadd(rect,render_origin+[0,0]))
def draw_gate(gate,rect,inmap=True):
    if inmap:
        pygame.draw.rect(buffer,(100,100,100),vadd(rect,render_origin+[0,0]),\
                        width=3)
    else:
        pygame.draw.rect(buffer,(100,100,100),rect,\
                        width=3)

    font=pygame.font.SysFont('arial',15)
    for p in gates[gate]['ports']:
        dp=[p[0]*BLOCK_RENDERW+rect[0],p[2]*BLOCK_RENDERW+rect[1],BLOCK_RENDERW,BLOCK_RENDERW]
        if inmap:
            pygame.draw.rect(buffer,(200,200,100),vadd(dp,render_origin+[0,0]))
        else:
            pygame.draw.rect(buffer,(200,200,100),dp)
    if inmap:
        buffer.blit(font.render(gate,True,(255,255,255)),vadd(rect,vadd((10,10,0,0),render_origin+[0,0])))
    else:
        buffer.blit(font.render(gate,True,(255,255,255)),vadd(rect,(10,10,0,0)))
def deal_sel(curpos:tuple[int,int]):
    '''
    处理鼠标模式（放置门etc)
    '''
    global selgate,selmode,blkmap,render_origin
    blkpos=[e-e%BLOCK_RENDERW for e in vsub(curpos,render_origin)]
    if selmode=='gate':
        gt=gates[selgate]
        if not available(blkpos,gt['size']):
            print('failed placing gate: place not enough')
            return
        blkmap.append({"type":selgate,"rect":[int(e/BLOCK_RENDERW) for e in blkpos]+(gt['size'])})
        #清空状态
        selmode=''
    elif selmode=='line1':
        global linep1
        linep1=blkpos
        selmode='line2'
    elif selmode=='line2':
        global linep2,linedir
        #做出选择:h or v
        if linedir=='h':
            linep2=[blkpos[0],linep1[1]]
        else:
            linep2=[linep1[0],blkpos[1]]
        
        addline([int(e/BLOCK_RENDERW) for e in linep1],[int(e/BLOCK_RENDERW) for e in linep2])
        selmode=''
def addline(p1,p2):
    '''
    p1,p2应该是以方块为单位的坐标
    '''
    dh=p2[0]-p1[0]
    dv=p2[1]-p1[1]
    if dh<0:
        dh=-dh
        p1[0]-=dh
    if dv<0:
        dv=-dv
        p1[1]-=dv
    l=p1+[dh,dv]
    
    conn.append(l)
#鼠标模式:=gate为放置门电路
def put_gate(type:str):
    global selgate,selmode
    '''
    在界面中放置门
    '''
    selgate=type
    selmode='gate'
def put_line():
    global selmode
    selmode='line1'
def menuopen():
    path=filedialog.askopenfilename()
    tkroot.title(DEFAULT_TITLE+" %s"%(path))
    openf(path)
def menusave():
    global curf
    if len(curf)==0:
        curf=filedialog.asksaveasfilename()
    tkroot.title(DEFAULT_TITLE+" %s"%(curf))
    savef(curf)
def menunew():
    global curf,selmode
    curf=''
    blkmap.clear()
    conn.clear()
    selmode=''
def menuexp():
    expf=filedialog.asksaveasfilename()
    export(expf)
def export(path:str):
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
                rz=sub['rect'][1]+bz
                struct.setblock(rx,ry,rz,newi)
        for lc in conn:
            #连接线
            rx,rz=lc[0],lc[1]
            for l in range(max(lc[2:])):
                struct.setblock(rx,1,rz,1)
                struct.setblock(rx,0,rz,0)
                if lc[3]:
                    rz+=1
                else:
                    rx+=1
        with open(path,'wb') as f:
            nbt.write_to_nbt_file(f,struct.get_nbt())
        print('done')

def draw_gridline(stpos,enpos):
    #考虑相对坐标
    pygame.draw.line(buffer,(100,100,100),vadd(stpos,render_origin),vadd(enpos,render_origin))
def clear_selmode():
    global selmode
    selmode=''
if __name__=='__main__':
    DEFAULT_TITLE="Minecraft Redstone Designer"
    selmode=''
    selgate=''
    linep1,linep2=[0,0],[0,0]
    linedir='h'
    render_origin=[0,0]
    dragging=False
    # pygame.init()  #内部各功能模块进行初始化创建及变量设置，默认调用
    # pygame.display.set_caption("MCrs")  #设置显示窗口的标题内容，是一个字符串类型
    size = width,height = 1200,600  #设置游戏窗口大小，分别是宽度和高度
    BLOCK_RENDERW=20
    #tkinter内嵌pygame 以便于加gui
    tkroot=tk.Tk()
    tkroot.title(DEFAULT_TITLE)
    frame=tk.Frame(tkroot,width=width,height=height)
    #状态栏
    status_bar=tk.Frame(tkroot,height=25,bd=1,relief=tk.RAISED)
    status_label=tk.Label(status_bar,text="(,)")
    frame.pack(fill=tk.BOTH,side=tk.TOP)
    status_label.pack(side=tk.LEFT)
    status_bar.pack(fill=tk.X,side=tk.BOTTOM)
    os.environ['SDL_WINDOWID'] = str(frame.winfo_id())
    os.environ['SDL_VIDEODRIVER'] = 'windib'
    tkroot.update()
    #菜单栏# 创建顶层菜单
    menubar = tk.Menu(tkroot)
    # 添加菜单项

    filemenu=tk.Menu(menubar)
    filemenu.add_command(label='Open',command=menuopen)
    filemenu.bind_all("<Control-o>",lambda arg:menuopen())
    filemenu.add_command(label='Save',command=menusave)
    filemenu.bind_all("<Control-s>",lambda arg:menusave())
    filemenu.add_command(label='New',command=menunew)
    filemenu.bind_all("<Control-n>",lambda arg:menunew())
    filemenu.add_command(label='Export',accelerator="Ctrl+E",command=menuexp)
    filemenu.bind_all("<Control-e>",lambda arg:menuexp())
    editmenu=tk.Menu(menubar)
    gatemenu=tk.Menu(editmenu)
    gatemenu.add_command(label='And',accelerator='q',command=lambda :put_gate('and'))
    gatemenu.bind_all("<q>",lambda arg:put_gate('and'))
    gatemenu.add_command(label='Or',accelerator= 'w' ,command=lambda :put_gate('or'))
    gatemenu.bind_all("<w>",lambda arg:put_gate('or'))
    gatemenu.add_command(label='Not',accelerator='e',command=lambda :put_gate('not'))
    gatemenu.bind_all("<e>",lambda arg:put_gate('not'))

    editmenu.add_cascade(label='Add Gate',menu=gatemenu)
    editmenu.add_command(label='Add Line',command=put_line,accelerator="Ctrl+f")
    gatemenu.bind_all("<Control-f>",lambda arg:put_line())
    # 将下拉菜单添加到顶层菜单项
    menubar.add_cascade(label='Files', menu=filemenu)
    menubar.add_cascade(label='Edit', menu=editmenu)

    tkroot.bind_all('<Escape>',lambda arg:clear_selmode())
    # 显示菜单
    tkroot.config(menu=menubar)
    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode(size)  #初始化显示窗口
    buffer=pygame.Surface(size)
    font=pygame.font.SysFont("Arial",25)
    while True:  #无限循环，直到Python运行时退出结束
        buffer.fill((0,0,0))
        if not comm.empty():
            #有来自cmd的消息
            data:list=comm.get()
            #解析
            if data[0]=='setblock':
                rect=[e*BLOCK_RENDERW for e in data[1]]
                pygame.draw.rect(screen,(255,255,255),(rect[0],rect[1],rect[0]+BLOCK_RENDERW,rect[1]+BLOCK_RENDERW))
            elif data[0]=='q':
                break
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

        #绘制网格
        #得出视野范围
        camerapos=[int(-e/BLOCK_RENDERW) for e in render_origin]
        grid=[size[0]/BLOCK_RENDERW,size[1]/BLOCK_RENDERW]
        #铅锤线
        for gx in range(int(grid[0])):
            draw_gridline(((camerapos[0]+gx)*BLOCK_RENDERW,camerapos[1]*BLOCK_RENDERW),((camerapos[0]+gx)*BLOCK_RENDERW,camerapos[1]*BLOCK_RENDERW+size[1]))
        #水平线
        for gy in range(int(grid[1])):
            draw_gridline((camerapos[0]*BLOCK_RENDERW,(camerapos[1]+gy)*BLOCK_RENDERW),(camerapos[0]*BLOCK_RENDERW+size[0],(camerapos[1]+gy)*BLOCK_RENDERW))
        #绘制已经放置的
        for e in blkmap:
            draw_gate(e['type'],[ee*BLOCK_RENDERW for ee in e['rect']])
        for e in conn:
            conrect=[max(ee*BLOCK_RENDERW,BLOCK_RENDERW) for ee in e]
            pygame.draw.rect(buffer,(255,255,255),vadd(conrect,render_origin+[0,0]))
        curpos=pygame.mouse.get_pos()
        #在状态栏显示鼠标所处的方块坐标
        curpos_toblkpos=[e/BLOCK_RENDERW for e in vsub(copy.deepcopy(curpos),render_origin)]
        txt_coordinate="(%d,%d)"%(curpos_toblkpos[0],curpos_toblkpos[1])
        status_label.config(text=txt_coordinate)
        #在左上角显示
        buffer.blit(font.render(txt_coordinate,False,(255,255,255)),(0,0))
        for event in pygame.event.get():  #从Pygame的事件队列中取出事件，并从队列中删除该事件
            if event.type == pygame.QUIT:  #获得事件类型，并逐类响应
                break
            elif event.type==pygame.MOUSEMOTION:
                if selmode=='line2':
                    #确定方向
                    cp_curpos=vsub(copy.deepcopy(curpos),render_origin)
                    delta=[cp_curpos[0]-linep1[0],cp_curpos[1]-linep1[1]]
                    if abs(delta[0])>abs(delta[1]):
                        linedir='h'
                    else:
                        linedir='v'
                    linep2=[e-e%BLOCK_RENDERW for e in cp_curpos]
                #拖动
                if dragging:
                    movdelta=pygame.mouse.get_rel()
                    render_origin=vadd(render_origin,movdelta)
            elif event.type==pygame.MOUSEBUTTONDOWN:
                deal_sel(pygame.mouse.get_pos())
                msebtn=pygame.mouse.get_pressed()
                #中键按下，开始拖动
                if msebtn[1]:
                    dragging=True
                    pygame.mouse.get_rel()
            elif event.type==pygame.MOUSEBUTTONUP:
                msebtn=pygame.mouse.get_pressed()
                if not msebtn[1]:
                    dragging=False
            elif event.type==pygame.WINDOWRESIZED:
                #重新设置画布大小
                size=width,height=(tkroot.winfo_width(),tkroot.winfo_height())
                buffer=pygame.display.set_mode(size)
                screen=pygame.display.set_mode(size)
                status_bar.lift()
        #绘制鼠标上面的内容
        if selmode=='gate':
            cp_curpos=vsub(copy.deepcopy(curpos),render_origin)
            drawpos=[e-e%BLOCK_RENDERW for e in cp_curpos]
            drawpos+=[e*BLOCK_RENDERW for e in gates[selgate]['size']]
            draw_gate(selgate,drawpos)
        elif selmode == 'line1':
            cp_curpos=vsub(copy.deepcopy(curpos),render_origin)
            drre=[e-e%BLOCK_RENDERW for e in cp_curpos]+[BLOCK_RENDERW,BLOCK_RENDERW]
            drawline(drre)
        elif selmode=='line2':
            i=0 if linedir=='h' else 1
            length=linep2[i]-linep1[i]
            st=copy.deepcopy(linep1)
            if length<0:
                length=-length
                st[i]-=length
            drawline(st+[length if not i else BLOCK_RENDERW,length if i else BLOCK_RENDERW])
                
        screen.blit(buffer,(0,0))
        pygame.display.flip()  #对显示窗口进行更新，默认窗口全部重绘
        tkroot.update()

