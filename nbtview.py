import math
import nbt
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Texture, NodePath, Geom, GeomNode, GeomVertexData, GeomVertexFormat, GeomVertexWriter, GeomTriangles
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import WindowProperties
from panda3d.core import LPoint3f
class NBTPreviewer(ShowBase):
    def __init__(self, nbt_file_path):
        ShowBase.__init__(self)# 新增一个变量来标记鼠标是否锁定
        self.mouse_locked = True

        # 加载 NBT 数据
        self.nbt_data = nbt.nbt.NBTFile(nbt_file_path)
        # 隐藏鼠标指针并锁定到窗口中心
        self.props = WindowProperties()

        # 显示结构
        self.display_structure()

        # 初始化摄像机移动速度
        self.move_speed = 0.2
        # 初始化鼠标灵敏度
        self.mouse_sensitivity = 0.2
        # 初始化按键状态
        self.key_map = {
            'w': False, 'a': False, 's': False, 'd': False,
            'space': False, 'shift': False
        }
        # 绑定按键事件
        self.accept('w', self.set_key, ['w', True])
        self.accept('w-up', self.set_key, ['w', False])
        self.accept('a', self.set_key, ['a', True])
        self.accept('a-up', self.set_key, ['a', False])
        self.accept('s', self.set_key, ['s', True])
        self.accept('s-up', self.set_key, ['s', False])
        self.accept('d', self.set_key, ['d', True])
        self.accept('d-up', self.set_key, ['d', False])
        self.accept('space', self.set_key, ['space', True])
        self.accept('space-up', self.set_key, ['space', False])
        self.accept('shift', self.set_key, ['shift', True])
        self.accept('shift-up', self.set_key, ['shift', False])
        # 绑定 Esc 键事件
        self.accept('escape', self.release_mouse)

        # 隐藏鼠标指针并锁定到窗口中心
        # props = WindowProperties()
        # props.setCursorHidden(True)
        # self.win.requestProperties(props)
        self.mouse_center_x = self.win.getXSize() // 2
        self.mouse_center_y = self.win.getYSize() // 2
        # self.win.movePointer(0, self.mouse_center_x, self.mouse_center_y)
        self.pos=[0,0,0]
        self.hpv=[0,0,0]
        # 添加任务来更新摄像机位置和视角
        self.taskMgr.add(self.update_camera, "update_camera")

    # 定义 release_mouse 方法
    def release_mouse(self):
        if self.mouse_locked:
            # 显示鼠标指针
            self.props.setCursorHidden(False)
            self.win.requestProperties(self.props)
            self.mouse_locked = False
        else:
            # 隐藏鼠标指针并锁定到窗口中心
            self.props.setCursorHidden(True)
            self.win.requestProperties(self.props)
            self.win.movePointer(0, self.mouse_center_x, self.mouse_center_y)
            self.mouse_locked = True
    def set_key(self, key, value):
        self.key_map[key] = value

    def update_camera(self, task):
        # 处理鼠标移动
        # if self.mouse_locked and self.mouseWatcherNode.hasMouse():
        #     mouse_x = self.mouseWatcherNode.getMouseX()
        #     mouse_y = self.mouseWatcherNode.getMouseY()
        #     dx = (mouse_x * self.win.getXSize() - self.mouse_center_x) * self.mouse_sensitivity
        #     dy = (mouse_y * self.win.getYSize() - self.mouse_center_y) * self.mouse_sensitivity

        #     # 更新摄像机视角
        #     self.hpv[0]-=dx
        #     self.hpv[1]=max(-90, min(90, self.hpv[1]-dy))
        #     print(self.hpv)
        #     self.camera.setH(self.hpv[0])
        #     self.camera.setP(self.hpv[1])
            # 限制俯仰角度
            # self.camera.setP(max(-90, min(90, self.camera.getP())))

            # 将鼠标移回窗口中心
            # self.win.movePointer(0, self.mouse_center_x, self.mouse_center_y)
            # 处理按键移动
        left = self.key_map['s'] - self.key_map['w']
        forward = self.key_map['a'] - self.key_map['d']
        up = self.key_map['space'] - self.key_map['shift']
        # 根据摄像机朝向计算移动向量
        camera_h = self.camera.getH()
        speed_delta=self.move_speed
        move_x = (forward * speed_delta * -self.math_sin(math.radians(camera_h))) + (left * speed_delta * -self.math_cos(math.radians(camera_h)))
        move_y = (forward * speed_delta * self.math_cos(math.radians(camera_h))) + (left * speed_delta * -self.math_sin(math.radians(camera_h)))
        move_z = up * speed_delta
        
        # 更新摄像机位置

        current_pos = self.pos#self.camera.getPos()
        
        delta=(move_x, move_y, move_z)
        new_pos = [current_pos[i]+delta[i] for i in range(3)]
        self.camera.setPos(new_pos[0],new_pos[1],new_pos[2])
        self.pos=new_pos
        return Task.cont

    def math_sin(self, angle):
        import math
        return math.sin(math.radians(angle))

    def math_cos(self, angle):
        import math
        return math.cos(math.radians(angle))

    def display_structure(self):
        # 获取结构的大小
        size = self.nbt_data['size']
        width = size[0].value
        height = size[1].value
        length = size[2].value

        # 获取方块数据
        blocks = self.nbt_data['blocks']

        # 遍历每个方块
        for block in blocks:
            # 获取方块的位置
            pos = block['pos']
            x = pos[0].value
            y = pos[1].value
            z = pos[2].value

            # 获取方块的状态
            state = block['state'].value

            # 优先从 palettes 获取，若没有则从 palette 获取
            if 'palettes' in self.nbt_data:
                palettes = self.nbt_data['palettes']
                # 这里简单假设使用第一个 palette，实际可根据需求调整
                palette = palettes[0]
            elif 'palette' in self.nbt_data:
                palette = self.nbt_data['palette']
            else:
                print("未找到有效的 palette 或 palettes 数据")
                continue

            # 确保 state 在有效范围内
            if state < len(palette):
                block_state = palette[state]
                # 获取方块名称
                block_name = block_state['Name'].value
            else:
                print(f"方块状态索引 {state} 超出 palette 范围")
                continue

            # 假设可以通过 block_name 确定方块类型，这里简单用 block_name 作为材质文件名
            texture_name = f"res/blocks/{block_name}.png"

            block_name=block_name.removeprefix('minecraft:')
            #部分方块的名字要变一下
            block_name=block_name.replace('redstone_wall_torch','redstone_torch')\
            .replace('redstone_wire','redstone_dust_line1')
            # 假设可以通过 state 确定方块类型，这里简单用 state 作为材质文件名
            texture_name = f"res/block/{block_name}.png"

            # 创建一个方块
            if block_name!='air':
                # 创建一个方块
                cube = self.create_cube(texture_name)
                cube.setPos(x, y, z)
                cube.reparentTo(self.render)

    def create_cube(self, texture_path):
        # 创建顶点数据
        format = GeomVertexFormat.getV3t2()
        vdata = GeomVertexData('cube', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        texcoord = GeomVertexWriter(vdata, 'texcoord')

        # 定义立方体的顶点
        vertices = [
            (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
            (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)
        ]

        # 定义立方体的面
        faces = [
            [0, 1, 2, 3], [1, 5, 6, 2], [5, 4, 7, 6],
            [4, 0, 3, 7], [3, 2, 6, 7], [4, 5, 1, 0]
        ]

        # 写入顶点和纹理坐标
        for face in faces:
            for i in face:
                vertex.addData3f(*vertices[i])
                if i % 2 == 0:
                    texcoord.addData2f(0, 0)
                else:
                    texcoord.addData2f(1, 1)

        # 创建几何图元
        prim = GeomTriangles(Geom.UHStatic)
        for i in range(0, len(vertices), 4):
            prim.addVertices(i, i + 1, i + 2)
            prim.addVertices(i, i + 2, i + 3)

        # 创建几何对象
        geom = Geom(vdata)
        geom.addPrimitive(prim)

        # 创建节点路径
        node = GeomNode('cube')
        node.addGeom(geom)
        cube = NodePath(node)

        # 加载纹理
        texture = self.loader.loadTexture(texture_path)
        cube.setTexture(texture)

        return cube


if __name__ == "__main__":
    nbt_file_path = 'examples/RSlocker.nbt'  # 替换为你的 NBT 文件路径
    app = NBTPreviewer(nbt_file_path)
    app.run()