import string
from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QBrush, QColor, QFontMetrics, QPainter, QPaintEvent
    from PySide6.QtWidgets import *  # pyright: ignore[reportWildcardImportFromLibrary]
else:
    from PySide.QtCore import QRect, Qt
    from PySide.QtGui import QBrush, QColor, QFontMetrics, QPainter, QPaintEvent
    from PySide.QtWidgets import *

import FreeCAD
from FreeCAD import DocumentObject, GeoFeature, GroupExtension
from Part import Shape

if TYPE_CHECKING:
    from FreeCADGui import SelectionObject
else:
    SelectionObject = object

from .export_vrml import FREE2KI_PROPS, export_vrml, prefs_use_compression
from .mat4cad import Material, hex2rgb, rgb2hex
from .mat4cad.materials import BASE_MATERIAL_COLORS, BASE_MATERIAL_VARIANTS, BASE_MATERIALS


class Free2KiExport:
    def Activated(self):
        active_document = FreeCAD.ActiveDocument
        if not active_document or not active_document.FileName:
            critical("Error", "Failed to export. Active Document is not saved.")
            return

        if not (objects := get_shape_objects()):
            root_objects: list[FreeCAD.DocumentObject] = active_document.RootObjects
            if not (objects := get_shape_objects(root_objects)):
                critical("Error", "Failed to export. Nothing to export.")
                return

        document_path = Path(active_document.FileName)
        path = document_path.parent / document_path.stem
        path = path.with_suffix(".wrz" if prefs_use_compression() else ".wrl")

        if path.exists():
            if path.is_file():
                if (
                    question("Overwrite?", f'"{path}" already exists. Overwrite?')
                    == QMessageBox.StandardButton.No
                ):
                    return
            else:
                critical("Error", f'Failed to export. "{path}" exists and is not a file.')
                return

        export_vrml(path, objects)
        print(f'info: successfully exported "{path.name}"')

    def GetResources(self):
        return {
            "Pixmap": str((Path(__file__).parent / "icons" / "kicad-export.png").resolve()),
            "MenuText": "Export",
            "Tooltip": "Export selected, visible objects (with children).",
        }


Free2KiSelection = dict[GeoFeature, NDArray[np.integer] | None]


class Free2KiSetMaterials:
    def Activated(self):
        active_doc = FreeCAD.ActiveDocument
        if not active_doc:
            critical("Error", "Failed to set material. No Active Document.")
            return

        selection: Free2KiSelection = {}
        elements: list[SelectionObject] = FreeCAD.Gui.Selection.getSelectionEx()
        for element in elements:
            obj: DocumentObject = element.Object
            if element.HasSubObjects and isinstance(obj, GeoFeature) and has_shape(obj):
                faces = [
                    int(name[4:]) - 1 for name in element.SubElementNames if name.startswith("Face")
                ]
                selection[obj] = np.array(faces)
            else:
                for child in get_shape_objects([obj]):
                    selection[child] = None

        if not selection:
            critical("Error", "Failed to set material. Nothing is selected.")
            return

        if not (selected_materials := SelectMaterialDialog(selection).execute()):
            return

        for obj, faces, material in selected_materials:
            self.setup_material_indices(material, obj, faces)
        for obj in selection:
            self.recalculate_materials(obj)

        objects_to_recompute: set[FreeCAD.DocumentObject] = set().union(
            *({obj, *(parent for parent, _ in obj.Parents)} for obj in selection)
        )
        active_doc.recompute(list(objects_to_recompute))

    @staticmethod
    def setup_material_indices(material: Material, obj: GeoFeature, faces: NDArray[np.integer]):
        if FREE2KI_PROPS.MATERIALS not in obj.PropertiesList:
            obj.addProperty("App::PropertyStringList", FREE2KI_PROPS.MATERIALS)
        if FREE2KI_PROPS.MATERIAL_INDICES not in obj.PropertiesList:
            obj.addProperty("App::PropertyIntegerList", FREE2KI_PROPS.MATERIAL_INDICES)

        materials = getattr(obj, FREE2KI_PROPS.MATERIALS)
        index = len(materials)
        materials.append(material.name)

        setattr(obj, FREE2KI_PROPS.MATERIALS, materials)

        material_indices = np.array(getattr(obj, FREE2KI_PROPS.MATERIAL_INDICES), dtype=int)
        material_indices.resize(len(get_shape(obj).Faces))
        material_indices[faces] = index
        setattr(obj, FREE2KI_PROPS.MATERIAL_INDICES, material_indices.tolist())

    @staticmethod
    def recalculate_materials(obj: GeoFeature):
        materials = getattr(obj, FREE2KI_PROPS.MATERIALS)
        material_indices = np.array(getattr(obj, FREE2KI_PROPS.MATERIAL_INDICES))
        material_indices = material_indices[: len(get_shape(obj).Faces)]

        used_materials = list({materials[index] for index in set(material_indices)})
        index_mapping = np.zeros(len(materials), dtype=int)
        for i, name in enumerate(used_materials):
            for index in np.where(np.array(materials, dtype=object) == name):
                index_mapping[index] = i

        colors = [
            mat.diffuse if (mat := Material.from_name(name)) else (0.0, 0.0, 0.0)
            for name in used_materials
        ]
        colors = np.array(colors)

        remapped_indices = index_mapping[material_indices]
        diffuse_color = colors[remapped_indices]

        setattr(obj, FREE2KI_PROPS.MATERIALS, used_materials)
        setattr(obj, FREE2KI_PROPS.MATERIAL_INDICES, remapped_indices.tolist())
        setattr(obj.ViewObject, "DiffuseColor", [tuple(color) for color in diffuse_color])

    def GetResources(self):
        return {
            "Pixmap": str((Path(__file__).parent / "icons" / "material.png").resolve()),
            "MenuText": "Set Materials",
            "Tooltip": "Set material for selected, visible objects.",
        }


