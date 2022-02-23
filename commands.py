from export_wrl import export_wrl, MATERIALS_PROPERTY, MATERIAL_INDICES_PROPERTY
from mat4cad import *

from FreeCAD import Gui
import FreeCAD as App
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import QRect

from pathlib import Path
from math import ceil
import numpy as np

FREE2KI_CMD_EXPORT = "Free2KiExport"
FREE2KI_CMD_SET_MATERIAL = "Free2KiSetMaterial"

class Free2KiExport:
    def Activated(self):
        active_doc = App.ActiveDocument
        if not active_doc or not active_doc.FileName:
            QMessageBox.critical(None, "Error",
                "Failed to export. Active Document is not saved.")
            return

        if not (objects := get_shape_objects()):
            if not (objects := get_shape_objects(active_doc.RootObjects)):
                QMessageBox.critical(None, "Error",
                    "Failed to export. Nothing to export.")
                return

        document_path = Path(App.ActiveDocument.FileName)
        path = document_path.parent / (document_path.stem + ".wrl")

        if path.exists():
            if path.is_file():
                if QMessageBox.question(None, "Overwrite?",
                        f"\"{path}\" already exists. Overwrite?") == QMessageBox.No:
                    return
            else:
                QMessageBox.critical(None, "Error",
                    f"Failed to export. \"{path}\" exists and is not a file.")
                return

        export_wrl(path, objects)
        print(f"info: successfully exported \"{path.name}\"")

    def GetResources(self):
        return {
            "Pixmap": str((Path(__file__).parent / "icons" / "kicad.png").resolve()),
            "MenuText": "Export",
            "Tooltip": 
                "Export selected, visible objects (with children)."
        }

class Free2KiSetMaterial:
    def Activated(self):
        if not (material_name := SelectMaterialDialog().execute()):
            return

        material = Material.from_name(material_name)

        selection = {}
        for element in App.Gui.Selection.getSelectionEx():
            if element.HasSubObjects and hasattr(element.Object, "Shape"):
                faces = [int(name[4:]) - 1 for name in element.SubElementNames if name.startswith("Face")]
                selection[element.Object] = faces
            else:
                for obj in get_shape_objects([element.Object]):
                    selection[obj] = None

        for obj, faces in selection.items():
            if not MATERIALS_PROPERTY in obj.PropertiesList:
                obj.addProperty("App::PropertyStringList", MATERIALS_PROPERTY)
            if not MATERIAL_INDICES_PROPERTY in obj.PropertiesList:
                obj.addProperty("App::PropertyIntegerList", MATERIAL_INDICES_PROPERTY)

            if not faces:
                setattr(obj, MATERIALS_PROPERTY, [material_name])
                setattr(obj, MATERIAL_INDICES_PROPERTY, [0] * len(obj.Shape.Faces))
                obj.ViewObject.ShapeColor = material.diffuse
                obj.ViewObject.DiffuseColor = [material.diffuse]
                obj.ViewObject.Transparency = int(material.transparency * 99.0)
            else:
                materials = getattr(obj, MATERIALS_PROPERTY)
                if material_name in materials:
                    index = materials.index(material_name)
                else:
                    index = len(materials)
                    materials.append(material_name)
                
                setattr(obj, MATERIALS_PROPERTY, materials)

                material_indices = np.array(getattr(obj, MATERIAL_INDICES_PROPERTY), dtype=int)
                material_indices.resize(len(obj.Shape.Faces))
                material_indices[faces] = index
                setattr(obj, MATERIAL_INDICES_PROPERTY, material_indices.tolist())

            self.recalculate_materials(obj)

    @staticmethod
    def recalculate_materials(obj):
        materials = getattr(obj, MATERIALS_PROPERTY)
        material_indices = np.array(getattr(obj, MATERIAL_INDICES_PROPERTY))

        material_indices = material_indices[:len(obj.Shape.Faces)]

        used_materials = set()
        for index in material_indices:
            used_materials.add(materials[index])

        index_mapping = np.zeros(len(used_materials), dtype=int)
        colors = []
        for i, material_name in enumerate(used_materials):
            index_mapping[materials.index(material_name)] = i
            color = (0.0, 0.0, 0.0)
            if material := Material.from_name(material_name):
                color = material.diffuse
            colors.append(color)
        remapped_indices = index_mapping[material_indices]
        diffuse_color = np.array(colors, dtype=float)[remapped_indices]

        setattr(obj, MATERIALS_PROPERTY, list(used_materials))
        setattr(obj, MATERIAL_INDICES_PROPERTY, remapped_indices.tolist())
        obj.ViewObject.DiffuseColor = list(map(tuple, diffuse_color))

    def GetResources(self):
        return {
            "Pixmap": str((Path(__file__).parent / "icons" / "material.png").resolve()),
            "MenuText": "Set Material",
            "Tooltip": 
                "Set material for selected, visible objects."
        }

