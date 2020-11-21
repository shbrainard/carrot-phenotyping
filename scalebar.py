from multiprocessing import Pool, cpu_count
import warnings

import click

from lib.scalebar import measure_scalebar
from lib.utils import get_files_to_process


@click.command()
@click.option("--old", is_flag=True, help="the old pictures")
@click.option("--src", "-s", type=click.Path(exists=True), help="source file")
def run(old, src):
    if src:
        click.secho("Measuring scalebars...", fg="white")
        subdirs = get_files_to_process(src)
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(measure_scalebar, [(dir, old) for dir in subdirs])
        click.secho("Done!", fg="green")

    else:
        click.secho("no source", fg="red")


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run()
