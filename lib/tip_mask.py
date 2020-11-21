import collections
from itertools import groupby
import os
import shutil


import click
import cv2
import numpy as np

from append import append_or_change_filename
from lib.crop import reduce_to_contour
from lib.constants import (
    METHODS,
    STRAIGHTENED_MASKS_DIR,
    DETIPPED_MASKS_DIR,
    TIP_MASK_PSEUDO_MAX_LENGTH,
)
from lib.utils import (
    count_white_pixels,
    write_file,
    get_attributes_from_filename,
    pixel_to_mm,
)
from phenotype import (
    get_length,
    get_max_width_unstraightened,
    get_index_of_tip,
    get_biomass,
)


def mark_start_of_tail(mask, index, color=[0, 0, 255]):
    """
    draw a red line where the beginning of the tip should be
    """
    try:
        assert len(mask[0][0]) == 3
    except:
        mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
    if index and index > 0:
        mask[:, index] = color
    return mask


def find_tip_brute_force(mask, pixel_threshold=15):
    """
    get the index of the beginning of the tip based on a hardcoded
    threshold value
    """

    mask_trans = mask.T
    mask_reversed = mask_trans[::-1]

    index = 0

    for i, column in enumerate(mask_reversed):
        # TODO: find bins
        white_pixel = count_white_pixels(column)
        if white_pixel > 0 and white_pixel <= pixel_threshold:
            index = i
            break

    if index != 0:
        return len(mask_reversed) - index - 1
    return index


def find_tip_brute_force_by_bins(mask, pixel_threshold=15):
    """
    get the index of the beginning of the tip based on a hardcoded
    threshold value
    """

    mask_trans = mask.T
    mask_reversed = mask_trans[::-1]

    index = 0

    for i, column in enumerate(mask_reversed):
        # all white cells
        bin_indexes = [x[0] for x in np.argwhere(column == 255)]

        # detect the number of bins
        bins = []
        for k, g in groupby(enumerate(bin_indexes), lambda ix: ix[0] - ix[1]):
            bins.append(list(g))

        if bins:
            sorted_bins = sorted(bins, key=lambda x: len(x), reverse=True)
            largest_bin = sorted_bins[0]
            if len(largest_bin) > 0 and len(largest_bin) <= pixel_threshold:
                index = i
                break

    if index != 0:
        return len(mask_reversed) - index - 1
    return index


def find_tip_pseudo_dynamic(mask, pure=False):
    """
    get the index of the beginning of the tip based on a hardcoded
    threshold value

    Args:
        mask - the binary mask as a numpy array
        pure - if true, only the threshold will be applied
    """
    length = get_length(mask)
    max_width = get_max_width_unstraightened(mask)

    length_width_ratio = length / max_width
    length_width_ratio = round(length_width_ratio, 2)

    if length_width_ratio > 10:
        carrot_type = "slender"
        pixel_threshold = 6
    elif length_width_ratio <= 10 and length_width_ratio >= 2.5:
        carrot_type = "normal"
        pixel_threshold = 6
    elif length_width_ratio < 2.5:
        carrot_type = "ball"
        pixel_threshold = 15
    else:
        pixel_threshold = 10

    mask_trans = mask.T
    mask_reversed = mask_trans[::-1]

    index = 0

    # 0. find a bin that is smaller or equal to the threshold
    for i, column in enumerate(mask_reversed):
        bin_height = count_bins_in_column(column)
        if bin_height > 0 and bin_height <= pixel_threshold:
            index = i
            break

    if index != 0:
        # look back and ahead!
        # 1. look ahead 20px. if any bin has white count of 0, then just return 0
        columns_lookahead = 13
        for j in range(columns_lookahead):
            try:
                bin_height = count_bins_in_column(mask_reversed[i + j])
                if bin_height == 0:
                    return 0
            except IndexError:
                return 0

        if pure is False:
            # 2. look back
            # back_index_avg = check_back_average(
            #     mask_reversed, length, i, pixel_threshold
            # )
            back_index_avg = check_back_abrupt_change(
                mask_reversed, length, i, pixel_threshold, carrot_type
            )
            if back_index_avg > 0:
                index = back_index_avg
            else:
                return 0

        return len(mask_reversed) - index - 1
    return index


def check_back_average(mask, length, start_index, pixel_threshold):
    """
    Tries to find some back corrected index by using an average
    of bin heights as it walks back...

    Args:
        mask: np.array - the binary mask
        length: int - the length of the carrot
        start_index: int - the index where the threshold was met
        pixel_threshold: int - the pixel threshold
    Returns:
        back corrected index: int
    """
    # check back 20% of the carrot
    back_length = round(length * 0.2)
    # the difference has to be at least 25 px
    min_back = 25

    bin_sum = 0
    count = 0
    for k in range(start_index, start_index - back_length, -1):
        count += 1
        bin_height = count_bins_in_column(mask[k])
        bin_sum += bin_height
        bin_avg = bin_sum / count

        if bin_avg >= pixel_threshold * 1.6:
            if count < min_back:
                return 0
            else:
                return k
    return 0


