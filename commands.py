from .export_wrl import export_wrl
from .mat4cad import MATERIALS

from FreeCAD import Gui
import FreeCAD as App
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import QRect

from pathlib import Path

FREE2KI_CMD_EXPORT = "Free2KiExport"
FREE2KI_CMD_SET_MATERIAL = "Free2KiSetMaterial"

class Free2KiExport:
    def Activated(self):
        active_doc = App.ActiveDocument
        if not active_doc or not active_doc.FileName:
            QMessageBox.critical(None, "Error",
                "Failed to export. Active Document is not saved.")
            return

        if not (objects := get_bodies_and_features()):
            if not (objects := get_bodies_and_features(active_doc.RootObjects)):
                QMessageBox.critical(None, "Error",
                    "Failed to export. Nothing to export.")
                return

        document_path = Path(App.ActiveDocument.FileName)
        path = document_path.parent / (document_path.stem + ".wrl")

        if path.exists():
            if path.is_file():
                if QMessageBox.question(None, "Overwrite?",
                        f"\"{path}\" already exists. Overwrite?") == QMessageBox.No:
                    print("skipping")
                    return
            else:
                QMessageBox.critical(None, "Error",
                    f"Failed to export. \"{path}\" exists and is not a file.")
                return

        export_wrl(path, objects)
        print(f"successfully exported \"{path.name}\"")

    def GetResources(self):
        return {
            "Pixmap": str((Path(__file__).parent / "icons" / "kicad.png").resolve()),
            "MenuText": "Export",
            "Tooltip": 
                "Export selected, visible objects (with children)."
        }

class Free2KiSetMaterial:
    def Activated(self):
        if material_name := SelectMaterialDialog().execute():
            material = MATERIALS[material_name]
            
            for obj in get_bodies_and_features():
                if hasattr(obj, "ViewObject"):
                    obj.ViewObject.ShapeColor = material.diffuse
                obj.addProperty("App::PropertyString", "Free2KiMaterial")
                obj.Free2KiMaterial = material_name

    def GetResources(self):
        return {
            "Pixmap": str((Path(__file__).parent / "icons" / "material.png").resolve()),
            "MenuText": "Set Material",
            "Tooltip": 
                "Set material for selected, visible objects."
        }

def get_bodies_and_features(parents=None):
    if parents is None:
        parents = App.Gui.Selection.getSelection()

    result = []
    for parent in parents:
        if parent.Visibility:
            if parent.TypeId in {"Part::Feature", "PartDesign::Body"}:
                result.append(parent)
            elif hasattr(parent, "Group"):
                result += get_bodies_and_features(parent.Group)

    return result

class SelectMaterialDialog(QDialog):
    def __init__(self):
        super().__init__(None, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.color_preview = ColorBox()
        self.combo_material = QComboBox()
        self.combo_material.currentTextChanged.connect(self.on_material_change)
        for i, (name, material) in enumerate(MATERIALS.items()):
            self.combo_material.addItem(name)
            r, g, b = material.diffuse
            self.combo_material.setItemData(i, QColor(r*255, g*255, b*255), Qt.DecorationRole)

        self.button_set_material = QPushButton("Set Material")
        self.button_set_material.clicked.connect(self.set_material)
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.clicked.connect(self.reject)

        row_material = QHBoxLayout()
        row_material.addItem(QSpacerItem(4, 40))
        row_material.addWidget(self.color_preview)
        row_material.addItem(QSpacerItem(10, 40))
        row_material.addWidget(self.combo_material)
        row_material.addItem(QSpacerItem(4, 40))

        row_button = QHBoxLayout()
        row_button.addWidget(self.button_set_material)
        row_button.addWidget(self.button_cancel)

        layout = QVBoxLayout()
        layout.addLayout(row_material)
        layout.addLayout(row_button)
        self.setLayout(layout)

    def set_material(self):
        self.accept()

    def on_material_change(self, new_material):
        self.color_preview.updateColor(MATERIALS[new_material].diffuse)

    def execute(self):
        if self.exec_():
            return self.combo_material.currentText()

class ColorBox(QWidget):
    def __init__(self):
        super().__init__()

        self.setMinimumWidth(40)
        self.setMinimumHeight(24)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._color = QColor(0, 0, 0)

    def updateColor(self, rgb):
        r, g, b = rgb
        self._color = QColor(r * 255, g * 255, b * 255)
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
