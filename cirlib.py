import json
import os
import math


class Component:
    '''
    元件基类
    '''
    size = [0, 0, 0]
    input_num = 0
    output_num = 0

    def __init__(self, type, name):
        self.type = type
        self.name = name


class Gate(Component):
    '''
    门类，继承自Component
    '''
    def __init__(self, type, name):
        super().__init__(type, name)


# 以下是一些门实例
class AndGate(Gate):
    '''
    与门类，继承自Gate
    '''


class OrGate(Gate):
    '''
    或门类，继承自Gate
    '''


class NotGate(Gate):
    '''
    非门类，继承自Gate
    '''


class Connection:
    '''
    连接类，表示一个红石电路中的连接。
    '''
    def __init__(self, a, b):
        self.a = a
        self.b = b


class RedstoneCircuit:
    '''
    一个红石电路的抽象表示。
    '''
    def __init__(self):
        self.components = []
        self.cons = []

    def add_component(self, component):
        self.components.append(component)

    def remove_component(self, component):
        if component in self.components:
            self.components.remove(component)

    def connect(self, a, b):
        # 连接两个组件
        self.cons.append(Connection(a, b))

    def disconnect(self, a, b):
        # 断开两个组件的连接
        if Connection(a, b) in self.cons:
            self.cons.remove(Connection(a, b))

    def is_wire_conflict(self, new_wire, existing_wires):
        """
        检查新的连线是否与已有的连线冲突
        """
        from_pos, to_pos = new_wire["from"], new_wire["to"]
        for existing_wire in existing_wires:
            existing_from, existing_to = existing_wire["from"], existing_wire["to"]
            # 检查是否有重叠部分
            if (min(from_pos[0], to_pos[0]) <= max(existing_from[0], existing_to[0]) and
                    max(from_pos[0], to_pos[0]) >= min(existing_from[0], existing_to[0]) and
                    min(from_pos[1], to_pos[1]) <= max(existing_from[1], existing_to[1]) and
                    max(from_pos[1], to_pos[1]) >= min(existing_from[1], existing_to[1]) and
                    min(from_pos[2], to_pos[2]) <= max(existing_from[2], existing_to[2]) and
                    max(from_pos[2], to_pos[2]) >= min(existing_from[2], existing_to[2])):
                return True
        return False

    def is_wire_collide_with_component(self, new_wire, components):
        """
        检查新的连线是否与元件冲突
        """
        from_pos, to_pos = new_wire["from"], new_wire["to"]
        for component in components:
            pos = component["position"]
            size = component["size"]
            # 元件的边界范围
            min_x, max_x = pos[0], pos[0] + size[0]
            min_y, max_y = pos[1], pos[1] + size[1]
            min_z, max_z = pos[2], pos[2] + size[2]
            # 检查连线是否穿过元件
            if (min(from_pos[0], to_pos[0]) <= max_x and
                    max(from_pos[0], to_pos[0]) >= min_x and
                    min(from_pos[1], to_pos[1]) <= max_y and
                    max(from_pos[1], to_pos[1]) >= min_y and
                    min(from_pos[2], to_pos[2]) <= max_z and
                    max(from_pos[2], to_pos[2]) >= min_z):
                return True
        return False

    def calculate_spacing(self, num_connections):
        """
        根据连线数量动态计算间距
        """
        # 简单的线性关系，可根据实际情况调整
        return max(10, num_connections // 5)

    def check_connection_limit(self, component_list, connection_list):
        """
        检查连接是否超出元件的最大输入输出数量
        """
        input_counts = {comp["name"]: 0 for comp in component_list}
        output_counts = {comp["name"]: 0 for comp in component_list}

        for connection in connection_list:
            from_name = next((c["name"] for c in component_list if c["position"] == connection["from"][:3]), None)
            to_name = next((c["name"] for c in component_list if c["position"] == connection["to"][:3]), None)

            if from_name and to_name:
                output_counts[from_name] += 1
                input_counts[to_name] += 1

        for component in component_list:
            json_file = f"lib/{component['type']}_2_1.json"
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    max_input = len(data["in"])
                    max_output = len(data["out"])
                    if input_counts[component["name"]] > max_input or output_counts[component["name"]] > max_output:
                        raise ValueError(f"Connection limit exceeded for component {component['name']}")

    def export_json(self):
        ''' 
        将电路导出为可以被可视化编辑器读取的JSON格式。将会自动规划元件的放置位置。
        json文件格式如下：

        {
            "circuit_name":"circuit1",
            "circuit_size":[100,100,100],
            "components":[
                {
                    "type":"and_gate",
                    "name":"and1",
                    "in":2,
                    "out":1,
                    "position":[10,0,10],
                    "size":[50,50,50]
                },
                {
                    "type":"subcircuit",
                    "name":"comparator",
                    "in":2,
                    "out":1,
                    "position":[10,0,10],
                    "size":[50,50,50]
                },
                ...
            ],
            "connections":[
                {
                    "from":[50,0,50],
                    "to":[25,0,25],
                    "type":"horizontal_wire"
                },
                {
                    "from":[25,0,25],
                    "to":[25,10,25],
                    "type":"vertical_wire"
                }
            ]
        }
        '''
        circuit_name = "circuit1"
        circuit_size = [100, 100, 100]
        component_list = []
        connection_list = []

        # 计算方阵的行数和列数
        num_components = len(self.components)
        num_cols = int(math.ceil(math.sqrt(num_components)))
        num_rows = int(math.ceil(num_components / num_cols))

        # 动态计算间距
        spacing = self.calculate_spacing(len(self.cons))

        current_x = 10
        current_y = 0
        current_z = 10

        # 规划元件的放置位置
        for i, component in enumerate(self.components):
            # 读取元件的尺寸信息
            json_file = f"lib/{component.type.lower()}_2_1.json"
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    component.size = data["size"]
                    component.input_num = len(data["in"])
                    component.output_num = len(data["out"])
            else:
                raise FileNotFoundError(f"File for component not found: {json_file}")
                # component.size = [50, 50, 50]
                # component.input_num = 0
                # component.output_num = 0

            # 计算元件的位置
            row = i // num_cols
            col = i % num_cols
            position = [
                current_x + col * (component.size[0] + spacing),
                current_y,
                current_z + row * (component.size[2] + spacing)
            ]

            component_list.append({
                "type": component.type.lower(),
                "name": component.name,
                "in": component.input_num,
                "out": component.output_num,
                "position": position,
                "size": component.size,
                "used_inputs": [False] * component.input_num,
                "used_outputs": [False] * component.output_num
            })

        # 生成连线信息
        for connection in self.cons:
            a = next((c for c in component_list if c["name"] == connection.a.name), None)
            b = next((c for c in component_list if c["name"] == connection.b.name), None)

            if a and b:
                # 读取元件的端口信息
                json_file_a = f"lib/{a['type']}_2_1.json"
                json_file_b = f"lib/{b['type']}_2_1.json"
                if os.path.exists(json_file_a) and os.path.exists(json_file_b):
                    with open(json_file_a, 'r') as f:
                        data_a = json.load(f)
                    with open(json_file_b, 'r') as f:
                        data_b = json.load(f)

                    # 找到可用的输出端口
                    out_port_index = next((i for i, used in enumerate(a["used_outputs"]) if not used), None)
                    if out_port_index is None:
                        raise ValueError(f"No available output ports for component {a['name']}")
                    a["used_outputs"][out_port_index] = True
                    out_port_a = data_a["out"][out_port_index][:3]

                    # 找到可用的输入端口
                    in_port_index = next((i for i, used in enumerate(b["used_inputs"]) if not used), None)
                    if in_port_index is None:
                        raise ValueError(f"No available input ports for component {b['name']}")
                    b["used_inputs"][in_port_index] = True
                    in_port_b = data_b["in"][in_port_index][:3]

                    # 计算端口的全局坐标
                    from_pos = [a["position"][0] + out_port_a[0], a["position"][1] + out_port_a[1], a["position"][2] + out_port_a[2]]
                    to_pos = [b["position"][0] + in_port_b[0], b["position"][1] + in_port_b[1], b["position"][2] + in_port_b[2]]

                    # 生成连接线，只能朝着坐标轴的方向行进
                    current_pos = from_pos.copy()
                    while current_pos != to_pos:
                        if current_pos[0] != to_pos[0]:
                            next_pos = [to_pos[0] if abs(to_pos[0] - current_pos[0]) < 1 else current_pos[0] + (1 if to_pos[0] > current_pos[0] else -1), current_pos[1], current_pos[2]]
                            connection_type = "horizontal_wire" if current_pos[1] == next_pos[1] else "vertical_wire"
                            new_wire = {
                                "from": current_pos.copy(),
                                "to": next_pos.copy(),
                                "type": connection_type
                            }
                            if not self.is_wire_conflict(new_wire, connection_list) and not self.is_wire_collide_with_component(new_wire, component_list):
                                connection_list.append(new_wire)
                            current_pos = next_pos
                        elif current_pos[1] != to_pos[1]:
                            next_pos = [current_pos[0], to_pos[1] if abs(to_pos[1] - current_pos[1]) < 1 else current_pos[1] + (1 if to_pos[1] > current_pos[1] else -1), current_pos[2]]
                            connection_type = "horizontal_wire" if current_pos[1] == next_pos[1] else "vertical_wire"
                            new_wire = {
                                "from": current_pos.copy(),
                                "to": next_pos.copy(),
                                "type": connection_type
                            }
                            if not self.is_wire_conflict(new_wire, connection_list) and not self.is_wire_collide_with_component(new_wire, component_list):
                                connection_list.append(new_wire)
                            current_pos = next_pos
                        elif current_pos[2] != to_pos[2]:
                            next_pos = [current_pos[0], current_pos[1], to_pos[2] if abs(to_pos[2] - current_pos[2]) < 1 else current_pos[2] + (1 if to_pos[2] > current_pos[2] else -1)]
                            connection_type = "horizontal_wire" if current_pos[1] == next_pos[1] else "vertical_wire"
                            new_wire = {
                                "from": current_pos.copy(),
                                "to": next_pos.copy(),
                                "type": connection_type
                            }
                            if not self.is_wire_conflict(new_wire, connection_list) and not self.is_wire_collide_with_component(new_wire, component_list):
                                connection_list.append(new_wire)
                            current_pos = next_pos

        # 检查连接是否超出元件的最大输入输出数量
        self.check_connection_limit(component_list, connection_list)

        # 移除临时的 used_inputs 和 used_outputs 字段
        for component in component_list:
            component.pop("used_inputs", None)
            component.pop("used_outputs", None)

        # 整理成JSON格式
        circuit_json = {
            "circuit_name": circuit_name,
            "circuit_size": circuit_size,
            "components": component_list,
            "connections": connection_list
        }

        return json.dumps(circuit_json, indent=4)

# 创建一个红石电路实例
circuit = RedstoneCircuit()

# 创建两个或非门来构建RS锁存器
# 这里假设 or_gate1 是上半部分的或非门，or_gate2 是下半部分的或非门
or_gate1 = OrGate("or", "or_gate1")
or_gate2 = OrGate("or", "or_gate2")

# 将或非门添加到电路中
circuit.add_component(or_gate1)
circuit.add_component(or_gate2)

# 连接两个或非门以构建RS锁存器
# or_gate1的输出连接到or_gate2的一个输入
# or_gate2的输出连接到or_gate1的一个输入
circuit.connect(or_gate1, or_gate2)
circuit.connect(or_gate2, or_gate1)

# 导出电路为JSON格式
json_output = circuit.export_json()

# 将JSON输出保存到文件
with open('rs_latch_circuit.json', 'w') as f:
    f.write(json_output)

print("RS锁存器电路已成功导出到 rs_latch_circuit.json 文件。")