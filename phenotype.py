import click
import collections
import csv
import math
from datetime import datetime
import pytz
import timeit

import cv2
import numpy as np
from pymongo import MongoClient

from lib.constants import (
    config,
    DETIPPED_MASKS_DIR,
    BINARY_MASKS_DIR,
    STRAIGHTENED_MASKS_DIR,
)
from lib.utils import (
    get_masks_to_process,
    get_attributes_from_filename,
    show_image,
    pixel_to_mm,
)


def get_collection(collection_name):
    client = MongoClient()
    db = client.carrots
    collection = db[collection_name]
    return collection


def insert_or_update_instance(collection, instance, verbose: bool) -> str:
    """
    insert a carrot (represented as a dict) into a mongodb collection 
    update if exists
    """
    now = datetime.now(pytz.utc)
    # also use photo number to identify
    # therefore the db has to be dropped first
    if instance.get("Photo", None):
        existing = collection.find_one(
            {"UID": instance["UID"], "Photo": instance["Photo"]}
        )
        if not existing:
            existing = collection.find_one({"UID": instance["UID"]})
    else:
        existing = collection.find_one({"UID": instance["UID"]})
    if not existing:
        instance["created"] = now
        collection.insert_one(instance)
        return "inserted"
    else:
        instance["modified"] = now
        if verbose:
            print("updated UID:", instance["UID"])
            print("genotype before update:", existing["genotype"])
            print("genotype after update:", instance["genotype"])
        collection.update_one({"UID": instance["UID"]}, {"$set": instance})
        return "updated"


def convert_length_to_mm(scale, length_px):
    mm_per_pixel = pixel_to_mm(scale)
    length_mm = length_px * mm_per_pixel
    return round(length_mm, 4)


def convert_surface_to_mm2(scale, surface_px):
    mm_per_pixel = pixel_to_mm(scale)
    mm2_per_pixel = mm_per_pixel ** 2
    surface_mm2 = mm2_per_pixel * surface_px
    return round(surface_mm2, 4)


def count_white_pixels(row):
    """
    count the amount of pixels in an array
    """
    count = collections.Counter(row)

    if count.get(255, None):
        return count.get(255)
    return 0


def get_biomass(binary_mask):
    """
    counts the number of white pixels
    """

    white_pixels = cv2.countNonZero(binary_mask)
    return white_pixels


def get_max_width(binary_mask):
    """
    returns the max width of the carrot in pixel

    ###################################
    only works reliably for straightened mask!!!
    ###################################

    """
    start_px = 0
    end_px = 0

    for i, row in enumerate(binary_mask):
        max = np.argmax(row)
        if max > 0:
            start_px = i
            break

    for i, row in enumerate(binary_mask[::-1]):
        max = np.argmax(row)
        if max > 0:
            end_px = i
            break

    return binary_mask.shape[0] - start_px - end_px


def get_decile_widths(binary_mask, scale):
    mask_T = binary_mask.T

    tip_index = get_index_of_tip(mask_T)
    shoulder_index = get_index_of_shoulder(mask_T)
    # print("t", tip_index, "s", shoulder_index)
    decile = int((shoulder_index - tip_index) / 10)
    decile_indices = [i for i in range(tip_index, tip_index + decile * 10, decile)] + [
        shoulder_index - 1
    ]
    decile_widths = [count_white_pixels(mask_T[i]) for i in decile_indices]
    mm_per_pixel = pixel_to_mm(scale)
    decile_widths_mm = [round(i * mm_per_pixel, 2) for i in decile_widths]

    # shoulder to tip, that's why it's reversed here.
    return decile_widths_mm[::-1]


def get_max_width_unstraightened(binary_mask):
    mask_transposed = binary_mask.T
    white = [count_white_pixels(c) for c in mask_transposed]
    return max(white)


def get_index_of_tip(transposed_mask):
    start_px = 0
    for i, row in enumerate(transposed_mask):
        max = np.argmax(row)
        if max > 0:
            start_px = i
            break
    return start_px


def get_index_of_shoulder(transposed_mask):
    end_px = 0
    for i, row in enumerate(transposed_mask[::-1]):
        max = np.argmax(row)
        if max > 0:
            end_px = i
            break
    return transposed_mask.shape[0] - end_px
    # return end_px


