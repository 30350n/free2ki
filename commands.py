from export_vrml import export_vrml, MATERIALS_PROPERTY, MATERIAL_INDICES_PROPERTY, PROPERTIES
from mat4cad import *

from FreeCAD import Gui
import FreeCAD as App
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import QRect

import string
from pathlib import Path
from math import ceil
import numpy as np

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
        path = document_path.parent / document_path.stem

        if path.exists():
            if path.is_file():
                if QMessageBox.question(None, "Overwrite?",
                        f"\"{path}\" already exists. Overwrite?") == QMessageBox.No:
                    return
            else:
                QMessageBox.critical(None, "Error",
                    f"Failed to export. \"{path}\" exists and is not a file.")
                return

        export_vrml(path, objects)
        print(f"info: successfully exported \"{path.name}\"")

    def GetResources(self):
        return {
            "Pixmap": str((Path(__file__).parent / "icons" / "kicad.png").resolve()),
            "MenuText": "Export",
            "Tooltip": 
                "Export selected, visible objects (with children)."
        }

class Free2KiSetMaterials:
    def Activated(self):
        selection = {}
        for element in App.Gui.Selection.getSelectionEx():
            obj = element.Object
            if element.HasSubObjects and hasattr(obj, "Shape"):
                faces = [
                    int(name[4:]) - 1
                    for name in element.SubElementNames if name.startswith("Face")
                ]
                selection[obj] = faces
            else:
                for child in get_shape_objects([obj]):
                    selection[child] = None

        if not selection:
            QMessageBox.critical(None, "Error",
                "Failed to set material. Nothing is selected.")
            return

        if not (selected_materials := SelectMaterialDialog(selection).execute()):
            return

        for obj, faces, material in selected_materials:
            self.setup_material_indices(material, obj, faces)
        for obj in selection:
            self.recalculate_materials(obj)

    @staticmethod
    def setup_material_indices(material, obj, faces=None):
        if not MATERIALS_PROPERTY in obj.PropertiesList:
            obj.addProperty("App::PropertyStringList", MATERIALS_PROPERTY)
        if not MATERIAL_INDICES_PROPERTY in obj.PropertiesList:
            obj.addProperty("App::PropertyIntegerList", MATERIAL_INDICES_PROPERTY)

        if not faces:
            setattr(obj, MATERIALS_PROPERTY, [material.name])
            setattr(obj, MATERIAL_INDICES_PROPERTY, [0] * len(obj.Shape.Faces))
            obj.ViewObject.Transparency = int(material.transparency * 99.0)
        else:
            materials = getattr(obj, MATERIALS_PROPERTY)
            index = len(materials)
            materials.append(material.name)

            setattr(obj, MATERIALS_PROPERTY, materials)

            material_indices = np.array(getattr(obj, MATERIAL_INDICES_PROPERTY), dtype=int)
            material_indices.resize(len(obj.Shape.Faces))
            material_indices[faces] = index
            setattr(obj, MATERIAL_INDICES_PROPERTY, material_indices.tolist())

    @staticmethod
    def recalculate_materials(obj):
        materials = np.array(getattr(obj, MATERIALS_PROPERTY), dtype=object)
        material_indices = np.array(getattr(obj, MATERIAL_INDICES_PROPERTY))
        material_indices = material_indices[:len(obj.Shape.Faces)]

        used_materials = list({materials[index] for index in set(material_indices)})
        index_mapping = np.zeros(len(materials), dtype=int)
        for i, name in enumerate(used_materials):
            for index in np.where(materials == name):
                index_mapping[index] = i
        colors = np.array([
            mat.diffuse if (mat := Material.from_name(name)) else (0.0, 0.0, 0.0)
            for name in used_materials
        ])

        remapped_indices = index_mapping[material_indices]
        diffuse_color = colors[remapped_indices]

        setattr(obj, MATERIALS_PROPERTY, used_materials)
        setattr(obj, MATERIAL_INDICES_PROPERTY, remapped_indices.tolist())
        obj.ViewObject.DiffuseColor = list(map(tuple, diffuse_color))

    def GetResources(self):
        return {
            "Pixmap": str((Path(__file__).parent / "icons" / "material.png").resolve()),
            "MenuText": "Set Materials",
            "Tooltip": 
                "Set material for selected, visible objects."
        }

