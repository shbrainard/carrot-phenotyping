import click
import cv2
from joblib import dump, load
import plotly.graph_objects as go

from lib.tip_mask import tip_mask_ml
from lib.utils import get_attributes_from_filename, pixel_to_mm
from phenotype import get_length

from tipmask_train import get_mask_pairs


def get_histogram_data(src, diff_thresh=25):
    diff_too_big_count = 0
    total_count = 0
    regr = load("tip-mask-model.joblib")
    pairs = get_mask_pairs(src)
    data = []
    for pair in pairs:
        total_count += 1
        raw = pair["with-tips"]
        training = pair["without-tips"]

        raw_mask = cv2.imread(raw, cv2.IMREAD_GRAYSCALE)
        training_mask = cv2.imread(training, cv2.IMREAD_GRAYSCALE)

        attributes = get_attributes_from_filename(raw)
        scale = attributes.get("Scale", None)
        mm_per_px = pixel_to_mm(scale)

        tip_index = tip_mask_ml(raw_mask, regr, mm_per_px)

        detipped_length = get_length(training_mask)

        length_diff = round(tip_index[0]) - detipped_length

        if abs(length_diff) > diff_thresh:
            diff_too_big_count += 1
            raw_length = get_length(raw_mask)
            print(">>>>>>>>>>>>>>>>")
            print(f"tip mask diff > {diff_thresh} px", raw)
            print("with-tip -> without-tip diff: ", raw_length - detipped_length)
        data.append(length_diff)
    print(f"diff > {diff_thresh}px in {diff_too_big_count} out of {total_count} cases.")
    return data


@click.command()
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True),
    help="source directory of images to process",
)
@click.option("--diff", "-d", type=click.INT, help="difference threshold")
def run(src, diff):
    histogram_data = get_histogram_data(src, diff)
    fig = go.Figure(data=[go.Histogram(x=histogram_data)])
    fig.show()


if __name__ == "__main__":
    run()