def get_length(binary_mask):
    """
    returns the length of the carrot in pixel
    """
    mask_T = binary_mask.T

    tip_index = get_index_of_tip(mask_T)
    shoulder_index = get_index_of_shoulder(mask_T)

    return shoulder_index - tip_index


def get_length_width_ratio(binary_mask):
    width = get_max_width(binary_mask)
    length = get_length(binary_mask)
    ratio = length / width
    return round(ratio, 2)


def get_tip_angle_points(binary_mask, tip_length=0.16):
    mask_T = binary_mask.T
    tip_index = get_index_of_tip(mask_T)
    shoulder_index = get_index_of_shoulder(mask_T)

    length = shoulder_index - tip_index
    one_quarter = round(length * tip_length)

    first_quarter = binary_mask[:, tip_index : (tip_index + one_quarter)]

    first_quarter_T = first_quarter.T

    #####
    # TOP
    #####
    tip_y = np.argmax(first_quarter_T[0])
    quarter_y = np.argmax(first_quarter_T[-1])

    A_top = (tip_index, tip_y)
    B_top = (tip_index + one_quarter, quarter_y)

    ########
    # BOTTOM
    ########

    tip_y = np.argmax(first_quarter_T[0][::-1])
    quarter_y = np.argmax(first_quarter_T[-1][::-1])

    # here a conversion has to take place
    tip_y = len(first_quarter_T[0]) - 1 - tip_y
    quarter_y = len(first_quarter_T[0]) - 1 - quarter_y

    A_bottom = (tip_index, tip_y)
    B_bottom = (tip_index + one_quarter, quarter_y)

    return A_top, B_top, A_bottom, B_bottom


def get_biomass_above_tip_angle(binary_mask, tip_length=0.16):
    """
    count the amount of white pixels above the tip angle line.
    """
    A_top, B_top, A_bottom, B_bottom = get_tip_angle_points(binary_mask, tip_length)

    mask_T = binary_mask.T

    m_top = (B_top[1] - A_top[1]) / (B_top[0] - A_top[0]) * -1
    access_top = 0
    for x in range(0, B_top[0] - A_top[0]):
        y_calc = round(m_top * x)
        y_meas = A_top[1] - np.argmax(mask_T[x + A_top[0]])
        if y_meas > y_calc:
            access_top += y_meas - y_calc

    m_bottom = (B_bottom[1] - A_bottom[1]) / (B_bottom[0] - A_bottom[0]) * -1
    access_bottom = 0
    for x in range(0, B_bottom[0] - A_bottom[0]):
        y_meas = (
            len(mask_T[0]) - 1 - np.argmax(mask_T[x + A_bottom[0]][::-1]) - A_bottom[1]
        )
        y_calc = round(m_bottom * x) * -1
        if y_meas > y_calc:
            access_bottom += y_meas - y_calc

    return access_top, access_bottom


def get_tip_angles(binary_mask, tip_length=0.16):
    """
    a heuristic for the pointedness of the tip

    Args:
        binary_mask
    """
    A_top, B_top, A_bottom, B_bottom = get_tip_angle_points(binary_mask, tip_length)

    ax_top, ay_top = A_top
    bx_top, by_top = B_top

    theta_top = math.atan2(by_top - ay_top, bx_top - ax_top)
    theta_top_deg = np.abs(math.degrees(theta_top))

    ax_bottom, ay_bottom = A_bottom
    bx_bottom, by_bottom = B_bottom
    theta_bottom = math.atan2(by_bottom - ay_bottom, bx_bottom - ax_bottom)

    theta_bottom_deg = np.abs(math.degrees(theta_bottom))
    return theta_top_deg, theta_bottom_deg


