from connexion import FlaskApp
import six
from flask import json
from repo_harvester_server.models.base_model_ import Model


class JSONEncoder(json.JSONEncoder):
    include_nulls = False

    def default(self, o):
        if isinstance(o, Model):
            dikt = {}
            for attr, _ in six.iteritems(o.swagger_types):
                value = getattr(o, attr)
                if value is None and not self.include_nulls:
                    continue
                attr = o.attribute_map[attr]
                dikt[attr] = value
            return dikt
        return super(JSONEncoder, self).default(o)
