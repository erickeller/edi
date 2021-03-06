# -*- coding: utf-8 -*-
# Copyright (C) 2016 Matthias Luescher
#
# Authors:
#  Matthias Luescher
#
# This file is part of edi.
#
# edi is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# edi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with edi.  If not, see <http://www.gnu.org/licenses/>.

import logging
import subprocess
from edi.commands.lxc import Lxc
from edi.commands.imagecommands.imagelxc import Lxc as LxcImageCommand
from edi.lib.shellhelpers import run
from edi.lib.helpers import print_success


class Import(Lxc):

    @classmethod
    def advertise(cls, subparsers):
        help_text = "import an edi image into the LXD image store"
        description_text = "Import an edi image into the LXD image store."
        parser = subparsers.add_parser(cls._get_short_command_name(),
                                       help=help_text,
                                       description=description_text)
        cls._require_config_file(parser)

    def run_cli(self, cli_args):
        self.run(cli_args.config_file)

    def run(self, config_file):
        self._setup_parser(config_file)

        if self._is_in_image_store():
            logging.info(("{0} is already in image store. "
                          "Delete it to regenerate it."
                          ).format(self._result()))
            return self._result()

        image = LxcImageCommand().run(config_file)

        print("Going to import lxc image into image store.")

        self._import_image(image)

        print_success("Imported lxc image into image store as {}.".format(self._result()))

        return self._result()

    def clean(self, config_file):
        self._setup_parser(config_file)

        if self._is_in_image_store():
            logging.info(("Removing '{}' from image store."
                          ).format(self._result()))
            self._delete_image()
            print_success("Removed {} from image store.".format(self._result()))

    def _result(self):
        return "{}_{}".format(self.config.get_project_name(),
                              self._get_command_file_name_prefix())

    def _is_in_image_store(self):
        cmd = []
        cmd.append("lxc")
        cmd.append("image")
        cmd.append("show")
        cmd.append("local:{}".format(self._result()))
        result = run(cmd, check=False, stderr=subprocess.PIPE)
        return result.returncode == 0

    def _import_image(self, image):
        cmd = []
        cmd.append("lxc")
        cmd.append("image")
        cmd.append("import")
        cmd.append(image)
        cmd.append("local:")
        cmd.extend(["--alias", self._result()])
        run(cmd)

    def _delete_image(self):
        cmd = []
        cmd.append("lxc")
        cmd.append("image")
        cmd.append("delete")
        cmd.append("local:{}".format(self._result()))
        run(cmd)
