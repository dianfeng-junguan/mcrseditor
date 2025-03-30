import json
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk

def create_3d_preview(json_file_path):
    try:
        # 读取 JSON 文件
        with open(json_file_path, 'r') as f:
            circuit_data = json.load(f)

        # 初始化 VTK 场景
        renderer = vtk.vtkRenderer()
        render_window = vtk.vtkRenderWindow()
        render_window.AddRenderer(renderer)
        interactor = vtk.vtkRenderWindowInteractor()
        interactor.SetRenderWindow(render_window)

        # 创建主窗口
        app = QApplication([])
        window = QMainWindow()
        v_layout = QVBoxLayout()

        # VTK 渲染器控件
        vtk_widget = QVTKRenderWindowInteractor()
        v_layout.addWidget(vtk_widget)
        render_window_interactor = vtk_widget.GetRenderWindow().GetInteractor()

        # 设置渲染器背景颜色
        renderer.SetBackground(0.1, 0.2, 0.4)

        # 绘制组件
        for component in circuit_data["components"]:
            pos = np.array(component["position"])
            size = np.array(component["size"])
            box_actor = vtk.vtkCubeSource()
            box_actor.SetXLength(size[0])
            box_actor.SetYLength(size[1])
            box_actor.SetZLength(size[2])

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(box_actor.GetOutputPort())

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(0, 1, 0)  # 绿色
            actor.SetPosition(pos)

            renderer.AddActor(actor)

        # 绘制连接
        for connection in circuit_data["connections"]:
            from_pos = np.array(connection["from"])
            to_pos = np.array(connection["to"])
            axis = to_pos - from_pos

            line_source = vtk.vtkLineSource()
            line_source.SetPoint1(from_pos)
            line_source.SetPoint2(to_pos)

            pipeline = vtk.vtkPolyDataPipe()
            pipeline.SetInputConnection(line_source.GetOutputPort())
            pipeline.SetRadius(0.1)  # 线的宽度

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(pipeline.GetOutputPort())

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(1, 0, 0)  # 红色
            renderer.AddActor(actor)

        # 添加到 VTK 渲染器中
        render_window.Render()

        # 设置相机位置和角度
        cam = renderer.GetActiveCamera()
        cam.SetPosition(5, 3, 1)
        cam.SetFocalPoint(0, 0, 0)

        # 显示窗口并运行事件循环
        window.setGeometry(100, 100, 800, 600)
        v_layout.addWidget(vtk_widget)
        window.setLayout(v_layout)
        window.show()

        render_window_interactor.Start()
    except FileNotFoundError:
        print(f"未找到文件: {json_file_path}")
    except json.JSONDecodeError:
        print(f"JSON 文件解析错误: {json_file_path}")
    except Exception as e:
        print(f"发生未知错误: {e}")

if __name__ == "__main__":
    json_file_path = 'rs_latch_circuit.json'  # 替换为实际的 JSON 文件路径
    create_3d_preview(json_file_path)