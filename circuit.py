#TODO export的部分还要再优化一下。

from enum import Enum
import traceback
from PyQt6 import QtCore, QtGui, QtWidgets
import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtWidgets import QMainWindow
import json
import python_nbt.nbt as nbt
import pickle
from gatesel import *
from PyQt6.QtCore import Qt
from nbtrd import *
from ui import *
from subcircuitname import *
def export(path:str):
#生成nbt
    # nbtgates={"and":nbt.read_from_nbt_file('lib/nbt/and_2_1.nbt'),\
    #           "or":nbt.read_from_nbt_file('lib/nbt/or_2_1.nbt'),\
    #             "not":nbt.read_from_nbt_file('lib/nbt/not_1_1.nbt')}
    nbtgates={}
    for gatename in gateselwndui.gates.keys():
        nbtgates[gatename]=nbt.read_from_nbt_file(f'lib/nbt/{gatename}.nbt')

    struct=NBTStructure()
    all_palette=struct.palette
    for sub in current_circuit.gates:
        '''
        获取nbt
        获取nbt.blocks
        获取palette
        获取palette对应方块名对应id
        set_block
        '''
        schemanbt:nbt.NBTTagCompound=nbtgates[sub[1].name]
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
            rx=sub[0].x+bx
            ry=0+by
            #sub['rect'][1]
            rz=sub[0].y+bz
            struct.set_block(rx,ry,rz,newi)
    connected_sets=[]#sets of connected lines
    for lc in current_circuit.wires:
        lc=lc[0].tolist()+lc[1].tolist()
        #连接线
        startpos,endpos=lc[:2],lc[2:]
        startpos.insert(1,0)
        endpos.insert(1,0)
        #determine which index(direction) to extend
        direction_index=0 if startpos[0]!=endpos[0] else 2
        for l in range(startpos[direction_index],endpos[direction_index]):
            #calc interpolation
            ry=interpolation(startpos[1],endpos[1],startpos[direction_index],endpos[direction_index],l)
            rx=l if direction_index ==0 else startpos[0]
            rz=l if direction_index ==2 else startpos[2]
            struct.set_block(rx,ry,  rz,1)
            struct.set_block(rx,ry-1,rz,0)
            #check if neighboring a line or port
            side1=get_object_at([rx+int(direction_index/2),rz+1-int(direction_index/2)])
            side2=get_object_at([rx-int(direction_index/2),rz-1+int(direction_index/2)])
            #3 and 4 are used to detect extra points at two ends
            side3=get_object_at([rx-1+int(direction_index/2),rz-int(direction_index/2)]) if l==startpos[direction_index] else None
            side4=get_object_at([rx+1-int(direction_index/2),rz+int(direction_index/2)]) if l==endpos[direction_index]-1 else None
            for set in connected_sets:
                if lc in set:
                    #this line has been added
                    break#choose this set
            else:
                #has not been added
                set=[lc]
                connected_sets.append(set)
            #adding neighbors into the set of lc
            if not side1 is None and not side1 in set:
                set.append(side1)
            if not side2 is None and not side2 in set:
                set.append(side2)
            if not side3 is None and not side3 in set:
                set.append(side3)
            if not side4 is None and not side4 in set:
                set.append(side4)
    #now the connected_sets should contain sets where lines or ports are connected to each other
    #but not across the sets
    #put repeaters
    for set in connected_sets:
        pouts=[]
        pins=[]
        lines=[]
        tmpmap=ConMap()
        #classification
        for e in set:
            if isinstance(e[3],str):
                if e[3]=='out':
                    pouts.append(e)
                    tmpmap.addport(e[:3],'out')
                else:
                    pins.append(e)
                    tmpmap.addport(e[:3],'in')
            else:
                tmpmap.addline(e)
                lines.append(e)
        for outport in pouts:
            #for each outport, we find a way to every inport connected
            outport:list
            ways=[]
            #bfs
            buf=[outport.copy()+[-1]]#the last element is the parent index
            bufi=0
            cpos=outport
            def _bfs_bufcontains(pos):
                for b in buf:
                    if b[:3]==pos:
                        return True
                return False
            while bufi<len(buf):
                cpos=buf[bufi]
                for d in [[0,0,-1],[0,0,1],[0,-1,0],[0,1,0],[-1,0,0],[1,0,0]]:
                    newpos=vadd(cpos,d)
                    if tmpmap.isinput(newpos):
                        #found an inport, save the path
                        ptr=cpos
                        ways.append([])
                        while ptr[-1]!=-1:
                            ways[-1].insert(0,ptr)
                            ptr=buf[ptr[-1]]
                    elif tmpmap.walkable(newpos) and not _bfs_bufcontains(newpos):
                        buf.append(newpos+[bufi])
                bufi+=1
            #now we have paths from outport to inports. now check redstone power
            REDSTONE_FULLPOWER=15
            for pp in ways:
                power=REDSTONE_FULLPOWER
                i=0
                while i<len(pp):
                    if power==0:
                        #time to put a repeator
                        while i>=0 and not tmpmap.can_place_repeater(pp[i]):
                            i-=1
                        if i==-1:
                            #TODO nowhere to place
                            print('err: there\'s one or more path(s) that cannot be put with repeator. however, the exportation can still continue.')
                            break
                        tmpmap.put_repeater(pp[i])
                        prev=pp[i-1]
                        vdelta=vsub(pp[i],prev)
                        if vdelta[2]<0:#west
                            idelta_of_dir=0
                        if vdelta[2]>0:#east
                            idelta_of_dir=1
                        elif vdelta[0]<0:#north
                            idelta_of_dir=2
                        elif vdelta[0]>0:#south
                            idelta_of_dir=3
                        struct.set_block(pp[i][0],pp[i][1],pp[i][2],nbtrd.blocks.BLOCK_REPEATOR+idelta_of_dir)
                        power=REDSTONE_FULLPOWER#restore
                    if tmpmap.is_repeater(pp[i]):
                        power=REDSTONE_FULLPOWER
                    else:
                        power-=1
                    i+=1
    #must pass str path, otherwise it might cause problem
    nbt.write_to_nbt_file(path,struct.get_nbt())
    print('done')
