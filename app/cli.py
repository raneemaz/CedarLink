"""Custom Flask CLI commands.

These run with `flask <command>` and require server/database access, so they
are the safe place to perform privileged actions that must never be exposed
through a public HTTP endpoint (e.g. creating an administrator).
"""

import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import User

VALID_VERIFICATION_METHODS = ("email", "sms", "whatsapp")
MIN_ADMIN_PASSWORD_LENGTH = 8


@click.command("create-admin")
@click.option("--email", required=True, prompt=True, help="Admin email address.")
@click.option(
    "--password",
    required=True,
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Admin password (min 8 characters).",
)
@click.option("--first-name", required=True, prompt="First name")
@click.option("--last-name", required=True, prompt="Last name")
@click.option("--phone", required=True, prompt=True, help="Admin phone number.")
@click.option(
    "--verification-method",
    default="email",
    show_default=True,
    type=click.Choice(VALID_VERIFICATION_METHODS),
    help="Channel used for the login verification code.",
)
@with_appcontext
def create_admin(
    email,
    password,
    first_name,
    last_name,
    phone,
    verification_method,
):
    """Create an administrator account.

    Administrators cannot be created through public registration. This command
    is the only supported way to bootstrap the first admin.
    """
    email = (email or "").strip().lower()

    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise click.ClickException(
            "Password must be at least "
            f"{MIN_ADMIN_PASSWORD_LENGTH} characters."
        )

    existing = User.query.filter_by(email=email).first()

    if existing:
        raise click.ClickException(
            f"A user with email {email} already exists "
            f"(id={existing.id}, role={existing.role})."
        )

    admin = User(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email,
        password=generate_password_hash(password),
        phone=phone.strip(),
        role="admin",
        # Admins are created out of band by a trusted operator, so the account
        # is verified immediately (no registration email challenge).
        is_verified=True,
        verification_method=verification_method,
    )

    db.session.add(admin)
    db.session.commit()

    click.echo(
        f"Admin account created: {admin.email} (id={admin.id}). "
        f"Login sends a verification code via '{verification_method}'."
    )


def register_cli(app):
    app.cli.add_command(create_admin)
