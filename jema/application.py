# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2014 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    jema.application
    ~~~~~~~~~~~~~~~~

    JeMa web application
'''

# Let's make PyLint not complain about our module global lowercased variables
# pylint: disable=C0103


# Import python libs
import os
import sys
from traceback import format_exception
from urlparse import urlparse, urljoin

# Import Flask libs & plugins
from flask import (Blueprint, Flask, g, render_template, flash, url_for, session, request,
                   redirect, request_started, request_finished)
from flask_babel import Babel, gettext as _
from flask_cache import Cache
from flask_script import Command, Option, Manager
from flask_sqlalchemy import get_debug_queries
from flask_migrate import Migrate, MigrateCommand
from flask_menubuilder import MenuBuilder, MenuItemContent

# Import 3rd-party libs
from jinja2 import Markup

# Import JeMa libs
from jema.signals import application_configured, configuration_loaded
# pylint: disable=W0401,W0614
from jema.helpers import *
from jema.database import *
from jema.permissions import *
# pylint: enable=W0401,W0614

# ----- Simplify * Imports ---------------------------------------------------------------------->
__all__ = [
    '_',
    'g',
    'db',
    'app',
    'babel',
    'cache',
    'flash',
    'menus',
    'session',
    'url_for',
    'request',
    'redirect',
    'redirect_to',
    'redirect_back',
    'get_locale',
    'Blueprint',
    'render_template',
    'glyphiconer',

    # Menu entries permissions check functions
    'main_nav',
    'top_account_nav',
    'build_context_nav',
    'check_wether_account_is_none',
    'check_wether_account_is_not_none',
    'check_wether_is_admin',
    'check_wether_is_manager',
] + ALL_PERMISSION_IMPORTS + ALL_DB_IMPORTS
# <---- Simplify * Imports ----------------------------------------------------------------------

# ----- Setup The Flask Application ------------------------------------------------------------->
# First we instantiate the application object
app = Flask(__name__)


def configure_app(config):
    '''
Configure App hook
'''
    try:
        import jemaappconfig # pylint: disable=F0401
        app.config.from_object(jemaappconfig)
    except ImportError:
        errmsg = (
            'Can\'t configure application because the `jemaappconfig` module is not importable.'
        )
        if not config:
            print(errmsg)
            sys.exit(1)

        sys.path.insert(0, os.path.abspath(config))
        try:
            import jemaappconfig # pylint: disable=F0401
            app.config.from_object(jemaappconfig)
        except ImportError:
            print(errmsg)
            sys.exit(1)

    configuration_loaded.send(app)
    return app


# Database Migrations Support
migrate = Migrate(app, db)


# Scripts Support
class Administrator(Command):
    '''
