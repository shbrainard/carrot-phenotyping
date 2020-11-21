from multiprocessing import Pool, cpu_count
import os
import pathlib
import shutil
import warnings

import click
import cv2

from lib.constants import BINARY_MASKS_DIR
from lib.crop import (
    binary_mask_parallel,
    mask_overlay_parallel,
    straighten_binary_masks,
)
from lib.utils import (
    clear_and_create,
    get_threshold_values,
    get_files_to_process,
    get_attributes_from_filename,
)


def copy_results(source, dest, dest_dir_key="Genotype", dest_sub_key=None):
    """
    move the straightened masks to their final destination

    Args:
        source (str): absolute path to the source directory
        dest (str): absolute path to the dest directory
        dest_dir_key (str): key to be used to name the directory
        dest_sub_key (str): key to be used to name the subdirectory
    """

    for file in os.listdir(source):
        corrected_file = file.replace("_px", "px").replace("_ppm", "ppm")
        # extract info from file
        attributes = get_attributes_from_filename(corrected_file)
        year = attributes["UID"].split("-")[-1]
        # Year_Location > Genotype > straightened masks
        location = attributes.get("Location", "missing_location")
        year_location = "_".join([year, location])

        # compose target
        # default
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
        result_target = os.path.join(result_target, BINARY_MASKS_DIR)
        os.makedirs(result_target, exist_ok=True)

        # move mask there
        source_filepath = os.path.join(source, file)
        dest_filepath = os.path.join(result_target, corrected_file)
        shutil.copyfile(source_filepath, dest_filepath)


def clear_intermediate_dir(dir):
    print(dir)


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
@click.option("--no-black-tape", is_flag=True, help="no black tape around carrot")
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
@click.option("--visualize", is_flag=True, help="create the mask overlay")
def run(dest, destdir, destsub, keep, no_black_tape, old, smoothen, src, visualize):
    if not src:
        click.secho("No source specified. Use --src", fg="red")
        return

    if dest and not os.path.exists(dest):
        pathlib.Path(dest).mkdir(parents=True)

    subdirs = get_files_to_process(src)

    if visualize is True:
        name = None
        clear = True
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(
                mask_overlay_parallel,
                [(dir, smoothen, old, clear, name, no_black_tape) for dir in subdirs],
            )
        return

    clear = True
    name = None
    with Pool(processes=cpu_count()) as pool:
        pool.starmap(
            binary_mask_parallel,
            [(dir, smoothen, old, clear, name, no_black_tape) for dir in subdirs],
        )

    # move result to final destination
    if dest:
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(
                copy_results,
                [
                    (
                        os.path.join(dir["path"], BINARY_MASKS_DIR),
                        dest,
                        destdir,
                        destsub,
                    )
                    for dir in subdirs
                ],
            )

    if dest and not keep:
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(
                shutil.rmtree,
                [(os.path.join(dir["path"], BINARY_MASKS_DIR),) for dir in subdirs],
            )


if __name__ == "__main__":
    os.environ["JAVA_TOOL_OPTIONS"] = "-Dapple.awt.UIElement=true"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run()
