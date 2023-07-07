import flask_testing as testing
import flask_login as login

from sirius.models import user
from sirius.models.db import db
from sirius.web import webapp


# pylint: disable=no-member
class Base(testing.TestCase):
    """Common base class for tests that require database interactions."""

    def create_app(self):
        app = webapp.create_app("test")
        return app

    def setUp(self):
        testing.TestCase.setUp(self)
        db.create_all()
        db.session.begin_nested()
        self.testuser = user.User(
            username="testuser",
            twitter_oauth=user.TwitterOAuth(
                screen_name="testuser",
                token="token",
                token_secret="token_secret",
            ),
        )
        db.session.add(self.testuser)
        db.session.flush()
        db.session.refresh(self.testuser)

    def tearDown(self):
        db.session.rollback()
        db.session.remove()
        db.drop_all()

    def autologin(self):
        # Most disgusting hack but I see no other way to log in users:
        # Flask session doesn't pick up the cookies if I call just
        # login_user. The login_user call needs to be embedded in a
        # request.
        @self.app.route("/autologin")
        def autologin():
            login.login_user(self.testuser)
            return ""

        self.client.get("/autologin")