def check_back_abrupt_change(mask, length, start_index, pixel_threshold, carrot_type):
    """
    Looks back to see if an aprupt change in bin width can be detected

    Args:
        mask: np.array - the binary mask
        length: int - the length of the carrot
        start_index: int - the index where the threshold was met
        pixel_threshold: int - the pixel threshold
        carrot_type: string - the shape of the carrot
    Returns:
        back corrected index: int
    """

    if carrot_type == "slender":
        factor = 1.5
    else:
        factor = 2
    # check back 20% of the carrot
    back_length = round(length * 0.3)

    # the difference has to be at least 35 px
    min_back = 35
    max_back = 500

    count = 0
    for k in range(start_index, start_index - back_length, -1):
        count += 1
        bin_height = count_bins_in_column(mask[k])
        if bin_height > pixel_threshold * factor:
            if count < min_back or count > max_back:
                return 0
            else:
                return k
    return 0


def count_bins_in_column(column):
    """
    Args:
        column - np.array
    Returns:
        length of largest bin - int
    """
    # count of white cells
    bin_indexes = [x[0] for x in np.argwhere(column == 255)]

    # detect the number of bins
    bins = []
    for k, g in groupby(enumerate(bin_indexes), lambda ix: ix[0] - ix[1]):
        bins.append(list(g))

    if bins:
        sorted_bins = sorted(bins, key=lambda x: len(x), reverse=True)
        largest_bin = sorted_bins[0]
        return len(largest_bin)
    return 0


def tip_mask_ml(mask, model, mm_per_px):

    width_array = get_width_array_mm(mask, mm_per_px)[::-1]
    normalized_width_array = normalize_width_array(width_array)
    max_length = TIP_MASK_PSEUDO_MAX_LENGTH

    missing_len = max_length - len(normalized_width_array)
    widths = normalized_width_array + [0] * missing_len

    index = model.predict([widths])
    return index


def tip_mask(src, model, visualize=False):
    """
    mask the tips of the straightened carrots

    Args:
        src (str) - absolute path to the binary mask
        visualize (bool) - only visualize the masking
    """

    # if not dest:
    dest = src.split(STRAIGHTENED_MASKS_DIR)[0]
    dest = os.path.join(dest, DETIPPED_MASKS_DIR)
    if os.path.exists(dest):
        shutil.rmtree(dest)

    if not os.path.exists(dest):
        os.makedirs(dest)

    for file in os.listdir(src):
        print(file)
        src_filepath = os.path.join(src, file)
        dest_filepath = os.path.join(dest, file)

        mask = cv2.imread(src_filepath, cv2.IMREAD_GRAYSCALE)

        attributes = get_attributes_from_filename(src_filepath)
        scale = attributes.get("Scale", None)
        mm_per_px = pixel_to_mm(scale)

        if mask is None:
            msg = "File %s is empty!" % src_filepath
            click.secho(msg, fg="red")
            continue

        # get index from ml model
        try:
            tip_index = tip_mask_ml(mask, model, mm_per_px)
        except Exception as e:
            click.secho(file, fg="red")
            print(e)
            tip_index = [0]
        tip_index = int(tip_index[0])
        # print(tip_index)
        # print(mask.shape[1])
        tip_index = mask.shape[1] - tip_index

        # get index based on threshold
        # tip_index = find_tip_pseudo_dynamic(mask, pure=True)
        # tip_index_advanced = find_tip_pseudo_dynamic(mask, pure=False)

        # if tip_index_advanced > 0:
        #     crop_index = tip_index_advanced
        # else:
        #     crop_index = tip_index
        crop_index = tip_index

        if visualize:
            # paint only
            tip = mark_start_of_tail(mask.copy(), tip_index, [0, 0, 255])
            # tip = mark_start_of_tail(tip, tip_index_advanced, [0, 255, 0])
            # print(dest)
            write_file(tip, dest, file)
            continue

        else:
            # crop + buffer + wirte
            mask = mask[:, crop_index:]

            black_col = np.zeros((mask.shape[0], 10), dtype=np.uint8)
            mask = np.hstack([black_col, mask])

            # another round of contour reduction to remove dangling white pixels
            mask = reduce_to_contour(mask, minimize=False)

            cv2.imwrite(dest_filepath, mask)

        old_tip_index = get_index_of_tip(mask.T)
        tip_length = crop_index - old_tip_index
        if tip_length < 0:
            tip_length = 0
        tip_biomass = get_biomass(mask[:, old_tip_index:crop_index])
        new_filepath = append_or_change_filename(
            dest_filepath, "TipLength", None, tip_length
        )
        append_or_change_filename(new_filepath, "TipBiomass", None, tip_biomass)


def get_width_array(image):
    """
    creates an array of the bin width / 2 along the symmetry axis of the carrot

    Args:
        image (np.array) - greyscale image as nested np.array
    Returns:
        width_array (list)
    """

    width_array = []

    for column in image.T:
        count = collections.Counter(column)
        if count.get(255, None):
            width_array.append(count.get(255) / 2)
        else:
            width_array.append(0)
    return width_array


def get_width_array_mm(image, mm_per_px):
    """
    creates an array of the bin width / 2 along the symmetry axis of the carrot

    Args:
        image (np.array) - greyscale image as nested np.array
        mm_per_px (float) - mm per pixel
    Returns:
        width_array (list)
    """

    width_array = []

    for column in image.T:
        count = collections.Counter(column)
        if count.get(255, None):
            width_array.append(count.get(255) / 2)
        else:
            width_array.append(0)
    return [w * mm_per_px for w in width_array]


def normalize_width_array(width_array):
    """
    normalizes the width_array

    Args:
        width_array (list)
    Returns:
        normalized_width_array (list)
    """
    max_width = max(width_array)
    return [w / max_width for w in width_array]

