from joblib import dump, load
import os
import click
import collections
import timeit
import warnings

import cv2

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

from lib.utils import get_files_to_process, pixel_to_mm, get_attributes_from_filename
from lib.constants import STRAIGHTENED_MASKS_DIR, TIP_MASK_PSEUDO_MAX_LENGTH
from lib.tip_mask import get_width_array, get_width_array_mm, normalize_width_array

from phenotype import get_length

# 1. read in mask
# 2. find index of red line
# 3. along the length: get width
# 4. normalize width


def get_true_tip_index(row):
    """
    finds a red pixel in the row of an image

    Args:
        row (np.array) - the image row
    Returns:
        index (int) or None
    """
    for i, pixel in enumerate(row):
        b, g, r = pixel
        if r > 100:
            return i


def get_index_first_white_pixel(image):
    """
    finds the index of the first white pixel

    Args:
        image (np.array) - greyscale image as nested np.array
    Returns:
        index (int)
    """
    for i, column in enumerate(image.T):
        count = collections.Counter(column)
        if count.get(255, None):
            return i


def equalize_lengths(raw_data):
    """
    ensure all normalized width arrays are of the same lengh
    """
    # max_length = max([len(d["normalized_widths"]) for d in raw_data])
    max_length = TIP_MASK_PSEUDO_MAX_LENGTH

    for d in raw_data:
        normalized_widths = d["normalized_widths"]
        missing_len = max_length - len(normalized_widths)
        d["normalized_widths"] = normalized_widths + [0] * missing_len

    return raw_data


def get_mask_pairs(src):
    """
    Assembles a list of raw/training mask pairs for each genotype

    Args:
        src (str): path to the source folder
    Returns:
        pairs (list)
    """
    pairs = []

    raw = os.path.join(src, "with-tips")
    training = os.path.join(src, "without-tips")

    genotypes = os.listdir(raw)
    for g in genotypes:
        if not g.startswith("."):
            pair = {"genotype": g}
            raw_mask_dir = os.path.join(raw, g, STRAIGHTENED_MASKS_DIR)
            for f in os.listdir(raw_mask_dir):
                if not f.startswith("."):
                    raw_straight_mask = os.listdir(raw_mask_dir)[0]
                    break
            raw_straight_mask = os.path.join(raw_mask_dir, raw_straight_mask)
            pair["with-tips"] = raw_straight_mask

            training_mask_dir = os.path.join(training, g, STRAIGHTENED_MASKS_DIR)
            for f in os.listdir(training_mask_dir):
                if not f.startswith("."):
                    training_straight_mask = os.listdir(training_mask_dir)[0]
                    break
            training_straight_mask = os.path.join(
                training_mask_dir, training_straight_mask
            )
            pair["without-tips"] = training_straight_mask
            pairs.append(pair)
    return pairs


@click.command()
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True),
    help="source directory of images to process",
)
def run(src):
    start = timeit.default_timer()
    pairs = get_mask_pairs(src)

    # pixel müssen vergleichbar sein.
    data = []
    for pair in pairs:
        raw = pair["with-tips"]
        training = pair["without-tips"]

        # print(raw)
        attributes = get_attributes_from_filename(raw)
        scale = attributes.get("Scale", None)
        mm_per_px = pixel_to_mm(scale)
        # print(mm_per_px)

        raw_mask = cv2.imread(raw, cv2.IMREAD_GRAYSCALE)
        training_mask = cv2.imread(training, cv2.IMREAD_GRAYSCALE)

        # reverse, so the thick end is at 0
        width_array = get_width_array_mm(raw_mask, mm_per_px)[::-1]
        # print(width_array)
        normalized_width_array = normalize_width_array(width_array)

        # length of raw carrot
        # raw_length = get_length(raw_mask)
        # print("length", raw_length)

        # length of detipped carrot
        detipped_length = get_length(training_mask)
        # print("detipped length", detipped_length)

        # difference in length
        # length_diff = raw_length - detipped_length

        # white_index_raw = get_index_first_white_pixel(raw_mask)

        # tip_index = white_index_raw + length_diff

        # because the widths are reversed
        tip_index = detipped_length

        data.append(
            {"tip_index": tip_index, "normalized_widths": normalized_width_array}
        )

    # resampling sagt Gilles...
    equalized_data = equalize_lengths(data)

    X = [d["normalized_widths"] for d in equalized_data]
    y = [d["tip_index"] for d in equalized_data]

    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)

    # linreg = LinearRegression().fit(X_train, y_train)

    # print('R-squared score (training): {:.3f}'
    #  .format(linreg.score(X_train, y_train)))
    # print('R-squared score (test): {:.3f}'
    #     .format(linreg.score(X_test, y_test)))

    regr = RandomForestRegressor(max_depth=5, random_state=0, n_estimators=10)
    regr.fit(X_train, y_train)
    print("score", regr.score(X_test, y_test))

    # regr.predict([[feature1, feature2]])

    dump(regr, "tip-mask-model.joblib")
    print("model dumped")
    stop = timeit.default_timer()
    print(f"training: {stop - start}")


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run()
