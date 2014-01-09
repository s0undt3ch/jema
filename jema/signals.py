# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2014 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    jema.signals
    ~~~~~~~~~~~~~

    JeMa related signals
'''

# Import 3rd-party libs
from blinker import Namespace

# Get a reference to a name-spaced signal
signal = Namespace().signal

configuration_loaded = signal(
    'configuration-loaded',
    'Emitted once the configuration has been loaded.'
)

application_configured = signal(
    'application-configured',
    'Emitted once the application has been configured.'
)

after_identity_account_loaded = signal(
    'after-identity-account-loaded',
    'Emitted after loading the identity from the database.'
)
