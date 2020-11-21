import click
import cv2
import imutils
from multiprocessing import Pool
import numpy as np
import os
from scipy import ndimage
import shutil
import subprocess
import timeit

from lib.constants import (
    METHODS,
    BINARY_MASKS_DIR,
    STRAIGHTENED_MASKS_DIR,
    DETIPPED_MASKS_DIR,
    MASK_OVERLAYS_DIR,
    config,
)
from append import append_or_change_filename
from phenotype import (
    get_length,
    get_max_width_unstraightened,
    get_index_of_tip,
    get_biomass,
    get_index_of_shoulder,
)
from lib.utils import (
    get_files_to_process,
    read_file,
    write_file,
    get_attributes_from_filename,
    count_white_pixels,
    get_threshold_values,
    detect_backdrop,
)


def trim_tape_edges(image):
    """
    Trim away the tape edges where chromatic aberration is occuring
    in some unfortunate cases

    https://en.wikipedia.org/wiki/Chromatic_aberration
    """
    relative_tape_height = 0.1
    relative_tape_width = 0.05
    one_half = 0.5

    height, width, _ = image.shape

    tape_height = height * relative_tape_height
    tape_width = width * relative_tape_width

    width_from = int(tape_width * one_half)
    width_to = int(width - tape_width * one_half)

    height_from = int(tape_height * one_half)
    height_to = int(height - tape_height * one_half)

    return image[height_from:height_to, width_from:width_to]


