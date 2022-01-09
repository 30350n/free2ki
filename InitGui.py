class Free2KiWorkbench(Workbench):
    from pathlib import Path
    from .commands import __file__

    MenuText = "Free2Ki"
    Tooltip  = "Free2Ki Workbench"
    Icon = str((Path(__file__).parent / "icons" / "kicad.png").resolve())

    def Initialize(self):
        from .commands import FREE2KI_CMD_EXPORT, FREE2KI_CMD_SET_MATERIAL
        cmds = [
            FREE2KI_CMD_EXPORT,
            FREE2KI_CMD_SET_MATERIAL,
        ]

        self.appendToolbar("Free2Ki Tools", cmds)
        self.appendMenu("Free2Ki Tools", cmds)

Gui.addWorkbench(Free2KiWorkbench())
