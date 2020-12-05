import asyncio
import json
import logging
import socket
from datetime import datetime
from time import time
from tkinter import messagebox

import aiofiles as aiofiles
from anyio import create_task_group
from async_timeout import timeout

import gui
from utils import open_connection, sanitize, get_run_params, load_chat


class WrongToken(Exception):
    pass


async def read_msgs(host, port, queue, log_queue, status_queue, watchdog_queue):
    logging.debug(f'Run listening chat with params: {host}, {port}')

    status_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    async with open_connection(host, port) as (reader, writer):
        status_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
        while True:
            data = await reader.readline()
            message = f'[{datetime.now().strftime("%d.%m.%Y %H:%M")}] {data.decode()}'
            logging.debug(message.strip())
            queue.put_nowait(message)
            watchdog_queue.put_nowait('New message in chat')
            log_queue.put_nowait(message)


async def register(nickname, host, port):
    nickname = sanitize(nickname)

    async with open_connection(host, port) as (reader, writer):
        server_response = await reader.readline()
        logging.debug(f'Received: {server_response.decode()!r}')

        writer.write('\n'.encode())
        await writer.drain()
        logging.debug(f"Send '\\n'")

        server_response = await reader.readline()
        logging.debug(f'Received: {server_response.decode()!r}')

        writer.write(f'{nickname}\n'.encode())
        await writer.drain()
        logging.debug(f'Send {nickname!r}')

        server_response = await reader.readline()
        logging.debug(f'Received: {server_response.decode()!r}')

        return json.loads(server_response)['account_hash']


async def authorise(reader, writer, account_hash):
    server_response = await reader.readline()
    logging.debug(f'Received: {server_response.decode()!r}')

    writer.write(f'{account_hash}\n'.encode())
    logging.debug(f'Send {account_hash!r}')

    return await reader.readline()


async def submit_message(writer, message):
    message = sanitize(message)
    writer.write(f'{message}\n\n'.encode())
    await writer.drain()
    logging.debug(f'Send {message!r}')


async def send_msgs(host, port, user, token, queue, status_queue, watchdog_queue):
    status_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    token = token or await register(user, host, port)

    async with open_connection(host, port) as (reader, writer):
        status_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
        watchdog_queue.put_nowait('Prompt before auth')

        authorise_response = await authorise(reader, writer, token)
        watchdog_queue.put_nowait('Authorization done')

        json_response = json.loads(authorise_response.decode())
        if json_response:
            nickname = json_response["nickname"]
            event = gui.NicknameReceived(nickname)
            status_queue.put_nowait(event)

            logging.debug(f'Выполнена авторизация. Пользователь {nickname}')

            while True:
                msg = await queue.get()
                logging.debug(f'Пользователь ввел {msg}')
                await submit_message(writer, msg)
                watchdog_queue.put_nowait('Message sent')
        else:
            messagebox.showinfo("Неверный токен", "Проверь токен, сервер не узнал его.")
            raise WrongToken()


async def save_messages(filepath, queue):
    async with aiofiles.open(filepath, 'a') as f:
        while True:
            msg = await queue.get()
            await f.write(msg)


async def watch_for_connection(logger, watchdog_queue):
    while True:
        try:
            with timeout(2):
                msg = await watchdog_queue.get()
                logger.info(f'[{time()}] Connection is alive. Source: {msg}')
        except asyncio.TimeoutError:
            logger.info(f'[{time()}] 2s timeout is elapsed')
            raise ConnectionError


async def server_ping(host, port, watchdog_queue):
    while True:
        async with open_connection(host, port) as (reader, writer):
            await submit_message(writer, '')
            watchdog_queue.put_nowait('Ping message sent')
        await asyncio.sleep(1)


async def handle_connection(args, messages_queue, log_queue, status_updates_queue, watchdog_queue, sending_queue,
                            watchdog_logger):
    while True:
        try:
            async with create_task_group() as tg:
                await tg.spawn(read_msgs,
                               args.host, args.read_port,
                               messages_queue, log_queue, status_updates_queue, watchdog_queue)
                await tg.spawn(send_msgs,
                               args.host, args.write_port, args.username, args.token,
                               sending_queue, status_updates_queue, watchdog_queue)
                await tg.spawn(server_ping, args.host, args.write_port, watchdog_queue)
                await tg.spawn(watch_for_connection, watchdog_logger, watchdog_queue)
        except (ConnectionError, socket.gaierror) as e:
            watchdog_logger.error('Reconnecting to server')
            await asyncio.sleep(1)


async def main():
    watchdog_logger = logging.getLogger('watchdog_logger')
    args = get_run_params()
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    log_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    load_chat(args.history, messages_queue)

    async with create_task_group() as tg:
        await tg.spawn(handle_connection,
                       args,
                       messages_queue, log_queue, status_updates_queue,
                       watchdog_queue, sending_queue, watchdog_logger),
        await tg.spawn(save_messages, args.history, log_queue),
        await tg.spawn(gui.draw, messages_queue, sending_queue, status_updates_queue),


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, gui.TkAppClosed) as e:
        logging.info('Gui chat client closed by user!')
