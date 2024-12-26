'''
读取识别qucs的.schma文件

'''
import xml.etree.ElementTree as et
import re
class SchemaElement:
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
    def get(self,name):
        '''
        获取child
        '''
        for comp in self.child:
            comp:SchemaElement
            if comp.name==name:
                return comp
        return None
    def __repr__(self):
        return f'<{self.name} {self.prop}>'
#<type name active x y xtext ytext mirrorX rotate "Value1" visible "Value2" visible ...>
class SchemaComponent:
    def __init__(self,type=None,name=None,inc:int=2):
        '''
        inc:输入端口数
        '''
        self.type=type
        self.name=name
        self.inc=inc
        pass
    def __repr__(self):
        return '%s(%s),input port num=%d'%(self.name,self.type,self.inc)
        pass
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
    return SchemaElement(name,0,prop),i


    
def read_schema(path):
    text=open(path).read()
    ptr=0
    els=[]
    el:SchemaElement
    el,ptr=fetch(text,ptr)
    print(f'<{el.name} {el.prop}>')
    while el!=None:
        els.append(el)
        print(f'<{el.name} {el.prop}>')
        el,ptr=fetch(text,ptr)
    # print(els)
    #开始构建树结构
    root=None
    parent:SchemaElement=None
    indent=0
    fl=0
    for e in els:
        e:SchemaElement
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
        else:
            #2nd level
            parent.append(e)
        if fl==1:
            fl=0
            for i in range(indent-4):
                print(' ',end='')
        else:
            for i in range(indent):
                print(' ',end='')
        print(e.name)
    return root
#<type name active x y xtext ytext mirrorX rotate "Value1" visible "Value2" visible ...>
def get_components(tree:SchemaElement)->list:
    '''
    从树结构中获取部件
    tree:总树
    '''
    l=[]
    for comp in tree.child:
        comp:SchemaElement
        if comp.name=='Components':
            for com in comp.child:
                com:SchemaElement
                ins=com.prop[8]
                ins:str
                inc=int(ins[1:-1])#remove "
                l.append(SchemaComponent(com.name,com.prop[0],inc))
            break
    return l
def get_connections(tree:SchemaElement,comps:list)->list:
    '''
    获取各个部件之间的连接
    '''
    webs={}
    points=[]
    trwires:SchemaElement=tree.get('Wires')
    for w in trwires.child:
        w:SchemaElement
        pts=[w.name]+w.prop[:3]
        #转int
        for i in range(4):
            pts[i]=int(pts[i])
        p1=pts[:2]
        p2=pts[2:]
        #这两个点是相连的
        if not p1 in webs:
            webs[p1]=[p2]
        elif not p2 in webs[p1]:
            webs[p1].append(p2)
        
        if not p2 in webs:
            webs[p2]=[p1]
        elif not p1 in webs[p2]:
            webs[p2].append(p1)
    
        
        
def recurse(node:et.Element):
    for ch in node:
        print(ch)
        recurse(ch)
root=read_schema('rs.sch')
comps=get_components(root)
con=get_connections(root,comps)
print(comps)

