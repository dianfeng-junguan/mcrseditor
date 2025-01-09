import python_nbt.nbt as nbt
import threading
import multiprocessing
class structure:
    def __init__(self,x=48,y=48,z=48):
        self.data=nbt.NBTTagCompound()
        self.data['blocks']=nbt.NBTTagList(tag_type=nbt.NBTTagCompound)
        #引用
        self.blocks:nbt.NBTTagList=self.data['blocks']

        self.pal:nbt.NBTTagList=nbt.NBTTagList(tag_type=nbt.NBTTagCompound)
        self.data['palettes']=nbt.NBTTagList(tag_type=nbt.NBTTagList)
        self.data['palettes'].append(self.pal)
        #引用
        self.palette:nbt.NBTTagList=self.pal
        xx=nbt.NBTTagInt(x)
        yy=nbt.NBTTagInt(y)
        zz=nbt.NBTTagInt(z)
        self.data['size']=nbt.NBTTagList(value=[xx,yy,zz],tag_type=nbt.NBTTagInt)
        #引用
        self.size:nbt.NBTTagList=self.data['size']
    #放置一个方块。
    def setblock(self,x:int,y:int,z:int,type:int):
        blk=nbt.NBTTagCompound()
        blk['state']=nbt.NBTTagInt(type)
        xx=nbt.NBTTagInt(x)
        yy=nbt.NBTTagInt(y)
        zz=nbt.NBTTagInt(z)
        blk['pos']=nbt.NBTTagList(value=[xx,yy,zz],tag_type=nbt.NBTTagInt)
        #查重
        for b in self.blocks:
            if b['pos']==blk['pos']:
                self.blocks.remove(b)
        self.blocks.append(blk)
    def add_to_palette(self,index:int,blockstate:nbt.NBTTagCompound)->None:
        self.palette.insert(index,blockstate)
    def resize(self,x,y,z):
        self.data['size'][0]=nbt.NBTTagInt(x)
        self.data['size'][1]=nbt.NBTTagInt(y)
        self.data['size'][2]=nbt.NBTTagInt(z)
    @staticmethod
    def create_blockstate(name:str,properties:nbt.NBTTagCompound=None)->nbt.NBTTagCompound:
        state=nbt.NBTTagCompound()
        state['Name']=nbt.NBTTagString(name)
        if not (properties is None):
            state['Properties']=properties
        return state
    def get_type(self,name:str)->int:
        return self.palette.index(name)
    def get_nbt(self)->nbt.NBTTagCompound:
        return self.data
    def fill(self,x1:int,y1:int,z1:int,x2:int,y2:int,z2:int,type:int):
        '''
        填充方块，范围是[x1,x2),[y1,y2),[z1,z2)。
        '''
        #非常耗费时间，故使用多线程，每个线程负责一小块
        #线程数最大不超过5个
        #按照z方向分割
        dx=abs(x1-x2)
        dy=abs(y1-y2)
        dz=abs(z1-z2)
        threadc=max(1,min(20,int(dx*dy*dz/2000)))
        finished=[0]
        #线程完毕任务时，将finished+1，到等于线程数时，则全部完毕。
        thz=int(dz/threadc)
        #每个线程要完成的z长度
        taskz=[thz for i in range(threadc)]
        #开始的z坐标
        stz=[thz*i for i in range(threadc)]
        if dz%thz>0:
            #有余数，留给最后一个进程
            taskz[-1]+=dz%thz
        #这里用不了多进程，似乎nbt库里面的lambda会导致报错
        ths=[threading.Thread(target=fill_subtask, \
                              args=[x1,y1,stz[i],x2,y2,stz[i]+taskz[i],\
                                    type,self,finished],daemon=True) for i in range(threadc)]
        for t in ths:
            t.start()
        while finished[0]<threadc:
            pass
def fill_subtask(x1,y1,z1,x2,y2,z2,type,struct:structure,semaphore:list):
    for x in range(x1,x2):
        for y in range(y1,y2):
            # print('done %d,%d'%(x,y))
            for z in range(z1,z2):
                struct.setblock(x,y,z,type)
    print('task done')
    semaphore[0]+=1
class blocks(enumerate):
    BLOCK_STONE=0
    BLOCK_REDSTONE=1
    BLOCK_REPEATOR=2
    BLOCK_REDSTONE_TORCH=3
    BLOCK_LEVER=4

