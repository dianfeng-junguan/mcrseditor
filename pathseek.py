from mpl_toolkits.mplot3d import axes3d
import matplotlib.pyplot as plt
import numpy as np
import sys
import multiprocessing
import noise
'''
寻路算法，用来连接两个端口
红石电路连接问题可以看成无权图
'''
class Map:
    '''
    寻路时使用的地图。
    '''
    def __init__(self,w,h,l):
        self.size=(w,h,l)
        self.obstacles=[]
        self.max_recurse=0
        self.__bfstmp=[]
    def resize(self,w,h,l):
        self.size=(w,h,l)
    def add_obstacle(self,x,y,z):
        '''
        设置某个点为障碍点，不能走。
        '''
        if not (x,y,z) in self.obstacles:
            self.obstacles.append([x,y,z])
    def clear_obstacle(self,x,y,z):
        if (x,y,z) in self.obstacles:
            self.obstacles.remove([x,y,z])
    def contains(self,x,y,z)->bool:
        '''
        判断一个点是否在地图内。
        '''
        return 0<=x<self.size[0] and 0<=y<self.size[1] and 0<=z<self.size[2]
    def accessible(self,pos)->bool:
        if not self.contains(pos[0],pos[1],pos[2]) or pos[:3] in self.obstacles:
            return False
        return True
    def path_dfs(self,x1,y1,z1,x2,y2,z2,recurse=0)->list:
        '''
        寻找最短路径。使用深度优先。
        '''
        if recurse>self.max_recurse:
            self.max_recurse=recurse
        if not self.contains(x1,y1,z1) or not self.contains(x2,y2,z2):
            return None
        if x1==x2 and y1==y2 and z1==z2:
            return [[x1,y1,z1]]
        #六个方向
        dir=[[0,0,1],[0,0,-1],[0,1,0],[0,-1,0],[1,0,0],[-1,0,0]]
        #路径
        minlen=10**8
        cur=[x1,y1,z1]
        minpath=[]
        self.add_obstacle(x1,y1,z1)
        for d in dir:
            n=[x1+d[0],y1+d[1],z1+d[2]]
            if self.accessible(n):
                res=self.path_dfs(n[0],n[1],n[2],x2,y2,z2,recurse+1)
                if res==None:
                    continue 
                if len(res)<minlen:
                    minpath=res
                    minlen=len(res)
        self.clear_obstacle(x1,y1,z1)
        if len(minpath)==0:
            return None
        return [cur]+minpath
    def bfs_contains(self,pos)->bool:
        for e in self.__bfstmp:
            if e[:3]==pos[:3]:
                return True
        return False
    def path_bfs(self,x1,y1,z1,x2,y2,z2)->list:
        '''
        广搜。
        '''
        self.__bfstmp.clear()
        if not self.contains(x1,y1,z1) or not self.contains(x2,y2,z2):
            return None
        #六个方向
        dir=[[0,0,1],[0,0,-1],[0,1,0],[0,-1,0],[1,0,0],[-1,0,0]]
        #路径
        minlen=10**8
        cur=[x1,y1,z1,-1]#第四个量代表父路径点
        minpath=[]
        self.__bfstmp.append(cur)
        i=0
        while len(self.__bfstmp)>i:
            f=self.__bfstmp[i]
            # print(f)
            for d in dir:
                n=[f[0]+d[0],f[1]+d[1],f[2]+d[2],i]
                if self.accessible(n) and not self.bfs_contains(n):
                    self.__bfstmp.append(n)
                if n[:3]==[x2,y2,z2]:
                    node=n
                    while node[3]!=-1:
                        minpath.insert(0,node)
                        node=self.__bfstmp[node[3]]
                    return minpath
            i+=1
        return None

if __name__=='__main__':
    #测试代码
    # 创建一个新的图形
    SIZE=10
    fig=plt.figure()
    ax=fig.add_subplot(projection='3d')
    map=Map(SIZE,SIZE,SIZE)
    # 关闭坐标轴
    for x in range(SIZE):
        for y in range(SIZE):
            for z in range(SIZE):
                r=abs(np.arctan(np.random.randn()*1.5)/(0.5*np.pi))
                if r>=0.7 and not (x,y,z)==(0,0,0) and not (x,y,z)==(SIZE-1,SIZE-1,SIZE-1):
                    map.add_obstacle(x,y,z)
                    ax.scatter(xs=x,ys=y,zs=z,s=30,marker='.',c='g',depthshade=True)
    p=map.path_bfs(SIZE/2,0,0,SIZE-1,SIZE-1,SIZE-1)
    # print('deepest recurse:',map.max_recurse)
    if p==None:
        print('no path found')
        sys.exit(0)
    print('path:',p)
    for e in p:
        ax.plot(xs=e[0],ys=e[1],zs=e[2],c='y',marker='*')
    # 显示图形
    plt.show()
