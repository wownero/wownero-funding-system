import json

import redis
from flask_session import RedisSessionInterface

import settings
from funding.bin.utils import json_encoder


def redis_args():
    args = {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        'socket_connect_timeout': 2,
        'socket_timeout': 2,
        'retry_on_timeout': True,
        'decode_responses': True
    }
    if settings.REDIS_PASSWD:
        args["password"] = settings.REDIS_PASSWD
    return args


class JsonRedisSerializer:
    @staticmethod
    def loads(val):
        try:
            return json.loads(val).get("wow", {})
        except ValueError:
            return

    @staticmethod
    def dumps(val):
        try:
            return json.dumps({"wow": val})
        except ValueError:
            return


class JsonRedis(RedisSessionInterface):
    serializer = JsonRedisSerializer

    def __init__(self, key_prefix, use_signer=False, decode_responses=True):
        super(JsonRedis, self).__init__(
            redis=redis.Redis(**redis_args()),
            key_prefix=key_prefix,
            use_signer=use_signer)
