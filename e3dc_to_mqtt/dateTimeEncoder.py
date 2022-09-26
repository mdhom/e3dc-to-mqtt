import json
from datetime import timedelta, date


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, date):
            return o.isoformat()

        return super().default(self, o)