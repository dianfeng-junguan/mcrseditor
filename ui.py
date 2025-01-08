import pygame,sys #sys是python的标准库，提供Python运行时环境变量的操控
import threading
import json
import copy

import pygame_gui.ui_manager
import nbtrd
import python_nbt.nbt as nbt
import tkinter as tk
import os
import menu
import pygame_gui
from tkinter import filedialog
from queue import Queue


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
def vmul(vec,num)->list:
    '''
    multiply every item of the vector with num. \\
    does not guarantee intactness of vec.
    '''
    return [e*num for e in vec]
def vdiv(vec,num)->list:
    '''
    divide every item of the vector with num. \\
    does not guarantee intactness of vec.
    the items of the returned list are ints.
    '''
    return [int(e/num) for e in vec]
    
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
        json.dump({'components':blkmap,'connections':conn},f,indent=4)
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
def get_port_or_line(pos:list)->list:
    '''
    returns the 3d position of the port or line at **pos**.
    returns None if there's nothing.
    pos needs to be 2d.
    '''
    #detect whether a port or a line is clicked
    #gates
    for sub in blkmap:
        #gates
        according_gate:dict=gates[sub['type']]
        ports=according_gate['ports']
        clicked_port=None
        for p in ports:
            if pos==vadd([p[0],p[2]],sub['rect'][:2]):
                #this port is clicked
                clicked_port=p
                break
        if not clicked_port is None:
            print('clicked port:',clicked_port)
            return clicked_port
    #line
    for c in conn:
        #format of line data:[x1,y1,z1,x2,y2,z2]
        direction='h'
        if c[2]!=c[5]:
            direction='v'
        x1,y1,z1,x2,y2,z2=c[0],c[1],c[2],c[3],c[4],c[5]
        if direction=='h' and pos[1]==c[2] and min(x1,x2)<=pos[0]<max(x1,x2) or \
            direction=='v' and pos[0]==c[0] and min(z1,z2)<=pos[0]<max(z1,z2):
            #match
            #need to calculate the y at pos if the line is not in xOz
            yv=y1
            if not y1==y2:
                #can only decrease up to one block per block
                line_len=abs(x1-x2) if direction=='h' else abs(z1-z2)
                k=(y1-y2)/line_len
                yv=y1-int(k*((pos[0]-z1) if direction=='h' else (pos[1]-z1)))
            print('clicked line:',[pos[0],yv,pos[1]])
            return [pos[0],yv,pos[1]]
    return None
def deal_sel(curpos:tuple[int,int]):
    '''
    处理鼠标模式（放置门etc)
    '''
    global selgate,selmode,blkmap,render_origin
    floored_pos=[e-e%BLOCK_RENDERW for e in vsub(curpos,render_origin)]
    block_pos=vdiv(floored_pos,BLOCK_RENDERW)
    if selmode=='gate':
        gt=gates[selgate]
        if not available(floored_pos,gt['size']):
            print('failed placing gate: place not enough')
            selmode=''
            return
        blkmap.append({"type":selgate,"rect":[int(e/BLOCK_RENDERW) for e in floored_pos]+(gt['size'])})
        #清空状态
        selmode=''
    elif selmode=='line1':
        global linep1
        clicked_subject=get_port_or_line(block_pos)
        linep1=[floored_pos[0]/BLOCK_RENDERW,1,floored_pos[1]/BLOCK_RENDERW]
        if not clicked_subject is None:
            linep1[1]=clicked_subject[1]#set y
        #eliminate the sudden change of line len
        linep2=copy.deepcopy(linep1)
        selmode='line2'
    elif selmode=='line2':
        global linedir
        #做出选择:h or v
        if linedir=='h':
            linep2=[floored_pos[0]/BLOCK_RENDERW,1,linep1[2]]
        else:
            linep2=[linep1[0],1,floored_pos[1]/BLOCK_RENDERW]
        clicked_subject=get_port_or_line(block_pos)
        if not clicked_subject is None:
            linep2[1]=clicked_subject[1]#set y
        
        addline(linep1,linep2)
        selmode=''
        linedir=''
def addline(p1,p2):
    '''
    add a line.
    p1,p2 needs to be 3d blockpos.
    '''
    conn.append(list(map(int,(p1+p2))))
