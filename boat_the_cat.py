import os
import shutil
import click


WITH_TIPS = "with-tips"
WITHOUT_TIPS = "without-tips"
STRAIGHT_MASKS = "straight-masks"
FILE_SUFFIX = ".png"

broken_genotypes = [
    "Ames-29182",
    "B2566",
    "P6423",
    "PI-172890",
    "PI-182204",
    "PI-196847",
    "PI-234621",
    "PI-264235",
    "PI-294081",
    "PI-294083",
    "PI-294086",
    "PI-325993",
    "PI-341207",
    "PI-357982",
]
amount = 237


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
def run(src, dest):
    # src
    with_tips_src = os.path.join(src, WITH_TIPS)
    without_tips_src = os.path.join(src, WITHOUT_TIPS)

    # dest
    with_tips_dest = os.path.join(dest, WITH_TIPS)
    without_tips_dest = os.path.join(dest, WITHOUT_TIPS)

    genotypes = os.listdir(with_tips_src)

    for i, genotype in enumerate(genotypes):
        if genotype in broken_genotypes:
            continue

        if i >= amount - 1:
            break

        if genotype.startswith("."):
            continue

        # src image with tip
        mask_dir_with_tip_src = os.path.join(with_tips_src, genotype, STRAIGHT_MASKS)
        mask_with_tip_filename = [
            f
            for f in os.listdir(mask_dir_with_tip_src)
            if not f.startswith(".") and f.lower().endswith(FILE_SUFFIX)
        ][0]

        # src image without tip
        mask_dir_without_tip_src = os.path.join(
            without_tips_src, genotype, STRAIGHT_MASKS
        )
        mask_without_tip_filename = [
            f
            for f in os.listdir(mask_dir_without_tip_src)
            if not f.startswith(".") and f.lower().endswith(FILE_SUFFIX)
        ][0]

        # create dest dir
        mask_dir_with_tip_dest = os.path.join(with_tips_dest, genotype, STRAIGHT_MASKS)
        os.makedirs(mask_dir_with_tip_dest, exist_ok=True)

        mask_dir_without_tip_dest = os.path.join(
            without_tips_dest, genotype, STRAIGHT_MASKS
        )
        os.makedirs(mask_dir_without_tip_dest, exist_ok=True)

        # copy files
        mask_with_tip_src_image = os.path.join(
            mask_dir_with_tip_src, mask_with_tip_filename
        )
        mask_with_tip_dest_image = os.path.join(
            mask_dir_with_tip_dest, mask_with_tip_filename
        )
        print("copying ", mask_with_tip_src_image)
        shutil.copy(mask_with_tip_src_image, mask_with_tip_dest_image)

        mask_without_tip_src_image = os.path.join(
            mask_dir_without_tip_src, mask_without_tip_filename
        )
        mask_without_tip_dest_image = os.path.join(
            mask_dir_without_tip_dest, mask_without_tip_filename
        )

        print("copying ", mask_without_tip_src_image)
        shutil.copy(mask_without_tip_src_image, mask_without_tip_dest_image)


if __name__ == "__main__":
    run()
