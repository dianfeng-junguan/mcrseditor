# MC Redstone Circuit Editor

Mcrseditor is a Minecraft redstone circuit editor for faster building of large-scale circuit.

It provides a Gui to place gates and wires to build circuits and you can export the content to the nbt file for structure block.

It is still a immature project. The codes are still in a mess and many bugs are yet to be solved, yet it already is capable of converting circuit into valid nbt file smaller than 48\*48\*48 that can be actually generated in Minecraft.

This project needs **python_nbt** and **pygame_gui**.

## Files

**ui.py**

The core of the project. Run it and you can see the editor.

**nbtrd.py**

Nbt operations. **ui.py** uses this file to do nbt operations.

**menu.py**

The definition of the Menu widget.