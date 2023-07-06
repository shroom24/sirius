from unittest import mock

import flask_testing as testing
import flask_login as login

from sirius.models.db import db
from sirius.web import webapp
from sirius.web import twitter


# pylint: disable=no-member
class TestOAuthFlow(testing.TestCase):
    def setUp(self):
        testing.TestCase.setUp(self)
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        app = webapp.create_app("test")
        return app

    @mock.patch("twitter.get_self")
    def test_oauth_authorized(self, get_self_mock):
        get_self_mock.return_value = {"username": "test_screen_name"}
        self.assertEqual(login.current_user.is_authenticated, False)
        twitter.process_authorization(
            {"access_token": "token"},
            "/next_url",
        )
        self.assertEqual(login.current_user.username, "test_screen_name")
        self.assertEqual(login.current_user.is_authenticated, True)
