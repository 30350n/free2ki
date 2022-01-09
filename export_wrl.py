from .mat4cad import Material, MATERIALS
from math import radians

INCH_TO_MM = 1.0 / 2.54

def export_wrl(path, objects):
    with open(str(path), "w") as file:
        file.write(VRML_HEADER)

        material_ids = []
        materials_string = ""
        for obj in objects:
            if hasattr(obj, "Free2KiMaterial"):
                name = obj.Free2KiMaterial
                material = MATERIALS[name]
            elif hasattr(obj, "ViewObject"):
                name = obj.Label
                view = obj.ViewObject
                material = Material(diffuse=view.ShapeColor, alpha=1.0-view.Transparency)
            else:
                name = "default"
                material = Material()

            if not name in material_ids:
                file.write(SHAPE_FORMAT.format(MATERIAL_FORMAT.format(name=name, m=material)))
            material_ids.append(name)

        for obj, material_id in zip(objects, material_ids):
            points, triangles = obj.Shape.tessellate(0.01)

            global_matrix = obj.getGlobalPlacement().Matrix * obj.Placement.Matrix.inverse()
            global_matrix.scale(INCH_TO_MM, INCH_TO_MM, INCH_TO_MM)
            points = (global_matrix * v for v in points)
            
            points_str = ", ".join(f"{v.x:g} {v.y:g} {v.z:g}" for v in points)
            indices_str = ", ".join(f"{t[0]},{t[1]},{t[2]},-1" for t in triangles)
            file.write(
                SHAPE_FORMAT.format(
                    MESH_FORMAT.format(
                        points=points_str,
                        indices=indices_str,
                        material_id=material_id,
                        crease_angle=radians(30)
                    )
                )
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
