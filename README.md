[![freecad](https://img.shields.io/badge/FreeCAD-1.0-red)](https://www.freecadweb.org/)
[![gplv3](https://img.shields.io/badge/License-GPLv3-lightgrey)](https://www.gnu.org/licenses/gpl-3.0.txt)

<img src="images/header.jpg" alt="free2ki headline image"/>

The `free2ki` [FreeCAD](https://github.com/FreeCAD/FreeCAD) workbench enables you to apply
materials to 3D models in FreeCAD, as well as to easily export them to VRML (.wrl/.wrz) files
with correctly applied rotation and scaling for use in KiCad as well as Blender.

I created it as I wanted a fast to use, simple and less buggy/bloated alternative to the
[kicadStepUp](https://github.com/easyw/kicadStepUpMod) workbench that just works and better
integrates into my KiCad to Blender workflow
([pcb2blender](https://github.com/30350n/pcb2blender)).

## Usage

1. Switch to the Free2Ki Workbench.
2. Select the models or parts of models you want to apply a material too.
3. Use the `Set Materials` tool, to setup the materials you want (this tool can be used
   multiple times to setup multiple materials, on a single object)
4. Export the selected objects (or the whole file if nothing is selected) via the `Export`
   tool. This will create a `<project_name>.wrz` file, in the same directory your FreeCAD
   project file is in.
5. (optional) Install the [pcb2blender](https://github.com/30350n/pcb2blender)
   Blender addon and import your model via<br>
   `File -> Import -> X3D/VRML (.x3d/.wrl) (for pcb3d)`.<br>

### Materials

Missing anything from the selection of available materials? Feel free to create an issue
on the [mat4cad](https://github.com/30350n/mat4cad) repository, explaining what materials
you'd like to see (possibly also how they'd look like in Blender) and I might add them in the
next update!

## Installation

- (not available yet) via the builtin addon manager
  `Tools -> Addon manager -> Workbenches -> free2ki`

- (manual) Download the `free2ki_<version>.zip` from the
  [latest release](https://github.com/30350n/free2ki/releases/latest)
  and unpack its contents into your
  [FreeCAD Mod folder](https://wiki.freecadweb.org/Installing_more_workbenches#Installing_for_a_single_user).

## Other Projects

- All the 3D models of the
  [protorack-kicad](https://github.com/30350n/protorack-kicad) KiCad library, which contains
  all the custom symbols and footprints I use for eurorack module development, have been
  created using this workbench.

- The [pcb2blender](https://github.com/30350n/pcb2blender) workflow makes use of the
  [mat4cad](https://github.com/30350n/mat4cad) materials that this workbench lets you apply
  to your models. These materials will be recognized by Blender, and depending on the material
  type, different procedural textures/features will be used in Blender, making your models
  look more realistic.

## Credits

- The name of this project is inspired by the awesome
  [svg2shenzhen](https://github.com/badgeek/svg2shenzhen) Inkscape extension by
  [badgeek](https://github.com/badgeek).

## License

- This project is licensed under
  [GPLv3](https://github.com/30350n/free2ki/blob/master/LICENSE).
