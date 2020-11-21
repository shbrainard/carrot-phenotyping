import click
import cv2
import lensfunpy

from lib.constants import config


def unskew(image_path, old):
    cam_maker = config["camera_maker"]
    cam_model = config["camera_model"]

    lens_maker = config["lens_maker"]
    lens_model = config["lens_model"]

    # TODO: this would have to be removed...
    if old:
        cam_model = 'Nikon D3300'
        lens_model = "Nikon AF-S DX Zoom-Nikkor 18-55mm f/3.5-5.6G VR"

    db = lensfunpy.Database()

    try:
        cam = db.find_cameras(cam_maker, cam_model)[0]
    except Exception:
        raise(Exception("Camera not found!"))
    try:
        lens = db.find_lenses(cam, lens_maker, lens_model)[0]
    except Exception:
        raise(Exception("Lens not found!"))

    #  focal_length = lens.min_focal

    # TODO: read from exif

    focal_length = 30
    aperture = 4.2

    # TODO: what's the unit here?
    distance = 10

    im = cv2.imread(image_path)
    height, width = im.shape[0], im.shape[1]

    mod = lensfunpy.Modifier(lens, cam.crop_factor, width, height)
    mod.initialize(focal_length, aperture, distance)

    undist_coords = mod.apply_geometry_distortion()
    unskewed = cv2.remap(im, undist_coords, None, cv2.INTER_LANCZOS4)
    return unskewed
