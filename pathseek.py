from mpl_toolkits.mplot3d import axes3d
import matplotlib.pyplot as plt
import numpy as np
import sys
import multiprocessing
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
    def manhattan(self,x1,y1,z1,x2,y2,z2)->int:
        return abs(x1-x2)+abs(y1-y2)+abs(z1-z2)
    def __point_find(open_list,point)->int:
        '''
        只比较前三项（坐标），返回下标
        '''
        for i in range(len(open_list)):
            if open_list[i][:3]==point[:3]:
                return i
        return -1
    def path_astar(self,x1,y1,z1,x2,y2,z2)->list:
        '''
        a*算法。
        '''
        self.__bfstmp.clear()
        if not self.contains(x1,y1,z1) or not self.contains(x2,y2,z2):
            return None
        #六个方向
        dir=[[0,0,1],[0,0,-1],[0,1,0],[0,-1,0],[1,0,0],[-1,0,0]]
        #路径
        minlen=10**8
        cur=[x1,y1,z1,-1,0,0,0]#第四个量代表父路径点,第五个量是G,6th=h,7th=g+h
        INDEX_PARENT=3
        INDEX_G=4
        INDEX_H=5
        INDEX_F=6
        cur[INDEX_H]=self.manhattan(x1,y1,z1,x2,y2,z2)
        cur[INDEX_F]=cur[INDEX_H]
        minpath=[]
        #__bfstmp is the close list
        open_list=[]#open list
        open_list.append(cur)
        while len(open_list)>0:
            if len(self.__bfstmp)>3000:
                print('warning:path seeking taking more than 3000 steps')
            f=open_list.pop(0)
            self.__bfstmp.append(f)
            # print('distance:',self.__gh((x1,y1,z1),f[:3],(x2,y2,z2)))
            for d in dir:
                n=[f[0]+d[0],f[1]+d[1],f[2]+d[2],len(self.__bfstmp)-1,0,0,0]
                if n[:3]==[x2,y2,z2]:
                    node=n
                    while node[INDEX_PARENT]:
                        minpath.insert(0,node[:3])
                        node=self.__bfstmp[node[INDEX_PARENT]]
                    return minpath
                #忽略不能走以及已经在closed list中的
                if not self.accessible(n) or self.bfs_contains(n):
                    continue
                #gh
                n[INDEX_G]=f[INDEX_G]+1
                n[INDEX_H]=self.manhattan(n[0],n[1],n[2],x2,y2,z2)
                n[INDEX_F]=n[INDEX_G]+n[INDEX_H]
                #point find只比较前三项（坐标），返回下标
                finded=Map.__point_find(open_list,n)
                if finded == -1:
                    open_list.append(n)
                elif open_list[finded][INDEX_G]>n[INDEX_G]:
                    #重新计算G值，如果更小，就更新g值以及父节点
                    open_list[finded]=n

            #取gh最小,排序open list
            open_list.sort(key=lambda item: item[INDEX_F])
        return None
    def __gh(self,pst,pcu,pen)->int:
        #g+h
        g=0
        for i in range(3):
            g+=abs(pcu[i]-pst[i])
        h=0
        for i in range(3):
            g+=abs(pcu[i]-pen[i])
        return g+h