Promote account to administrator
'''

    def get_options(self):
        return [
            Option('username', help='The username to promote')
        ]

    def run(self, username):
        try:
            account = Account.query.get(username)
            if not account:
                print('The account {0!r} does not exist'.format(username))
                exit(1)
            group = Group.query.get('Administrator')
            if group is None:
                group = Group('Administrator')
            account.groups.add(group)
            db.session.commit()
            print('The {0!r} user is now an administrator'.format(username))
            exit(0)
        except:
            raise

manager = Manager(configure_app)
manager.add_command('db', MigrateCommand)
manager.add_command('administrator', Administrator)
manager.add_option('-c', '--config', dest='config', required=False)


# I18N & L10N Support
babel = Babel(app)

# Menus
menus = MenuBuilder(app)

# Cache Support
cache = Cache()


@configuration_loaded.connect
def on_configuration_loaded(app):
    '''
    Once the configuration is loaded hook
    '''

    # Init database
    db.init_app(app)

    # Init caching
    cache.init_app(app)

    # If we're debugging...
    if app.debug:
        # LessCSS Support
        from flask_sass import Sass
        sass = Sass(app)

        from werkzeug.debug import DebuggedApplication
        app.wsgi_app = DebuggedApplication(app.wsgi_app, True)

    application_configured.send(app)
# <---- Setup The Flask Application --------------------------------------------------------------


# ----- Setup Babel Selectors ------------------------------------------------------------------->
@babel.localeselector
def get_locale():
    if hasattr(g.identity, 'account') and g.identity.account is not None:
        # Return the user's preferred locale
        return g.identity.account.locale

    # otherwise try to guess the language from the user accept
    # header the browser transmits. The best match wins.

    # Which translations do we support?
    supported = set(['en'] + [str(l) for l in babel.list_translations()])
    return request.accept_languages.best_match(supported)


@babel.timezoneselector
def get_timezone():
    if not hasattr(g.identity, 'account') or g.identity.account is None:
        # No user is logged in, return the app's default timezone
        return app.config.get('BABEL_DEFAULT_LOCALE', 'UTC')
    # Return the user's preferred timezone
    return g.identity.account.timezone
# <---- Setup Babel Selectors --------------------------------------------------------------------


# ----- Setup The Web-Application Navigation ---------------------------------------------------->
def check_wether_account_is_none(menu_item):
    if hasattr(g.identity, 'account'):
        return g.identity.account is None
    return True


def check_wether_account_is_not_none(menu_item):
    if hasattr(g.identity, 'account'):
        return g.identity.account is not None
    return False


def check_wether_is_admin(menu_item):
    return g.identity.can(administrator_permission)


def check_wether_is_manager(menu_item):
    return g.identity.can(manager_permission)


def build_context_nav(name):
    context_nav = menus.add_menu(
        name, classes='{0} nav nav-tabs'.format(name)
    )
    return context_nav


def render_account_menu(menu):
    return render_template('_account_nav.html')


main_nav = menus.add_menu(
    'main_nav', classes='main_nav nav nav-tabs'
)
main_nav.add_menu_entry(
    glyphiconer('home', nbsp=False), 'main.index', priority=-1000
)

main_nav.add_menu_entry(
    glyphiconer('log-in') + _('Sign-In'), 'account.signin',
    title=_('Sign-In using your GitHub Account'),
    classes='btn btn-info', li_classes='account-nav pull-right dropdown',
    visiblewhen=check_wether_account_is_none
)

top_account_nav = menus.add_menu(
    'top_account_nav', classes='dropdown-menu',
    visiblewhen=check_wether_account_is_not_none
)
main_nav.add_menu_item(
    MenuItemContent(
        render_account_menu, is_link=False,
        li_classes='account-nav pull-right dropdown',
        visiblewhen=check_wether_account_is_not_none
    )
)
# <---- Setup The Web-Application Navigation -----------------------------------------------------


# ----- Helpers --------------------------------------------------------------------------------->
def redirect_to(*args, **kwargs):
    code = kwargs.pop('code', 302)
    return redirect(url_for(*args, **kwargs), code=code)


def redirect_back(*args, **kwargs):
    '''