def get_shoulders(binary_mask):
    mask_T = binary_mask.T

    length = get_length(binary_mask)
    shoulder_index = get_index_of_shoulder(mask_T)

    one_quarter = round(length / 4)
    last_quarter = binary_mask[:, (shoulder_index - one_quarter) : shoulder_index]

    last_quarter_T = last_quarter.T

    max_white_top = 1000
    max_white_top_index = 0
    for i, column in enumerate(last_quarter_T[::-1]):
        col_index = np.argmax(column)
        if col_index < max_white_top:
            max_white_top = col_index
            max_white_top_index = last_quarter.shape[1] - i

    max_white_bottom = 1000
    max_white_bottom_index = 0
    for i, column in enumerate(last_quarter_T[::-1]):
        col_index = np.argmax(column[::-1])
        if col_index < max_white_bottom:
            max_white_bottom = col_index
            max_white_bottom_index = last_quarter.shape[1] - i
    max_white_bottom = last_quarter.shape[0] - max_white_bottom - 1

    top_y_min = max_white_top
    top_y_max = last_quarter.shape[0] // 2

    top_x_min = shoulder_index - last_quarter.shape[1] + max_white_top_index - 1

    top_x_max = shoulder_index

    bottom_y_min = last_quarter.shape[0] // 2
    bottom_y_max = max_white_bottom

    bottom_x_min = shoulder_index - last_quarter.shape[1] + max_white_bottom_index - 1

    bottom_x_max = shoulder_index

    return {
        "top_y_min": top_y_min,
        "top_y_max": top_y_max,
        "top_x_min": top_x_min,
        "top_x_max": top_x_max,
        "bottom_y_min": bottom_y_min,
        "bottom_y_max": bottom_y_max,
        "bottom_x_min": bottom_x_min,
        "bottom_x_max": bottom_x_max,
    }


def get_shouldering(binary_mask):
    """
    a heuristic for the shouldering of the carrot.
    """
    shoulder_dict = get_shoulders(binary_mask)

    top_y_min = shoulder_dict["top_y_min"]
    top_y_max = shoulder_dict["top_y_max"]
    top_x_min = shoulder_dict["top_x_min"]
    top_x_max = shoulder_dict["top_x_max"]

    bottom_y_min = shoulder_dict["bottom_y_min"]
    bottom_y_max = shoulder_dict["bottom_y_max"]
    bottom_x_min = shoulder_dict["bottom_x_min"]
    bottom_x_max = shoulder_dict["bottom_x_max"]

    top_shoulder = binary_mask[top_y_min:top_y_max, top_x_min:top_x_max]
    bottom_shoulder = binary_mask[bottom_y_min:bottom_y_max, bottom_x_min:bottom_x_max]

    white_top = get_biomass(top_shoulder)
    black_top = (top_shoulder.shape[0] * top_shoulder.shape[1]) - white_top

    white_bottom = get_biomass(bottom_shoulder)
    black_bottom = (bottom_shoulder.shape[0] * bottom_shoulder.shape[1]) - white_bottom

    return black_top, black_bottom


def assemble_instance(file):
    instance = get_attributes_from_filename(file)

    scale = instance.get("Scale", None)

    if scale is None:
        click.secho(file, fg="red")
        click.secho("No 'Scale' attribute found!", fg="red")
        return

    image = cv2.imread(file, cv2.IMREAD_GRAYSCALE)

    width_px = get_max_width(image.copy())
    width_mm = convert_length_to_mm(scale, width_px)

    decile_widths = get_decile_widths(image.copy(), scale)

    length_px = get_length(image.copy())
    length_mm = convert_length_to_mm(scale, length_px)

    biomass_px = get_biomass(image.copy())
    biomass_mm2 = convert_surface_to_mm2(scale, biomass_px)

    instance["biomass"] = biomass_mm2
    instance["max_width"] = width_mm
    instance["width_0"] = decile_widths[0]
    instance["width_10"] = decile_widths[1]
    instance["width_20"] = decile_widths[2]
    instance["width_30"] = decile_widths[3]
    instance["width_40"] = decile_widths[4]
    instance["width_50"] = decile_widths[5]
    instance["width_60"] = decile_widths[6]
    instance["width_70"] = decile_widths[7]
    instance["width_80"] = decile_widths[8]
    instance["width_90"] = decile_widths[9]
    instance["width_100"] = decile_widths[10]
    instance["length"] = length_mm
    instance["length_width_ratio"] = get_length_width_ratio(image.copy())

    shoulder_top_px, shoulder_bottom_px = get_shouldering(image.copy())
    shoulder_top_mm2 = convert_surface_to_mm2(scale, shoulder_top_px)
    shoulder_bottom_mm2 = convert_surface_to_mm2(scale, shoulder_bottom_px)

    instance["shoulder_top"] = shoulder_top_mm2
    instance["shoulder_bottom"] = shoulder_bottom_mm2

    tip_angle_top, tip_angle_bottom = get_tip_angles(image.copy())
    instance["tip_angle_top"] = tip_angle_top
    instance["tip_angle_bottom"] = tip_angle_bottom

    above_tipangle_top_px, above_tipangle_bottom_px = get_biomass_above_tip_angle(
        image.copy()
    )
    above_tipangle_top_mm2 = convert_surface_to_mm2(scale, above_tipangle_top_px)
    above_tipangle_bottom_mm2 = convert_surface_to_mm2(scale, above_tipangle_bottom_px)
    instance["above_tipangle_top"] = above_tipangle_top_mm2
    instance["above_tipangle_bottom"] = above_tipangle_bottom_mm2

    return instance


