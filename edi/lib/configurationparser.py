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

import yaml
import collections
from jinja2 import Template
import os
from os.path import dirname, abspath, basename, splitext, isfile, join
import logging
from edi.lib.helpers import (get_user, get_user_gid, get_user_uid,
                             get_hostname, get_edi_plugin_directory, FatalError)
from edi.lib.versionhelpers import get_edi_version, get_stripped_version
from edi.lib.shellhelpers import get_user_environment_variable
from packaging.version import Version


def get_base_dictionary():
    base_dict = {}
    current_user_name = get_user()
    base_dict["edi_current_user_name"] = current_user_name
    base_dict["edi_current_user_uid"] = get_user_uid()
    base_dict["edi_current_user_gid"] = get_user_gid()
    base_dict["edi_current_user_host_home_directory"] = get_user_environment_variable("HOME")
    base_dict["edi_current_user_target_home_directory"] = "/home/{}".format(current_user_name)
    base_dict["edi_host_hostname"] = get_hostname()
    base_dict["edi_edi_plugin_directory"] = get_edi_plugin_directory()
    base_dict["edi_host_http_proxy"] = get_user_environment_variable('http_proxy', '')
    base_dict["edi_host_https_proxy"] = get_user_environment_variable('https_proxy', '')
    base_dict["edi_host_ftp_proxy"] = get_user_environment_variable('ftp_proxy', '')
    base_dict["edi_host_socks_proxy"] = get_user_environment_variable('all_proxy', '')
    base_dict["edi_host_no_proxy"] = get_user_environment_variable('no_proxy', '')
    return base_dict


