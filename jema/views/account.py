# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2013 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    jema.views.account
    ~~~~~~~~~~~~~~~~~~~

    Account related views
'''

# Import Python libs
import json
import urllib
import httplib
import logging
from uuid import uuid4

# Import 3rd-party libs
import pytz
import github
from babel.dates import get_timezone_name

# Import JeMa Libs
from jema.forms import *
from jema.application import *

log = logging.getLogger(__name__)


# ----- Blueprints & Menu Entries --------------------------------------------------------------->
account = Blueprint('account', __name__, url_prefix='/account')

top_account_nav.add_menu_entry(
    glyphiconer('user') + _('Profile'), 'account.profile', priority=-1,
    visiblewhen=check_wether_account_is_not_none
)
top_account_nav.add_menu_entry(
    glyphiconer('log-out') + _('Sign-Out'), 'account.signout', priority=100,
    visiblewhen=check_wether_account_is_not_none
)

account_view_nav = build_context_nav('account_view_nav')
# <---- Blueprints & Menu Entries ----------------------------------------------------------------


# ----- Forms ----------------------------------------------------------------------------------->
class ProfileForm(DBBoundForm):

    title = _('My Account')

    class Meta:
        model = Account

    # Actions
    update = PrimarySubmitField(_('Update Details'))
# <---- Forms ------------------------------------------------------------------------------------


# ----- Views ----------------------------------------------------------------------------------->
@account.route('/signin', methods=('GET',))
def signin():
    identity_account = getattr(g.identity, 'account', None)
    if identity_account is not None:
        # This user is already authenticated and is valid user(it's present in our database)
        flash(_('You\'re already authenticated!'))
        return redirect_back(url_for('main.index'))
    elif identity_account is None:
        # If we reached this point, the github token is not in our database
        session.clear()

    # Let's login the user using github's oauth

    # GitHub Access Scopes:
    #   http://developer.github.com/v3/oauth/#scopes
    github_state = uuid4().hex
    session['github_state'] = github_state

    urlargs = {
        'state': github_state,
        # We need 'repo' or 'public_repo' scopes in order to be able to create hooks.
        'scope': 'user:email, public_repo',
        'client_id': app.config.get('GITHUB_CLIENT_ID'),
        'redirect_uri': url_for('account.callback', _external=True)
    }
    log.debug('New signin request. Redirect args: {0}'.format(urlargs))
    return redirect(
        'https://github.com/login/oauth/authorize?{0}'.format(
            urllib.urlencode(urlargs)
        )
    )


@account.route('/signin/callback', methods=('GET',))
def callback():
    github_state = request.args.get('state', None)
    if github_state is None or github_state != session.pop('github_state', None):
        flash(_('This authentication has been tampered with! Aborting!!!'), 'error')

    code = request.args.get('code')

    urlargs = {
        'code': code,
        'state': github_state,
        'client_id': app.config.get('GITHUB_CLIENT_ID'),
        'client_secret': app.config.get('GITHUB_CLIENT_SECRET'),
    }

    # let's get some json back
    headers = {'Accept': 'application/json'}

    conn = httplib.HTTPSConnection('github.com')
    conn.request(
        'POST',
        '/login/oauth/access_token?{0}'.format(urllib.urlencode(urlargs)),
        headers=headers
    )
    resp = conn.getresponse()
    data = resp.read()
    if resp.status == 200:
        data = json.loads(data)
        token = data['access_token']

        account = Account.query.from_github_token(token)
        if account is None:
            # We do not know this token.
            gh = github.Github(
                token,
                client_id=app.config.get('GITHUB_CLIENT_ID'),
                client_secret=app.config.get('GITHUB_CLIENT_SECRET')
            )
            gh_user = gh.get_user()
            # Do we know the account by the id?
            account = Account.query.get(gh_user.id)
            if account is None:
                # This is a brand new account
                account = Account(
                    gh_user.id,
                    gh_user.login,
                    gh_user.name,
                    gh_user.email,
                    token,
                    gh_user.avatar_url
                )
                # New users are considered commiters
                db.session.add(account)
            else:
                # We know this account though the access token has changed.
                # Let's update the account details.
                account.id = gh_user.id
                account.login = gh_user.login
                account.name = gh_user.name
                account.email = gh_user.email
                account.access_token = token
                account.avatar_url = gh_user.avatar_url

            db.session.commit()

        identity_changed.send(app, identity=Identity(account.id, 'dbm'))
        flash(_('You are now signed in.'), 'success')
    return redirect(url_for('main.index'))


@account.route('/signout', methods=('GET',))
@authenticated_permission.require(403)
def signout():
    if g.identity.account is not None:
        session.clear()
        identity_changed.send(app, identity=AnonymousIdentity())
        flash(_('You are now signed out.'), 'success')
    else:
        flash(_('You\'re not authenticated!'))
    return redirect(url_for('main.index'))


@account.route('/profile', methods=('GET', 'POST'))
@authenticated_permission.require(403)
def profile():
    form = ProfileForm(formdata=request.values.copy(), obj=g.identity.account)
    if form.validate_on_submit():
        form.populate_obj(g.identity.account)
        flash(_('Account details updated.'), 'success')
        return redirect_to('account.profile')
    return render_template('account/profile.html', form=form)
# <---- Views ------------------------------------------------------------------------------------
