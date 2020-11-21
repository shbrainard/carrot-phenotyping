from multiprocessing import Pool, cpu_count
import os
import shutil
import warnings

import click
import cv2
import numpy as np

from lib.crop import binary_mask_parallel, straighten_binary_masks
from phenotype import get_tip_angle_points, get_shoulders
from lib.constants import BINARY_MASKS_DIR, STRAIGHTENED_MASKS_DIR, DETIPPED_MASKS_DIR
from lib.crop import (
    crop_left_of_blue_line_hsv,
    get_target_dir,
    crop_black_tape,
    trim_tape_edges,
)
from lib.tip_mask import tip_mask
from lib.utils import (
    get_files_to_process,
    get_threshold_values,
    show_image,
    read_file,
    detect_backdrop,
)
from lib.straighten import get_midline, get_graph
from straighten import copy_results

VISUALS = ["blue-line", "black-box", "midline", "graph", "tip-angle", "shouldering"]


def draw_blue_line(target, old=False):
    outdir = get_target_dir(target["path"], "blue-line", True)
    for file in target["files"]:
        filename = file.split("/")[-1]
        outfile = os.path.join(outdir, filename)
        print(filename)
        try:
            image = read_file(file)
            backdrop = detect_backdrop(image)
            if backdrop == "white":
                image = trim_tape_edges(image)
            with_blue_line = crop_black_tape(image, backdrop, False)
            with_blue_line = crop_left_of_blue_line_hsv(
                with_blue_line, backdrop, old, True
            )
            # outfile = os.path.join(outdir, filename)
            # print(outfile)
            cv2.imwrite(outfile, with_blue_line)
        except Exception as e:
            print(e)
            click.secho(file, fg="red")


def draw_black_box(target, old=False):
    outdir = get_target_dir(target["path"], "black-box", True)
    for file in target["files"]:
        image = read_file(file)
        backdrop = detect_backdrop(image)
        if backdrop == "white":
            image = trim_tape_edges(image)
        with_blue_line = crop_black_tape(image, backdrop, True)
        filename = file.split("/")[-1]
        outfile = os.path.join(outdir, filename)
        print(outfile)
        cv2.imwrite(outfile, with_blue_line)


def draw_midline(target):
    """
    Draws midlines using existing binary masks.
    """

    masks = os.path.join(target, BINARY_MASKS_DIR)
    # check for existing binary masks
    if not os.path.exists(masks):
        raise Exception(f"No {BINARY_MASKS_DIR} folder in {target}!")

    # create midline folder
    new_folder_name = os.path.join(target, "midline")

    if os.path.exists(new_folder_name):
        shutil.rmtree(new_folder_name)

    if not os.path.exists(new_folder_name):
        os.makedirs(new_folder_name)

    for file in os.listdir(masks):
        filepath = os.path.join(masks, file)
        mask = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
        midline = get_midline(mask)
        color_image = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)

        for point in midline:
            x = point[0]
            y = point[1]
            try:
                color_image[int(y), :][int(x)] = np.array([0, 0, 255])
            except:
                pass

        output_filepath = os.path.join(new_folder_name, file)
        click.secho(f"Visualized midline for {filepath}")
        cv2.imwrite(output_filepath, color_image)


def visualize_shouldering(target):

    masks = os.path.join(target, STRAIGHTENED_MASKS_DIR)
    # check for existing binary masks
    if not os.path.exists(masks):
        raise Exception(f"No {STRAIGHTENED_MASKS_DIR} folder in {target}!")

    # create shouldering folder
    new_folder_name = os.path.join(target, "shouldering")
    if os.path.exists(new_folder_name):
        shutil.rmtree(new_folder_name)

    if not os.path.exists(new_folder_name):
        os.makedirs(new_folder_name)

    for file in os.listdir(masks):
        filepath = os.path.join(masks, file)
        mask = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
        color_image = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)

        shoulder_dict = get_shoulders(mask)

        top_y_min = shoulder_dict["top_y_min"]
        top_y_max = shoulder_dict["top_y_max"]
        top_x_min = shoulder_dict["top_x_min"]
        top_x_max = shoulder_dict["top_x_max"]

        bottom_y_min = shoulder_dict["bottom_y_min"]
        bottom_y_max = shoulder_dict["bottom_y_max"]
        bottom_x_min = shoulder_dict["bottom_x_min"]
        bottom_x_max = shoulder_dict["bottom_x_max"]

        output_filepath = os.path.join(new_folder_name, file)
        click.secho(f"Visualized shouldering for {filepath}")

        cv2.rectangle(
            color_image, (top_x_min, top_y_min), (top_x_max, top_y_max), [0, 0, 255], 1
        )
        cv2.rectangle(
            color_image,
            (bottom_x_min, bottom_y_min),
            (bottom_x_max, bottom_y_max),
            [0, 0, 255],
            1,
        )

        cv2.imwrite(output_filepath, color_image)


