# carrots

## install

These scripts require `python>=3.6.`.

The following dependencies need to be installed with `brew` on macOS:

1. `mongodb`
2. `zbar`

Then:

Run `make install` in a terminal window at the root of the project.

### activate virtual python environment

Run `. ./env/bin/activate` from the same terminal window.

### deactivate virtual python environment

Run `deactivate` from the same terminal window.

## features

### binary masks

Run `python mask.py --help` to see what kind of commands you can run and what kind of flags you can use.

### straightened masks

Run `python straighten.py --help` to see what kind of commands you can run and what kind of flags you can use.

### detip masks

Run `python tipmask.py --help` to see what kind of commands you can run and what kind of flags you can use.

### altering filenames

Run `python append.py --help` to see what kind of options you can use.

- supply `-k` and `-v`: appends the key/value pair to the filename
- supply `-k` and `-v` where `k` already exists: overrides the key/value pair in the filename
- supply `-dk`: removes the key/value pair from the filename
- supply `-k` and `-nk`: overrides 'key' with 'new key'

### visualizations

Run `python visualize.py --help` to see what kind of options you can use.

### phenotyping and storage in mongodb

Run `python phenotype.py --help` to see what kind of options you can use.

### acquisition pipeline

Run `python acquire.py --help` to see what kind of options you can use.

Run `make acquisition-preview tmp=/path/to/tmp/folder` to fire up the acquisition preview.

## Connect to MongoDB from R-Studio

full mongolite documentation [here](https://jeroen.github.io/mongolite/)

1. install mongolite:

   `install.packages("mongolite")`

2. load package

   `library(mongolite)`

3. connect to database / collection

   `m <- mongo(collection = "test_collection", db = "test_database", url = "mongodb://localhost/")`

4. fire up a query

   `m$find("{}")` --> will return all documents from the collection

## `config.json`

The follwing configurations can be made in the `config.json` file:

- `scalebar_length` - the length of the scalebar in mm.
- `camera_maker` - the name of the camera maker. Run `config.py --cameras` to get a list of available cameras.
- `camera_model` - the name of the camera model.
- `lens_maker` - the name of the lens maker. Run `config.py --lenses` to get a list of available lenses.
- `lens_model` - the name of the lens model
- `file_format` - the format of the file. Defaults to `.png`.
