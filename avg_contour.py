import os
import shutil
import typing

import click
import cv2
import numpy as np

from lib.constants import AVERAGE_MASK_DIR, STRAIGHTENED_MASKS_DIR, AVERAGE_OVERLAY_DIR
from lib.crop import get_carrot_contour
from lib.utils import get_masks_to_process, get_attributes_from_filename


def get_max_x(masks):
    max_x = max([m.shape[1] for m in masks])
    if max_x % 2 > 0:
        max_x += 1
    return max_x


def get_max_y(masks):
    max_y = max([m.shape[0] for m in masks])
    if max_y % 2 > 0:
        max_y += 1
    return max_y


def pad_mask(mask: np.ndarray, max_x: int, max_y: int) -> np.ndarray:

    mask_shape = mask.shape

    padding_top = 0
    padding_right = 0
    padding_bottom = 0
    padding_left = 0

    if mask_shape[1] <= max_x:
        padding_left = max_x - mask_shape[1]

    if mask_shape[0] <= max_y:
        y_padding = max_y - mask_shape[0]
        if y_padding % 2 == 0:
            padding_top = y_padding / 2
            padding_bottom = y_padding / 2
        else:
            padding_top = round(y_padding / 2)
            padding_bottom = y_padding - padding_top

    return cv2.copyMakeBorder(
        mask,
        int(padding_top),
        int(padding_bottom),
        int(padding_left),
        int(padding_right),
        borderType=cv2.BORDER_CONSTANT,
        value=(0, 0, 0),
    )


def get_distance_transform(mask):
    return cv2.distanceTransform(mask, cv2.DIST_L2, 5) - cv2.distanceTransform(
        ~mask, cv2.DIST_L2, 5
    )


def create_average_mask(masks):
    # padding
    max_x = get_max_x(masks)
    max_y = get_max_y(masks)

    masks = [pad_mask(m, max_x, max_y) for m in masks]

    dist_transforms = [get_distance_transform(m) for m in masks]

    avg_mask = dist_transforms[0]
    for dist_trans in dist_transforms[1:]:
        avg_mask = np.add(avg_mask, dist_trans)
    white = avg_mask > 0
    binary = white * 255
    binary = binary.astype(np.uint8)

    return binary


def create_average_overlay(masks):
    binary = create_average_mask(masks)

    # mask contours
    contours_layer = (
        np.zeros((binary.shape[0], binary.shape[1], 3), dtype=np.uint8) + 255
    )
    for mask in masks:
        m = mask * 255
        contour = get_carrot_contour(m)

        # x offset: difference in length
        offset_x = binary.shape[1] - mask.shape[1]

        # y offset: difference in height
        offset_y = int((binary.shape[0] - mask.shape[0]) / 2)

        cv2.drawContours(
            contours_layer, [contour], -1, (0, 0, 0), 2, offset=(offset_x, offset_y)
        )

    # avg contour
    contour = get_carrot_contour(binary)

    avg_overlay = np.zeros((binary.shape[0], binary.shape[1], 3), dtype=np.uint8) + 255

    cv2.drawContours(avg_overlay, [contour], -1, (0, 0, 255), -1)

    alpha = 0.7
    cv2.addWeighted(avg_overlay, alpha, contours_layer, 1 - alpha, 0, contours_layer)

    return contours_layer


def generate_avg_filename(masks: typing.List) -> str:
    """
    generate the filename for the average masks
    """
    mask_count = 0
    scale_sum = 0
    genotypes = []
    for mask in masks:
        attrs = get_attributes_from_filename(mask)
        genotypes.append(attrs["Genotype"])
        scale = attrs.get("Scale", None)
        if scale:
            scale_sum += int(scale)
            mask_count += 1
    avg_scale = int(scale_sum / mask_count)

    filename = "{Scale_%s}" % avg_scale

    if len(list(set(genotypes))) == 1:
        avg_genotype = genotypes[0]
        filename += "{Genotype_%s}" % avg_genotype
    return f"{filename}.png"


@click.command()
@click.option("--overlay", is_flag=True, help="overlay or not")
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True),
    help="source directory of images to process",
)
def run(overlay, src):

    subdirs = get_masks_to_process(src, STRAIGHTENED_MASKS_DIR)
    for dir in subdirs:
        masks = dir["files"]
        avg_filename = generate_avg_filename(masks)
        masks = [cv2.imread(m, cv2.IMREAD_GRAYSCALE) for m in masks]

        avg_mask = create_average_mask(masks)
        dest_dir = os.path.join(dir["path"], "..", AVERAGE_MASK_DIR)
        try:
            shutil.rmtree(dest_dir)
        except Exception as e:
            pass
        os.makedirs(dest_dir, exist_ok=True)
        cv2.imwrite(os.path.join(dest_dir, avg_filename), avg_mask)

        if overlay:
            avg_image = create_average_overlay(masks)
            dest_dir = os.path.join(dir["path"], "..", AVERAGE_OVERLAY_DIR)
            try:
                shutil.rmtree(dest_dir)
            except Exception as e:
                pass
            os.makedirs(dest_dir, exist_ok=True)
            cv2.imwrite(os.path.join(dest_dir, avg_filename), avg_image)


if __name__ == "__main__":
    run()
