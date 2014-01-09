# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2013 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    jema.forms
    ~~~~~~~~~~~

    Web Forms
'''

# Import python libs
import logging
from datetime import datetime

# Import 3rd-party libs
import pytz
from wtforms import *
from wtforms.fields import *
from wtforms.validators import *
from wtforms.fields.html5 import *
#from wtforms.ext.sqlalchemy.orm import *
#from wtforms.ext.sqlalchemy.fields import *
from wtforms.fields import SubmitField as BaseSubmitField
from wtforms_alchemy import model_form_factory
#from wtforms_alchemy import *

from babel.dates import get_timezone_name
from werkzeug.datastructures import MultiDict
from jinja2 import Markup
from flask_wtf import Form

# Import JeMa libs
from jema.application import *

__SKIP_ZONES = (
    'America/Argentina/Salta',
    'Asia/Kathmandu',
    'America/Matamoros',
    'Asia/Novokuznetsk',
    'America/Ojinaga',
    'America/Santa_Isabel',
    'America/Santarem'
)

log = logging.getLogger(__name__)


@cache.memoize(3600)
def build_timezones():
    tzs = set()
    now = datetime.now()
    for tz_name in pytz.common_timezones:
        offset = pytz.timezone(tz_name).utcoffset(now)
        offset_real_secs = offset.seconds + offset.days * 24 * 60**2
        offset_hours, remainder = divmod(offset_real_secs, 3600)
        offset_minutes, _ = divmod(remainder, 60)
        offset_txt = u'(UTC {0:0=+3d}:{1:0>2d}) {2}'.format(offset_hours, offset_minutes, tz_name)
        tzs.add((offset_real_secs, tz_name, offset_txt))
    tzs = sorted(list(tzs))
    return [tz[1:] for tz in tzs]


class SubmitField(BaseSubmitField):

    _secondary_class_ = ''

    def __call__(self, *args, **kwargs):
        class_ = set(kwargs.pop('class_', '').split())
        class_.add('btn')
        class_.add('btn-lg')
        class_.add('btn-primary')
        class_.add(self._secondary_class_)
        kwargs['class_'] = ' '.join(class_)
        return super(SubmitField, self).__call__(*args, **kwargs)


class PrimarySubmitField(SubmitField):

    _secondary_class_ = 'btn-primary'


class CancelSubmitField(SubmitField):

    _secondary_class_ = 'btn-warning'


class SensibleSubmitField(SubmitField):

    _secondary_class_ = 'btn-danger'


class FormBase(Form):
    def __init__(self, formdata=None, *args, **kwargs):
        if formdata and not isinstance(formdata, MultiDict):
            formdata = MultiDict(formdata)
        super(FormBase, self).__init__(formdata, *args, **kwargs)

    def validate(self, extra_validators=None):
        rv = super(Form, self).validate()
        errors = []
        if 'csrf' in self.errors:
            del self.errors['csrf']
            errors.append(
                _('Form Token Is Invalid. You MUST have cookies enabled.')
            )
        for field_name, ferrors in self.errors.iteritems():
            errors.append(
                '<b>{0}:</b> {1}'.format(
                    self._fields[field_name].label.text, '; '.join(ferrors)
                )
            )
        if errors:
            flash(
                Markup(
                    '<h4>{0}</h4>\n<ul>{1}</ul>'.format(
                        _('Errors:'),
                        ''.join(['<li>{0}</li>'.format(e) for e in errors])
                    )
                ), "danger"
            )
        return rv


class DBBoundForm(model_form_factory(FormBase)):

    @classmethod
    def get_session(cls):
        return db.session
