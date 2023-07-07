import flask
import flask_wtf
import wtforms
import flask_login as login

from sirius.coding import claiming


blueprint = flask.Blueprint("landing", __name__)


class ClaimForm(flask_wtf.FlaskForm):
    claim_code = wtforms.StringField(
        "Claim code",
        validators=[wtforms.validators.DataRequired()],
    )
    printer_name = wtforms.StringField(
        "Name your printer",
        validators=[wtforms.validators.DataRequired()],
    )

    def validate_claim_code(self, field):
        try:
            claiming.unpack_claim_code(field.data)
        except claiming.InvalidClaimCode:
            raise wtforms.validators.ValidationError(
                "`{}` doesn't look like a valid claim code :(".format(field.data)
            )


@blueprint.route("/about")
def about():
    return flask.render_template("about.html")


@blueprint.route("/")
def landing():
    if not login.current_user.is_authenticated:
        return flask.render_template("landing.html")

    return overview()


@login.login_required
def overview():
    user = login.current_user
    my_printers = user.printers.all()

    return flask.render_template("overview.html", my_printers=my_printers)


@blueprint.route("/<int:user_id>/<username>/claim", methods=["GET", "POST"])
@login.login_required
def claim(user_id, username):
    user = login.current_user
    assert user_id == user.get_id()
    assert username == user.username

    form = ClaimForm()
    if form.validate_on_submit():
        user.claim_printer(form.claim_code.data, form.printer_name.data)
        return flask.redirect(flask.url_for(".landing"))

    return flask.render_template("claim.html", form=form)


@blueprint.route("/<int:user_id>/<username>/generate_api_key", methods=["POST"])
@login.login_required
def generate_api_key(user_id, username):
    user = login.current_user
    assert user_id == user.get_id()
    assert username == user.username

    user.generate_api_key()
    return flask.redirect(flask.url_for(".landing"))
