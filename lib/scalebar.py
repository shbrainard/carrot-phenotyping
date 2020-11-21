import click
import cv2
import imutils
import numpy as np

from append import append_or_change_filename
from lib.utils import read_file, get_files_to_process, write_file
from lib.crop import crop_left_of_blue_line_hsv
from phenotype import get_max_width


def create_binary_mask_by_green_index(image, threshold=70):
    """
    method suggested by Gilles. Used to detect the green scalebar.

    Detect by using an RGB index, in this index excess green
    """

    (B, G, R) = cv2.split(image.astype("float"))

    excess_green = 2 * G - R - B

    binary = np.piecewise(
        excess_green, [excess_green < threshold, excess_green >= threshold], [0, 1]
    )

    binary = binary * 255
    binary = binary.astype(np.uint8)

    return binary


def create_binary_mask_by_blue_index(image, threshold=0.3):
    """
    method suggested by Gilles. Used to detect the carrot.

    Detect by using an RGB index
    """

    (B, G, R) = cv2.split(image.astype("float"))

    blue_index = (B - R) / (B + R)

    binary = np.piecewise(
        blue_index, [blue_index < threshold, blue_index >= threshold], [0, 1]
    )

    binary = binary * 255
    binary = binary.astype(np.uint8)

    binary = cv2.erode(binary, None, iterations=2)
    binary = cv2.dilate(binary, None, iterations=2)

    return binary


def find_scalebar_contour(binary):
    cnts = cv2.findContours(binary.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if imutils.is_cv2() else cnts[1]
    c = max(cnts, key=cv2.contourArea)
    return c


def find_extreme_points_of_contour(c):
    left = tuple(c[c[:, :, 0].argmin()][0])
    right = tuple(c[c[:, :, 0].argmax()][0])
    top = tuple(c[c[:, :, 1].argmin()][0])
    bottom = tuple(c[c[:, :, 1].argmax()][0])

    return top, right, bottom, left


def measure_scalebar(dir, old):
    for file in dir["files"]:
        image = read_file(file)
        if old:
            if "_contour" in file or "_mask" in file or "_crop" in file:
                continue
            length = measure_scalebar_old(image)
        else:
            length = measure_scalebar_new(image)
        append_or_change_filename(file, "Scale", None, "%s" % length)


def measure_scalebar_new(rgb_image):
    """
    measure the length of the scalebar

    Returns:
        int - length in px
    """
    mask = create_binary_mask_by_green_index(rgb_image, threshold=120)
    contour = find_scalebar_contour(mask)
    top, right, bottom, left = find_extreme_points_of_contour(contour)
    length = right[0] - left[0]
    return length


def measure_scalebar_old(rgb_image):
    reversed_image = cv2.flip(rgb_image.copy(), 1)
    crop = crop_left_of_blue_line_hsv(reversed_image, True)

    # 0.19 --> might miss blue
    # 0.1 --> should catch all blue, but also catches red
    # 0.145 was working good!
    mask = create_binary_mask_by_blue_index(crop, 0.11)

    # consider just the second half to ignore the pink box
    mask = mask[:, mask.shape[1] // 2 :]

    # find contour of blue circle
    contour = find_scalebar_contour(mask)

    # create blank black slate
    rows = crop.shape[0]
    cols = crop.shape[1]
    img = np.zeros((rows, cols, 3), np.uint8)
    img[:, :] = (0, 0, 0)

    # draw white contour on black image
    cv2.drawContours(img, [contour], -1, (255, 255, 255), -1)
    # cv2.drawContours(crop, [contour], -1, (0, 255, 255), -1)

    # turn black image into binary mask
    thresh = cv2.threshold(img, 45, 255, cv2.THRESH_BINARY)[1]
    thresh = thresh[:, :-20]  # ignore the last 20px

    # add a black column so argmax can be > 0
    black_column = np.zeros((thresh.shape[0], 1, 3), dtype=np.uint8)
    black_column[:, :] = (0, 0, 0)

    thresh = np.append(black_column, thresh, axis=1)

    # determine the max width of the white contour
    max_height = get_max_width(thresh)
    # blue circle is 37 mm, so x2.7 to get pixels-per-10-cm
    height = round(max_height * 2.7)

    # filename = file.split(".")[0] + "_contour.png"
    # cv2.imwrite(filename, thresh)
    # filename = file.split(".")[0] + "_mask.png"
    # cv2.imwrite(filename, mask)
    # filename = file.split(".")[0] + "_crop.png"
    # cv2.imwrite(filename, crop)

    return height
