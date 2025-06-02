class Free2KiWorkbench(Workbench):
    from pathlib import Path
    from f2k_commands import __file__

    BASE_DIR = Path(__file__).parent.resolve()
    ICONS_DIR = BASE_DIR / "icons"

    MenuText = "Free2Ki"
    Tooltip = "Free2Ki Workbench"
    Icon = str(ICONS_DIR / "kicad.png")

    def Initialize(self):
        from f2k_commands import register_commands

        cmds = register_commands()
        self.appendToolbar("Free2Ki Tools", cmds)
        self.appendMenu("Free2Ki Tools", cmds)

        Gui.addPreferencePage(str(self.BASE_DIR / "free2ki_preferences.ui"), "Free2Ki")
        Gui.addIconPath(str(self.ICONS_DIR))


Gui.addWorkbench(Free2KiWorkbench())
