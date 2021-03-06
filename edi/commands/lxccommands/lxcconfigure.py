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

from edi.commands.lxc import Lxc
from edi.commands.lxccommands.profile import Profile
from edi.commands.lxccommands.launch import Launch
from edi.lib.playbookrunner import PlaybookRunner
from edi.lib.helpers import print_success
from edi.lib.shellhelpers import run
from edi.lib.sharedfoldercoordinator import SharedFolderCoordinator


class Configure(Lxc):

    @classmethod
    def advertise(cls, subparsers):
        help_text = "configure an edi LXC container"
        description_text = "Configure an edi LXC container."
        parser = subparsers.add_parser(cls._get_short_command_name(),
                                       help=help_text,
                                       description=description_text)
        parser.add_argument('container_name')
        cls._require_config_file(parser)

    def run_cli(self, cli_args):
        self.run(cli_args.container_name, cli_args.config_file)

    def run(self, container_name, config_file):
        self._setup_parser(config_file)
        self.container_name = container_name

        Launch().run(container_name, config_file)

        print("Going to configure container {} - be patient.".format(self._result()))

        playbook_runner = PlaybookRunner(self.config, self._result(), "lxd")
        playbook_runner.run_all()

        sfc = SharedFolderCoordinator(self.config)
        sfc.create_host_folders()
        sfc.verify_container_mountpoints(container_name)

        profiles = Profile().run(config_file, include_post_config_profiles=True)
        # TODO: stop container if profiles need to be updated
        self._apply_lxc_profiles(container_name, profiles)
        # TODO: restart container if needed

        print_success("Configured container {}.".format(self._result()))
        return self._result()

    def _result(self):
        return self.container_name

    @staticmethod
    def _apply_lxc_profiles(container_name, profiles):
        cmd = ['lxc', 'profile', 'apply', container_name, ','.join(profiles)]
        run(cmd)
