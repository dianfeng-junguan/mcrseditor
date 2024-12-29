import pygame,sys #sys是python的标准库，提供Python运行时环境变量的操控
import threading
import json
from queue import Queue

comm=Queue(32)#两个线程通信用

def display_thread():
    pygame.init()  #内部各功能模块进行初始化创建及变量设置，默认调用
    size = width,height = 800,600  #设置游戏窗口大小，分别是宽度和高度
    screen = pygame.display.set_mode(size)  #初始化显示窗口
    pygame.display.set_caption("MCrs")  #设置显示窗口的标题内容，是一个字符串类型
    BLOCK_RENDERW=20
    while True:  #无限循环，直到Python运行时退出结束
        if not comm.empty():
            #有来自cmd的消息
            data:list=comm.get()
            #解析
            if data[0]=='setblock':
                pos=[e*BLOCK_RENDERW for e in data[1]]
                # blktp=data[2]
                pygame.draw.rect(screen,(255,255,255),(pos[0],pos[1],pos[0]+BLOCK_RENDERW,pos[1]+BLOCK_RENDERW))
            elif data[0]=='q':
                return
        for event in pygame.event.get():  #从Pygame的事件队列中取出事件，并从队列中删除该事件
            if event.type == pygame.QUIT:  #获得事件类型，并逐类响应
                return
                
        pygame.display.update()  #对显示窗口进行更新，默认窗口全部重绘
#设置pygame线程
displayth=threading.Thread(target=display_thread,daemon=True)
displayth.start()

helper="help\t\
    setblock <x,z> <block>\
        \tsave <path>\
        \tload <path>\
        \tgate [and/not/or] <x,z>\
        \tline <x1,z1> <x2,z2>"
def within(v,bot,up)->bool:
    return bot<=v<up
def inarea(point,pos,size)->bool:
    return within(pos[0],pos[0],pos[0]+size[0]) and within(pos[1],pos[1],pos[1]+size[1])
def vadd(a,b)->list:
    c=[]
    for i in range(len(a)):
        c.append(a[i]+b[i])
    return c
def overlap(rect1,rect2)->bool:
    pos=rect1[:2]
    size=rect1[2:]
    return inarea(pos,rect2[:2],rect2[2:]) or inarea(vadd(pos,[0,size[1]]),rect2[:2],rect2[2:]) or\
              inarea(vadd(pos,[size[0],0]),rect2[:2],rect2[2:]) or inarea(vadd(pos,[size[0],size[1]]),rect2[:2],rect2[2:])
def available(pos,size)->bool:
    for i in blkmap:
        if overlap(pos+size,i) or overlap(i,pos+size):
            return False
    return True



blkmap=[]
#加载门电路库
with open('gates.json','r') as f:
    global gates
    gates=json.load(f)
while True:
    cmd=input('cmd:')
    args=cmd.strip().lower().split(' ')
    if args[0]=='help':
        print(helper)
    elif args[0] =='gate':
        pos=list(map(int,args[2].split(',')))
        gt=gates[args[1]]
        if not available(pos,gt['size']):
            print('failed placing gate: place not enough')
            continue
        blkmap.append(pos+gt['size'])
        for x in range(gt['size'][0]):
            for y in range(gt['size'][1]):
                comm.put(['setblock',vadd(pos,(x,y))])
    elif args[0] in ['q','exit','quit']:
        comm.put('q')
        break