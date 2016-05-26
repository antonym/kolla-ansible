#!/usr/bin/python

# Copyright 2015 Sam Yaple
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ConfigParser import ConfigParser
from cStringIO import StringIO
import os

from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):

    TRANSFERS_FILES = True

    def read_config(self, source, config):
        # Only use config if present
        if os.access(source, os.R_OK):
            with open(source, 'r') as f:
                template_data = f.read()
            result = self._templar.template(template_data)
            fakefile = StringIO(result)
            config.readfp(fakefile)
            fakefile.close()

    def run(self, tmp=None, task_vars=None):

        if task_vars is None:
            task_vars = dict()
        result = super(ActionModule, self).run(tmp, task_vars)

        if not tmp:
            tmp = self._make_tmp_path()

        sources = self._task.args.get('sources', None)
        extra_vars = self._task.args.get('vars', list())

        if not isinstance(sources, list):
            sources = [sources]

        temp_vars = task_vars.copy()
        temp_vars.update(extra_vars)

        config = ConfigParser()
        old_vars = self._templar._available_variables
        self._templar.set_available_variables(temp_vars)

        for source in sources:
            self.read_config(source, config)

        self._templar.set_available_variables(old_vars)
        # Dump configparser to string via an emulated file

        fakefile = StringIO()
        config.write(fakefile)

        remote_path = self._connection._shell.join_path(tmp, 'src')
        xfered = self._transfer_data(remote_path, fakefile.getvalue())
        fakefile.close()

        new_module_args = self._task.args.copy()
        del new_module_args['vars']
        del new_module_args['sources']

        new_module_args.update(
            dict(
                src=xfered
            )
        )

        result.update(self._execute_module(module_name='copy',
                                           module_args=new_module_args,
                                           task_vars=task_vars,
                                           tmp=tmp))
        return result