def draw_graph(target):
    for file in os.listdir(target):
        filepath = os.path.join(target, file)
        mask = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
        nodes, line = get_graph(mask)
        color_image = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)

        for point in line:
            x = point[0]
            y = point[1]
            try:
                cv2.circle(color_image, (x, y), 1, [255, 0, 0], -1)
            except Exception as e:
                print(e)
        for node in nodes:
            x = node[0]
            y = node[1]
            try:
                cv2.circle(color_image, (x, y), 4, [0, 255, 0], -1)
            except Exception as e:
                print(e)

        cv2.imwrite(filepath, color_image)

    new_folder_name = target.split("/")[:-1] + ["graph"]
    new_folder_name = "/".join(new_folder_name)
    try:
        shutil.rmtree(new_folder_name)
    except:
        pass
    os.rename(target, new_folder_name)


def draw_tip_lines(target):
    # target = os.path.join(target["path"], "binary_mask__tip-angle")
    for file in os.listdir(target):
        filepath = os.path.join(target, file)
        mask = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
        A_top, B_top, A_bottom, B_bottom = get_tip_angle_points(mask)

        ax_top, ay_top = A_top
        bx_top, by_top = B_top
        ax_bottom, ay_bottom = A_bottom
        bx_bottom, by_bottom = B_bottom
        mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        cv2.line(mask, (ax_top, ay_top), (bx_top, by_top), (0, 0, 255), 2)
        cv2.line(mask, (ax_bottom, ay_bottom), (bx_bottom, by_bottom), (0, 0, 255), 2)
        cv2.imwrite(filepath, mask)

    new_folder_name = target.split("/")[:-1] + ["tip-angle"]
    new_folder_name = "/".join(new_folder_name)
    try:
        shutil.rmtree(new_folder_name)
    except:
        pass
    os.rename(target, new_folder_name)


@click.command()
@click.option("--aspect", "-a", type=click.Choice(VISUALS))
@click.option("--length", help="length of the tip to consider", default=0.16)
@click.option("--old", is_flag=True, help="the old pictures")
@click.option(
    "--smoothen", default=0, help="smoothen the mask. Erosion iterations count."
)
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True),
    help="source directory of images to process",
)
def run(aspect, length, old, smoothen, src):
    if not aspect:
        click.secho("No aspect specified. Use --aspect", fg="red")
        return
    if not src:
        click.secho("No source specified. Use --src", fg="red")
        return

    clear = True

    mask_dest = BINARY_MASKS_DIR
    straight_dest = STRAIGHTENED_MASKS_DIR

    if aspect == "blue-line":
        name = None
        subdirs = get_files_to_process(src)
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(draw_blue_line, [(dir, old) for dir in subdirs])
        return

    if aspect == "black-box":
        name = None
        subdirs = get_files_to_process(src)
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(draw_black_box, [(dir, old) for dir in subdirs])
        return

    if aspect == "midline":
        subdirs = get_files_to_process(src)
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(draw_midline, [(dir["path"],) for dir in subdirs])
        return

    if aspect == "shouldering":
        subdirs = get_files_to_process(src)
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(visualize_shouldering, [(dir["path"],) for dir in subdirs])
        return

    # TODO: is this working??
    if aspect == "graph":
        subdirs = get_files_to_process(src)
        with Pool(processes=cpu_count()) as pool:

            # make masks
            pool.starmap(
                binary_mask_parallel,
                [(dir, smoothen, old, clear, None) for dir in subdirs],
            )

            # draw graphs
            pool.starmap(
                draw_graph, [(os.path.join(dir["path"], mask_dest),) for dir in subdirs]
            )
        return

    if aspect == "tip-angle":
        subdirs = get_files_to_process(src)
        no_tip_dest = "tip-angle"
        with Pool(processes=cpu_count()) as pool:
            # make masks
            pool.starmap(
                binary_mask_parallel,
                [(dir, smoothen, old, clear, None) for dir in subdirs],
            )

            # straighten mask (own folder)
            pool.starmap(
                straighten_binary_masks,
                [(os.path.join(dir["path"], mask_dest),) for dir in subdirs],
            )

        # moving straight masks
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(
                copy_results,
                [
                    (
                        os.path.join(dir["path"], mask_dest),
                        os.path.join(dir["path"], straight_dest),
                        "",
                        None,
                        True,
                    )
                    for dir in subdirs
                ],
            )

            # # tip mask
            dry = False
            pool.starmap(
                tip_mask,
                [(os.path.join(dir["path"], straight_dest), dry) for dir in subdirs],
            )

            # draw dip lines
            pool.starmap(
                draw_tip_lines,
                [(os.path.join(dir["path"], DETIPPED_MASKS_DIR),) for dir in subdirs],
            )

            # remove intermediate
            pool.starmap(
                shutil.rmtree,
                [(os.path.join(dir["path"], mask_dest),) for dir in subdirs],
            )
            pool.starmap(
                shutil.rmtree,
                [(os.path.join(dir["path"], straight_dest),) for dir in subdirs],
            )


if __name__ == "__main__":
    os.environ["JAVA_TOOL_OPTIONS"] = "-Dapple.awt.UIElement=true"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run()
