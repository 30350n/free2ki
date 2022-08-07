class Free2KiWorkbench(Workbench):
    from pathlib import Path
    from commands import __file__

    BASE_DIR = Path(__file__).parent.resolve()
    ICONS_DIR = BASE_DIR / "icons"

    MenuText = "Free2Ki"
    Tooltip  = "Free2Ki Workbench"
    Icon = str(ICONS_DIR / "kicad.png")

    def Initialize(self):
        from commands import cmds

        self.appendToolbar("Free2Ki Tools", cmds)
        self.appendMenu("Free2Ki Tools", cmds)

        FreeCADGui.addPreferencePage(str(self.BASE_DIR / "free2ki_preferences.ui"), "Free2Ki")
        FreeCADGui.addIconPath(str(self.ICONS_DIR))

Gui.addWorkbench(Free2KiWorkbench())
