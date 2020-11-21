import os
import json

BINARY_MASKS_DIR = "binary-masks"
STRAIGHTENED_MASKS_DIR = "straight-masks"
DETIPPED_MASKS_DIR = "detipped-masks"
MASK_OVERLAYS_DIR = "mask-overlays"
AVERAGE_MASK_DIR = "average-mask"
AVERAGE_OVERLAY_DIR = "average-overlay"

LEGACY_NAMES = [
    "average",
    "blue_crop",
    "white_crop",
    "binary-mask",
    "binary_mask",
    "mask-overlay",
    "mask_overlay",
    "straight_mask",
    "straight_mask_no_tip",
    "tip-mask",
    "tip-angle",
    "blue-line",
    "black-box",
    "midline",
    "graph",
    "shouldering",
    "normal-overlays",
    "width-profiles",
    "output-190905",
    "average-overlay",
    "average-mask",
]

METHODS = LEGACY_NAMES + [
    BINARY_MASKS_DIR,
    STRAIGHTENED_MASKS_DIR,
    DETIPPED_MASKS_DIR,
    MASK_OVERLAYS_DIR,
]

# Boaty, here you can define the defaults for the config
CONFIG_DEFAULTS = [
    {"key": "scalebar_length", "default": 100},
    {"key": "scalebar_color", "default": [133, 251, 111]},
    {"key": "camera_maker", "default": "Nikon Corporation"},
    {"key": "camera_model", "default": "Nikon D5500"},
    {"key": "lens_maker", "default": "Nikon"},
    {"key": "lens_model", "default": "Nikkor 24mm f/2.8D AF"},
    {"key": "file_format", "default": ".png"},
]


def get_config():
    """
    parse the configuration file
    """
    config_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "config.json"
    )
    config = {}
    try:
        with open(config_file) as f:
            config_from_file = json.load(f)
            for entry in CONFIG_DEFAULTS:
                config[entry["key"]] = config_from_file.get(
                    entry["key"], entry["default"]
                )
    except IOError:
        for entry in CONFIG_DEFAULTS:
            config[entry["key"]] = entry["default"]
    return config


config = get_config()


TIP_MASK_PSEUDO_MAX_LENGTH = 5000