def crop_left_of_blue_line_hsv(
    source_array, backdrop="white", old=False, visualize=False
):
    if old:
        # B G R
        blue_boundaries = ([170, 90, 40], [190, 110, 65])  # original

        lower = np.array(blue_boundaries[0], dtype="uint8")
        upper = np.array(blue_boundaries[1], dtype="uint8")

        mask = cv2.inRange(source_array, lower, upper)
        blues = []
        for row in mask:
            max_val = row.argmax()
            if max_val > 0:
                blues.append(max_val)

        min_blue = min(blues)

        cropped = source_array[:, : min_blue - 5]
        return cropped

    overlay = source_array.copy()
    output = source_array.copy()

    hsv_img = cv2.cvtColor(source_array, cv2.COLOR_BGR2HSV)
    if backdrop == "white":
        overlay_color = (255, 255, 255)
        BLUE_MIN = np.array([85, 50, 50], np.uint8)
        BLUE_MAX = np.array([150, 255, 255], np.uint8)
    else:
        overlay_color = (0, 0, 0)
        BLUE_MIN = np.array([85, 45, 45], np.uint8)
        BLUE_MAX = np.array([150, 255, 255], np.uint8)

    if visualize:
        overlay_color = (0, 255, 255)

    frame_threshed = cv2.inRange(hsv_img, BLUE_MIN, BLUE_MAX)

    cnts = cv2.findContours(
        frame_threshed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    cnts = cnts[0] if imutils.is_cv2() else cnts[1]

    sorted_contours = sorted(cnts, key=cv2.contourArea)[::-1]

    # ### DEBUGGING
    # alpha = 0.4
    # cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)
    # return output

    # top left corner of blue tape
    min_y_y = source_array.shape[0]
    min_y_x = None

    # bottom left corner of blue tape
    max_y_y = 0
    max_y_x = None

    # extreme left points of blue tape
    ext_lefts = []

    y_offset = 25  # corridor to search for min_x in
    biggest_contour_area = cv2.contourArea(sorted_contours[0])

    for c in sorted_contours[:2]:

        # if the contour is too small, it's probably no blue tape
        relative_area = cv2.contourArea(c) / biggest_contour_area
        if relative_area < 0.1:
            continue

        cv2.drawContours(overlay, [c], -1, overlay_color, -1)

        # chromatic abaration business
        if backdrop == "white":
            cv2.drawContours(overlay, [c], -1, overlay_color, 8)

        # extreme left point of blue tape
        ext_left = tuple(c[c[:, :, 0].argmin()][0])
        ext_lefts.append(ext_left)

        # cv2.circle(output, ext_left, 5, (0, 0, 255), -1)

        # find top left corner
        # find y coordinate
        min_y_index = c[:, :, 1].argmin()
        min_y_c = tuple(c[min_y_index][0])
        if min_y_c[1] < min_y_y:
            min_y_y = min_y_c[1]

            # find x coordinate
            if min_y_y < source_array.shape[0] / 4:
                min_y_min_x = c[min_y_index : min_y_index + y_offset, :, 0].argmin()
                min_y_x = c[min_y_min_x][0][0]

        # find bottom left corner
        # find y coordinate
        max_y_index = c[:, :, 1].argmax()
        max_y_c = tuple(c[max_y_index][0])
        if max_y_c[1] > max_y_y:
            max_y_y = max_y_c[1]

            # find x coordinate
            if max_y_y > source_array.shape[0] * 0.75:
                sorted_by_y = sorted(c, key=lambda x: x[0][1])[::-1]
                min_x_index = np.array(sorted_by_y)[:y_offset, :, 0].argmin()
                max_y_x = sorted_by_y[min_x_index][0][0]

    # x, y
    top_left = [min_y_x, 0]
    bottom_left = [max_y_x, overlay.shape[0]]
    bottom_right = [min_y_x + 150, overlay.shape[0]]
    top_right = [max_y_x + 150, 0]

    ext_lefts = sorted(ext_lefts, key=lambda x: x[1])

    # pnt = tuple(ext_lefts[0])
    # cv2.circle(output, pnt, 10, (0, 0, 255), -1)

    polygon = [
        top_left,  # top left
        ext_lefts[0],
        bottom_left,  # bottom left
        bottom_right,  # bottom right
        top_right,  # ... top right
    ]

    if len(ext_lefts) > 1:
        polygon.insert(2, ext_lefts[1])

    vrx = np.array(polygon, dtype=np.int32)

    cv2.fillPoly(overlay, pts=[vrx], color=overlay_color, lineType=cv2.LINE_AA)

    # corridor of carefullness
    # on white background, check again for blue with a wider definition of what blue is

    # TODO: legacy??
    # if backdrop == "white":
    if False:
        left = 10
        right = 30
        top_left = (ext_lefts[0][0] - left, 0)
        bottom_left = (ext_lefts[0][0] - left, overlay.shape[0])
        bottom_right = (ext_lefts[0][0] + right, overlay.shape[0])
        top_right = (ext_lefts[0][0] + right, 0)

        polygon = [top_left, bottom_left, bottom_right, top_right]

        corridor_in_image = hsv_img[0 : overlay.shape[0], top_left[0] : top_right[0]]
        BLUE_MIN = np.array([80, 30, 30], np.uint8)
        BLUE_MAX = np.array([160, 255, 255], np.uint8)
        frame_threshed = cv2.inRange(corridor_in_image, BLUE_MIN, BLUE_MAX)

        cnts = cv2.findContours(
            frame_threshed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cnts = cnts[0] if imutils.is_cv2() else cnts[1]
        cv2.drawContours(
            overlay[0 : overlay.shape[0], top_left[0] : top_right[0]],
            cnts,
            -1,
            overlay_color,
            -1,
        )

    crop_at = max(min_y_x, max_y_x)
    if visualize:
        cv2.circle(output, (crop_at, 0), 10, (0, 0, 255), -1)
        alpha = 0.35
        cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)
        return output
    else:
        cropped = overlay[:, :crop_at]
        return cropped


def crop_black_tape(source_array, backdrop="white", visualize=False):
    """
    crop the image inside of the black tape
    """
    gray = cv2.cvtColor(source_array, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    if backdrop == "white":
        thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.erode(thresh, None, iterations=5)
        thresh = cv2.dilate(thresh, None, iterations=5)
    else:
        thresh = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY_INV)[1]
        thresh = cv2.erode(thresh, None, iterations=2)
        thresh = cv2.dilate(thresh, None, iterations=2)

    # return thresh

    cnts = cv2.findContours(thresh.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if imutils.is_cv2() else cnts[1]

    con = max(cnts, key=cv2.contourArea)

    if visualize:
        cv2.drawContours(source_array, [con], -1, (0, 0, 255), 4)
        return source_array

    rc = cv2.minAreaRect(con)
    box = cv2.boxPoints(rc)
    x1, x2 = sorted(box[:, 0])[1:3]
    y1, y2 = sorted(box[:, 1])[1:3]
    crop_img = source_array[int(y1) + 25 : int(y2) - 25, int(x1) + 25 :]

    return crop_img


def create_binary_mask_by_index(image, threshold=0.1, smoothen=0):
    """
    method suggested by Gilles. Used to detect the carrot.

    Detect by using an RGB index
    """

    (B, G, R) = cv2.split(image.astype("float"))

    blue_index = np.absolute((B - R) / (B + R))

    binary = np.piecewise(
        blue_index, [blue_index < threshold, blue_index >= threshold], [0, 1]
    )

    binary = binary * 255

    #  # Gilles says he would not do this in the raw data
    # TODO: put in own function
    if smoothen > 0:
        thresh = cv2.erode(binary, None, iterations=smoothen)
        binary = cv2.dilate(thresh, None, iterations=smoothen)

    binary = binary.astype(np.uint8)

    #  return binary
    black_row = np.zeros((12, binary.shape[1]), dtype=np.uint8)
    buffered_binary = np.vstack([black_row, binary, black_row])

    return buffered_binary


def create_binary_mask_by_thresh(image, backdrop, threshold=125, smoothen=0):
    """
    Method taken from here: https://www.pyimagesearch.com/2016/04/11/finding-extreme-points-in-contours-with-opencv/

    Detect carrot by bw thresholding
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #  gray = cv2.GaussianBlur(gray, (5, 5), 0)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)

    if backdrop == "white":
        inv = cv2.THRESH_BINARY_INV
    else:
        inv = cv2.THRESH_BINARY

    # the lower the first value, the more grey is detected
    thresh = cv2.threshold(gray, threshold, 255, inv)[1]

    if smoothen > 0:
        thresh = cv2.erode(thresh, None, iterations=smoothen)
        thresh = cv2.dilate(thresh, None, iterations=smoothen)

    binary = thresh

    #  return binary
    black_row = np.zeros((12, binary.shape[1]), dtype=np.uint8)
    buffered_binary = np.vstack([black_row, binary, black_row])

    return buffered_binary


def get_carrot_contour(image):
    """
    Args:
        image (numpy.ndarray): the image as multidimensional array of 0 and 1
    """
    img = cv2.merge((image, image, image))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    cnts = cv2.findContours(gray.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if imutils.is_cv2() else cnts[1]
    if cnts:
        c = max(cnts, key=cv2.contourArea)
        return c


def reduce_to_contour(image, minimize=False):
    """
    find the biggest contour in image and paint it white

    https://www.youtube.com/watch?v=O4irXQhgMqg

    Args:
        image (numpy.ndarray): the image as multidimensional array of 0 and 1
    """

    # TODO: user get_carrot_contour function

    # create a three channel image again
    img = cv2.merge((image, image, image))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    mask = np.zeros(gray.shape, dtype=np.uint8)

    cnts = cv2.findContours(gray.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if imutils.is_cv2() else cnts[1]
    c = max(cnts, key=cv2.contourArea)
    cv2.drawContours(mask, [c], -1, (255, 0, 0), -1)

    # TODO: put in own function
    if minimize:
        # determine the most extreme points along the contour
        extLeft = tuple(c[c[:, :, 0].argmin()][0])
        # we don't need the extreme right point
        #  extRight = tuple(c[c[:, :, 0].argmax()][0])
        extTop = tuple(c[c[:, :, 1].argmin()][0])
        extBot = tuple(c[c[:, :, 1].argmax()][0])

        # crop at max points
        x = min(extLeft[0], extTop[0], extBot[0])
        y1 = min(extLeft[1], extTop[1], extBot[1])
        y2 = max(extLeft[1], extTop[1], extBot[1])

        buffer = 10

        mask = mask[y1 - buffer : y2 + buffer, x:]

    black_column = np.zeros((mask.shape[0], 10), dtype=np.uint8)

    mask = np.append(black_column, mask, axis=1)
    return mask


# TODO: remove dest argument
def straighten_binary_masks(src, dest=None):
    """
    pass the created binary masks into the java straightener

    Args:
        src (str): absolute path to the binary_maks dir
    """

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    java_files = "%s/java/binaries/*" % root
    binary_mask_dir = "/%s" % src

    cmd = ["java", "-cp", java_files, "org.uwm.carrots.Straightener", binary_mask_dir]

    click.secho("Running the following straightener command: ", fg="blue")
    click.secho(" ".join(cmd), fg="blue")

    subprocess.call(cmd)

    # crop away unnecessary black
    for file in os.listdir(src):
        src_filepath = os.path.join(src, file)
        mask = cv2.imread(src_filepath, cv2.IMREAD_GRAYSCALE)
        # TODO: stack black rows
        black_row = np.zeros((10, mask.shape[1]), dtype=np.uint8)
        mask = np.vstack([black_row, mask, black_row])
        black_col = np.zeros((mask.shape[0], 10), dtype=np.uint8)
        mask = np.hstack([black_col, mask, black_col])
        mask = reduce_to_contour(mask, True)
        cv2.imwrite(src_filepath, mask)


def create_binary_mask(
    image, smoothen=0, minimize=True, old=False, no_black_tape=False
):
    """
    create a binary mask of the carrot image
    """

    backdrop = detect_backdrop(image)
    index_threshold, grey_threshold = get_threshold_values(backdrop, old)

    if backdrop == "white" and no_black_tape is False:
        crop = trim_tape_edges(image)
    else:
        crop = image

    if no_black_tape is False:
        crop = crop_black_tape(image, backdrop)
    crop = crop_left_of_blue_line_hsv(crop, backdrop, old)

    binary_by_thresh = create_binary_mask_by_thresh(
        crop, backdrop, threshold=grey_threshold, smoothen=smoothen
    )

    if backdrop == "white":
        binary_by_index = create_binary_mask_by_index(
            crop, threshold=index_threshold, smoothen=smoothen
        )
        binary_combined = binary_by_index | binary_by_thresh

        contour = reduce_to_contour(binary_combined, minimize=minimize)
    else:
        contour = reduce_to_contour(binary_by_thresh, minimize=minimize)

    # find gaps in first shoulder column and fill them
    trans = contour.T
    trans_reverse = trans[::-1]

    last_white = None
    for i, col in enumerate(trans_reverse):
        white_pixels = count_white_pixels(col)
        if white_pixels:
            last_white = i * -1
            break

    if last_white is not None:
        for i in range(1, 8):
            column = contour[:, last_white - i].copy()
            column_filled = ndimage.binary_fill_holes(column).astype(int) * 255
            contour[:, last_white - i] = column_filled

        # ensure shoulder symmetry

        # as few magic numbers as possible
        columns_to_consider = 2
        length_difference = 0.9

        for i in range(columns_to_consider, 0, -1):
            column = contour[:, last_white - i].copy()
            prev_column = contour[:, last_white - i - 1].copy()
            white_pixels = count_white_pixels(column)
            white_pixels_prev = count_white_pixels(prev_column)

            if white_pixels <= white_pixels_prev * length_difference:

                # this column
                first_white_pixel_col = column.argmax()
                last_white_pixel_col = len(column) - 2 - column[::-1].argmax()

                # prev column
                first_white_pixel_prev_col = prev_column.argmax()
                last_white_pixel_prev_col = (
                    len(prev_column) - 2 - prev_column[::-1].argmax()
                )

                # where's the gap?
                start = abs(first_white_pixel_col - first_white_pixel_prev_col)
                end = abs(last_white_pixel_col - last_white_pixel_prev_col)

                if start < end:
                    # start at start
                    pixel = white_pixels_prev - start * 2 - 2
                    column[first_white_pixel_col : first_white_pixel_col + pixel] = 255
                    contour[:, last_white - i] = column
                else:
                    # start at end
                    pixel = white_pixels_prev - end * 2 - 2
                    column[last_white_pixel_col - pixel : last_white_pixel_col] = 255
                    contour[:, last_white - i] = column

        contour = reduce_to_contour(contour, minimize=False)

    # find and eliminate "empty" bins at right edge of image
    shoulder_index = get_index_of_shoulder(contour.T)
    cropped = contour[:, :shoulder_index]

    return cropped


def create_mask_overlay(image, smoothen=0, old=False, no_black_tape=False):
    """
    create binary mask and put if over the original image 
    inspiration: https://www.pyimagesearch.com/2016/03/07/transparent-overlays-with-opencv/

    Args:
        image (list): the original image as np array, cropped left of the blue line
        smoothen (bool): smoothen edges, y/n
    """
    backdrop = detect_backdrop(image)
    index_threshold, grey_threshold = get_threshold_values(backdrop, old)
    if backdrop == "white" and no_black_tape is False:
        image = trim_tape_edges(image)

    if no_black_tape is False:
        crop = crop_black_tape(image, backdrop)
    crop = crop_left_of_blue_line_hsv(crop, backdrop, old)
    # return crop

    overlay = crop.copy()
    output = crop.copy()

    # do this because the binary functions also do it
    white_row = np.zeros((12, overlay.shape[1]), dtype=np.uint8) + 1
    white_row = cv2.merge((white_row, white_row, white_row)) * 255

    overlay = np.vstack([white_row, overlay, white_row])
    output = np.vstack([white_row, output, white_row])

    binary_by_thresh = create_binary_mask_by_thresh(
        crop, backdrop, smoothen=smoothen, threshold=grey_threshold
    )

    if backdrop == "white":

        binary_by_index = create_binary_mask_by_index(
            crop, threshold=index_threshold, smoothen=smoothen
        )

        binary_combined = binary_by_index | binary_by_thresh
        contour = get_carrot_contour(binary_combined)
    else:
        contour = get_carrot_contour(binary_by_thresh)

    if backdrop == "white":
        overlay_color = (255, 0, 0)
    else:
        overlay_color = (0, 255, 0)
    alpha = 0.35

    cv2.drawContours(overlay, [contour], -1, overlay_color, -1)
    cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)

    c = contour
    extLeft = tuple(c[c[:, :, 0].argmin()][0])
    # we don't need the extreme right point
    #  extRight = tuple(c[c[:, :, 0].argmax()][0])
    extTop = tuple(c[c[:, :, 1].argmin()][0])
    extBot = tuple(c[c[:, :, 1].argmax()][0])

    # crop at max points
    x = min(extLeft[0], extTop[0], extBot[0])
    y1 = min(extLeft[1], extTop[1], extBot[1])
    y2 = max(extLeft[1], extTop[1], extBot[1])

    buffer = 25

    mask = output[y1 - buffer : y2 + buffer, x - buffer :]

    return mask


# #########################
# (mother's little) HELPERS
# #########################


def get_target_dir(dirpath, method_name, clear=False):
    """
    create the name of the target dir as a combination of the source dir and 
    the method name
    """

    target_dir = os.path.join(dirpath, method_name)

    if os.path.exists(target_dir) and clear is True:
        shutil.rmtree(target_dir)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    return target_dir


def move_straightened_masks(source, dest):
    """
    move the straightened masks to their final destination
    """

    for file in os.listdir(source):
        # only straightened masks
        if "Curvature" in file and file.endswith(config["file_format"]):
            corrected_file = file.replace("_px", "px").replace("_ppm", "ppm")
            # extract info from file
            attributes = get_attributes_from_filename(corrected_file)
            year = attributes["UID"].split("-")[-1]
            # Year_Location > Genotype > straightened masks
            location = attributes.get("Location", "missing_location")
            year_location = "_".join([year, location])
            # compose target
            source = attributes.get("Genotype", None)
            if source is None:
                source = attributes.get("Source", "missing_genotype")
            result_target = os.path.join(dest, year_location, source)
            # create target if it does not exist yet
            os.makedirs(result_target, exist_ok=True)

            # move mask there
            source_filepath = os.path.join(source, file)
            dest_filepath = os.path.join(result_target, corrected_file)
            os.rename(source_filepath, dest_filepath)


def log_activity(file, method, straighten=False):
    """
    create a verbose output of what the script is doing to which file
    """

    log = "Working on... "

    if method == BINARY_MASKS_DIR:
        log = "Creating binary mask"
        if straighten:
            log += " and straightening"

    elif method == MASK_OVERLAYS_DIR:
        log = "Creating mask overlay"

    elif method == "blue_crop":
        log = "Cropping left of blue line"

    elif method == "white_crop":
        log = "Cropping inside of black tape"

    elif method == "biomass_loss":
        log = "Assessing biomass loss"

    output = " ".join([log, "on", file])
    click.echo(output)


# ###############
# METHOD WRAPPERS
# ###############
def mask_overlay_parallel(
    dir, smoothen, old, clear, out_dir_name=None, no_black_tape=False
):
    """
    create minary mask overlays in parallel
    """
    method = MASK_OVERLAYS_DIR
    if out_dir_name is not None:
        dir_name = "__".join([method, out_dir_name])
    else:
        dir_name = method
    target = get_target_dir(dir["path"], dir_name, clear)
    for file in dir["files"]:
        try:
            log_activity(file, method)
            image = read_file(file)
            masked_overlay = create_mask_overlay(
                image, smoothen=smoothen, old=old, no_black_tape=no_black_tape
            )
            filename = file.split("/")[-1]
            write_file(masked_overlay, target, filename)
        except:
            click.secho(file, fg="red")


def binary_mask_parallel(
    dir, smoothen, old, clear, out_dir_name=None, no_black_tape=False
):
    """
    create binary masks in parallel

    Args:
        dir             <dict> : dictionary that holds the files to be processed
        index_threshold <float>: threshold for the mask by index function
        index_threshold <int>: threshold for the mask by threshold function
        smoothen        <bool>: whether or not to smoothen the contour
        old             <bool>: is this an "old" picture
        clear           <bool>: should the output dir be cleared?
        out_dir_name    <str>: alternative name for output dir
        no_black_tape   <bool>: no black tape arround carrot
    """
    method = "binary-masks"
    if out_dir_name is not None:
        dir_name = "__".join([method, out_dir_name])
    else:
        dir_name = method
    target = get_target_dir(dir["path"], dir_name, clear)
    for file in dir["files"]:
        log_activity(file, method, False)
        try:
            image = read_file(file)
            filename = file.split("/")[-1]

            minimize = True
            binary_mask = create_binary_mask(
                image,
                smoothen=smoothen,
                minimize=minimize,
                old=old,
                no_black_tape=no_black_tape,
            )
            write_file(binary_mask, target, filename)

        except Exception as error:
            click.secho(file, fg="red")
            click.secho(repr(error), fg="red")