def get_shape_objects(parents=None):
    if parents is None:
        parents = App.Gui.Selection.getSelection()

    result = []
    for parent in parents:
        if parent.Visibility:
            if hasattr(parent, "Shape"):
                result.append(parent)
            elif hasattr(parent, "Group"):
                result += get_shape_objects(parent.Group)

    return result

class SelectMaterialDialog(QDialog):
    def __init__(self):
        super().__init__(None, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.color_preview = ColorBox()

        self.combo_base_material = QComboBox()
        self.combo_base_material.currentTextChanged.connect(self.on_base_material_change)

        self.combo_color = QComboBox()
        self.combo_color.currentTextChanged.connect(self.on_color_change)

        self.combo_variant = QComboBox()

        self.combo_base_material.addItems(BASE_MATERIALS.keys())

        self.button_set_material = QPushButton("Set Material")
        self.button_set_material.clicked.connect(self.set_material)
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.clicked.connect(self.reject)

        row_material = QHBoxLayout()
        row_material.addItem(QSpacerItem(4, 40))
        row_material.addWidget(self.color_preview)
        row_material.addItem(QSpacerItem(10, 40))
        row_material.addWidget(self.combo_base_material)
        row_material.addItem(QSpacerItem(10, 40))
        row_material.addWidget(self.combo_color)
        row_material.addItem(QSpacerItem(10, 40))
        row_material.addWidget(self.combo_variant)
        row_material.addItem(QSpacerItem(4, 40))

        row_button = QHBoxLayout()
        row_button.addWidget(self.button_set_material)
        row_button.addWidget(self.button_cancel)

        layout = QVBoxLayout()
        layout.addLayout(row_material)
        layout.addLayout(row_button)
        self.setLayout(layout)

    def on_base_material_change(self, new_base_material):
        colors = BASE_MATERIAL_COLORS[new_base_material]
        old_active_color = self.combo_color.currentText()
        self.combo_color.clear()
        self.combo_color.addItems(colors.keys())

        if old_active_color in colors:
            self.combo_color.setCurrentText(old_active_color)
        else:
            self.combo_color.setCurrentIndex(0)

        for i, color in enumerate(colors.values()):
            if type(color) == Material:
                color = color.diffuse
            r, g, b = color
            self.combo_color.setItemData(i, QColor(r*255, g*255, b*255), Qt.DecorationRole)

        variants = BASE_MATERIAL_VARIANTS[new_base_material]
        old_active_variant = self.combo_variant.currentText()
        self.combo_variant.clear()
        self.combo_variant.addItems(variants.keys())

        if old_active_variant in variants:
            self.combo_variant.setCurrentText(old_active_variant)
        else:
            self.combo_variant.setCurrentIndex(len(variants) // 2)

    def on_color_change(self, _):
        color = self.combo_color.itemData(self.combo_color.currentIndex(), Qt.DecorationRole)
        self.color_preview.updateColor(color)

    def set_material(self):
        self.accept()

    def execute(self):
        if self.exec_():
            return "-".join((
                self.combo_base_material.currentText(),
                self.combo_color.currentText(),
                self.combo_variant.currentText()
            ))

class ColorBox(QWidget):
    def __init__(self):
        super().__init__()

        self.setMinimumWidth(40)
        self.setMinimumHeight(24)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._color = QColor(0, 0, 0)

    def updateColor(self, rgb):
        self._color = rgb
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        brush = QBrush()
        brush.setColor(self._color)
        brush.setStyle(Qt.SolidPattern)
        rect = QRect(0, 0, self.width(), self.height())
        painter.fillRect(rect, brush)
        painter.end()

Gui.addCommand(FREE2KI_CMD_EXPORT, Free2KiExport())
Gui.addCommand(FREE2KI_CMD_SET_MATERIAL, Free2KiSetMaterial())
