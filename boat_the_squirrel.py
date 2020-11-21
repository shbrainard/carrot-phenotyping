"""
This sonofabitch script 
"""
import csv
import os
import shutil
import click


STRAIGHT_MASKS = "binary-masks"
FILE_SUFFIX = ".png"


@click.command()
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True),
    help="source directory of images to process",
)
@click.option(
    "--dest",
    "-d",
    type=click.Path(exists=True),
    help="dest directory of images to process",
)
@click.option(
    "--curate",
    "-c",
    is_flag=True,
    help="if selected, read in exclude.csv file (should be on the src PATH), and exclude files identified in the various columns for binary, straight and de-tipped",
)
@click.option(
    "--type",
    "-y",
    type=click.Choice(["binary", "straight", "de-tipped"]),
    help="identifies which sub-folders to grab (and thereby which columns of exclude.csv to use).  Can accept multiple values separated with commas (or something) if you want to transfer multiple image types",
)
def run(src, dest, curate, type):
    print("🚢  the  🐿   digs  🥕")
    curate_mapping = None
    if curate:
        curate_mapping = {}
        with open(
            os.path.join(src, "exclude.csv"), mode="r", encoding="utf-8-sig"
        ) as f:
            reader = csv.reader(f, dialect="excel")
            lines_read = 0
            for row in reader:
                lines_read += 1
                if lines_read > 1:
                    curate_mapping[row[0]] = {
                        "uid": row[1],
                        "photo": row[2],
                        "binary": row[3] == "1",
                        "straight": row[4] == "1",
                        "detipped": row[5] == "1",
                    }

    genotypes = os.listdir(src)

    for i, genotype in enumerate(genotypes):

        if genotype.startswith("."):
            continue

        # src image
        mask_dir_src = os.path.join(src, genotype, STRAIGHT_MASKS)
        mask_filenames = [
            f
            for f in os.listdir(mask_dir_src)
            if not f.startswith(".") and f.lower().endswith(FILE_SUFFIX)
        ]

        # create dest dir
        mask_dir_dest = os.path.join(dest, genotype, STRAIGHT_MASKS)
        os.makedirs(mask_dir_dest, exist_ok=True)

        # copy files
        for mask_filename in mask_filenames:
            mask_src_image = os.path.join(mask_dir_src, mask_filename)
            mask_dest_image = os.path.join(mask_dir_dest, mask_filename)
            print("copying ", mask_src_image)
            shutil.copy(mask_src_image, mask_dest_image)


if __name__ == "__main__":
    run()
