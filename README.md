# Wownero Funding System

![whoop](https://i.imgur.com/xVS3UGq.png)

A simple Flask application for managing donations.

Example
-------

[https://funding.wownero.com](https://funding.wownero.com)

## Installation

Good luck with trying to get this to run! Some pointers:

#### Daemon

First make sure the daemon is up.

```bash
./wownerod --max-concurrency 4
```

#### Wallet RPC

Expose wallet via RPC.

```bash
./wownero-wallet-rpc --rpc-bind-port 45678 --disable-rpc-login --wallet-file wfs --password ""
```


#### Web application

Download application and configure.

```
sudo apt install libjpeg-dev libpng-dev python-virtualenv python3 redis-server postgresql-server postgresql-server-dev-*
git clone https://github.com/skftn/wownero-wfs.git
cd wownero-wfs
virtualenv -p /usr/bin/python3
source venv/bin/activate
pip uninstall pillow
pip install -r requirements.txt
CC="cc -mavx2" pip install -U --force-reinstall pillow-simd
cp settings.py_example settings.py
- change settings accordingly
```

Prepare a database in postgres and create an user for it.

Run the application:

```bash
python run_dev.py
```

Beware `run_dev.py` is meant as a development server.

When running behind nginx/apache, inject `X-Forwarded-For`.

### Contributors

- [camthegeek](https://github.com/camthegeek)

### License

© 2018 WTFPL – Do What the Fuck You Want to Public License
