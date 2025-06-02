from mat4cad import Material

import FreeCAD, Part
import MeshPart

import numpy as np
from math import radians
import gzip

INCH_TO_MM = 1.0 / 2.54

MATERIALS_PROPERTY = "Free2KiMaterials"
MATERIAL_INDICES_PROPERTY = "Free2KiMaterialIndices"
PROPERTIES = {MATERIALS_PROPERTY, MATERIAL_INDICES_PROPERTY}


def prefs_use_compression():
    FSParam = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Free2Ki")
    return FSParam.GetInt("VRMLCompression", 0) == 0


def export_vrml(path, objects, use_compression=None):
    if use_compression is None:
        use_compression = prefs_use_compression()
    _open = gzip.open if use_compression else open

    with _open(str(path), "wb") as file:
        file.write(VRML_HEADER.encode())

        points_list = []
        triangles_list = []
        material_ids = []
        for obj in objects:
            name = obj._Body.Label if hasattr(obj, "_Body") else obj.Label
            print(f'info: exporting "{name}"')

            obj_material_ids = ["default"]
            materials = [Material()]
            material_indices = np.zeros(len(obj.Shape.Faces), dtype=int)

            if hasattr(obj, MATERIALS_PROPERTY):
                if (ids := getattr(obj, MATERIALS_PROPERTY)) in ([], [""]):
                    print(f"warning: {name}.{MATERIALS_PROPERTY} is empty")
                elif not (indices := getattr(obj, MATERIAL_INDICES_PROPERTY)):
                    print(f"warning: {name}.{MATERIAL_INDICES_PROPERTY} is empty")
                else:
                    obj_material_ids = ids
                    materials = [
                        mat if (mat := Material.from_name(name)) else Material()
                        for name in obj_material_ids
                    ]
                    material_indices = np.array(indices)

            elif hasattr(obj, "ViewObject") and obj.ViewObject:
                obj_material_ids = [name]
                view = obj.ViewObject
                materials = [Material(diffuse=view.ShapeColor, alpha=1.0 - view.Transparency)]

            for material_id, material in zip(obj_material_ids, materials):
                if material_id not in material_ids:
                    material_string = MATERIAL_FORMAT.format(name=material_id, m=material)
                    file.write(SHAPE_FORMAT.format(material_string).encode())
                material_ids.append(material_id)

            global_matrix = obj.getGlobalPlacement().Matrix * obj.Placement.Matrix.inverse()
            global_matrix.scale(INCH_TO_MM, INCH_TO_MM, INCH_TO_MM)

            faces = np.array(obj.Shape.Faces)
            for i, material_id in enumerate(obj_material_ids):
                face_indices = np.nonzero(material_indices == i)[0]
                face_indices = np.extract(face_indices < len(obj.Shape.Faces), face_indices)
                compound = Part.makeCompound(faces[face_indices]).cleaned()

                mesh = MeshPart.meshFromShape(
                    Shape=compound, LinearDeflection=0.01, AngularDeflection=radians(20)
                )
                points = [global_matrix * point.Vector for point in mesh.Points]
                triangles = [facet.PointIndices for facet in mesh.Facets]
                points_list.append(points)
                triangles_list.append(triangles)

        for points, triangles, material_id in zip(points_list, triangles_list, material_ids):
            points_str = ", ".join(f"{v[0]:g} {v[1]:g} {v[2]:g}" for v in points)
            indices_str = ", ".join(f"{t[0]},{t[1]},{t[2]},-1" for t in triangles)
            file.write(
                SHAPE_FORMAT.format(
                    MESH_FORMAT.format(
                        points=points_str,
                        indices=indices_str,
                        material_id=material_id,
                        crease_angle=radians(30),
                    )
                ).encode()
            )


VRML_HEADER = "#VRML V2.0 utf8\n"

SHAPE_FORMAT = "Shape\n{{\n{}}}\n"

MATERIAL_FORMAT = (
    ""
    "    appearance Appearance\n"
    "    {{\n"
    "        material DEF {name} Material\n"
    "        {{\n"
    "            diffuseColor {m.diffuse[0]:.4g} {m.diffuse[1]:.4g} {m.diffuse[2]:.4g}\n"
    "            emissiveColor {m.emission[0]:.4g} {m.emission[1]:.4g} {m.emission[2]:.4g}\n"
    "            shininess {m.shininess:.4g}\n"
    "            specularColor 0.0 0.0 0.0\n"
    "            transparency {m.transparency:.4g}\n"
    "            ambientIntensity 0.2\n"
    "        }}\n"
    "    }}\n"
)

MESH_FORMAT = (
    ""
    "    geometry IndexedFaceSet\n"
    "    {{\n"
    "        creaseAngle {crease_angle:.4g}\n"
    "        coordIndex [{indices}]\n"
    "        coord Coordinate\n"
    "        {{\n"
    "            point[{points}]\n"
    "        }}\n"
    "    }}\n"
    "    appearance Appearance\n"
    "    {{\n"
    "        material USE {material_id}\n"
    "    }}\n"
)