def interpolation(vst,ven,pst,pen,pcur)->int:
    '''
    calcs the linear interpolation of v.\\
    the return value is an interpolation between vst and ven,\\
    the ratio is calced from pst, pen and pcur. pst and pen are the boundaries,\\
    and pcur is the point you want to calc.\\
    the result is floored.
    '''
    vdelta=ven-vst
    pdelta=pen-pst
    k=vdelta/pdelta
    pcurdelta=pcur-pst
    return int(vst+k*pcurdelta)
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
    pygame.display.set_caption(DEFAULT_TITLE+" %s"%(path))
    openf(path)
def menusave():
    global curf
    if len(curf)==0:
        curf=filedialog.asksaveasfilename()
    pygame.display.set_caption(DEFAULT_TITLE+" %s"%(curf))
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
                ry=0+by
                #sub['rect'][1]
                rz=sub['rect'][1]+bz
                struct.setblock(rx,ry,rz,newi)
        for lc in conn:
            #连接线
            #TODO 添加中继器
            startpos,endpos=lc[0:3],lc[3:]
            #determine which index(direction) to extend
            direction_index=0 if startpos[0]!=endpos[0] else 2
            for l in range(startpos[direction_index],endpos[direction_index]):
                #calc interpolation
                ry=interpolation(startpos[1],endpos[1],startpos[direction_index],endpos[direction_index],l)
                rx=l if direction_index ==0 else startpos[0]
                rz=l if direction_index ==2 else startpos[2]
                struct.setblock(rx,ry,  rz,1)
                struct.setblock(rx,ry-1,rz,0)
        #must pass str path, otherwise it might cause problem
        nbt.write_to_nbt_file(path,struct.get_nbt())
        print('done')

def draw_gridline(stpos,enpos):
    #考虑相对坐标
    pygame.draw.line(buffer,(100,100,100),vadd(stpos,render_origin),vadd(enpos,render_origin))
def clear_selmode():
    global selmode
    selmode=''

def window_end():
    global _lock
    _lock=False
    pygame.quit()
    sys.exit(0)
