from multiprocessing import Pool, cpu_count
import os
import pathlib
import shutil
import warnings

import click
import cv2

from lib.constants import BINARY_MASKS_DIR, METHODS, config
from lib.crop import (
    binary_mask_parallel,
    mask_overlay_parallel,
    straighten_binary_masks,
)
from lib.utils import (
    clear_and_create,
    get_threshold_values,
    get_attributes_from_filename,
)


def get_directories_of_interest(source_dir, key, value, allowed_methods=[]):
    """
    get the absolute paths of the raw files to process
    """
    dirs_of_interest = []
    for subdir, dirs, files in os.walk(source_dir):
        dirname = subdir.split("/")[-1].split("__")[0]
        if dirname not in METHODS or dirname in allowed_methods:
            for file_name in files:
                if (
                    file_name.endswith(config["file_format"])
                    and (not file_name.startswith("."))
                    and (key in file_name)
                    and (value in file_name)
                ):
                    # figure out relative path
                    dirs_of_interest.append(subdir)
                    break
    return dirs_of_interest


@click.command()
@click.option(
    "--dest", "-d", type=click.Path(), help="destination directory of files to copy"
)
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True),
    help="source directory of images to process",
)
@click.option("--key", default="", help="key to filter for")
@click.option("--value", default="", help="value to filter for")
def run(dest, src, key, value):
    if not src:
        click.secho("No source specified. Use --src", fg="red")
        return

    directories_of_interest = get_directories_of_interest(src, key, value)

    for directory in directories_of_interest:
        dir_name = directory.split("/")[-1]
        abs_dest = os.path.join(dest, dir_name)
        print(f"copy {directory} to {abs_dest}...")
        shutil.copytree(directory, abs_dest)
        for subdir, dirs, files in os.walk(abs_dest):
            for file_name in files:
                if f"{key}_{value}" not in file_name:
                    os.remove(os.path.join(subdir, file_name))


if __name__ == "__main__":
    run()
