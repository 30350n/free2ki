from mat4cad import Material

import FreeCAD, Part

import numpy as np
from math import radians
import gzip

INCH_TO_MM = 1.0 / 2.54

MATERIALS_PROPERTY = "Free2KiMaterials"
MATERIAL_INDICES_PROPERTY = "Free2KiMaterialIndices"
PROPERTIES = {MATERIALS_PROPERTY, MATERIAL_INDICES_PROPERTY}

def use_compression():
    FSParam = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Free2Ki")
    return FSParam.GetInt("VRMLCompression", 0) == 0

def export_wrl(path, objects):
    _open = gzip.open if use_compression() else open
    path = path.with_suffix(".wrz" if use_compression() else ".wrl")

    with _open(str(path), "wb") as file:
        file.write(VRML_HEADER.encode())

        points_list = []
        triangles_list = []
        material_ids = []
        for obj in objects:
            name = obj._Body.Label if hasattr(obj, "_Body") else obj.Label
            print(f"info: exporting \"{name}\"")

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

            elif hasattr(obj, "ViewObject"):
                obj_material_ids = [name]
                view = obj.ViewObject
                materials = [Material(diffuse=view.ShapeColor, alpha=1.0-view.Transparency)]

            for material_id, material in zip(obj_material_ids, materials):
                if not material_id in material_ids:
                    material_string = MATERIAL_FORMAT.format(name=material_id, m=material)
                    file.write(SHAPE_FORMAT.format(material_string).encode())
                material_ids.append(material_id)

            global_matrix = obj.getGlobalPlacement().Matrix * obj.Placement.Matrix.inverse()
            global_matrix.scale(INCH_TO_MM, INCH_TO_MM, INCH_TO_MM)

            for i, material_id in enumerate(obj_material_ids):
                face_indices = np.nonzero(material_indices == i)[0]
                face_indices = np.extract(face_indices < len(obj.Shape.Faces), face_indices)
                faces = [obj.Shape.Faces[index] for index in face_indices]
                compound = Part.makeCompound(faces)

                points, triangles = compound.tessellate(0.01)
                points = [global_matrix * v for v in points]
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
                        crease_angle=radians(30)
                    )
                ).encode()
            )

VRML_HEADER = "#VRML V2.0 utf8\n"

SHAPE_FORMAT = ""\
	"Shape\n"\
	"{{\n"\
	"{}"\
    "}}\n"

MATERIAL_FORMAT = ""\
    "    appearance Appearance\n"\
    "    {{\n"\
    "        material DEF {name} Material\n"\
	"        {{\n"\
    "            diffuseColor {m.diffuse[0]:.4g} {m.diffuse[1]:.4g} {m.diffuse[2]:.4g}\n"\
    "            emissiveColor {m.emission[0]:.4g} {m.emission[1]:.4g} {m.emission[2]:.4g}\n"\
    "            shininess {m.shininess:.4g}\n"\
    "            specularColor 0.0 0.0 0.0\n"\
    "            transparency {m.transparency:.4g}\n"\
    "            ambientIntensity 0.2\n"\
    "        }}\n"\
    "    }}\n"

MESH_FORMAT = ""\
	"    geometry IndexedFaceSet\n"\
	"    {{\n"\
    "        creaseAngle {crease_angle:.4g}\n"\
    "        coordIndex [{indices}]\n"\
	"        coord Coordinate\n"\
	"        {{\n"\
    "            point[{points}]\n"\
    "        }}\n"\
    "    }}\n"\
    "    appearance Appearance\n"\
    "    {{\n"\
    "        material USE {material_id}\n"\
    "    }}\n"