def has_shape(obj: GeoFeature):
    return obj.getPropertyNameOfGeometry() == "Shape"


def get_shape(obj: GeoFeature):
    assert has_shape(obj)
    return cast(Shape, obj.getPropertyByName("Shape"))


def get_shape_objects(objects: list[DocumentObject] | None = None) -> list[GeoFeature]:
    if objects is None:
        objects = FreeCAD.Gui.Selection.getSelection()

    shape_objects: list[GeoFeature] = []
    for obj in objects:
        if obj.Visibility:
            if obj.hasExtension("App::GroupExtension"):
                shape_objects += get_shape_objects(cast(GroupExtension, obj).Group)
            elif isinstance(obj, GeoFeature) and has_shape(obj) and get_shape(obj).Faces:
                shape_objects.append(obj)

    return list(set(shape_objects))


class SelectMaterialDialog(QDialog):
    DEFAULT_MATERIAL: Material = Material.from_name("plastic-mouse_grey-semi_matte") or Material()
    MAX_HEIGHT: int = 300

    material_selectors: list[tuple[GeoFeature, NDArray[np.integer], "MaterialSelector"]]

    def __init__(self, selection: Free2KiSelection):
        super().__init__(None, Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)

        box_materials = QVBoxLayout()

        self.material_selectors = []
        names = (
            body.Label if (body := getattr(obj, "_Body", None)) else obj.Label for obj in selection
        )
        for name, obj, faces in sorted(zip(names, selection.keys(), selection.values())):
            existing_materials = self.get_existing_materials(obj, faces)

            if len(selection) > 1 and len(existing_materials) <= 1:
                box_materials.addWidget(QLabel(name))

            for sub_faces, material in existing_materials:
                if len(existing_materials) > 1:
                    label = f"{name} {np.array2string(sub_faces, threshold=7)}"
                    box_materials.addWidget(QLabel(label))
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
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
            scroll_area.adjustSize()
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.adjustSize()
            scroll_area.setFixedSize(size.width() + scroll_bar.size().width(), self.MAX_HEIGHT)
            layout.addWidget(scroll_area)
        else:
            layout.addWidget(widget_materials)

        self.button_set_material: QAbstractButton = QPushButton("Set Material")
        self.button_set_material.clicked.connect(self.set_material)
        self.button_cancel: QAbstractButton = QPushButton("Cancel")
        self.button_cancel.clicked.connect(self.reject)

        row_buttons = QHBoxLayout()
        row_buttons.addWidget(self.button_set_material)
        row_buttons.addWidget(self.button_cancel)
        layout.addLayout(row_buttons)

        self.setLayout(layout)

    @classmethod
    def get_existing_materials(
        cls, obj: GeoFeature, faces: NDArray[np.integer] | None
    ) -> list[tuple[NDArray[np.integer], Material]]:
        shape = get_shape(obj)
        if faces is None:
            faces = np.arange(len(shape.Faces))

        if FREE2KI_PROPS.ALL.issubset(obj.PropertiesList) and getattr(obj, FREE2KI_PROPS.MATERIALS):
            material_indices = np.array(getattr(obj, FREE2KI_PROPS.MATERIAL_INDICES), dtype=int)
            material_indices.resize(len(shape.Faces))

            face_material_indices = material_indices[faces]
            unique_material_indices = np.unique(face_material_indices)
            materials = [Material.from_name(name) for name in getattr(obj, FREE2KI_PROPS.MATERIALS)]

            return [
                (faces[np.nonzero(index == face_material_indices)], materials[index])
                for index in unique_material_indices
            ]
        elif colors := getattr(obj.ViewObject, "DiffuseColor", None):
            if len(colors) > 1:
                colors = np.array(colors)
                colors.resize((len(shape.Faces), 4))

                face_colors = colors[faces]
                unique_colors = np.unique(face_colors, axis=0)
                materials = [
                    Material.from_name(f"plastic-custom_{rgb2hex(color)}-semi_matte") or Material()
                    for color in unique_colors
                ]

                return [
                    (faces[np.nonzero(np.all(color == face_colors, axis=1))], materials[index])
                    for index, color in enumerate(unique_colors)
                ]
            else:
                color = colors[0]
                if np.all(np.isclose(color, (0.8, 0.8, 0.8, 0.0))):
                    material = cls.DEFAULT_MATERIAL
                else:
                    material = (
                        Material.from_name(f"plastic-custom_{rgb2hex(color)}-semi_matte")
                        or cls.DEFAULT_MATERIAL
                    )
                return [(faces, material)]
        else:
            return [(faces, cls.DEFAULT_MATERIAL)]

    def set_material(self):
        self.accept()

    def execute(self):
        if self.exec_():
            return [
                (obj, faces, material_selector.get_material())
                for (obj, faces, material_selector) in self.material_selectors
            ]


