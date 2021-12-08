import traceback
import urllib
import asyncio
import asyncssh

from datetime import datetime
from termcolor import cprint, colored
from typing import Dict, List, Tuple, Optional

from .context import context

async def run_client(hostname: str, exec_cmd: str, *,
                     username=None, port=None, custom_name=None,
                     poll_delay=None, timeout=30.0, verbose=False, config=None):
    if poll_delay is None:
        poll_delay = context.interval

    async def _loop_body():
        async with asyncssh.connect(hostname, username=username, port=port) as conn:
            cprint(f"[{hostname}:{port}] SSH connection established!", attrs=['bold'])
            while True:
                if verbose:
                    print(f"[{hostname}:{port}] querying... ")
                result = await asyncio.wait_for(conn.run(exec_cmd), timeout=timeout)
                now = datetime.now().strftime('%Y/%m/%d-%H:%M:%S.%f')
                if result.exit_status != 0:
                    cprint(f"[{now} [{hostname}:{port}] Error, exitcode={result.exit_status}", color='red')
                    cprint(result.stderr or '', color='red')
                    stderr_summary = (result.stderr or '').split('\n')[0]
                    context.host_set_status(hostname, port, -1)
                    context.host_set_message(hostname, port, colored(f'[exitcode {result.exit_status}] {stderr_summary}', 'red'))
                else:
                    if verbose: cprint(f"[{now} [{hostname}:{port}] OK from gpustat ({len(result.stdout)} bytes)", color='cyan')
                    context.host_set_status(hostname, port, 1)
                    context.host_update_message(hostname, port, result.stdout, custom_name=custom_name, config=config)
                await asyncio.sleep(poll_delay)
    while True:
        try:
            await _loop_body()
        except asyncio.CancelledError:
            cprint(f"[{hostname}:{port}] Closed as being cancelled.", attrs=['bold'])
            break
        except (asyncio.TimeoutError) as ex:
            cprint(f"Timeout after {timeout} sec: {hostname}", color='red')
            context.host_set_message(hostname, port, colored(f"Timeout after {timeout} sec", 'red'))
        except (asyncssh.misc.DisconnectError, asyncssh.misc.ChannelOpenError, OSError) as ex:
            cprint(f"Disconnected : {hostname}, {str(ex)}", color='red')
            context.host_set_message(hostname, port, colored(str(ex), 'red'))
        except Exception as e:
            cprint(f"[{hostname}:{port}] {e}", color='red')
            context.host_set_message(hostname, port, colored(f"{type(e).__name__}: {e}", 'red'))
            cprint(traceback.format_exc())
            raise
        cprint(f"[{hostname}:{port}] Disconnected, retrying in {poll_delay} sec...", color='yellow')
        await asyncio.sleep(poll_delay)

async def spawn_clients(hosts: Dict[str, str], exec_cmd: str, *, default_port: int, verbose=False, config=None):
    def _parse_host_string(netloc: str) -> Tuple[str, Optional[int]]:
        pr = urllib.parse.urlparse('ssh://{}/'.format(netloc))
        assert pr.hostname is not None, netloc
        return (pr.hostname, pr.username, pr.port if pr.port else default_port)
    try:
        custom_names = list(hosts.keys())
        hosts = list(hosts.values())
        host_names, host_usernames, host_ports = zip(*(_parse_host_string(host) for host in hosts))
        for hostname, port in zip(host_names, host_ports):
            context.host_set_status(hostname, port, 0)
            context.host_set_message(hostname, port, "Loading ...")
        await asyncio.gather(*[
            run_client(hostname, exec_cmd, username=username, port=port or default_port, custom_name=custom_name, verbose=verbose, config=config)
            for (hostname, username, port, custom_name) in zip(host_names, host_usernames, host_ports, custom_names)
        ])
    except Exception as ex:
        traceback.print_exc()
        cprint(colored("Error: An exception occured during the startup.", 'red'))







