#
# -*- coding: utf-8 -*-
# Copyright 2023 Allied Telesis
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
The awplus rip fact class
It is in this file the configuration is collected from the device
for a given resource, parsed, and the facts tree is populated
based on the configuration.
"""
import re
from copy import deepcopy

from ansible_collections.ansible.netcommon.plugins.module_utils.network.common import (
    utils,
)
from ansible_collections.alliedtelesis.awplus.plugins.module_utils.network.awplus.argspec.rip.rip import RipArgs


class RipFacts(object):
    """ The awplus rip fact class
    """

    def __init__(self, module, subspec='config', options='options'):
        self._module = module
        self.argument_spec = RipArgs.argument_spec
        spec = deepcopy(self.argument_spec)
        if subspec:
            if options:
                facts_argument_spec = spec[subspec][options]
            else:
                facts_argument_spec = spec[subspec]
        else:
            facts_argument_spec = spec

        self.generated_spec = utils.generate_dict(facts_argument_spec)


    # Needs to be mockable for unit tests.
    @staticmethod
    def get_rip_config(connection):
        return connection.get("show running-config router rip").splitlines()

    def populate_facts(self, connection, ansible_facts, data=None):
        """ Populate the facts for rip
        :param connection: the device connection
        :param ansible_facts: Facts dictionary
        :param data: previously collected conf
        :rtype: dictionary
        :returns: facts
        """
        grc = self.get_rip_config(connection)

        config = deepcopy(self.generated_spec)
        config["neighbors"] = self.render_neighbors(grc)
        config["networks"] = self.render_networks(grc)
        config["passive_interfaces"] = self.render_passive_interfaces(grc)
        config.update(self.render_other(grc))

        config = utils.remove_empties(config)

        ansible_facts['ansible_network_resources'].pop('rip', None)

        facts = {'rip': config}
        ansible_facts['ansible_network_resources'].update(facts)

        return ansible_facts


    def render_neighbors(self, grc):
        """
        Get neighbor configuration
        IN: grc - splitlines output of "show running-config router rip"
        OUT: list of neighbors
        """
        n_list = []
        for l in grc:
            l = l.strip()
            match = re.search(r'neighbor (\S+)', l)
            if match:
                n_list.append(match.group(1))
        return n_list
    
    def render_networks(self, grc):
        """
        Get networks configuration
        IN: grc - splitlines output of "show running-config router rip"
        OUT: list of networks
        """
        n_list = []
        for l in grc:
            l = l.strip()
            match = re.search(r'network (\S+)', l)
            if match:
                n_list.append(match.group(1))
        return n_list

    def render_passive_interfaces(self, grc):
        """
        Get passive interfaces configuration
        IN: grc - splitlines output of "show running-config router rip"
        OUT: list of passive interfaces
        """
        pi_list = []
        for l in grc:
            l = l.strip()
            match = re.search(r'passive-interfaces (\S+)', l)
            if match:
                pi_list.append(match.group(1))
        return pi_list

    def render_other(self, grc):
        """
        Get other configuration
        IN: grc - splitlines output of "show running-config router rip"
        OUT: dict of other parameters
        """
        other_params = {
            "timers": {
                "routing_table_update": 30,
                "routing_table_timeout": 180,
                "garbage_collection": 120
            },
            "version": 2,
            "administrative_distance": {
                "global": 120
            }
        }

        # timers
        for l in grc:
            l = l.strip()
            match = re.search(r'timers (\d+)', l)
            if match:
                other_params["timers"]["routing_table_update"] = match.group(1)
                other_params["timers"]["routing_table_timeout"] = match.group(2)
                other_params["timers"]["garbage_collection"] = match.group(3)
        
        # version
        for l in grc:
            l = l.strip()
            match = re.search(r'version (\d+)', l)
            if match:
                other_params["version"] = match.group(1)
        
        # administrative distance
        for l in grc:
            l = l.strip()
            match = re.search(r'distance (\d+) (\S+)', l)
            if match:
                if match.group(2):
                    other_params["administrative_distance"][match.group(2)] = match.group(1)
                else:
                    other_params["administrative_distance"]["global"] = match.group(1)
