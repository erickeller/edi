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

from edi.lib.helpers import FatalError
from edi.commands.config import Config


class Ssh(Config):

    @classmethod
    def advertise(cls, subparsers):
        help_text = "generate ssh keys"
        description_text = "Generate ssh keys."
        parser = subparsers.add_parser(cls._get_short_command_name(),
                                       help=help_text,
                                       description=description_text)
        cls._require_config_file(parser)

    def run_cli(self, cli_args):
        results = self.run(cli_args.config_file)
        print("Generated {0}.".format(results))

    def run(self, config_file):
        self._setup_parser(config_file)
        raise FatalError('The command to generate ssh keys is not yet implemented.')

    def clean(self, config_file):
        self._setup_parser(config_file)
