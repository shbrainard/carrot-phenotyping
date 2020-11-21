# changelog

## 2018.10.29
* make sure the images from this other dataset can be processed.

## 2018.10.22
* improve blue line cropping

## 2018.10.17
* directory and subdirectory for final masks configurable
* add --uid-insert argument to append.py

## 2018.10.15
* improve qr code scanning
* fix post straightening edge case bug
* rotate images so that qr code is always on the right

## 2018.09.22
* improve cropping of the frame that the carrot is in

## 2018.09.21
* fix whitespace problem when reading data from csv

## 2018.08.24
* rotate images if needed
* convert px to mm
* fix timezone issue

## 2018.08.22
* autodetect backdrop color
* acquire script is more resilient in finding the boxes
* "carrots" is the default database name
* tip biomass gets always appended to filename
* all photos are enumerated ({Photo_n})

## 2018.08.17
* visualize.py script for all the visualizations
* do masking from mask.py script

## 2018.08.10
* integrate tip masking with binary_mask method
* add collection argument to phenotype script
* calculate length and biomass of masked tip

## 2018.08.09
* acquisition pipeline established

## 2018.08.07
* images with black backdrop can be processed using the `-b black` argument.
* tip masking WIP in master branch
* clean up the code
* shoulder phenotype heuristic

## 2018.08.02
* improve scalebar detection of old images

## 2018.08.01
* add -nk option to append.py script
* add explicit -dk option to append.py script

## 2018.07.23
* move straightened masks to output directory
* add "keep" argument to crop.py script
* add csv-to-mongo functionality

## 2018.07.17

* file name altering
* minor refactorings

## 2018.07.10

* mask overlay --> blue
* improve black tape cropping
* `--name` or `-n` argument --> alternative output name
* make sure the shoulders are symmetrical

## 2018.07.03

* very verbose description of what the script is doing

## 2018.07.02

* everything gets straightened again
* coloured console output for better readability
* auto-minimizing (no need for the --minimize flag anymore. As a matter of fact, it no longer exists)
* post straightening cropping to trim excess black area