def get_shape_objects(parents=None):
    if parents is None:
        parents = App.Gui.Selection.getSelection()

    result = []
    for parent in parents:
        if parent.Visibility:
            if "PartDesign.Feature" in str(type(parent)):
                result.append(parent)
            elif hasattr(parent, "Group"):
                result += get_shape_objects(parent.Group)
            elif hasattr(parent, "Shape") and parent.Shape.Faces:
                result.append(parent)

    return list(set(result))

class SelectMaterialDialog(QDialog):
    MAX_HEIGHT = 300

    def __init__(self, selection):
        super().__init__(None, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        box_materials = QVBoxLayout()

        self.material_selectors = []
        names = (obj._Body.Label if hasattr(obj, "_Body") else obj.Label for obj in selection)
        for name, obj, faces in sorted(zip(names, *zip(*selection.items()))):
            if len(selection) > 1:
                box_materials.addWidget(QLabel(name))

            for sub_faces, material in self.get_existing_materials(obj, faces):
                material_selector = MaterialSelector(material)
                box_materials.addWidget(material_selector)
                self.material_selectors.append((obj, sub_faces, material_selector))

        layout = QVBoxLayout()

        widget_materials = QWidget()
        widget_materials.setLayout(box_materials)
        widget_materials.adjustSize()
        size = widget_materials.size()

        if size.height() > self.MAX_HEIGHT:
            scroll_area = QScrollArea()
            scroll_area.setWidget(widget_materials)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            scroll_area.adjustSize()
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.adjustSize()
            scroll_area.setFixedSize(size.width() + scroll_bar.size().width(), self.MAX_HEIGHT)
            layout.addWidget(scroll_area)
        else:
            layout.addWidget(widget_materials)

        self.button_set_material = QPushButton("Set Material")
        self.button_set_material.clicked.connect(self.set_material)
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.clicked.connect(self.reject)

        row_buttons = QHBoxLayout()
        row_buttons.addWidget(self.button_set_material)
        row_buttons.addWidget(self.button_cancel)
        layout.addLayout(row_buttons)

        self.setLayout(layout)

    @staticmethod
    def get_existing_materials(obj, faces):
        if PROPERTIES.issubset(obj.PropertiesList) and getattr(obj, MATERIALS_PROPERTY):
            material_indices = np.array(getattr(obj, MATERIAL_INDICES_PROPERTY), dtype=int)
            material_indices.resize(len(obj.Shape.Faces))

            face_material_indices = material_indices[faces] if faces else material_indices
            unique_material_indices = np.unique(face_material_indices)
            materials = [Material.from_name(name) for name in getattr(obj, MATERIALS_PROPERTY)]

            return [
                (np.nonzero(index == face_material_indices), materials[index])
                for index in unique_material_indices
            ]
        elif len(obj.ViewObject.DiffuseColor) > 1:
            colors = np.array(obj.ViewObject.DiffuseColor)
            colors.resize((len(obj.Shape.Faces), 4))
            
            face_colors = colors[faces] if faces else colors
            unique_colors = np.unique(face_colors, axis=0)
            materials = [
                Material.from_name(f"plastic-custom_{rgb2hex(color)}-semi_matte")
                for color in unique_colors
            ]

            return [
                (np.nonzero(np.all(color == face_colors, axis=1)), materials[index])
                for index, color in enumerate(unique_colors)
            ]
        else:
            color = obj.ViewObject.DiffuseColor[0]
            if np.all(np.isclose(color, (0.8, 0.8, 0.8, 0.0))):
                material = Material.from_name("plastic-mouse_grey-semi_matte")
            else:
                material = Material.from_name(f"plastic-custom_{rgb2hex(color)}-semi_matte")

            return [
                (faces, material)
            ]

    def set_material(self):
        self.accept()

    def execute(self):
        if self.exec_():
            return [
                (obj, faces, material_selector.get_material())
                for (obj, faces, material_selector) in self.material_selectors
            ]

class MaterialSelector(QWidget):
    def __init__(self, material=None):
        super().__init__()

        self.custom_color = (0.8, 0.8, 0.8)
        self.suppress_hexcode_update = False

        self.color_preview = ColorBox()
        self.combo_base_material = QComboBox()
        self.combo_color = QComboBox()
        self.color_hexcode = QLineEdit()
        self.combo_variant = QComboBox()

        self.combo_base_material.currentTextChanged.connect(self.on_base_material_change)
        self.combo_color.currentTextChanged.connect(self.on_color_change)
        self.color_hexcode.textChanged.connect(self.on_hexcode_change)
        self.combo_base_material.addItems(list(BASE_MATERIALS.keys()))

        self.color_hexcode.setMaxLength(6)
        self.color_hexcode.setInputMask("HHHHHH")
        font_metrics = QFontMetrics(self.font(), self)
        width = max((font_metrics.widthChar(c) for c in string.hexdigits)) * 6
        self.color_hexcode.setFixedWidth(width)

        self.combo_color.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Ignored)
        self.combo_variant.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Ignored)

        if material:
            self.combo_base_material.setCurrentText(material.base)
            if material.has_custom_color:
                self.combo_color.setCurrentText("custom")
                self.color_hexcode.setText(material.custom_color)
            else:
                self.combo_color.setCurrentText(material.color)
            self.combo_variant.setCurrentText(material.variant)

        layout = QHBoxLayout()
        layout.addItem(QSpacerItem( 4, 0))
        layout.addWidget(self.color_preview)
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(self.combo_base_material)
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(self.combo_color)
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(self.color_hexcode)
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(self.combo_variant)
        layout.addItem(QSpacerItem( 4, 0))
        self.setLayout(layout)

    def get_material(self):
        base = self.combo_base_material.currentText()
        if (color := self.combo_color.currentText()) == "custom":
            color = f"custom_{rgb2hex(self.custom_color)}"
        variant = self.combo_variant.currentText()
        return Material.from_name("-".join((base, color, variant)))

    def on_base_material_change(self, new_base_material):
        colors = BASE_MATERIAL_COLORS[new_base_material]
        if new_base_material not in ("special",):
            colors = {"custom": self.custom_color, **colors}

        old_active_color = self.combo_color.currentText()

        self.combo_color.clear()
        self.combo_color.addItems(list(colors.keys()))
        for i, color in enumerate(colors.values()):
            if type(color) == Material:
                color = color.diffuse
            r, g, b = color
            self.combo_color.setItemData(i, QColor(r*255, g*255, b*255), Qt.DecorationRole)
        if old_active_color in colors:
            self.combo_color.setCurrentText(old_active_color)
        else:
            self.combo_color.setCurrentIndex(0)

        variants = BASE_MATERIAL_VARIANTS[new_base_material]
        old_active_variant = self.combo_variant.currentText()
        self.combo_variant.clear()
        self.combo_variant.addItems(list(variants.keys()))

        if old_active_variant in variants:
            self.combo_variant.setCurrentText(old_active_variant)
        else:
            self.combo_variant.setCurrentIndex(len(variants) // 2)

    def on_color_change(self, new_color):
        qcolor = self.combo_color.itemData(self.combo_color.currentIndex(), Qt.DecorationRole)
        if qcolor and not self.suppress_hexcode_update:
            self.color_hexcode.setReadOnly(new_color != "custom")
            self.color_hexcode.setText(qcolor.name()[1:])
        self.color_preview.updateColor(qcolor)

    def on_hexcode_change(self, new_hexcode):
        self.custom_color = r, g, b = hex2rgb(new_hexcode.rjust(6, "0"))
        self.suppress_hexcode_update = True
        self.combo_color.setItemData(self.combo_color.currentIndex(),
            QColor(r*255, g*255, b*255), Qt.DecorationRole)
        self.suppress_hexcode_update = False

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

FREE2KI_CMD_EXPORT = "Free2KiExport"
FREE2KI_CMD_SET_MATERIALS = "Free2KiSetMaterials"

Gui.addCommand(FREE2KI_CMD_EXPORT, Free2KiExport())
Gui.addCommand(FREE2KI_CMD_SET_MATERIALS, Free2KiSetMaterials())

cmds = [
    FREE2KI_CMD_EXPORT,
    FREE2KI_CMD_SET_MATERIALS,
]
