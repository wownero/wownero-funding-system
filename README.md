# WOW funding

## installation (locally)

Create a Postgres user/database for this project

```
sudo apt install python-virtualenv python3 redis-server postgresql-server-dev-*
git clone ...
cd ffs_site
virtualenv -p /usr/bin/python3
source venv/bin/activate
pip install -r requirements.txt
cp settings.py_example settings.py
- change settings accordingly
python run_dev.py
```

### to-do

- rate limit posting of proposals per user

https://imgur.com/KKzFQe9
https://imgur.com/Dl3wRgD