class ConfigurationParser():

    # shared data for all configuration parsers
    _configurations = {}

    def dump(self):
        return yaml.dump(self._get_config(), default_flow_style=False)

    def get_project_name(self):
        return self.config_id

    def get_workdir(self):
        # we might want to overwrite it by a config setting
        return os.getcwd()

    def get_bootstrap_repository(self):
        return self._get_bootstrap_item("repository", None)

    def get_bootstrap_architecture(self):
        return self._get_bootstrap_item("architecture", None)

    def get_bootstrap_tool(self):
        return self._get_bootstrap_item("tool", "debootstrap")

    def get_bootstrap_repository_key(self):
        return self._get_bootstrap_item("repository_key", None)

    def get_qemu_repository(self):
        return self._get_qemu_item("repository", None)

    def get_qemu_package_name(self):
        return self._get_qemu_item("package", "qemu-user-static")

    def get_qemu_repository_key(self):
        return self._get_qemu_item("repository_key", None)

    def get_compression(self):
        return self._get_general_item("edi_compression", "xz")

    def get_ordered_path_items(self, section):
        citems = self._get_config().get(section, {})
        ordered_items = collections.OrderedDict(sorted(citems.items()))
        item_list = []
        for name, content in ordered_items.items():
            if not content.get("skip", False):
                path = content.get("path", None)
                if not path:
                    raise FatalError(("Missing path item in section '{}' for '{}'."
                                      ).format(section, name))
                resolved_path = self._resolve_path(path)
                node_dict = self._get_node_dictionary(content)
                item_list.append((name, resolved_path, node_dict))
            else:
                logging.debug("Skipping named item '{}' from section '{}'.".format(name, section))

        return item_list

    def get_ordered_raw_items(self, section):
        citems = self._get_config().get(section, {})
        ordered_items = collections.OrderedDict(sorted(citems.items()))
        item_list = []
        for name, content in ordered_items.items():
            if not content.get("skip", False):
                node_dict = self._get_node_dictionary(content)
                item_list.append((name, content, node_dict))
            else:
                logging.debug("Skipping named item '{}' from section '{}'.".format(name, section))

        return item_list

    def get_project_plugin_directory(self):
        return join(self.config_directory, "plugins")

    def __init__(self, base_config_file):
        self.config_directory = dirname(abspath(base_config_file.name))
        self.config_id = splitext(basename(base_config_file.name))[0]
        if not ConfigurationParser._configurations.get(self.config_id):
            logging.info(("Load time dictionary:\n{}"
                          ).format(yaml.dump(self._get_load_time_dictionary(),
                                             default_flow_style=False)))
            logging.info(("Using base configuration file '{0}'"
                          ).format(base_config_file.name))
            base_config = self._get_base_config(base_config_file)
            global_config = self._get_overlay_config(base_config_file,
                                                     "global")
            system_config = self._get_overlay_config(base_config_file,
                                                     get_hostname())
            user_config = self._get_overlay_config(base_config_file,
                                                   get_user())

            merge_1 = self._merge_configurations(base_config, global_config)
            merge_2 = self._merge_configurations(merge_1, system_config)
            merged_config = self._merge_configurations(merge_2, user_config)

            ConfigurationParser._configurations[self.config_id] = merged_config
            logging.info("Merged configuration:\n{0}".format(self.dump()))

            self._verify_version_compatibility()

    def _verify_version_compatibility(self):
        current_version = get_edi_version()
        required_version = str(self._get_general_item('edi_required_minimal_edi_version', current_version))
        if Version(get_stripped_version(current_version)) < Version(get_stripped_version(required_version)):
            raise FatalError(('The current configuration requires a newer version of edi (>={}).\n'
                              'Please update your edi installation!'
                              ).format(get_stripped_version(required_version)))

    def _get_config(self):
        return ConfigurationParser._configurations.get(self.config_id, {})

    def _parse_jina2_file(self, config_file):
        template = Template(config_file.read())
        return template.render(self._get_load_time_dictionary())

    def _get_base_config(self, config_file):
        return yaml.load(self._parse_jina2_file(config_file)) or {}

    def _get_overlay_config(self, base_config_file, overlay_name):
        fname, extension = splitext(basename(base_config_file.name))
        directory = dirname(base_config_file.name)
        overlay_file = "{0}.{1}{2}".format(fname, overlay_name,
                                           extension)
        overlay = join(directory, "configuration", "overlay",
                       overlay_file)
        if isfile(overlay) and os.access(overlay, os.R_OK):
            with open(overlay, encoding="UTF-8", mode="r") as config_file:
                logging.info(("Using overlay configuration file '{0}'"
                              ).format(config_file.name))
                return yaml.load(self._parse_jina2_file(config_file))
        else:
            return {}

    def _merge_configurations(self, base, overlay):
        merged_config = {}

        elements = ["general", "bootstrap", "qemu"]
        for element in elements:
            merged_config[element
                          ] = self._merge_key_value_node(base, overlay,
                                                         element)

        nested_elements = ["playbooks", "keys", "lxc_templates",
                           "lxc_profiles", "shared_folders"]
        for element in nested_elements:
            merged_config[element
                          ] = self._merge_nested_node(base, overlay,
                                                      element)
        return merged_config

    def _merge_key_value_node(self, base, overlay, node_name):
        base_node = base.get(node_name, {})
        overlay_node = overlay.get(node_name, {})
        if base_node is None and overlay_node is None:
            return {}
        if base_node is None:
            return overlay_node
        if overlay_node is None:
            return base_node
        return dict(base_node, **overlay_node)

    def _merge_nested_node(self, base, overlay, node):
        merged_node = self._merge_key_value_node(base, overlay,
                                                 node)

        for key, _ in merged_node.items():
            base_node = base.get(node, {})
            overlay_node = overlay.get(node, {})
            merged_node[key] = self._merge_key_value_node(base_node,
                                                          overlay_node,
                                                          key)

            element = "parameters"
            base_params = base_node.get(key, {})
            overlay_params = overlay_node.get(key, {})
            merged_params = self._merge_key_value_node(base_params,
                                                       overlay_params,
                                                       element)
            if merged_params:
                merged_node[key][element] = merged_params

        return merged_node

    def _get_bootstrap_item(self, item, default):
        return self._get_config().get("bootstrap", {}
                                      ).get(item, default)

    def _get_qemu_item(self, item, default):
        return self._get_config().get("qemu", {}
                                      ).get(item, default)

    def _get_general_item(self, item, default):
        return self._get_config().get("general", {}
                                      ).get(item, default)

    def _get_load_time_dictionary(self):
        load_dict = get_base_dictionary()
        load_dict["edi_work_directory"] = self.get_workdir()
        load_dict["edi_config_directory"] = self.config_directory
        load_dict["edi_project_plugin_directory"] = self.get_project_plugin_directory()
        return load_dict

    def _get_node_dictionary(self, node):
        node_dict = self._get_load_time_dictionary()

        node_dict["edi_lxc_network_interface_name"] = self._get_general_item("edi_lxc_network_interface_name",
                                                                             "lxcif0")
        node_dict["edi_config_management_user_name"] = self._get_general_item("edi_config_management_user_name",
                                                                              "edicfgmgmt")

        parameters = node.get("parameters", None)

        if parameters:
            return dict(node_dict, **parameters)

        return node_dict

    def _resolve_path(self, path):
        if os.path.isabs(path):
            if not os.path.isfile(path):
                raise FatalError(("'{}' does not exist."
                                  ).format(path))
            return path
        else:
            locations = [self.get_project_plugin_directory(), get_edi_plugin_directory()]

            for location in locations:
                abspath = os.path.join(location, path)
                if os.path.isfile(abspath):
                    return abspath

            raise FatalError(("'{0}' not found in the "
                              "following locations:\n{1}"
                              ).format(path, "\n".join(locations)))
