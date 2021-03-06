import asyncio
import ssl
import os
import aiohttp_jinja2 as aiojinja2

from termcolor import cprint
from aiohttp import web
from typing import Optional

from .context import context
from .worker import spawn_clients
from .handler import handler, websocket_handler
from .config import config_parser

__PATH__ = os.path.abspath(os.path.dirname(__file__))

def create_app(*,
               hosts=['localhost'],
               default_port: int = 22,
               ssl_certfile: Optional[str] = None,
               ssl_keyfile: Optional[str] = None,
               exec_cmd: Optional[str] = None,
               verbose=True):

    DEFAULT_GPUSTAT_COMMAND = "gpustat --color --gpuname-width 25"
    if not exec_cmd: exec_cmd = DEFAULT_GPUSTAT_COMMAND

    app = web.Application()
    app.router.add_get('/', handler)
    app.add_routes([web.get('/ws', websocket_handler)])

    async def start_background_tasks(app):
        clients = spawn_clients(hosts, exec_cmd, default_port=default_port, verbose=verbose)
        loop = app.loop if hasattr(app, 'loop') else asyncio.get_event_loop()
        app['tasks'] = loop.create_task(clients)
        await asyncio.sleep(0.1)
    app.on_startup.append(start_background_tasks)

    async def shutdown_background_tasks(app):
        cprint(f"... Terminating the application", color='yellow')
        app['tasks'].cancel()
    app.on_shutdown.append(shutdown_background_tasks)

    import jinja2
    aiojinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(__PATH__, 'template')))

    if ssl_certfile and ssl_keyfile:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=ssl_certfile, keyfile=ssl_keyfile)
        cprint(f"Using Secure HTTPS (SSL/TLS) server ...", color='green')
    else:
        ssl_context = None
    return app, ssl_context


def main():
    config = config_parser(file_path='config.ini')
    context.config = config

    exec_file = config.get('exec', 'file')
    exec_cmd = open(exec_file, 'r').read()
    exec_hosts = eval(config.get('exec', 'hosts'))
    
    cprint(f"Hosts : {exec_hosts}", color='green')
    cprint(f"Cmd   : {exec_cmd}", color='yellow')

    exec_interval = float(config.get('exec', 'interval'))
    if exec_interval > 0.1:
        context.interval = exec_interval

    app, ssl_context = create_app(
        hosts=exec_hosts,
        exec_cmd=exec_cmd,
        verbose = eval(config.get('debug', 'verbose'))
    )

    web.run_app(
        app, 
        host=config.get('web', 'host'),
        port=int(config.get('web', 'port')), 
        ssl_context=ssl_context
    )

if __name__ == '__main__':
    main()