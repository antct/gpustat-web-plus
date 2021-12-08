gpustat-web-plus
===========

A web interface across multiple lab server nodes (modify from [wookayin/gpustat-web](https://github.com/wookayin/gpustat-web)).

Usage
-----
Fill in the configuration file `config.ini` (refer template `config.ini.template`), and make sure ssh works under a proper authentication scheme such as SSH key (e.g. `id-rsa`).


```bash
python -m gpustat_web_plus / bash run.sh
```

![](screenshot.png)