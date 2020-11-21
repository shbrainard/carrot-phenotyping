from multiprocessing import Pool, cpu_count
import os
import pathlib
import shutil
import warnings

import click
import cv2

from lib.constants import BINARY_MASKS_DIR, STRAIGHTENED_MASKS_DIR, config
from lib.crop import binary_mask_parallel, straighten_binary_masks
from lib.utils import (
    clear_and_create,
    get_threshold_values,
    get_masks_to_process,
    get_attributes_from_filename,
)


def copy_results(
    source, dest, dest_dir_key="Genotype", dest_sub_key=None, flat_files=False
):
    """
    move the straightened masks to their final destination

    Args:
        source (str): absolute path to the source directory
        dest (str): absolute path to the dest directory
        dest_dir_key (str): key to be used to name the directory
        dest_sub_key (str): key to be used to name the subdirectory
    """
    for file in os.listdir(source):
        if "Curvature" in file and file.endswith(config["file_format"]):
            corrected_file = file.replace("_px", "px").replace("_ppm", "ppm")
            if flat_files:
                source_filepath = os.path.join(source, file)
                dest_filepath = os.path.join(dest, file)
                os.makedirs(dest, exist_ok=True)
                os.rename(source_filepath, dest_filepath)
                continue
            # extract info from file
            attributes = get_attributes_from_filename(corrected_file)
            year = attributes["UID"].split("-")[-1]
            # Year_Location > Genotype > straightened masks
            location = attributes.get("Location", "missing_location")
            year_location = "_".join([year, location])

            # compose target
            # default
            if not dest:
                # move to sibling
                result_target = source.split(BINARY_MASKS_DIR)[0]

            else:
                result_target = os.path.join(dest, year_location)

                dirname = attributes.get(dest_dir_key, None)
                if dirname:
                    result_target = os.path.join(dest, year_location, dirname)

                    if dest_sub_key:
                        subdirname = attributes.get(dest_sub_key, None)
                        if subdirname:
                            result_target = os.path.join(
                                dest, year_location, dirname, subdirname
                            )

            # create target if it does not exist yet
            result_target = os.path.join(result_target, STRAIGHTENED_MASKS_DIR)
            os.makedirs(result_target, exist_ok=True)

            # move mask there
            source_filepath = os.path.join(source, file)
            dest_filepath = os.path.join(result_target, corrected_file)
            os.rename(source_filepath, dest_filepath)
            # shutil.copyfile(source_filepath, dest_filepath)


@click.command()
@click.option(
    "--dest",
    "-d",
    type=click.Path(),
    help="destination directory of straightened binary masks",
)
@click.option(
    "--destdir",
    default="Genotype",
    help="The key to be used to name the destination directory",
)
@click.option(
    "--destsub",
    default="",
    help="The key to be used to name the destination sub directory",
)
@click.option("--keep", is_flag=True, help="keep binary masks in source directory")
@click.option("--smoothen", is_flag=True, help="smoothen the mask")
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True),
    help="source directory of binary masks to process",
)
def run(dest, destdir, destsub, keep, smoothen, src):
    if not src:
        click.secho("No source specified. Use --src", fg="red")
        return

    subdirs = get_masks_to_process(src, BINARY_MASKS_DIR)

    # straighten masks
    with Pool(processes=cpu_count()) as pool:
        pool.starmap(straighten_binary_masks, [(dir["path"],) for dir in subdirs])

    if dest and not os.path.exists(dest):
        pathlib.Path(dest).mkdir(parents=True)

    # moving masks
    with Pool(processes=cpu_count()) as pool:
        pool.starmap(copy_results, [(dir["path"], dest) for dir in subdirs])


if __name__ == "__main__":
    os.environ["JAVA_TOOL_OPTIONS"] = "-Dapple.awt.UIElement=true"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run()
