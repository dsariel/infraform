# Copyright 2020 Arie Bregman
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import crayons
from difflib import SequenceMatcher
import jinja2 as j2
import logging
import os
import re

from infraform.exceptions import usage as usage_exc
from infraform.exceptions.utils import success_or_exit
from infraform import filters
from infraform.utils import get_file_content

LOG = logging.getLogger(__name__)


class Scenario(object):

    SCENARIOS_PATH = os.path.dirname(__file__) + '/scenarios'

    def __init__(self, name, variables):
        self.name = name
        self.variables = variables
        self.file_path, self.file_name = self.get_scenario_file_path_name(
            self.SCENARIOS_PATH, self.name)
        self.dir_path = os.path.dirname(self.file_path)
        self.dir_name = self.dir_path.split('/')[-1]

    @staticmethod
    def get_scenario_file_path_name(scenarios_dir_path, scenario_name):
        """Returns file name and path."""
        similar_scenarios = []
        for p, d, files in os.walk(scenarios_dir_path):
            for f in files:
                until_dot_pattern = re.compile(r"^[^.]*")
                file_without_suffix = re.search(until_dot_pattern, f).group(0)
                file_name = f
                if f.endswith('.j2'):
                    file_name = f[:-3]
                if file_without_suffix == scenario_name:
                    scenario_file_path = p + '/' + f
                    scenario_file = file_name
                    return scenario_file_path, scenario_file
                elif ".ifr" in f and SequenceMatcher(
                    None, file_without_suffix, scenario_name).ratio() >= 0.25:
                    similar_scenarios.append(file_without_suffix)
        if similar_scenarios:
            LOG.info("Perhaps you meant:\n\n{}".format(
                crayons.yellow("\n".join(similar_scenarios))))
        success_or_exit(1, usage_exc.missing_scenario(scenario_name))

    def render(self):
        """Render the scenario and save to disk."""
        # Create Jinja2 environment
        j2_env = j2.Environment(loader=j2.FunctionLoader(
            get_file_content), trim_blocks=True, undefined=j2.StrictUndefined)

        j2_env.filters['env_override'] = filters.env_override
        template = j2_env.get_template(self.file_path)

        try:
            rendered_scenario = template.render(vars=self.variables)
        except j2.exceptions.UndefinedError as e:
            LOG.error(e)
            missing_arg = re.findall(
                r'no attribute (.*)', e.message)[0].strip("'")
            LOG.error(usage_exc.missing_arg(missing_arg))
            sys.exit(2)
        self.write_rendered_scenario(rendered_scenario)

    def write_rendered_scenario(self, scenario):
        """Save the rendered scenario."""
        with open('./' + self.file_name, 'w+') as f:
            f.write(scenario)