from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

MODEL_DIR = Path("E:\\projects\\modular\\kicad\\protorack-kicad\\3dmodels\\Protorack.3dshapes")

MODELS = (
    "AudioJacks/QingPu_WQP-PJ612A",
    "AudioJacks/QingPu_WQP-WQP518MA-BM",
    "Switches/E-Switch_EG2201B/E-Switch_EG2201B",
    "PushButtons/E-Switch_TL1105T/E-Switch_TL1105T",
    "Connectors/Amphenol_12402012E212A/Amphenol_12402012E212A",
    "Connectors/Amphenol_UE27AC/Amphenol_UE27AC",
    "Potentiometers/Alpha_RD901F-40/Alpha_RD901F-40-15F",
    "Potentiometers/Alpha_RV16AF/Alpha_RV16AF-10-17K",
)

OUTPUT_SIZE = (len(MODELS) * 900, 900)

combined = Image.new("RGB", OUTPUT_SIZE)
mask = Image.new("1", OUTPUT_SIZE)

for i, model in enumerate(MODELS):
    image = Image.open(MODEL_DIR / (model + ".jpg"))
    cropped = image.crop((50, 50, 950, 950))
    combined.paste(cropped, (900 * i, 0))

    grayscale = cropped.convert("L")
    threshold = grayscale.point((np.arange(256) > 44) * 255)
    blurred = threshold.filter(ImageFilter.GaussianBlur(15))
    mono = blurred.point((np.arange(256) > 5) * 255)
    mask.paste(mono, (900 * i, 0))

combined.save("template.png")
mask.save("template_mask.png")
