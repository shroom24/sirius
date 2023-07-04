import logging

from requests_oauthlib import OAuth2Session
import requests
import flask
import flask_login as login

from sirius.models import user as user_model
from sirius.models.db import db

logger = logging.getLogger(__name__)

blueprint = flask.Blueprint("twitter", __name__)

auth_url = "https://twitter.com/i/oauth2/authorize"
token_url = "https://api.twitter.com/2/oauth2/token"

scopes = ["tweet.read", "users.read", "offline.access"]

oauth_session: OAuth2Session
code_challenge: str
code_verifier: str


def make_token():
    global oauth_session
    global code_verifier
    global code_challenge

    client_id = flask.current_app.config.get("TWITTER_OAUTH_CLIENT_KEY")
    redirect_uri = flask.current_app.config.get("OAUTH_REDIRECT_URI")

    oauth_session = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)
    code_verifier = oauth_session._client.create_code_verifier(43)
    code_challenge = oauth_session._client.create_code_challenge(
        code_verifier, code_challenge_method="S256"
    )


def get_self():
    access_token = flask.session.get("twitter_token").get("access_token")
    resp = requests.get(
        url="https://api.twitter.com/2/users/me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    if not resp.ok:
        rule = flask.request.url_rule
        msg = f"Error from {rule.endpoint}!"
        logger.debug(msg)
        flask.flash(msg, category="error")
        return flask.redirect("/")

    return resp.json().get("data")


@blueprint.route("/twitter/logout")
def twitter_logout():
    flask.session.pop("user_id", None)
    flask.flash("You were signed out")
    return flask.redirect("/")


def process_authorization(token, next_url):
    """Process the incoming twitter oauth data. Validation has already
    succeeded at this point and we're just doing the book-keeping."""

    flask.session["twitter_token"] = token
    screen_name = get_self().get("username")
    flask.session["twitter_screen_name"] = screen_name
    oauth = user_model.TwitterOAuth.query.filter_by(
        screen_name=screen_name,
    ).first()

    # Create local user model for keying resources (e.g. claim codes)
    # if we haven't seen this twitter user before.
    if oauth is None:
        new_user = user_model.User(
            username=screen_name,
        )

        oauth = user_model.TwitterOAuth(
            user=new_user,
            screen_name=screen_name,
            token=token.get("access_token"),
            token_secret=token.get("access_token"),
        )

        db.session.add(new_user)
        db.session.add(oauth)
        db.session.commit()

    login.login_user(oauth.user)

    flask.flash("Successfully signed in! Hi, @%s." % screen_name)

    return flask.redirect(next_url)


@blueprint.route("/twitter")
def twitter_logged_in():
    make_token()

    authorization_url, state = oauth_session.authorization_url(
        auth_url, code_challenge=code_challenge, code_challenge_method="S256"
    )
    flask.session["oauth_state"] = state
    return flask.redirect(authorization_url)


@blueprint.route("/twitter/authorized", methods=["GET"])
def twitter_callback():
    client_secret = flask.current_app.config.get("TWITTER_OAUTH_CLIENT_SECRET")
    next_url = "/"
    code = flask.request.args.get("code")
    error = flask.request.args.get("error")
    if error is not None:
        logger.debug("twitter_callback: we got a problem")
        rule = flask.request.url_rule
        msg = f"OAuth error from {rule.endpoint}! message={error}"
        logger.debug(msg)
        flask.flash(msg, category="error")
        return flask.redirect(next_url)

    token = oauth_session.fetch_token(
        token_url=token_url,
        client_secret=client_secret,
        code_verifier=code_verifier,
        code=code,
    )

    if token is None:
        flask.flash("Twitter didn't authorize our sign-in request.", category="error")
        return flask.redirect(next_url)

    return process_authorization(token, next_url)
