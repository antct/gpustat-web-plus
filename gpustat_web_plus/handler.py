from .context import context

import time
import ansi2html
import collections
import collections
import time
import aiohttp

from termcolor import cprint, colored
from aiohttp import web
import aiohttp_jinja2 as aiojinja2


scheme = 'solarized'
ansi2html.style.SCHEME[scheme] = list(ansi2html.style.SCHEME[scheme])
ansi2html.style.SCHEME[scheme][0] = '#555555'
ansi_conv = ansi2html.Ansi2HTMLConverter(dark_bg=True, scheme=scheme)

def render_gpustat_body():
    body = ''
    machine_tot, machine_alive = 0, 0
    for host, data in context.host_data.items():
        if not data: continue
        machine_tot += 1
        if data['status'] == 1:
            machine_alive += 1
        body += data['msg']
    gpu_num, gpu_use, gpu_tot, power = 0, 0, 0, 0
    user2mem = collections.defaultdict(int)
    for host, data in context.host_data.items():
        if not data: continue
        if 'gpu' in data:
            gpu_num += data['gpu']['num']
            gpu_use += data['gpu']['use']
            gpu_tot += data['gpu']['tot']
        if 'pow' in data:
            power += data['pow']
        if 'usr2mem' in data:
            for user, mem in data['usr2mem'].items():
                user2mem[user] += mem
    user2mem = list(user2mem.items())
    if len(user2mem) < 3:
        user2mem.extend([["null", 0]] * (3-len(user2mem)))
    user2mem = sorted(user2mem, key=lambda x: x[1], reverse=True)
    template = 'time@now: {}\n' + \
        'machine@alive: {}  machine@dead: {}  power@total: {}W\n' + \
        'gpu@num: {}  gpu@used: {}G  gpu@free: {}G  gpu@total: {}G\n' + \
        'gpu@rank: top@1({}:{}G)  top@2({}:{}G)  top@3({}:{}G)\n\n'
    body = colored(template.format(
        time.asctime( time.localtime(time.time())),
        machine_alive, machine_tot-machine_alive, power,
        gpu_num, int(gpu_use/1024.0), int((gpu_tot-gpu_use)/1024.0), int(gpu_tot/1024.0),
        user2mem[0][0], int(user2mem[0][1]/1024.0),
        user2mem[1][0], int(user2mem[1][1]/1024.0),
        user2mem[2][0], int(user2mem[2][1]/1024.0)
        ), "white") + body
    return ansi_conv.convert(body, full=False)

async def handler(request):
    data = dict(
        ansi2html_headers=ansi_conv.produce_headers().replace('\n', ' '),
        http_host=request.host,
        interval=int(context.interval * 1000)
    )
    response = aiojinja2.render_template('index.html', request, data)
    response.headers['Content-Language'] = 'en'
    return response

async def websocket_handler(request):
    print("INFO: Websocket connection from {} established".format(request.remote))
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async def _handle_websocketmessage(msg):
        if msg.data == 'close':
            await ws.close()
        else:
            body = render_gpustat_body()
            await ws.send_str(body)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.CLOSE:
            break
        elif msg.type == aiohttp.WSMsgType.TEXT:
            await _handle_websocketmessage(msg)
        elif msg.type == aiohttp.WSMsgType.ERROR:
            cprint("Websocket connection closed with exception %s" % ws.exception(), color='red')
    print("INFO: Websocket connection from {} closed".format(request.remote))
    return ws