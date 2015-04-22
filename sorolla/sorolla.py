import subprocess
import math
import os
from pipes import quote
import platform


class Sorolla:
    """
    Main class which will launch ImageMagick commands to apply selected
    transformations to the given images.
    It needs ImageMagick & GhostScript installed in the system and in PATH
    to work properly
    """

    @staticmethod
    def scale_resource(source_file, dest_file, scale):
        """
        Scales a resource; detects if it's a nine-patch via filename in order
        to scale it properly

        Arguments:
            source_file Source file to convert. Path can be relative or
                        absolute
            dest_file   Destination file where the converted file will be
                        saved. Path can be relative or absolute
            scale       Scale value as a float. If it's greater than zero, the
                        function upscales the image; if less than zero,
                        it downscales the image

        Returns:
            Whether the action could be run or not
        """
        if not Sorolla._check_needed_commands:
            return False

        # Default base density in dpi, set by Imagemagick
        base_pdf_density_dpi = 72

        try:
            command = ""
            if ".9." not in source_file:
                # Not a resource identified as nine-patch
                density = int(scale * base_pdf_density_dpi)
                # Scales a vector resource to the desired density
                command = 'convert -background transparent -density {0} {1} {2}'
                command = command.format(
                    density,
                    Sorolla._shellquote(source_file),
                    Sorolla._shellquote(dest_file),
                )
            else:
                # Resource defined as nine-patch
                # Attributes used in Imagemagick command
                imagemagick_scale = scale * 100
                border_size = math.ceil(scale)

                # The following ImageMagick command works as follows (each step
                # generates a temporary image)
                #
                # 0. Tell convert the image that we're going to use, and that
                #    we want a transparent background
                # 1. Create a copy of (0) with our base density (72 DPI)
                # 2. Remove 9-patch border from (1) and replace it with
                #    color
                # 3. Mix (1) & (2) so that 9-patch borders are extracted from
                #    the transparent original image
                # 4. Resize (3) to 'imagemagick_scale'. We get scaled 9-patch
                #    borders, but there will be semi-transparent pixels
                # 5. Apply a threshold in (4)'s alpha channel so we can make
                #    semi-transparent pixels fully opaque
                # 6-7. Same process as in 2-3 to extract a bigger 9-patch
                #      border
                # 8-12. Process to adjust the 9-patch border in (7) so we don't
                #       leave extra space between the border & the image
                # 13. Create a raster of the original image (0), keeping
                #     original quality if PDF or SVG
                # 14. Remove 9-patch border of (13) depending on the scale used
                # 15. Merge (14) with (12) so we finally have the result
                #     9-patch for the given dpi scale
                # 16. Delete all generated files in each step
                #
                # There might be some pixel data loss in ldpi & hdpi
                # resolutions as they use float scales to resize the source
                # files
                #
                # In order to debug the process, copy the command to your
                # console, remove the 'delete' parenthesis block and add
                # '-append' before the destination file. This'll generate a
                # .png with all the image steps described by the commands

                command = 'convert {0} -background transparent '\
                    '\( +clone -density {1} \) '\
                    '\( +clone -shave 1x1 -bordercolor transparent -border 1x1 \) '\
                    '\( -clone 1 +clone -compose ChangeMask -composite -compose Over \) '\
                    '\( +clone -resize {2}%% \) '\
                    '\( +clone -channel A -threshold 50%% +channel \) '\
                    '\( +clone -shave 1x1 -bordercolor transparent -border 1x1 \) ' \
                    '\( -clone 5 +clone -compose ChangeMask -composite -compose Over \) '\
                    '\( -clone 7 -repage +{3}+0 -background none -flatten \) '\
                    '\( -clone 7 -repage +0+{3} -background none -flatten \) '\
                    '\( -clone 7 -repage -{3}+0 -background none -flatten \) '\
                    '\( -clone 7 -repage +0-{3} -background none -flatten \) '\
                    '\( -clone 8 -clone 9 -compose Over -composite -clone 10 -composite -clone 11 -composite -shave {3}x{3} \) '\
                    '\( -clone 0 -scale {2}% \) '\
                    '\( +clone -shave {4}x{4} -bordercolor transparent -border 1x1 \) '\
                    '\( +clone -clone 12 -composite \) '\
                    '\( -delete 0-14 \) '\
                    '{5}'.format(
                        Sorolla._shellquote(
                            os.path.abspath(source_file)),
                        base_pdf_density_dpi,
                        imagemagick_scale,
                        border_size - 1,
                        border_size,
                        Sorolla._shellquote(os.path.abspath(dest_file))
                    )

            return Sorolla._run_command(command)
        except Exception as e:
            print e.errno, e.strerror
            return False

    @staticmethod
    def color_resource(source_file, dest_file, fill_color):
        """
        Colors a raster resource; detects if it's a nine-patch via filename in
        order to scale it properly

        Arguments:
            source_file Source file to color. Path can be relative or
                        absolute
            dest_file   Destination file where the colored file will be
                        saved. Path can be relative or absolute
            fill_color  Color to fill the resource. Must be a RRGGBB string.

        Returns:
            Whether the action could be run or not
        """
        if not Sorolla._check_needed_commands:
            return False

        try:
            command = ""
            if ".9." not in source_file:
                # Not a resource identified as nine-patch
                command = 'convert -background transparent {0} +level-colors "#{1}", '\
                    '{2}'.format(
                        Sorolla._shellquote(
                            os.path.abspath(source_file)),
                        fill_color,
                        Sorolla._shellquote(os.path.abspath(dest_file)),
                    )
            else:
                # nine-patch
                command = 'convert -background transparent {0} '\
                    '\( +clone -shave 1x1 -bordercolor transparent -border 1x1 +level-colors "#{1}",  \) '\
                    '\( -clone 0 +clone -composite \) '\
                    '\( -delete 0-1 \) '\
                    '{2}'.format(
                        Sorolla._shellquote(
                            os.path.abspath(source_file)),
                        fill_color,
                        Sorolla._shellquote(os.path.abspath(dest_file))
                    )

            return Sorolla._run_command(command)
        except Exception as e:
            print e.value
            return False

    @staticmethod
    def tint_resource(source_file, dest_file, tint_color):
        """
        Tints a gray-scaled raster resource; detects if it's a nine-patch via
        filename in order to tint it properly

        Arguments:
            source_file Source file to tint. Path can be relative or
                        absolute
            dest_file   Destination file where the tinted file will be
                        saved. Path can be relative or absolute
            fill_color  Color to tint the resource. Must be a RRGGBB string.

        Returns:
            Whether the action could be run or not
        """
        if not Sorolla._check_needed_commands:
            return False

        try:
            command = ""
            if ".9." not in source_file:
                # Not a resource identified as nine-patch
                # Check http://www.imagemagick.org/Usage/color_mods/#tint_overlay
                command = 'convert -background transparent {0} '\
                    '\( +clone +matte -fill "#{1}" -colorize 100%% +clone +swap -compose overlay -composite \) '\
                    '-compose SrcIn -composite {2}'.format(
                        Sorolla._shellquote(
                            os.path.abspath(source_file)),
                        tint_color,
                        Sorolla._shellquote(os.path.abspath(dest_file))
                    )
            else:
                # nine-patch
                command = 'convert -background transparent {0} '\
                    '\( +clone -shave 1x1 -bordercolor transparent -border 1x1 \) '\
                    '\( +clone +matte -fill "#{1}" -colorize 100%% \) '\
                    '\( -clone 0 +clone -compose overlay -composite \) '\
                    '\( -clone 0 +clone -compose SrcIn -composite \) '\
                    '\( -delete 0-3 \) {2}'.format(
                        Sorolla._shellquote(
                            os.path.abspath(source_file)),
                        tint_color,
                        Sorolla._shellquote(os.path.abspath(dest_file))
                    )

            return Sorolla._run_command(command)
        except Exception as e:
            print e.value
            return False

    @staticmethod
    def _run_command(command):
        """
        Runs a given ImageMagick command
        """
        # Windows check; remove escape sequences from parentheses so cmd can
        # properly launch the command
        if Sorolla._is_windows():
            command = command.replace('\\(', '(').replace('\\)', ')')

        return subprocess.call(command, shell=True) == 0

    @staticmethod
    def _shellquote(s):
        """
        Util method to escape data in order to use it in shell commands
        """
        # return "'" + s.replace("'", "'\\''") + "'"
        # Windows check
        if not Sorolla._is_windows():
            return quote(s)
        else:
            return '"{0}"'.format(s)

    @staticmethod
    def _check_command(command, args=[]):
        """
        Checks if a command can be executed in the file-system
        """
        devnull = open(os.devnull, 'w')
        try:
            status = subprocess.call(
                [command] + args, stdout=devnull, stderr=devnull)
            return status == 0
        except Exception as e:
            print e
            return False

    @staticmethod
    def _check_needed_commands():
        """
        Check needed commands: ImageMagick's convert & GhostScript
        """
        # Imagemagick check
        if not Sorolla._check_command("convert"):
            print "Imagemagick is not installed"
            return False
        # Ghostscript check
        if not Sorolla._check_command("gs", ["-version"]):
            print "GhostScript is not installed"
            return False

        return True

    @staticmethod
    def _is_windows():
        """
        Check if the current platform is Windows
        """
        return platform.uname()[0].find("Win") != -1
