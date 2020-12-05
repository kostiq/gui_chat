import asyncio
import re
from contextlib import asynccontextmanager

import configargparse


@asynccontextmanager
async def open_connection(host, port):
    reader, writer = await asyncio.open_connection(host, port)

    try:
        yield reader, writer
    finally:
        writer.close()


def sanitize(message):
    return re.sub(r'\n', '', message)


def get_run_params():
    parser = configargparse.ArgParser(default_config_files=['./config.conf'])
    parser.add_argument('--host', env_var='HOST')
    parser.add_argument('--read-port', env_var='READ_PORT')
    parser.add_argument('--write-port', env_var='WRITE_PORT')
    parser.add_argument('--history', env_var='HISTORY_FILENAME')
    parser.add_argument('--token', env_var='TOKEN')
    parser.add_argument('--username', env_var='USERNAME')

    args = parser.parse_args()

    return args


def load_chat(filepath, queue):
    with open(filepath, 'r') as f:
        for line in f.readlines():
            queue.put_nowait(line)
