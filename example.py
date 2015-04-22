#!/usr/bin/env python

"""
Script that colorizes, scales & tints Android resources, returning a
ready-to-copy resources folder.
Relies in ImageMagick commands, so it needs to be installed for this script
to work.
It will also need GhostScript libs installed to work with .pdf files
For more data in ImageMagick color mods,
check: http://www.imagemagick.org/Usage/color_mods/

To use the script, use the following syntax:
script.py source_res_folder destination_res_folder rgb_hex_color_without_#

The source resource directory must contain the following folders:
- drawable -> Folder that contains the assets that must be scaled & colorized
  with solid color. It can also include nine-patches whose file name follows
  the convention: filename.9.ext where 'ext' is your file extension: pdf,
  svg...
- drawable-<dpi_string> -> Folder that contains assets that must be tinted,
  but are already scaled (for our use case, gray-scaled .9.png)

The preferred way to work with scalable files is to export them as PDF or SVG
files. The PDF or SVG file must be exported from a canvas with 72 dpi & for
mdpi screen density.
"""

import os
import re
import sys
from sorolla import Sorolla

"""
Available resolution dirs & scales; we'll use mdpi as the base resolution.
xxxdpi is not included yet, as it's just needed for launcher icon:
http://developer.android.com/guide/practices/screens_support.html#xxxhdpi-note
"""
AVAILABLE_RESOLUTION_SCALES = {
    'ldpi': 0.75,
    'mdpi': 1,
    'hdpi': 1.5,
    'xhdpi': 2,
    'xxhdpi': 3
}


def _create_folders_if_needed(destination_dir):
    """
    Creates needed folders for the script to work
    """

    for res, scale in AVAILABLE_RESOLUTION_SCALES.iteritems():
        folder = os.path.join(destination_dir,
                              "drawable-{0}".format(res))
        if not os.path.isdir(folder):
            os.makedirs(folder)


def _scale_and_color_resources(source_dir, destination_dir, fill_color):
    """
    Scans through the drawable folder of 'source_dir' and tries to color
    and scale every resource found there with the given color
    """

    drawable_res_dir = os.path.join(source_dir, "drawable")
    if os.path.isdir(drawable_res_dir):
        for filename in os.listdir(drawable_res_dir):
            filename_without_ext = filename[:-4]
            for res, scale in AVAILABLE_RESOLUTION_SCALES.iteritems():
                original_file = os.path.join(drawable_res_dir, filename)
                scaled_file = os.path.join(
                    destination_dir, "drawable-{0}".format(res),
                    "{0}_scaled.png".format(filename_without_ext)
                    )
                # Replace badly formatted nine-patch name so Imagemagick can
                # properly convert the resource to PNG
                if ".9_scaled" in scaled_file:
                    scaled_file = scaled_file.replace(".9_scaled", "_scaled.9")
                generated_file = os.path.join(
                    destination_dir, "drawable-{0}".format(res),
                    "{0}.png".format(filename_without_ext)
                    )
                Sorolla.scale_resource(
                    original_file, scaled_file, scale)
                Sorolla.color_resource(
                    scaled_file, generated_file, fill_color)
                os.remove(scaled_file)
    else:
        print("No drawable folder in {0}. Skipping...".format(source_dir))


def _tint_resources(source_dir, destination_dir, tint_color):
    """
    Scans through the 'drawable-<dpi_string>' folders of 'source_dir' and tries
    to tint gray-scaled resources
    """

    for res, scale in AVAILABLE_RESOLUTION_SCALES.iteritems():
        drawable_res_dir = os.path.join(
            source_dir, "drawable-{0}".format(res))
        if os.path.isdir(drawable_res_dir):
            for filename in os.listdir(drawable_res_dir):
                filename_without_ext = filename[:-4]
                original_file = os.path.join(drawable_res_dir, filename)
                generated_file = os.path.join(
                    destination_dir, "drawable-{0}".format(res),
                    "{0}.png".format(filename_without_ext)
                    )

                Sorolla.tint_resource(
                    original_file, generated_file, tint_color)
        else:
            print "No drawable-{0} folder in {1}. Skipping...".format(
                res, source_dir)


def _check_args(source_dir, base_color):
    """
    Checks if the needed arguments are valid
    """

    # Check input parameters
    if not os.path.isdir(source_dir):
        print "The source dir is not valid or it doesn't exist"
        return False
    elif not re.match("[0-9,a-f,A-F]{6}", base_color):
        print "The color string must have the following format: RRGGBB"
        return False
    return True


def main(args):
    """
    Main method. It receives three arguments: source folder, destination folder
    & RGB hex color (without #)
    """

    source_dir = os.path.abspath(args[0])
    destination_dir = os.path.abspath(args[1])
    base_color = args[2]

    if not _check_args(source_dir, base_color):
        sys.exit(1)

    if _create_folders_if_needed(destination_dir):
        print "Can't create destination folder. Is the path valid?"
        sys.exit(1)

    print "Scaling & coloring 'drawable' resources..."
    _scale_and_color_resources(source_dir, destination_dir, base_color)
    print "Tinting 'drawable-<dpi_string>' resources..."
    _tint_resources(source_dir, destination_dir, base_color)


if __name__ == "__main__":
    if ((len(sys.argv) > 1) and (len(sys.argv[1:]) == 3)):
        main(sys.argv[1:])
    else:
        print 'usage: {0} res_src_dir res_dest_dir rgb_hex_color'.format(
            sys.argv[0])
