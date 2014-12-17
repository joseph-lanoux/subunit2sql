# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy
import functools
import sys

from oslo.config import cfg
import subunit
from subunit import iso8601

from subunit2sql.db import api
from subunit2sql import shell

STATUS_CODES = frozenset([
    'exists',
    'fail',
    'skip',
    'success',
    'uxsuccess',
    'xfail',
])

CONF = cfg.CONF

SHELL_OPTS = [
    cfg.StrOpt('run_id', required=True, positional=True,
               help='Run id to use for creating a subunit stream'),
    cfg.StrOpt('out_path', short='o', default=None,
               help='Path to write the subunit stream output, if none '
                    'is specified STDOUT will be used')
]


def cli_opts():
    for opt in SHELL_OPTS:
        cfg.CONF.register_cli_opt(opt)


def convert_datetime(timestamp):
    tz_timestamp = timestamp.replace(tzinfo=iso8601.UTC)
    return tz_timestamp


def write_test(output, start_time, stop_time, status, test_id, metadatas):
    write_status = output.status
    if 'tags' in metadatas:
        tags = metadatas['tags']
        write_status = functools.partial(write_status,
                                         test_tags=tags.split(','))
    start_time = convert_datetime(start_time)
    write_status = functools.partial(write_status,
                                     timestamp=start_time)
    write_status = functools.partial(write_status, test_id=test_id)
    if status in STATUS_CODES:
        write_status = functools.partial(write_status,
                                         test_status=status)
    write_status = functools.partial(write_status,
                                     timestamp=convert_datetime(stop_time))
    write_status()


def sql2subunit(run_id, output=sys.stdout):
    session = api.get_session()
    test_runs = api.get_tests_run_dicts_from_run_id(run_id, session)
    session.close()
    output = subunit.v2.StreamResultToBytes(output)
    output.startTestRun()
    for test_id in test_runs:
        test = test_runs[test_id]
        write_test(output, test['start_time'], test['stop_time'],
                   test['status'], test_id, test['metadata'])
    output.stopTestRun()


def list_opts():
    opt_list = copy.deepcopy(SHELL_OPTS)
    return [('DEFAULT', opt_list)]


def main():
    cli_opts()
    shell.parse_args(sys.argv)
    if CONF.out_path:
        fd = open(CONF.out_path, 'w')
    else:
        fd = sys.stdout
    sql2subunit(CONF.run_id, fd)
    if CONF.out_path:
        fd.close()

if __name__ == "__main__":
    sys.exit(main())
