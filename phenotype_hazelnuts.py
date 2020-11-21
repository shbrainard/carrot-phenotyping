import csv

import click
import cv2
import imutils
import numpy as np

from lib.constants import BINARY_MASKS_DIR
from lib.crop import get_carrot_contour
from lib.utils import get_masks_to_process, get_attributes_from_filename


def assemble_instance(file):
    # print(file)
    instance = get_attributes_from_filename(file)

    if "kernel" in file:
        image_type = "kernel"
    elif "in-shell" in file:
        image_type = "in-shell"
    instance["type"] = image_type

    image = cv2.imread(file, cv2.IMREAD_GRAYSCALE)

    white_pixels = cv2.countNonZero(image)
    instance["white_pixels"] = white_pixels

    contour = get_carrot_contour(image)

    # https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_imgproc/py_contours/py_contour_features/py_contour_features.html
    # cnts = cv2.findContours(image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # cnts = cnts[0] if imutils.is_cv2() else cnts[1]
    # print(type(cnts))
    # c = max(cnts, key=cv2.contourArea)
    # color_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    # cv2.drawContours(color_image, [contour], -1, (0, 0, 255), 3)

    x, y, w, h = cv2.boundingRect(contour)
    # color_image = cv2.rectangle(color_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
    instance["width"] = w
    instance["height"] = h

    # https://stackoverflow.com/questions/31281235/anomaly-with-ellipse-fitting-when-using-cv2-ellipse-with-different-parameters
    # https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_gui/py_drawing_functions/py_drawing_functions.html#drawing-ellipse
    ellipse = cv2.fitEllipse(contour)
    ellipse_major_axis, ellipse_minor_axis = ellipse[1]
    ellipse_angle = ellipse[2]
    instance["ellipse_major_axis"] = round(ellipse_major_axis, 2)
    instance["ellipse_minor_axis"] = round(ellipse_minor_axis, 2)
    instance["ellipse_angle"] = round(ellipse_angle, 2)
    # print(ellipse[1], ellipse[2])
    # rect = cv2.minAreaRect(contour)
    # box = cv2.boxPoints(rect)
    # box = np.int0(box)
    # cv2.drawContours(color_image, [box], 0, (255, 0, 0), 4)
    # print(len(cnts))
    # cv2.imwrite("/Users/creimers/Downloads/affe.png", color_image)
    return instance


def spit_out_csv(instances: list, dest: str):
    header = instances[0].keys()

    with open(dest, "w") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow(list(header))
        for instance in instances:
            row = [v for k, v in instance.items()]
            writer.writerow(row)
            # print(row)
        # for line in data:
        #     writer.writerow(line)
    # print(header)
    # pass


@click.command()
@click.option("--dest", "-d", type=click.Path(), help="destination directory of csv")
@click.option("--dry", "-d", is_flag=True, help="don't touch the database")
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True),
    help="source directory of images to process",
)
def run(dest, dry, src):
    instances = []
    subdirs = get_masks_to_process(src, BINARY_MASKS_DIR)
    for dir in subdirs:
        for file in dir["files"]:
            try:
                instance = assemble_instance(file)
                instances.append(instance)
                if dry:
                    print(instance)
            except Exception as e:
                print(e)
    if not dry:
        spit_out_csv(instances, dest)


if __name__ == "__main__":
    run()
