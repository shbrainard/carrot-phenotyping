from lib.crop import crop_left_of_blue_line_hsv
from lib.utils import get_files_to_process, read_file, write_file, detect_backdrop

import click


@click.command()
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True),
    help="source directory of images to process",
)
def run(src):
    subdirs = get_files_to_process(src)
    # print(subdirs)
    for dir in subdirs:
        for file in dir["files"]:
            image = read_file(file)
            backdrop = detect_backdrop(image)
            crop = crop_left_of_blue_line_hsv(image, backdrop=backdrop, visualize=True)
            filename = file.split("/")[-1]
            write_file(crop, "/Users/creimers/Downloads", filename)


if __name__ == "__main__":
    run()
