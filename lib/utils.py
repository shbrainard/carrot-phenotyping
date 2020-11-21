import collections
import cv2
import os
import re
import shutil

from lib.constants import METHODS, config


def read_file(file_path):
    """
    read picture from disc using its absolute path
    """
    return cv2.imread(file_path)


def write_file(source_array, target_dir, filename):
    """
    write the picture to disc
    """
    target_file = os.path.join(target_dir, filename)
    cv2.imwrite(target_file, source_array)


def get_masks_to_process(source_dir, mask_type):
    """
    get the absolute paths of the binary mask files to process
    Args:
        source_dir (str) - path
        mask_type (str) - 
    """
    subdirs = []
    for subdir, dirs, files in os.walk(source_dir):
        dirname = subdir.split("/")[-1].split("__")[0]
        if dirname == mask_type:
            dir_entry = {"path": subdir}
            dir_files = []
            for file_name in files:
                if file_name[0] is not "." and file_name.endswith(
                    config["file_format"]
                ):
                    file_path = os.path.join(subdir, file_name)
                    dir_files.append(file_path)
            if len(dir_files):
                dir_entry["files"] = dir_files
                subdirs.append(dir_entry)
    return subdirs


def get_files_to_process(source_dir, allowed_methods=[]):
    """
    get the absolute paths of the raw files to process
    """
    subdirs = []
    for subdir, dirs, files in os.walk(source_dir):
        dirname = subdir.split("/")[-1].split("__")[0]
        if dirname not in METHODS or dirname in allowed_methods:
            dir_entry = {"path": subdir}
            dir_files = []
            for file_name in files:
                if file_name.endswith(
                    config["file_format"]
                ) and not file_name.startswith("."):
                    file_path = os.path.join(subdir, file_name)
                    dir_files.append(file_path)
            if len(dir_files):
                dir_entry["files"] = dir_files
                subdirs.append(dir_entry)
    return subdirs


def get_kv_pairs(filename):
    key_value_re = r"{([\w-]+_[\w-]+)}"
    kv_pairs = re.findall(key_value_re, filename)
    return kv_pairs


def get_kv_pairs_dict(filename):
    kv_pairs = get_kv_pairs(filename)
    pairs = [p.split("_") for p in kv_pairs]
    return {k: v for (k, v) in pairs}


def get_attributes_from_filename(filename):
    instance = {}
    kv_pairs = get_kv_pairs(filename)
    for pair in kv_pairs:
        key, value = pair.split("_")
        instance[key] = value
    return instance


def show_image(image):
    cv2.namedWindow("image", cv2.WINDOW_NORMAL)
    cv2.imshow("image", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def count_white_pixels(array):
    """
    count the amount of pixels in an array
    """
    count = collections.Counter(array)

    if count.get(255, None):
        return count.get(255)
    return 0


def get_threshold_values(backdrop, old):
    # threshold values for new images
    # lower --> more orange is detected
    index_threshold = 0.14

    # higher --> more grey included
    grey_threshold = 150  # original!!

    if old:
        # threshold values for old images
        index_threshold = 0.13
        grey_threshold = 63

    if backdrop == "black":
        grey_threshold = 50

    return index_threshold, grey_threshold


def clear_and_create(path):
    if os.path.exists(path):
        shutil.rmtree(path)

    if not os.path.exists(path):
        os.makedirs(path)


def detect_backdrop(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.erode(thresh, None, iterations=2)
    thresh = cv2.dilate(thresh, None, iterations=2)

    white_pixels = cv2.countNonZero(thresh)
    total_pixels = thresh.shape[0] * thresh.shape[1]
    white_ratio = white_pixels / total_pixels

    if white_ratio > 0.6:
        return "white"
    return "black"


def pixel_to_mm(scale):
    """
    convert the length of one px to mm
    """
    scale = int(scale)
    scalebar_length = config["scalebar_length"]
    # pixel_per_mm = scale / scalebar_length
    mm_per_px = scalebar_length / scale
    return round(mm_per_px, 4)