class MaterialSelector(QWidget):
    ITEM_DATA_ROLE = Qt.ItemDataRole.DecorationRole

    def __init__(self, material: Material | None = None):
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
        width = max((font_metrics.horizontalAdvance(c * 6) for c in string.hexdigits)) + 10
        self.color_hexcode.setFixedWidth(width)

        self.combo_color.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Ignored
        )
        self.combo_variant.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Ignored)

        if material:
            assert material.base and material.color and material.variant
            self.combo_base_material.setCurrentText(material.base)
            if material.has_custom_color:
                assert (custom_color := material.custom_color)
                self.combo_color.setCurrentText("custom")
                self.color_hexcode.setText(custom_color)
            else:
                self.combo_color.setCurrentText(material.color)
            self.combo_variant.setCurrentText(material.variant)

        layout = QHBoxLayout()
        layout.addItem(QSpacerItem(4, 0))
        layout.addWidget(self.color_preview)
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(self.combo_base_material)
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(self.combo_color)
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(self.color_hexcode)
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(self.combo_variant)
        layout.addItem(QSpacerItem(4, 0))
        self.setLayout(layout)

    def get_material(self):
        base = self.combo_base_material.currentText()
        if (color := self.combo_color.currentText()) == "custom":
            color = f"custom_{rgb2hex(self.custom_color)}"
        variant = self.combo_variant.currentText()
        assert (material := Material.from_name("-".join((base, color, variant))))
        return material

    def on_base_material_change(self, new_base_material: str):
        colors = BASE_MATERIAL_COLORS[new_base_material]
        if new_base_material not in ("special",):
            colors = {"custom": self.custom_color, **colors}

        old_active_color = self.combo_color.currentText()

        self.combo_color.clear()
        self.combo_color.addItems(list(colors.keys()))
        for i, color in enumerate(colors.values()):
            if isinstance(color, Material):
                color = color.diffuse
            qcolor = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
            self.combo_color.setItemData(i, qcolor, self.ITEM_DATA_ROLE)
        if old_active_color in colors:
            self.combo_color.setCurrentText(old_active_color)
        else:
            self.combo_color.setCurrentIndex(0)

        variants = BASE_MATERIAL_VARIANTS[new_base_material] or {"default": None}
        old_active_variant = self.combo_variant.currentText()
        self.combo_variant.clear()
        self.combo_variant.addItems(list(variants.keys()))

        if old_active_variant in variants:
            self.combo_variant.setCurrentText(old_active_variant)
        else:
            self.combo_variant.setCurrentIndex(len(variants) // 2)

    def on_color_change(self, new_color: str):
        qcolor = self.combo_color.itemData(self.combo_color.currentIndex(), self.ITEM_DATA_ROLE)
        if qcolor:
            if not self.suppress_hexcode_update:
                self.color_hexcode.setReadOnly(new_color != "custom")
                self.color_hexcode.setText(qcolor.name()[1:])
            self.color_preview.updateColor(qcolor)

    def on_hexcode_change(self, new_hexcode: str):
        self.custom_color = r, g, b = hex2rgb(new_hexcode.rjust(6, "0"))
        self.suppress_hexcode_update = True
        qcolor = QColor(int(r * 255), int(g * 255), int(b * 255))
        self.combo_color.setItemData(self.combo_color.currentIndex(), qcolor, self.ITEM_DATA_ROLE)
        self.suppress_hexcode_update = False


class ColorBox(QWidget):
    def __init__(self):
        super().__init__()

        self.setMinimumWidth(40)
        self.setMinimumHeight(24)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._color = QColor(0, 0, 0)

    def updateColor(self, rgb: QColor):
        self._color = rgb
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        brush = QBrush()
        brush.setColor(self._color)
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        rect = QRect(0, 0, self.width(), self.height())
        painter.fillRect(rect, brush)
        painter.end()


def critical(title: str, text: str):
    return QMessageBox.critical(None, title, text)  # pyright: ignore[reportArgumentType]


def question(title: str, text: str):
    return QMessageBox.question(None, title, text)  # pyright: ignore[reportArgumentType]


command_classes = (
    Free2KiSetMaterials,
    Free2KiExport,
)


def register_commands():
    commands: list[str] = []
    for cls in command_classes:
        commands.append(cls.__name__)
        FreeCAD.Gui.addCommand(cls.__name__, cls())

    return commands
