'''
读取识别qucs的.schma文件

'''
import xml.etree.ElementTree as et
import re
class Element:
    def __init__(self,name,value,prop):
        self.name=name
        self.value=value
        self.prop=prop
        self.parent=None
        self.child=[]
    def append(self,ch):
        self.child.append(ch)
    def drop(self,ch):
        self.child.remove(ch)
    def __str__(self):
        return f'<{self.name} {self.prop}>'
    
    def __repr__(self):
        return f'<{self.name} {self.prop}>'
def skipspace(text,start)->int:
    '''返回第一个不是空白字符的下标'''
    i=start
    while i<len(text) and text[i]==' ':
        i+=1
    if i>=len(text):
        return -1
    return i
def forward(text:str,st:int)->tuple[str,int]:
    '''去字符串开头连续的没有遇到终止字符的子串'''
    s=''
    for i in range(st,len(text)):
        c=text[i]
        if c in [' ','>','\n']:
            break
        s+=c
    return s,i
def fetch(text:str,st:int):
    '''
    从文本中读出一个标签。一个<>。
    返回标签以及结束的下标+1。
    '''
    i=st
    name=''
    prop=[]
    try:
        i=text.index('<',st)+1
    except ValueError:
        i=-1
    if i==-1:
        return (None,None)
    
    i=skipspace(text,i)
    if i==-1:
        return (None,None)
    name,i=forward(text,i)
    i=skipspace(text,i)
    while i<len(text) and i!=-1 and text[i]!='>':
        p,i=forward(text,i)
        prop.append(p)
        i=skipspace(text,i)
    if i==-1:
        #没有遇到>就结束了
        return (None,None)
    i+=1
    return Element(name,0,prop),i


    
def tree(path):
    text=open(path).read()
    ptr=0
    els=[]
    el:Element
    el,ptr=fetch(text,ptr)
    print(f'<{el.name} {el.prop}>')
    while el!=None:
        els.append(el)
        print(f'<{el.name} {el.prop}>')
        el,ptr=fetch(text,ptr)
    # print(els)
    #开始构建树结构
    root=None
    parent:Element=None
    indent=0
    fl=0
    for e in els:
        e:Element
        if e.name in ['Qucs','Properties','Wires','Components','Diagrams','Symbol','Paintings']:
            #添加层级
            indent+=4
            fl=1
            if parent!=None:
                parent.append(e)
            e.parent=parent
            parent=e
            if root==None:
                root=parent
        elif e.name[0]=='/':
            parent=parent.parent
            indent-=4
        if fl==1:
            fl=0
            for i in range(indent-4):
                print(' ',end='')
        else:
            for i in range(indent):
                print(' ',end='')
        print(e.name)
    
            
def recurse(node:et.Element):
    for ch in node:
        print(ch)
        recurse(ch)
tree('rs.sch')
