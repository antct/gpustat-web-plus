import re
import collections

from termcolor import colored

from .noticer import dingding_notice


class Context(object):
    def __init__(self):
        self.interval = 5.0
        self.config = None
        self.host_data = collections.defaultdict(lambda: collections.defaultdict())

    def host_set_status(self, hostname: str, port: str, status: int):
        if eval(self.config.get('notice', 'on')) and self.host_data[f"{hostname}:{port}"].get('notice_flag') == True and status == -1:
            dingding_notice(
                title='服务器监控报警信息',
                text='[主机] {}:{}\n\n[异常] 宕机 请及时处理'.format(hostname, port),
                token=self.config.get('notice', 'dingding_token'),
                secret=self.config.get('notice', 'dingding_secret')
            )
        self.host_data[f"{hostname}:{port}"]['status'] = status
        if status != -1: self.host_data[f"{hostname}:{port}"]['notice_flag'] = True
        else: self.host_data[f"{hostname}:{port}"]['notice_flag'] = False

    def host_set_message(self, hostname: str, port: str, msg: str):
        self.host_data[f"{hostname}:{port}"]['msg'] = colored(f"({hostname}:{port}) ", 'white') + msg + '\n'

    def host_update_message(self, hostname: str, port: str, data: str, custom_name: str):
        ansi_escape = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        # 去掉颜色字符
        data_nocolor = ansi_escape.sub('', data)
        # 更改主机名
        name = data_nocolor.splitlines()[0].split()[0]
        if custom_name: data = data.replace(name + ' ' * len(custom_name), custom_name + ' ' * len(name))
        # meta信息颜色更换，如果超过阈值
        data = data.splitlines()
        title, info, meta = data[0], data[1:-1], data[-1]
        # 调整meta信息和主机信息的位置
        user_cnt = re.search(r'user\((.*?)\)', meta).group(1)
        title_splits = title.split()
        title_splits[0] = '{}({}\x1b[1m\x1b[37m)'.format(title_splits[0], colored(user_cnt, 'red') if int(user_cnt) >= 3 else user_cnt)
        cuda_version = ansi_escape.sub('', title_splits[-1])
        cuda_version = cuda_version[:cuda_version.find('.')]
        meta = '\t'.join(meta.split('\t')[1:])
        # 调整meta信息中的颜色
        meta_names = eval(self.config.get('meta', 'names'))
        meta_thres_low = eval(self.config.get('meta', 'low_thresholds'))
        meta_thres_high = eval(self.config.get('meta', 'high_thresholds'))
        meta_thres_notice = eval(self.config.get('meta', 'notice_thresholds'))
        meta_notice_flags = self.host_data[f"{hostname}:{port}"].get('meta_notice_flags')
        if meta_notice_flags is None: self.host_data[f"{hostname}:{port}"]['meta_notice_flags'] = [True] * len(meta_names)

        meta_zip = zip(meta_names, meta_thres_low, meta_thres_high, meta_thres_notice, self.host_data[f"{hostname}:{port}"]['meta_notice_flags'])
        for idx, (meta_name, meta_thre_low, meta_thre_high, meta_thre_notice, _) in enumerate(meta_zip):
            cur_meta = re.search(r'{}\((.*?)\%\)'.format(meta_name), meta)
            cur_value = float(cur_meta.group(1))
            if cur_value >= meta_thre_notice:
                if self.host_data[f"{hostname}:{port}"]['meta_notice_flags'][idx] and eval(self.config.get('notice', 'on')):
                    dingding_notice(
                        title='服务器监控报警信息',
                        text='[主机] {}:{}\n\n[异常] {}占用已达{}% 请及时处理'.format(hostname, port, meta_name, cur_value),
                        token=self.config.get('notice', 'dingding_token'),
                        secret=self.config.get('notice', 'dingding_secret')
                    )
                self.host_data[f"{hostname}:{port}"]['meta_notice_flags'][idx] = False
            else:
                self.host_data[f"{hostname}:{port}"]['meta_notice_flags'][idx] = True
            if cur_value >= meta_thre_high:
                modify_meta = colored(cur_meta.group(0), 'red')
            elif cur_value <= meta_thre_low:
                modify_meta = colored(cur_meta.group(0), 'green')
            else:
                modify_meta = colored(cur_meta.group(0), 'yellow')
            meta = meta.replace(cur_meta.group(0), modify_meta)
        # 新的显示信息
        title = ''.join(title_splits[:2]) + ' \t' + meta + ' \t' + 'cuda({})'.format(cuda_version)
        data = [title] + info
        data = '\n'.join(data) + '\n'
        self.host_data[f"{hostname}:{port}"]['msg'] = data
        # 统计显存消耗
        lines = re.findall(r'([0-9]*) */ *([0-9]*) MB', data_nocolor)
        gpu_num = len(lines)
        gpu_use, gpu_tot = 0, 0
        for line in lines:
            gpu_use += int(line[0])
            gpu_tot += int(line[1])
        # 统计功率
        lines = re.findall(r'([0-9]*) / ([0-9]*) W', data_nocolor)
        power = sum([int(line[0]) for line in lines])
        # 统计用户使用显存使用
        # lines = re.findall(r'([a-z|A-Z]*?)/[0-9]*?\(([0-9]*)M\)', data_nocolor)
        lines = re.findall(r'([a-z|A-Z]*?):.*?/[0-9]*?\(([0-9]*)M\)', data_nocolor)
        usr2mem = collections.defaultdict(int)
        for name, mem in lines:
            usr2mem[str(name)] += int(mem)
        # 更新当前主机数据
        self.host_data[f"{hostname}:{port}"].update({
            'gpu': {'use': gpu_use, 'tot': gpu_tot, 'num': gpu_num, 'score': gpu_num*(1.0-gpu_use/gpu_tot)},
            'pow': power,
            'usr2mem': usr2mem,
            'custom_name': custom_name
        })

context = Context()