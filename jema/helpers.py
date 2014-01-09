# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2014 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    jema.helpers
    ~~~~~~~~~~~~~

    Several helpers
'''

# Import 3rd-party libs
from jinja2 import Markup


def glyphiconer(*classes, **kwargs):
    nbsp = kwargs.pop('nbsp', True) is True
    _classes = []
    for class_name in classes:
        if not class_name.startswith('glyphicon-'):
            class_name = 'glyphicon-{0}'.format(class_name)
        _classes.append(class_name)
    return Markup('<i class="glyphicon {0}">{1}</i>'.format(' '.join(_classes),
                                                            nbsp and '&nbsp;' or ''))