class Point2D:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __add__(self, other):
        return Point2D(self.x + other.x, self.y + other.y)
    def __sub__(self, other):
        return Point2D(self.x - other.x, self.y - other.y)
    def __mul__(self, other):    # dot product
        return self.x * other.x + self.y * other.y
    def __abs__(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5
    def __str__(self):
        return f"({self.x}, {self.y})"
    def __truediv__(self, other):
        return Point2D(self.x / other, self.y / other)
    def tolist(self):
        return [self.x, self.y]
    def __dict__(self):
        return {"x": self.x, "y": self.y}
class SelectMode(Enum):
    NONE=0
    GATE = 1
    WIRE_START = 2
    WIRE_END = 3
    DELETE=4
class Selection:
    def __init__(self, mode:SelectMode=SelectMode.NONE,items=[]):
        self.mode = mode
        self.items = items
    def to_dict(self):
        return {"mode": self.mode.value, "items": [item.__dict__() for item in self.items]}
class Circuit:
    '''
    保存电路结构信息
    '''
    def __init__(self):
        self.gates = []
        self.wires = []

    def add_gate(self, position:Point2D,gate:Gate):
        self.gates.append([position, gate])
    def add_wire(self, start, end):
        self.wires.append([start, end])
    def remove_gate(self, gate):
        self.gates.remove(gate)
    def remove_wire(self, wire):
        self.wires.remove(wire)
    def clear(self):
        self.gates.clear()
        self.wires.clear()
    def to_dict(self):
        gates_json = []
        for gate in self.gates:
            gate:list[Point2D,Gate]
            gates_json.append({"position": gate[0].tolist(), "gate": gate[1].to_dict()})
        wires_json = []
        for wire in self.wires:
            wire:list[Point2D,Point2D]
            wires_json.append({"start": wire[0].tolist(), "end": wire[1].tolist()})
        return {"gates": gates_json, "wires": wires_json}
    def from_dict(self, data):
        self.clear()
        for gate_data in data["gates"]:
            gate_data:dict
            position = Point2D(*gate_data["position"])
            gate = Gate.from_dict(gate_data["gate"])
            self.add_gate(position, gate)
        for wire_data in data["wires"]:
            wire_data:dict
            start = Point2D(*wire_data["start"])
            end = Point2D(*wire_data["end"])
            self.add_wire(start, end)
    def to_nbt(self,path):
        export(path)
    def get_size(self):
        max_x = 0
        max_y = 0
        min_x = 0
        min_y = 0
        for gate in self.gates:
            gate:list[Point2D,Gate]
            max_x = max(max_x, gate[0].x)
            max_y = max(max_y, gate[0].y)
            min_x = min(min_x, gate[0].x)
            min_y = min(min_y, gate[0].y)
        for wire in self.wires:
            wire:list[Point2D,Point2D]
            max_x = max(max_x, wire[0].x, wire[1].x)
            max_y = max(max_y, wire[0].y, wire[1].y)
            min_x = min(min_x, wire[0].x, wire[1].x)
            min_y = min(min_y, wire[0].y, wire[1].y)
        return (max_x - min_x, max_y - min_y)
    def get_ports(self):
        ports = []
        for gate in self.gates:
            gate:list[Point2D,Gate]
            for port in gate[1].ports:
                ports.append([gate[0].x + port[0], gate[0].y + port[2], port[1]])
        return ports
    def get_pos_as_subcircuit(self):
        if len(self.gates)==0:
            return (0,0)
        min_x = self.gates[0][0].x
        min_y = self.gates[0][0].y
        for gate in self.gates:
            gate:list[Point2D,Gate]
            min_x = min(min_x, gate[0].x)
            min_y = min(min_y, gate[0].y)
        for wire in self.wires:
            wire:list[Point2D,Point2D]
            min_x = min(min_x, wire[0].x, wire[1].x)
            min_y = min(min_y, wire[0].y, wire[1].y)
        return (min_x, min_y)
    def get_ports_as_subcircuit(self):
        ports = []
        base_pos=self.get_pos_as_subcircuit()
        for gate in self.gates:
            gate:list[Point2D,Gate]
            for port in gate[1].ports:
                ports.append([gate[0].x + port[0] - base_pos[0], port[1], gate[0].y + port[2] - base_pos[1],port[3]])
        return ports
class RenderConfig:
    '''
    绘制的一些设置，包括绘制原点等等
    '''
    #绘制原点
    render_origin = Point2D(0, 0)
    #绘制缩放比例
    render_scale = 100
    #上述两个变量，只是用于存储graphicsView的内置缩放比例和绘制原点，不会被用作绘制的依据
    #网格线的设置
    grid_num_rows = 48
    grid_num_cols = 48
    grid_spacing = 30
    def __init__(self,render_origin=Point2D(0, 0),render_scale=100,grid_num_rows=48,grid_num_cols=48,grid_spacing=30):
        self.render_origin = render_origin
        self.render_scale = render_scale
        self.grid_num_rows = grid_num_rows
        self.grid_num_cols = grid_num_cols
        self.grid_spacing = grid_spacing
    def to_dict(self):
        return {"render_origin": self.render_origin.tolist(), "render_scale": self.render_scale, "grid_num_rows": self.grid_num_rows, "grid_num_cols": self.grid_num_cols, "grid_spacing": self.grid_spacing}
class CircuitArchive:
    '''
    用于将电路存储到文件中的类
    因为pickle不能存储带有自定义函数的类，所以只能另外定义一个
    '''
    gates=[]
    wires=[]
    def __init__(self, circuit:Circuit):
        tmpgates = circuit.gates
        tmpwires = circuit.wires
        for gate in tmpgates:
            gate:Point2D
            self.gates.append(gate.tolist())
        # for wire in tmpwires:
        #     wire:QLineF
        #     self.wires.append(wire)
class GridItem(QtWidgets.QGraphicsItem):
    '''
    辅助网格线的类，用于绘制网格线
    '''
    def __init__(self, num_rows=10, num_cols=10, spacing=100, parent=None):
        super().__init__(parent)
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.spacing = spacing

    def boundingRect(self):
        # 返回网格的边界矩形
        #由于地图理论上是无限大小，所以不应该有边界矩形
        #暂且使用很大很大的边界，当然边界要考虑绘制缩放比例
        return QtCore.QRectF(-10000, -10000,20000, 20000)
    
    def config_grid(self, num_rows, num_cols, spacing):
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.spacing = spacing

    def paint(self, painter, option, widget=None):
        # 定义网格线的画笔
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 1, QtCore.Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        # 绘制横线
        for i in range(self.num_rows + 1):
            y = i * self.spacing
            painter.drawLine(0, y, self.num_cols * self.spacing, y)

        # 绘制竖线
        for i in range(self.num_cols + 1):
            x = i * self.spacing
            painter.drawLine(x, 0, x, self.num_rows * self.spacing)
        
class GateItem(QtWidgets.QGraphicsItem):
    def __init__(self, position, parent=None,size_in_pixel=QtCore.QSize(30, 30),gate_info:Gate=None):
        super().__init__(parent)
        self.position = position
        self.size_in_pixel = size_in_pixel
        self.gate_info = gate_info
        if self.gate_info:
            self.size_in_pixel = QtCore.QSize(self.gate_info.size[0]*render_config.grid_spacing, self.gate_info.size[1]*render_config.grid_spacing)
    def boundingRect(self):
        return QtCore.QRectF(self.position.x, self.position.y, self.size_in_pixel.width(), self.size_in_pixel.height())
    def paint(self, painter, option, widget=None):
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 2, QtCore.Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        #绘制的时候要考虑到绘制原点和缩放比例
        w,h=self.size_in_pixel.width(),self.size_in_pixel.height()
        painter.drawRect(self.position.x, self.position.y, self.size_in_pixel.width(), self.size_in_pixel.height())
        painter.drawText(self.position.x +w//2, self.position.y + h//2, self.gate_info.name)
        painter.setBrush(QtGui.QColor(255, 0, 255))
        #绘制端口
        if self.gate_info:
            for port in self.gate_info.ports:
                painter.drawRect(self.position.x + port[0]*render_config.grid_spacing, self.position.y + port[2]*render_config.grid_spacing, render_config.grid_spacing, render_config.grid_spacing)

class GraphicsView(QtWidgets.QGraphicsView):
    def __init__(self, *args, **kwargs):
        '''
        请务必parent参数，调用setPrivateSceneProperty方法设置私有场景属性
        '''
        if kwargs.get('app'):
            self.app = kwargs.get('app')
            del kwargs['app']
        super().__init__(*args, **kwargs)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)  # 允许拖动
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.middleMouseButtonPressed = False
        self.gate_item = None
        self.selected_wire_start_item = None
        self.selected_wire_item = None
        self.setMouseTracking(True)

    def setPrivateSceneProperty(self, scene):
        '''
        设置私有场景属性，内部方法要用到
        '''
        self.__scene = scene
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.middleMouseButtonPressed = True
            self.middleMouseButtonPressPosition = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if select.mode == SelectMode.GATE:
            if self.gate_item:
                self.__scene.removeItem(self.gate_item)
            # 对齐到最近的网格点
            proto_pos=event.position()
            mapped_pos=self.mapToScene(int(proto_pos.x()), int(proto_pos.y()))
            grid_pos = self.snap_to_grid(mapped_pos)
            self.gate_item = GateItem(Point2D(int(grid_pos.x), int(grid_pos.y)), gate_info=select.items[0])
            self.__scene.addItem(self.gate_item)
            event.accept()
        elif select.mode == SelectMode.WIRE_START:
            #正在选择线路的起点，只显示一个大小的矩形
            if self.selected_wire_start_item:
                self.__scene.removeItem(self.selected_wire_start_item)
            # 对齐到最近的网格点
            proto_pos=event.position()
            mapped_pos=self.mapToScene(int(proto_pos.x()), int(proto_pos.y()))
            grid_pos = self.snap_to_grid(mapped_pos)
            select.items[0] = Point2D(int(grid_pos.x), int(grid_pos.y))
            self.selected_wire_start_item = QtWidgets.QGraphicsRectItem(QtCore.QRectF(select.items[0].x, select.items[0].y, render_config.grid_spacing, render_config.grid_spacing))
            self.selected_wire_start_item.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 2, QtCore.Qt.PenStyle.SolidLine))
            self.selected_wire_start_item.setBrush(QtGui.QColor(0, 0, 0))
            self.__scene.addItem(self.selected_wire_start_item)
            event.accept()
        elif select.mode == SelectMode.WIRE_END:
            if self.selected_wire_start_item:
                self.__scene.removeItem(self.selected_wire_start_item)
                self.selected_wire_start_item = None
            if self.selected_wire_item:
                self.__scene.removeItem(self.selected_wire_item)
                self.selected_wire_item = None
            #，从起点绘制到终点一条一格粗的线，这一条线只能是水平的或者竖直的，至于方向是由鼠标位置相对开始点的位移决定的
            proto_pos=event.position()
            mapped_pos=self.mapToScene(int(proto_pos.x()), int(proto_pos.y()))
            grid_pos = self.snap_to_grid(mapped_pos)
            start_pos = select.items[0]
            end_pos = Point2D(int(grid_pos.x), int(grid_pos.y))
            #根据相对位移得出是水平还是竖直的线
            if abs(grid_pos.x - start_pos.x) > abs(grid_pos.y - start_pos.y):
                #水平线
                end_pos = Point2D(int(grid_pos.x), int(start_pos.y))
            else:
                #竖直线
                end_pos = Point2D(int(start_pos.x), int(grid_pos.y))
            select.items[1]=end_pos
            #有的时候方向会向负方向，这样就需要修改start_pos和end_pos的位置
            #同时，负方向的时候，起点就没有被考虑在内，需要加上一个网格大小
            if end_pos.x < start_pos.x or end_pos.y < start_pos.y:
                start_pos, end_pos = end_pos, start_pos
                #FIXME 这里不正确，画出来会很长很长，一动还会变长
                # end_pos.x += render_config.grid_spacing
            #计算线大小
            size = [max(render_config.grid_spacing,abs(end_pos.x - start_pos.x)), max(render_config.grid_spacing,abs(end_pos.y - start_pos.y))]
            #向__scene添加rectitem来实现绘制直线
            rect = QtCore.QRectF(start_pos.x, start_pos.y, size[0], size[1])
            self.selected_wire_item =QtWidgets.QGraphicsRectItem(rect)
            self.selected_wire_item.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 2, QtCore.Qt.PenStyle.SolidLine))
            self.selected_wire_item.setBrush(QtGui.QColor(0, 0, 0))
            self.__scene.addItem(self.selected_wire_item)
            event.accept()
        elif select.mode==SelectMode.DELETE:
            pass
        elif self.middleMouseButtonPressed and event.buttons() & QtCore.Qt.MouseButton.MiddleButton:
            delta = event.position() - self.middleMouseButtonPressPosition
            # render_config.render_origin += Point2D(delta.x(), delta.y())
            self.middleMouseButtonPressPosition = event.position()
            # self.refresh_display()
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if select.mode == SelectMode.GATE and self.gate_item:
            # 对齐到最近的网格点
            proto_pos=event.position()
            mapped_pos=self.mapToScene(int(proto_pos.x()), int(proto_pos.y()))
            end_pos = self.snap_to_grid(mapped_pos)
            final_pos=Point2D(int(end_pos.x), int(end_pos.y))
            self.gate_item = GateItem(final_pos)
            #存储的时候要除以格子大小，保持统一
            divided_pos=Point2D(final_pos.x//render_config.grid_spacing,final_pos.y//render_config.grid_spacing)
            current_circuit.add_gate(divided_pos,Gate(select.items[0].name,select.items[0].size,select.items[0].ports))
            # self.__scene.removeItem(self.gate_item)
            self.gate_item = None
            select.mode = SelectMode.NONE
            # self.refresh_display()
            event.accept()
        elif select.mode == SelectMode.WIRE_START:
            select.mode = SelectMode.WIRE_END
            self.selected_wire_item = None
        elif select.mode == SelectMode.WIRE_END:
            #应该添加线路到current_circuit
            start_pos = select.items[0]
            end_pos = select.items[1]
            if end_pos.x < start_pos.x or end_pos.y < start_pos.y:
                start_pos, end_pos = end_pos, start_pos
            divided_start_pos=Point2D(start_pos.x//render_config.grid_spacing,start_pos.y//render_config.grid_spacing)
            divided_end_pos=Point2D(end_pos.x//render_config.grid_spacing,end_pos.y//render_config.grid_spacing)
            current_circuit.add_wire(divided_start_pos,divided_end_pos)
            self.selected_wire_start_item = None
            self.selected_wire_item = None
            select.mode = SelectMode.NONE
            select.items.clear()
        elif select.mode==SelectMode.DELETE:
            #根据鼠标点击位置获取该处的门电路或者线路，然后删除
            proto_pos=event.position()
            mapped_pos=self.mapToScene(int(proto_pos.x()), int(proto_pos.y()))
            grid_pos = self.snap_to_grid(mapped_pos)
            #当鼠标点击到门的矩形范围内或者线的范围内时删除
            for gate in current_circuit.gates:
                gte_spx=gate[0].x*render_config.grid_spacing
                gte_spy=gate[0].y*render_config.grid_spacing
                gte_epx=gte_spx+gate[1].size[0]*render_config.grid_spacing
                gte_epy=gte_spy+gate[1].size[1]*render_config.grid_spacing
                if gte_spx<=grid_pos.x<=gte_epx and gte_spy<=grid_pos.y<=gte_epy:
                    current_circuit.remove_gate(gate)
                    print("remove gate")
                    break
            for wire in current_circuit.wires:
                wire_spx=wire[0].x*render_config.grid_spacing
                wire_spy=wire[0].y*render_config.grid_spacing
                wire_epx=wire[1].x*render_config.grid_spacing
                wire_epy=wire[1].y*render_config.grid_spacing
                if wire_spx<=grid_pos.x<=wire_epx and wire_spy<=grid_pos.y<=wire_epy:
                    current_circuit.remove_wire(wire)
                    print("remove wire")
                    break
            self.app.refresh_display()
            event.accept()
        elif event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.middleMouseButtonPressed = False
        super().mouseReleaseEvent(event)

    def snap_to_grid(self, position):
        x = round(position.x() / render_config.grid_spacing) * render_config.grid_spacing
        y = round(position.y() / render_config.grid_spacing) * render_config.grid_spacing
        return Point2D(x, y)
#=================global variables=

opened_circuit = None
render_config = RenderConfig()
#选择数据
select=Selection()
current_circuit=Circuit()
#=================global variables end=

def save_circuit(circ:Circuit,path:str):
    # 直接将circuit以json格式保存电路，不经过可视化编辑
    #设置render_config
    render_config.render_origin=Point2D(0,0)
    render_config.render_scale=1.0

    # 已经有保存路径，直接保存
    try:
        with open(path, 'w') as f:
            #使用json保存，因为Point2D不能序列化也不能直接json.dumps,所以要对每一个gates中的Point2D转换成字典
            #然后再json.dumps
            json.dump({"circuit":circ.to_dict(), "select":Selection().to_dict(), "render_config":render_config.to_dict()}, f,indent=4)
        print("saved circuit")
    except Exception as e:
        print(f"保存电路时发生错误: {e}")
        traceback.print_exc()
def open_circuit(filename:str)->Circuit:
    '''
    直接加载json文件到全局变量中。
    '''
    circ:Circuit
    if filename:
        try:
            with open(filename, 'rb') as f:
                #因为json里面gates和wires都是用dict存储的，所以要每个dict表示的点转换成Point2D再存到current_circuit中
                data=json.load(f)
                circ.from_dict(data["circuit"])
                select=Selection(**data["select"])
                render_config=RenderConfig(**data["render_config"])
            opened_circuit = filename
        except Exception as e:
            print(f"打开电路时发生错误: {e}")
    else:
        raise ValueError("未提供有效的文件路径")
    return circ
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(804, 605)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setAutoFillBackground(True)
        self.graphicsView = GraphicsView(parent=self.centralwidget,app=self)
        self.graphicsView.setGeometry(QtCore.QRect(0, 0, 801, 561))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.graphicsView.sizePolicy().hasHeightForWidth())
        self.graphicsView.setSizePolicy(sizePolicy)
        self.graphicsView.setAutoFillBackground(True)
        self.graphicsView.setObjectName("graphicsView")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 804, 22))
        self.menubar.setObjectName("menubar")
        self.menu = QtWidgets.QMenu(parent=self.menubar)
        self.menu.setObjectName("menu")
        self.menu_2 = QtWidgets.QMenu(parent=self.menubar)
        self.menu_2.setObjectName("menu_2")
        self.menu_3 = QtWidgets.QMenu(parent=self.menubar)
        self.menu_3.setObjectName("menu_3")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionnew = QtGui.QAction(parent=MainWindow)
        self.actionnew.setObjectName("actionnew")
        self.actionnew.triggered.connect(self.new_circuit)
        self.actionsave = QtGui.QAction(parent=MainWindow)
        self.actionsave.setObjectName("actionsave")
        self.actionsave.triggered.connect(self.save_circuit)
        self.actionsave_as = QtGui.QAction(parent=MainWindow)
        self.actionsave_as.setObjectName("actionsave_as")
        self.actionsave_as.triggered.connect(self.save_as_circuit)
        self.actionopen = QtGui.QAction(parent=MainWindow)
        self.actionopen.setObjectName("actionopen")
        self.actionopen.triggered.connect(self.open_circuit)
        self.actionclose = QtGui.QAction(parent=MainWindow)
        self.actionclose.setObjectName("actionclose")
        self.actionclose.triggered.connect(self.close_circuit)
        self.actionexport = QtGui.QAction(parent=MainWindow)
        self.actionexport.setObjectName("actionexport")
        self.actionexport.triggered.connect(self.export_circuit)
        self.actiongate = QtGui.QAction(parent=MainWindow)
        self.actiongate.setObjectName("actiongate")
        self.actiongate.triggered.connect(self.add_gate)
        self.actionwire = QtGui.QAction(parent=MainWindow)
        self.actionwire.setObjectName("actionwire")
        self.actionwire.triggered.connect(self.add_wire)
        self.actiondelete = QtGui.QAction(parent=MainWindow)
        self.actiondelete.setObjectName("actiondelete")
        self.actiondelete.triggered.connect(self.delete_item)
        self.actioncancel = QtGui.QAction(parent=MainWindow)
        self.actioncancel.setObjectName("actioncancel")
        self.actioncancel.triggered.connect(self.cancel_do)
        self.actionexportassubcircuit = QtGui.QAction(parent=MainWindow)
        self.actionexportassubcircuit.setObjectName("actionexportassubcircuit")
        self.actionexportassubcircuit.triggered.connect(self.export_as_subcircuit)
        self.menu.addAction(self.actionnew)
        self.menu.addAction(self.actionsave)
        self.menu.addAction(self.actionsave_as)
        self.menu.addAction(self.actionopen)
        self.menu.addAction(self.actionclose)
        self.menu.addAction(self.actionexport)
        self.menu.addAction(self.actionexportassubcircuit)
        self.menu_2.addAction(self.actiongate)
        self.menu_2.addAction(self.actionwire)
        self.menu_2.addAction(self.actiondelete)
        self.menu_2.addAction(self.actioncancel)
        self.menubar.addAction(self.menu.menuAction())
        self.menubar.addAction(self.menu_2.menuAction())
        self.menubar.addAction(self.menu_3.menuAction())

        self.scene = QtWidgets.QGraphicsScene(parent=self.graphicsView)
        self.graphicsView.setScene(self.scene)
        self.graphicsView.setPrivateSceneProperty(self.scene)


        # 重写 wheelEvent
        self.graphicsView.wheelEvent = self.wheelEventOverride

        self.retranslateUi(MainWindow)
        
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.refresh_display()

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Minecraft redstone circuit editor"))
        self.menu.setTitle(_translate("MainWindow", "文件"))
        self.menu_2.setTitle(_translate("MainWindow", "编辑"))
        self.menu_3.setTitle(_translate("MainWindow", "关于"))
        self.actionnew.setText(_translate("MainWindow", "新建"))
        self.actionnew.setShortcut(_translate("MainWindow", "Ctrl+N"))
        self.actionsave.setText(_translate("MainWindow", "保存"))
        self.actionsave.setShortcut(_translate("MainWindow", "Ctrl+S"))
        self.actionsave_as.setText(_translate("MainWindow", "另存为"))
        self.actionsave_as.setShortcut(_translate("MainWindow", "Ctrl+Shift+S"))
        self.actionopen.setText(_translate("MainWindow", "打开"))
        self.actionopen.setShortcut(_translate("MainWindow", "Ctrl+O"))
        self.actionclose.setText(_translate("MainWindow", "关闭"))
        self.actionexport.setText(_translate("MainWindow", "导出"))
        self.actionexport.setShortcut(_translate("MainWindow", "Ctrl+E"))
        self.actiongate.setText(_translate("MainWindow", "电路元件"))
        self.actiongate.setShortcut(_translate("MainWindow", "Ctrl+G"))
        self.actionwire.setText(_translate("MainWindow", "线路"))
        self.actionwire.setShortcut(_translate("MainWindow", "Ctrl+R"))
        self.actiondelete.setText(_translate("MainWindow", "删除"))
        self.actiondelete.setShortcut(_translate("MainWindow", "Del"))
        self.actioncancel.setText(_translate("MainWindow", "取消操作"))
        self.actioncancel.setShortcut(_translate("MainWindow", "Esc"))
        self.actionexportassubcircuit.setText(_translate("MainWindow", "导出为子电路"))
        self.actionexportassubcircuit.setShortcut(_translate("MainWindow", "Ctrl+Shift+E"))

    def new_circuit(self):
        global current_circuit, opened_circuit
        #先保存已经打开的电路
        if opened_circuit:
            self.save_circuit()
            opened_circuit = None
        #新建电路
        current_circuit = Circuit()
        #刷新显示
        self.refresh_display()
    def cancel_do(self):
        #取消选择
        select.mode=SelectMode.NONE
        #设置光标为默认
        self.graphicsView.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        #刷新显示    
        self.refresh_display()
    def refresh_display(self):
        #清空画布
        self.scene.clear()
        #绘制电路
        for gate in current_circuit.gates:
            self.draw_gate(gate)
        for wire in current_circuit.wires:
            self.draw_wire(wire)
        #绘制辅助定位用网格线
        self.draw_grid()

    def draw_grid(self):
        # 考虑绘制缩放比例
        #使用griditem
        grid_item = GridItem(render_config.grid_num_rows, render_config.grid_num_cols, render_config.grid_spacing)
        self.scene.addItem(grid_item)

    def draw_gate(self, gate):
        #绘制门电路
        #存储的坐标是没有乘以格子大小的，这里要乘上
        gate_pos=Point2D(gate[0].x*render_config.grid_spacing,gate[0].y*render_config.grid_spacing)
        gate_item = GateItem(gate_pos,gate_info=gate[1])
        self.scene.addItem(gate_item)

    def draw_wire(self, wire):
        #绘制线路
        start_pos = wire[0]
        end_pos = wire[1]
        #考虑格子大小，要乘上
        start_pos=Point2D(start_pos.x*render_config.grid_spacing,start_pos.y*render_config.grid_spacing)
        end_pos=Point2D(end_pos.x*render_config.grid_spacing,end_pos.y*render_config.grid_spacing)
        rect = QtCore.QRectF(start_pos.x, start_pos.y, max(render_config.grid_spacing,abs(end_pos.x - start_pos.x)), max(render_config.grid_spacing,abs(end_pos.y - start_pos.y)))
        rectitem=QtWidgets.QGraphicsRectItem(rect)
        rectitem.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 2, QtCore.Qt.PenStyle.SolidLine))
        rectitem.setBrush(QtGui.QColor(0, 0, 0))
        self.scene.addItem(rectitem)
    def save_circuit(self):
        # 以json格式保存电路
        if not opened_circuit:  # 还没选定保存路径，先弹出文件选择窗口选择保存路径
            self.save_as_circuit()
        #设置render_config
        render_config.render_origin=Point2D(self.graphicsView.mapToScene(0,0).x(),self.graphicsView.mapToScene(0,0).y())
        render_config.render_scale=self.graphicsView.transform().m11()

        # 已经有保存路径，直接保存
        try:
            with open(opened_circuit, 'w') as f:
                #使用json保存，因为Point2D不能序列化也不能直接json.dumps,所以要对每一个gates中的Point2D转换成字典
                #然后再json.dumps
                json.dump({"circuit":current_circuit.to_dict(), "select":select.to_dict(), "render_config":render_config.to_dict()}, f,indent=4)
            print("saved circuit")
        except Exception as e:
            print(f"保存电路时发生错误: {e}")
            traceback.print_exc()

    def save_as_circuit(self):
        # 弹出文件选择窗口选择保存路径
        global opened_circuit
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(None, "保存电路", "", "MCRS Circuit Files (*.mcrs)")
        if filename:
            opened_circuit = filename
            self.save_circuit()

    def open_circuit(self):
        # 弹出文件选择窗口选择打开路径
        global opened_circuit, current_circuit, select, render_config
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(None, "打开电路", "", "MCRS Circuit Files (*.mcrs)")
        if filename:
            try:
                with open(filename, 'rb') as f:
                    #因为json里面gates和wires都是用dict存储的，所以要每个dict表示的点转换成Point2D再存到current_circuit中
                    data=json.load(f)
                    current_circuit.from_dict(data["circuit"])
                    select=Selection(**data["select"])
                    render_config=RenderConfig(**data["render_config"])
                opened_circuit = filename
                self.refresh_display()
            except Exception as e:
                print(f"打开电路时发生错误: {e}")


    def close_circuit(self):
        global opened_circuit, current_circuit, select, render_config
        #先保存已经打开的电路
        if opened_circuit:
            self.save_circuit()
            opened_circuit = None
        #清空画布
        self.scene.clear()
        #清空选择数据
        select=Selection()
        #清空电路数据
        current_circuit=Circuit()
        #清空渲染设置
        render_config=RenderConfig()

    def export_circuit(self):
        # 弹出文件选择窗口选择保存路径
        global opened_circuit
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(None, "导出电路", "", "NBT Files (*.nbt)")
        if filename:
            # 将文件保存为nbt格式
            try:
                current_circuit.to_nbt(filename)
                print("导出电路成功")
            except Exception as e:
                print(f"导出电路时发生错误: {e}")
                traceback.print_exc()

    def add_gate(self):
        #弹出添加门对话框
        gateselwndui.setupUi(gateselwnd)
        gateselwndui.set_grid_size(render_config.grid_spacing)
        gateselwnd.show()
        while gateselwnd.isVisible():
            app.processEvents()
        #选择完毕（show的时候会被阻塞）
        select.items.clear()
        if gateselwndui.selected_gate is None:
            print("未选择门")
            return
        select.items.append(gateselwndui.selected_gate)
        #选择完毕，更新选择模式
        select.mode=SelectMode.GATE
        #刷新显示    
        self.refresh_display()

    def add_wire(self):
        #更新选择模式
        select.mode=SelectMode.WIRE_START
        select.items.clear()
        select.items.append(Point2D(0,0))
        select.items.append(Point2D(0,0))
        #刷新显示    
        self.refresh_display()

    def delete_item(self):
        #更新选择模式
        select.mode=SelectMode.DELETE
        #设置光标为叉叉模样
        self.graphicsView.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.CrossCursor))
        #刷新显示    
        self.refresh_display()

    def wheelEventOverride(self, event):
       # 使用 Ctrl + 鼠标滚轮 改变缩放比例
       if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
           zoomFactor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
           self.graphicsView.scale(zoomFactor, zoomFactor)
           self.refresh_display()
           event.accept()
       else:
           # 默认的 wheelEvent 处理
           super(self.graphicsView.__class__, self.graphicsView).wheelEvent(event)
    
    def export_as_subcircuit(self):
        # 弹出文件选择窗口选择保存路径
        global opened_circuit
        subcircuit_dialog_app=Ui_SubcircuitNameDialog()
        subcircuit_dialog=QtWidgets.QDialog()
        subcircuit_dialog_app.setupUi(subcircuit_dialog)
        subcircuit_dialog.show()
        while subcircuit_dialog.isVisible():
            app.processEvents()
        #选择完毕（show的时候会被阻塞）
        #如果dialog被拒绝，则返回
        if not subcircuit_dialog.accepted:
            return
        filename=subcircuit_dialog_app.lineEdit.text()
        if not filename:
            print("未输入子电路名称")
            return
        #计算电路占用最小大小
        circuit_size=current_circuit.get_size()
        '''
        1.将文件保存为nbt格式
        2.生成相应的json
        '''
        #生成json
        gate_dict={"size":list(circuit_size),"ports":current_circuit.get_ports_as_subcircuit()}
        try:
            #读取一下已有的门放置丢失信息
            gateselwndui.load_gate_data()
            current_circuit.to_nbt("lib/nbt/"+filename+".nbt")
            gateselwndui.gates[filename]=gate_dict
            gateselwndui.save_gates()
            print("导出子电路成功")
        except Exception as e:
            print(f"导出子电路时发生错误: {e}")
            traceback.print_exc()
if __name__ == '__main__':
    app = QApplication(sys.argv)

    main_window = QMainWindow()
    w=Ui_MainWindow()
    w.setupUi(main_window)
    
    gateselwnd=QMainWindow()
    gateselwndui=Ui_GateSelectMainWindow()

    main_window.setWindowTitle('Minecraft redstone circuit editor')
    main_window.show()

    sys.exit(app.exec())