Redirect back to the page we are coming from or the URL rule given.
'''
    code = kwargs.pop('code', 302)
    target = get_redirect_target(kwargs.pop('invalid_targets', ()))
    if target is None:
        target = url_for(*args, **kwargs)
    return redirect(target, code=code)


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def get_redirect_target(invalid_targets=()):
    check_target = (request.values.get('_redirect_target') or
                    request.args.get('next') or
                    session.get('_redirect_target', None) or
                    request.environ.get('HTTP_REFERER'))

    # if there is no information in either the form data
    # or the wsgi environment about a jump target we have
    # to use the target url
    if not check_target:
        return

    # otherwise drop the leading slash
    app_url = url_for('main.index', _external=True)
    url_parts = urlparse(app_url)
    check_parts = urlparse(urljoin(app_url, check_target))

    # if the jump target is on a different server we probably have
    # a security problem and better try to use the target url.
    if url_parts[:2] != check_parts[:2]:
        return

    # if the jump url is the same url as the current url we've had
    # a bad redirect before and use the target url to not create a
    # infinite redirect.
    current_parts = urlparse(urljoin(app_url, request.path))
    if check_parts[:5] == current_parts[:5]:
        return

    # if the `check_target` is one of the invalid targets we also fall back.
    if not isinstance(invalid_targets, (tuple, list)):
        invalid_targets = [invalid_targets]
    for invalid in invalid_targets:
        if check_parts[:5] == urlparse(urljoin(app_url, invalid))[:5]:
            return

    if is_safe_url(check_target):
        return check_target
# <---- Helpers ----------------------------------------------------------------------------------


# ----- Setup Request Decorators ---------------------------------------------------------------->
@request_started.connect_via(app)
def on_request_started(app):
    if request.path.startswith(app.static_url_path):
        # Nothing else needs to be done here, it's a static URL
        return

    redirect_target = get_redirect_target(session.pop('_redirect_target', ()))
    if redirect_target is not None:
        session['_redirect_target'] = redirect_target


@request_finished.connect_via(app)
def on_request_finished(app, response):

    if request.path.startswith(app.static_url_path):
        return

    if response.status_code == 404:
        session.pop('not_found', None)
        app.save_session(session, response)
# <---- Setup Request Decorators -----------------------------------------------------------------


# ----- Error Handlers -------------------------------------------------------------------------->
@app.errorhandler(401)
def on_401(error):
    flash(_('You have not signed in yet.'), 'error')
    return redirect_to('account.signin', code=307)


@app.errorhandler(403)
def on_403(error):
    flash(_('You don\'t have the required permissions.'), 'error')
    return redirect_to('main.index', code=307)


@app.errorhandler(404)
def on_404(error):
    if request.endpoint and 'static' not in request.endpoint:
        session['not_found'] = True
    return render_template('404.html'), 404


@app.errorhandler(500)
def on_500(error):
    from pprint import pprint
    from StringIO import StringIO

    user = 'anonymous'

    identity = getattr(g, 'identity', None)

    if identity:
        account = getattr(identity, 'account', None)
        if account:
            user = account.login

    summary = str(error)
    longtext = ''.join(format_exception(*sys.exc_info()))
    request_details = StringIO()
    pprint(request.__dict__, request_details)
    request_details.seek(0)

    return render_template(
        '500.html', error=error, user=user, summary=summary,
        longtext=longtext, request_details=request_details.read()
    ), 500
# <---- Error Handlers ---------------------------------------------------------------------------


# ----- Custom Jinja Template Filters ----------------------------------------------------------->
@app.template_filter('formatseconds')
def seconds_format_filter(seconds):
    if 0 < seconds < 1:
        return '{0:.3f}ms'.format(seconds * 1000.0)
    else:
        return '{0:.3f}s'.format(seconds * 1.0)


@app.template_filter('mask_access_token')
def mask_access_token(access_token, visible=3):
    return '{0}{1}{2}'.format(
        access_token[:visible],
        '*' * (len(access_token) - (2*visible)),
        access_token[visible*-1:]
    )


@application_configured.connect
def define_highlight(app):
    if app.config.get('DEBUG', False) or app.config.get('SQLALCHEMY_RECORD_QUERIES', False):
        try:
            # This is from the snippet found at http://pastebin.com/7jS9BeAH
            from pygments import highlight
            from pygments.lexers import get_lexer_by_name
            from pygments.formatters import HtmlFormatter

            @app.template_filter('sql_highlight')
            def code_highlight(code):
                lexer = get_lexer_by_name('sql', stripall=False)
                formatter = HtmlFormatter(
                    linenos=False, style='tango', noclasses=True, nobackground=True, nowrap=True
                )
                return Markup(highlight(code, lexer, formatter))
        except ImportError:
            @app.template_filter('sql_highlight')
            def code_highlight(code):
                return Markup(code)
# <---- Custom Jinja Template Filters ------------------------------------------------------------


# ----- Jinja Context Injectors ----------------------------------------------------------------->
@app.context_processor
def inject_in_context():
    try:
        locale = g.identity.account.locale
    except AttributeError:
        locale = 'en'
    return dict(
        lang=locale,
        glyphiconer=glyphiconer,
        get_debug_queries=get_debug_queries,
        account_is_admin=g.identity.can(administrator_permission)
    )
# <---- Jinja Context Injectors ------------------------------------------------------------------


# ----- Setup The Web-Application Views --------------------------------------------------------->
from jema.views.main import main
from jema.views.account import account
#from jema.views.servers import servers
#from jema.views.builders import builders
#from jema.views.users import users
#from jema.views.groups import groups

app.register_blueprint(main)
app.register_blueprint(account)
#app.register_blueprint(servers)
#app.register_blueprint(builders)
#app.register_blueprint(users)
#app.register_blueprint(groups)
# <---- Setup The Web-Application Views ----------------------------------------------------------