if __name__=='__main__':
    DEFAULT_TITLE="Minecraft Redstone Designer"
    selmode=''
    selgate=''
    #the starting and ending points of a line to be added in block pos.
    linep1,linep2=[0,0,0],[0,0,0]
    linedir='h'
    render_origin=[0,0]
    dragging=False
    pygame.init()  #内部各功能模块进行初始化创建及变量设置，默认调用
    pygame.display.set_caption(DEFAULT_TITLE)  #设置显示窗口的标题内容，是一个字符串类型
    size = width,height = 1200,600  #设置游戏窗口大小，分别是宽度和高度
    BLOCK_RENDERW=20
    
    ctrl=False
    #hot keys
    hot_key_map={
        'ctrl':{
            pygame.K_o:menuopen,
            pygame.K_s:menusave,
            pygame.K_e:menuexp,
        },
        'single':{
            pygame.K_q:lambda :put_gate('and'),
            pygame.K_w:lambda :put_gate('or'),
            pygame.K_e:lambda :put_gate('not'),
            pygame.K_r:put_line,
            pygame.K_ESCAPE:clear_selmode
        }   
    }
    screen = pygame.display.set_mode(size,pygame.RESIZABLE)  #初始化显示窗口
    buffer=pygame.Surface(size)
    font=pygame.font.SysFont("Arial",25)
    ui_manager=pygame_gui.ui_manager.UIManager(size)

    mainmenu=menu.MenuBar(width,ui_manager)
    mainmenu.add_item('Files',{'Open ctrl+o':menuopen,'Save ctrl+s':menusave,'Export ctrl+e':menuexp})
    mainmenu.add_item('Edit',{'Add q':lambda :put_gate('and'),\
                              'Or w':lambda :put_gate('or'),\
                                'Not e': lambda :put_gate('not'),\
                                    'Line r':put_line})
    clock=pygame.Clock()
    _lock=True
    while _lock:  #无限循环，直到Python运行时退出结束
        delta_time=clock.tick(60)/1000
        buffer.fill((0,0,0))

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
            e:list
            conrect=e.copy()
            conrect.pop(1)
            conrect.pop(3)#drop two ys
            conrect=vmul(conrect,BLOCK_RENDERW)
            #convert to [x1,z1,w,h]
            conrect[2]=conrect[2]-conrect[0]
            if conrect[2]==0:
                conrect[2]=BLOCK_RENDERW
            elif conrect[2]<0:
                conrect[2]*=-1
                conrect[0]-=conrect[2]
            conrect[3]=conrect[3]-conrect[1]
            if conrect[3]==0:
                conrect[3]=BLOCK_RENDERW
            elif conrect[3]<0:
                conrect[3]*=-1
                conrect[1]-=conrect[3]
            drawline(conrect)
            del conrect
        curpos=pygame.mouse.get_pos()
        #在状态栏显示鼠标所处的方块坐标
        curpos_toblkpos=[e/BLOCK_RENDERW for e in vsub(copy.deepcopy(curpos),render_origin)]
        txt_coordinate="(%d,%d)"%(curpos_toblkpos[0],curpos_toblkpos[1])
        if linedir in ['h','v']:
            txt_coordinate+=',%s'%(linedir)
        # status_label.config(text=txt_coordinate)
        #在左上角显示
        buffer.blit(font.render(txt_coordinate,False,(255,255,255)),(0,height-30))
        for event in pygame.event.get():  #从Pygame的事件队列中取出事件，并从队列中删除该事件
            if event.type == pygame.QUIT:  #获得事件类型，并逐类响应
                _lock=False
                break
            elif event.type==pygame.MOUSEMOTION:
                if selmode=='line2':
                    #确定方向
                    cp_curpos=vsub(copy.deepcopy(curpos),render_origin)
                    delta=[cp_curpos[0]-linep1[0]*BLOCK_RENDERW,cp_curpos[1]-linep1[2]*BLOCK_RENDERW]
                    if abs(delta[0])>abs(delta[1]):
                        linedir='h'
                    else:
                        linedir='v'
                    linep2=[(e-e%BLOCK_RENDERW)/BLOCK_RENDERW for e in cp_curpos]
                    linep2.insert(1,0)
                #拖动
                if dragging:
                    movdelta=pygame.mouse.get_rel()
                    render_origin=vadd(render_origin,movdelta)
            elif event.type==pygame.MOUSEBUTTONDOWN:
                msebtn=pygame.mouse.get_pressed()
                #中键按下，开始拖动
                if msebtn[1]:
                    dragging=True
                    pygame.mouse.get_rel()
                elif msebtn[0]:
                    #lbutton
                    deal_sel(pygame.mouse.get_pos())
            elif event.type==pygame.MOUSEBUTTONUP:
                msebtn=pygame.mouse.get_pressed()
                if not msebtn[1]:
                    dragging=False
            elif event.type==pygame.VIDEORESIZE:
                #重新设置画布大小
                size=width,height=(event.w,event.h)
                screen=pygame.display.set_mode(size,pygame.RESIZABLE)
                buffer=pygame.Surface(size)
            elif event.type==pygame.KEYUP:
                if event.key in [pygame.K_LCTRL,pygame.K_RCTRL]:
                    ctrl=False
            elif event.type==pygame.KEYDOWN:
                if event.key in [pygame.K_LCTRL,pygame.K_RCTRL]:
                    ctrl=True
                #hot keys
                #need control
                if ctrl:
                    for htk,f in hot_key_map['ctrl'].items():
                        if htk==event.key:
                            #hotkey
                            f()
                #single keys
                for htk,f in hot_key_map['single'].items():
                        if htk==event.key:
                            #hotkey
                            f()
            mainmenu.tackle_event(event,delta_time)
            ui_manager.process_events(event)
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
            i=0 if linedir=='h' else 2
            length=(linep2[i]-linep1[i])*BLOCK_RENDERW
            st=vmul(copy.deepcopy(linep1),BLOCK_RENDERW)
            if length<0:
                length=-length
                st[i]-=length
            st.pop(1)
            drawline(st+[length if not i else BLOCK_RENDERW,length if i else BLOCK_RENDERW])
                
        ui_manager.update(delta_time)
        ui_manager.draw_ui(buffer)
        screen.blit(buffer,(0,0))
        pygame.display.flip()  #对显示窗口进行更新，默认窗口全部重绘
        # tkroot.update()

