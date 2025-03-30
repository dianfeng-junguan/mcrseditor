'''
circuit.py的代码用法的简单示例
simple demonstration of coding usage of circuit.py
'''
from circuit import *
template_circuit = Circuit()

and_gate_dict=json.load(open("lib/and_2_1.json","r"))
ports=[p[:3]+["in"] for p in and_gate_dict['in']]+[p[:3]+["out"] for p in and_gate_dict['out']]
size=[and_gate_dict['size'][0],and_gate_dict['size'][1]]

and_gate1 = Gate("and",size,ports)
and_gate2 = Gate("and",size,ports)

template_circuit.add_gate(Point2D(0,0),and_gate1)
template_circuit.add_gate(Point2D(10,10),and_gate2)
template_circuit.add_wire(Point2D(0,0),Point2D(0,10))
template_circuit.add_wire(Point2D(0,10),Point2D(10,10))

save_circuit(template_circuit,"template_circuit.mcrs")
template_circuit.to_nbt("template_circuit.nbt")


