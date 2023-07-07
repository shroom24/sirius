import io
import base64

import flask
import flask_login as login
import flask_wtf
import wtforms

from sirius.models import hardware
from sirius.coding import image_encoding
from sirius.coding import templating
from sirius import stats


blueprint = flask.Blueprint("printer_print", __name__)


class PrintForm(flask_wtf.FlaskForm):
    target_printer = wtforms.SelectField(
        "Printer",
        coerce=int,
        validators=[wtforms.validators.DataRequired()],
    )
    face = wtforms.SelectField(
        "Face",
        coerce=str,
        validators=[wtforms.validators.DataRequired()],
    )
    message = wtforms.TextAreaField(
        "Message",
        validators=[wtforms.validators.DataRequired()],
    )


@login.login_required
@blueprint.route("/printer/<int:printer_id>/print", methods=["GET", "POST"])
def printer_print(printer_id):
    printer = hardware.Printer.query.get(printer_id)
    if printer is None:
        flask.abort(404)

    # PERMISSIONS
    # the printer must either belong to this user
    if printer.owner.id == login.current_user.id:
        # fine
        pass
    else:
        flask.abort(404)

    form = PrintForm()
    # Note that the form enforces access permissions: People can't
    # submit a valid printer-id that's not owned by the user.
    choices = [(x.id, x.name) for x in login.current_user.printers]
    form.target_printer.choices = choices
    form.face.choices = [("default", "Default face"), ("noface", "No face")]

    # Set default printer on get
    if flask.request.method != "POST":
        form.target_printer.data = printer.id
        form.face.data = "default"

    if form.validate_on_submit():
        try:
            printer.print_html(
                html=form.message.data,
                from_name="@" + login.current_user.username,
            )
            flask.flash("Sent your message to the printer!")
        except hardware.Printer.OfflineError:
            flask.flash(
                "Could not send message because the printer {} is offline.".format(
                    printer.name
                ),
                "error",
            )

        return flask.redirect(
            flask.url_for("printer_overview.printer_overview", printer_id=printer.id)
        )

    return flask.render_template(
        "printer_print.html",
        printer=printer,
        form=form,
    )


@blueprint.route(
    "/<int:user_id>/<username>/printer/<int:printer_id>/preview", methods=["POST"]
)
@login.login_required
def preview(user_id, username, printer_id):
    assert user_id == login.current_user.id
    assert username == login.current_user.username

    message = flask.request.data.decode("utf-8")
    pixels = image_encoding.default_pipeline(
        templating.default_template(message, from_name=login.current_user.username)
    )
    png = io.BytesIO()
    pixels.save(png, "PNG")

    stats.inc("printer.preview")

    return '<img style="width: 100%;" src="data:image/png;base64,{}">'.format(
        base64.b64encode(png.getvalue()).decode("utf-8")
    )
