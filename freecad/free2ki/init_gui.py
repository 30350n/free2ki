from pathlib import Path

import FreeCADGui as Gui

from .commands import register_commands

BASE_DIR = Path(__file__).parent.resolve()
ICONS_DIR = BASE_DIR / "icons"


class Free2KiWorkbench(Gui.Workbench):
    MenuText = "Free2Ki"
    Tooltip = "Free2Ki Workbench"
    Icon = str(ICONS_DIR / "kicad.png")

    def Initialize(self):
        cmds = register_commands()
        self.appendToolbar("Free2Ki Tools", cmds)
        self.appendMenu("Free2Ki Tools", cmds)

        Gui.addPreferencePage(str(BASE_DIR / "preferences.ui"), "Free2Ki")
        Gui.addIconPath(str(ICONS_DIR))


Gui.addWorkbench(Free2KiWorkbench())
