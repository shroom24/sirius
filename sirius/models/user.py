"""User models. Login only via twitter for now to avoid the whole
forgot-password/reset-password dance.
"""
import collections
import datetime
import random
import string

from sirius.coding import claiming

from sirius.models.db import db
from sirius.models import hardware


class CannotChangeOwner(Exception):
    pass


class ClaimCodeInUse(Exception):
    pass


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    api_key = db.Column(db.String)

    # username can't be unique because we may have multiple identity
    # providers. For now we just copy the  twitter handle.
    username = db.Column(db.String)
    twitter_oauth = db.relationship(
        "TwitterOAuth", uselist=False, backref=db.backref("user")
    )

    def __repr__(self):
        return "User {}".format(self.username)

    # Flask-login interface:
    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    def get_id(self):
        return self.id

    def generate_api_key(self):
        self.api_key = "".join(
            random.choice(string.ascii_letters + string.digits) for _ in range(32)
        )

    def claim_printer(self, claim_code, name):
        """Claiming can happen before the printer "calls home" for the first
        time so we need to be able to deal with that."""

        # TODO(tom): This method probably belongs to printer, not
        # user. Move at some point.

        claim_code = claiming.canonicalize(claim_code)

        hcc = hardware.ClaimCode.query.filter_by(claim_code=claim_code).first()
        hardware_xor, _ = claiming.process_claim_code(claim_code)

        if hcc is not None and hcc.by != self:
            raise ClaimCodeInUse(
                "Claim code {} already claimed by {}".format(claim_code, hcc.by)
            )

        if hcc is None:
            hcc = hardware.ClaimCode(
                by_id=self.id,
                hardware_xor=hardware_xor,
                claim_code=claim_code,
                name=name,
            )
            db.session.add(hcc)
        else:
            # we already have a claim code, don't do anything.
            pass

        # Check whether we've seen this printer and if so: connect it
        # to claim code and make it "owned" but *only* if it does not
        # have an owner yet.
        printer_query = hardware.Printer.query.filter_by(hardware_xor=hardware_xor)
        printer = printer_query.first()
        if printer is None:
            return

        if printer.owner is not None and printer.owner != self:
            raise CannotChangeOwner(
                "Printer {} already owned by {}. Cannot claim for {}.".format(
                    printer, printer.owner, self
                )
            )

        assert printer_query.count() == 1, "hardware xor collision: {}".format(
            hardware_xor
        )

        printer.used_claim_code = claim_code
        printer.hardware_xor = hardware_xor
        printer.owner_id = hcc.by_id
        printer.name = name
        db.session.add(printer)
        return printer


class TwitterOAuth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    screen_name = db.Column(db.String, unique=True)

    token = db.Column(db.String)
    token_secret = db.Column(db.String)
