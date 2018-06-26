from flask.json import JSONEncoder
from datetime import datetime, date


def json_encoder(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))