def assemble_instance_from_csv(csv_file):
    instances = {}
    header = []
    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, dialect="excel")
        lines_read = 0
        for row in reader:
            lines_read += 1
            if lines_read == 1:
                if row[0] != "UID":
                    raise Exception(
                        "Looks like the first column does not contain the UIDs."
                    )
                header = row
                continue
            uid = row[0].strip()
            if uid not in instances.keys():
                instances[uid] = {}
            for i, key in enumerate(header[1:]):
                instances[uid][key] = row[i + 1].strip()

    instances_list = []
    for uid in instances.keys():
        instance = instances[uid]
        instance["UID"] = uid
        instances_list.append(instance)
    return instances_list


@click.command()
@click.option(
    "--collection",
    "-c",
    default="test_collection",
    help="name of the database collection",
)
@click.option(
    "--csv", type=click.Path(exists=True), help="csv file to import into mongodb"
)
@click.option("--dry", "-d", is_flag=True, help="don't touch the database")
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True),
    help="source directory of images to process",
)
@click.option(
    "--type",
    "-t",
    type=click.Choice(["binary", "straight", "detipped"]),
    help="subfolders to look out for",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Output details about the instances that are updated in the database.",
)
def run(collection, csv, dry, src, type, verbose):
    """

    Curvature: mm (describing the number of mm the carrot has been pulled down to center)  

    Biomass: mm^2

    Max_width: mm

    Length: mm

    L/W ratio: mm / mm

    Shoulder top / bottom: mm^2

    Tip angle top / bottom: absolute value of angle up/down from center line

    above tipangle top: mm2
    above tipangle bottom: mm2

    """
    mask_type = type

    if mask_type is None and not csv:
        click.echo("No mask type specified...")
        click.echo("run 'python phenotype.py --help to see options'")
        return

    if src is None and csv is None:
        click.echo("No source specified...")
        click.echo("run 'python phenotype.py --help to see options'")
        return

    if src is not None and csv is not None:
        click.echo(
            "Both source and csv file specified. I can only do one thing at a time"
        )
        click.echo("run 'python phenotype.py --help to see options'")
        return

    if csv is not None and not csv.endswith(".csv"):
        click.echo("That doesn't look like a csv file.")
        return

    tic = timeit.default_timer()
    if dry:
        collection = None
    else:
        collection = get_collection(collection)

    inserted = 0
    updated = 0

    if src is not None:
        type_map = {
            "binary": BINARY_MASKS_DIR,
            "straight": STRAIGHTENED_MASKS_DIR,
            "detipped": DETIPPED_MASKS_DIR,
        }
        subdirs = get_masks_to_process(src, type_map[mask_type])
        for dir in subdirs:
            for file in dir["files"]:
                try:
                    instance = assemble_instance(file)
                except Exception as e:
                    print(e)
                    instance = None
                    click.secho(file, fg="red")
                if instance is not None:
                    if dry:
                        print(instance)
                    else:
                        try:
                            action = insert_or_update_instance(
                                collection, instance, verbose
                            )
                        except Exception as e:
                            click.secho(f"failed to insert {file}", fg="red")
                        if action == "inserted":
                            inserted += 1
                        elif action == "updated":
                            updated += 1

    if csv is not None:
        instances = assemble_instance_from_csv(csv)
        for instance in instances:
            if dry:
                print(instance)
            else:
                action = insert_or_update_instance(collection, instance)
                if action == "inserted":
                    inserted += 1
                elif action == "updated":
                    updated += 1

    toc = timeit.default_timer()
    duration = toc - tic
    msg = "Inserted %s and updated %s in %.2f seconds." % (inserted, updated, duration)
    click.secho(msg, fg="green")


if __name__ == "__main__":

    run()
