import base64
import hashlib
import io
import re
import hmac
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import make_msgid

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy import or_, update
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.two_factor_challenge import TwoFactorChallenge
from app.models.two_factor_recovery_code import TwoFactorRecoveryCode
from app.models.user import User

EMAIL_METHOD = "email"
TOTP_METHOD = "totp"

# Email is the only delivery channel. SMS and WhatsApp verification were
# removed in v1: both need a provider account that in practice requires a
# registered business entity, and delivery to Lebanese carriers through
# international aggregators is unreliable even once that exists. The
# coding plan's "cut permanently" table records the decision; the phone
# number is still collected, and the UI says it is not verified.
#
# Kept as a set rather than collapsed into a bare == comparison: it is
# what separates a "code was sent somewhere" challenge from a TOTP one
# throughout this module, and it is the seam a future channel slots into.
DELIVERY_METHODS = {
    EMAIL_METHOD,
}

SUPPORTED_METHODS = {
    EMAIL_METHOD,
    TOTP_METHOD,
}

LOGIN_PURPOSE = "login"
SETUP_PURPOSE = "setup"
SECURITY_PURPOSE = "security"
REGISTRATION_PURPOSE = "registration"
PASSWORD_RESET_PURPOSE = "password_reset"  # nosec B105

PASSWORD_RESET_MIN_LENGTH = 8


class TwoFactorError(Exception):
    status_code = 400

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class TwoFactorRateLimitError(TwoFactorError):
    status_code = 429


class TwoFactorConfigurationError(TwoFactorError):
    status_code = 503


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def issue_auth_tokens(user):
    return {
        "access_token": create_access_token(
            identity=str(user.id),
            additional_claims={
                "role": user.role,
            },
        ),
        "refresh_token": create_refresh_token(identity=str(user.id)),
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
        },
    }


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _challenge_expiration():
    return utcnow() + timedelta(
        seconds=current_app.config["TWO_FACTOR_CHALLENGE_TTL_SECONDS"]
    )


def _generate_verification_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def _normalize_code(code):
    return str(code or "").strip()


def _normalize_recovery_code(code):
    return re.sub(
        r"[^A-Za-z0-9]",
        "",
        _normalize_code(code),
    ).upper()


def _challenge_payload(challenge, challenge_token, **extra):
    payload = {
        "challenge_token": challenge_token,
        "method": challenge.method,
        "expires_at": challenge.expires_at.isoformat(),
    }

    payload.update(extra)

    return payload


def _fernet():
    key = current_app.config.get("TWO_FACTOR_ENCRYPTION_KEY")

    if not key:
        raise TwoFactorConfigurationError(
            "TOTP is unavailable until "
            "TWO_FACTOR_ENCRYPTION_KEY is configured"
        )

    try:
        return Fernet(key.encode("utf-8"))

    except (
        TypeError,
        ValueError,
    ) as error:
        raise TwoFactorConfigurationError(
            "TWO_FACTOR_ENCRYPTION_KEY is invalid"
        ) from error


def encrypt_totp_secret(secret):
    return _fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_totp_secret(encrypted_secret):
    if not encrypted_secret:
        raise TwoFactorError("Authenticator setup is unavailable")

    try:
        return (
            _fernet().decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")
        )

    except InvalidToken as error:
        raise TwoFactorError("Authenticator setup is invalid") from error


def _build_qr_code_data_url(provisioning_uri):
    image = qrcode.make(provisioning_uri)

    image_buffer = io.BytesIO()

    image.save(
        image_buffer,
        format="PNG",
    )

    encoded_image = base64.b64encode(image_buffer.getvalue()).decode("ascii")

    return "data:image/png;base64," f"{encoded_image}"


def _challenge_ttl_minutes():
    """The challenge lifetime in whole minutes, floored at 1 -- the text
    and HTML halves of the email have to quote the same number."""
    ttl_seconds = current_app.config["TWO_FACTOR_CHALLENGE_TTL_SECONDS"]

    return max(
        1,
        ttl_seconds // 60,
    )


def _verification_message(code):
    ttl_minutes = _challenge_ttl_minutes()

    return (
        f"Your CedarLink verification code is: {code}\n\n"
        f"It expires in {ttl_minutes} minutes. "
        "Do not share this code with anyone."
    )


def _load_email_logo():
    """The CedarLink logo bytes for the verification email, or ``None``.

    Never raises. A decorative asset is not allowed to stand between a
    user and their account, so a missing or unreadable file degrades to a
    logo-less email rather than failing the send.
    """
    path = current_app.config.get("MAIL_LOGO_PATH")

    if not path:
        return None

    try:
        with open(path, "rb") as logo_file:
            return logo_file.read()

    except OSError:
        current_app.logger.warning(
            "Verification email logo could not be read from %s -- "
            "sending without it",
            path,
        )

        return None


# Hex, not the oklch() design tokens in frontend/src/index.css: mail
# clients support neither oklch nor CSS custom properties, so these are
# the literal equivalents of --color-brand (emerald-700) and friends.
# Keep them in step with the token file by hand -- there is no build step
# that can do it for an email.
_MAIL_BRAND = "#047857"
_MAIL_BRAND_SUBTLE = "#ecfdf5"
_MAIL_BRAND_TINT = "#d1fae5"
_MAIL_TEXT_PRIMARY = "#111827"
_MAIL_TEXT_SECONDARY = "#4b5563"
_MAIL_TEXT_MUTED = "#6b7280"
_MAIL_SURFACE = "#f9fafb"
_MAIL_BORDER = "#e5e7eb"

_MAIL_FONT = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "Helvetica, Arial, sans-serif"
)


def _verification_email_html(code, ttl_minutes, logo_cid=None):
    """The branded HTML alternative for the verification email.

    Tables and inline styles on purpose: mail clients strip <style>
    blocks unpredictably and flexbox/grid support is patchy, so this is
    deliberately written like it is 2009. Nothing is loaded from the
    network -- the only image is the CID part attached alongside.
    """
    if logo_cid:
        # cid: references the part without its angle brackets.
        logo_block = (
            f'<img src="cid:{logo_cid[1:-1]}" width="56" alt="CedarLink" '
            'style="display:block;width:56px;height:auto;border:0;'
            'margin:0 auto;">'
        )
    else:
        logo_block = ""

    return f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:{_MAIL_SURFACE};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           border="0" style="background-color:{_MAIL_SURFACE};
           padding:32px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" cellpadding="0" cellspacing="0"
                 border="0" width="100%"
                 style="max-width:480px;background-color:#ffffff;
                 border:1px solid {_MAIL_BORDER};border-radius:12px;">
            <tr>
              <td align="center" style="padding:32px 32px 0 32px;">
                {logo_block}
                <div style="font-family:{_MAIL_FONT};font-size:20px;
                     font-weight:700;color:{_MAIL_BRAND};padding-top:12px;">
                  CedarLink
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 32px 0 32px;font-family:{_MAIL_FONT};
                  font-size:15px;line-height:22px;
                  color:{_MAIL_TEXT_SECONDARY};">
                Use this code to verify your CedarLink account.
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:20px 32px;">
                <div style="font-family:'SFMono-Regular',Consolas,
                     'Liberation Mono',Menlo,monospace;font-size:30px;
                     font-weight:700;letter-spacing:8px;text-indent:8px;
                     color:{_MAIL_TEXT_PRIMARY};
                     background-color:{_MAIL_BRAND_SUBTLE};
                     border:1px solid {_MAIL_BRAND_TINT};border-radius:8px;
                     padding:16px 12px;">
                  {code}
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 24px 32px;font-family:{_MAIL_FONT};
                  font-size:13px;line-height:20px;color:{_MAIL_TEXT_MUTED};">
                It expires in {ttl_minutes} minutes. Do not share this code
                with anyone &mdash; CedarLink will never ask you for it.
              </td>
            </tr>
          </table>
          <div style="font-family:{_MAIL_FONT};font-size:12px;
               color:{_MAIL_TEXT_MUTED};padding-top:16px;">
            If you did not request this, you can ignore this email.
          </div>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def send_email_verification_code(user, code):
    message = EmailMessage()

    message["Subject"] = "Your CedarLink verification code"

    message["From"] = (
        current_app.config.get("MAIL_FROM") or "no-reply@cedarlink.local"
    )

    message["To"] = user.email

    # text/plain stays the body; the branded HTML is an alternative, so a
    # plain-text client still gets a perfectly readable code.
    message.set_content(_verification_message(code))

    logo_bytes = _load_email_logo()

    logo_cid = make_msgid(domain="cedarlink.local") if logo_bytes else None

    message.add_alternative(
        _verification_email_html(
            code,
            _challenge_ttl_minutes(),
            logo_cid,
        ),
        subtype="html",
    )

    if logo_bytes:
        # add_related turns the HTML part into multipart/related so the
        # logo travels inside the message: there is no public URL to link
        # to yet, and mail clients strip data: URIs.
        message.get_payload()[-1].add_related(
            logo_bytes,
            maintype="image",
            subtype="png",
            cid=logo_cid,
            filename="cedarlink-logo.png",
        )

    if current_app.config.get(
        "MAIL_SUPPRESS_SEND",
        False,
    ):
        current_app.logger.warning(
            "Development email verification code " "for %s: %s",
            user.email,
            code,
        )

        return

    mail_server = current_app.config.get("MAIL_SERVER")

    if not mail_server:
        raise TwoFactorConfigurationError(
            "Email verification requires MAIL_SERVER "
            "or MAIL_SUPPRESS_SEND=true"
        )

    try:
        if current_app.config.get(
            "MAIL_USE_SSL",
            False,
        ):
            smtp_client = smtplib.SMTP_SSL(
                mail_server,
                current_app.config.get(
                    "MAIL_PORT",
                    465,
                ),
                timeout=10,
                context=ssl.create_default_context(),
            )

        else:
            smtp_client = smtplib.SMTP(
                mail_server,
                current_app.config.get(
                    "MAIL_PORT",
                    587,
                ),
                timeout=10,
            )

        with smtp_client as server:
            if current_app.config.get(
                "MAIL_USE_TLS",
                False,
            ) and not current_app.config.get(
                "MAIL_USE_SSL",
                False,
            ):
                server.starttls(context=ssl.create_default_context())

            if current_app.config.get("MAIL_USERNAME"):
                server.login(
                    current_app.config["MAIL_USERNAME"],
                    current_app.config.get("MAIL_PASSWORD") or "",
                )

            server.send_message(message)

    except (
        OSError,
        smtplib.SMTPException,
    ) as error:
        raise TwoFactorConfigurationError(
            "Unable to send the verification email. " "Please try again later."
        ) from error


def _send_verification_code(user, method, code):
    if method == EMAIL_METHOD:
        send_email_verification_code(
            user,
            code,
        )
        return

    raise TwoFactorError("Unsupported verification method")


def _invalidate_active_challenges(user_id, purpose):
    TwoFactorChallenge.query.filter(
        TwoFactorChallenge.user_id == user_id,
        TwoFactorChallenge.purpose == purpose,
        TwoFactorChallenge.consumed_at.is_(None),
    ).update(
        {
            "consumed_at": utcnow(),
        }
    )


def _new_challenge(
    user,
    purpose,
    method,
    code_hash=None,
    encrypted_secret=None,
):
    _invalidate_active_challenges(
        user.id,
        purpose,
    )

    challenge_token = secrets.token_urlsafe(32)

    now = utcnow()

    challenge = TwoFactorChallenge(
        user_id=user.id,
        token_hash=_token_hash(challenge_token),
        purpose=purpose,
        method=method,
        code_hash=code_hash,
        totp_secret_encrypted=encrypted_secret,
        expires_at=_challenge_expiration(),
        send_count=(1 if method in DELIVERY_METHODS else 0),
        last_sent_at=(now if method in DELIVERY_METHODS else None),
    )

    db.session.add(challenge)

    return (
        challenge,
        challenge_token,
    )


def _create_delivery_challenge(user, purpose, method):
    if method not in DELIVERY_METHODS:
        raise TwoFactorError("Unsupported verification method")

    code = _generate_verification_code()

    challenge, challenge_token = _new_challenge(
        user,
        purpose,
        method,
        code_hash=generate_password_hash(code),
    )

    try:
        _send_verification_code(
            user,
            method,
            code,
        )

        db.session.commit()

    except (
        TwoFactorError,
        TwoFactorConfigurationError,
    ):
        db.session.rollback()
        raise

    except Exception as error:
        db.session.rollback()

        raise TwoFactorConfigurationError(
            "Unable to send the verification code"
        ) from error

    extra = {}

    if method == EMAIL_METHOD:
        extra["email"] = user.email

    return _challenge_payload(
        challenge,
        challenge_token,
        **extra,
    )


def _create_totp_challenge(user, purpose, encrypted_secret=None):
    challenge, challenge_token = _new_challenge(
        user,
        purpose,
        TOTP_METHOD,
        encrypted_secret=encrypted_secret,
    )

    db.session.commit()

    return _challenge_payload(
        challenge,
        challenge_token,
    )


def create_registration_challenge(user, method):
    method = str(method or "").strip().lower()

    if method not in DELIVERY_METHODS:
        raise TwoFactorError("Unsupported verification method")

    return _create_delivery_challenge(
        user,
        REGISTRATION_PURPOSE,
        method,
    )


def decoy_registration_challenge(email, phone, method):
    """A registration response for an email that is already taken.

    Same shape as a real ``create_registration_challenge`` payload, so
    ``/register`` cannot be used to tell which emails exist (CL-10). No user
    row, no code, no message sent — the challenge_token verifies to nothing.
    """
    method = str(method or "").strip().lower()

    payload = {
        "challenge_token": secrets.token_urlsafe(32),
        "method": method,
        "expires_at": _challenge_expiration().isoformat(),
    }

    if method == EMAIL_METHOD:
        payload["email"] = email

    return payload


def verify_registration_challenge(challenge_token, code):
    challenge = _get_active_challenge(
        challenge_token,
        REGISTRATION_PURPOSE,
    )

    user = challenge.user

    if not _verify_challenge_code(
        challenge,
        user,
        code,
    ):
        _record_failed_attempt(challenge)

        raise TwoFactorError("Verification code is invalid")

    challenge.consumed_at = utcnow()

    user.is_verified = True

    db.session.commit()

    return user


def resend_registration_code(challenge_token):
    return _resend_delivery_code(
        challenge_token,
        REGISTRATION_PURPOSE,
    )


def _account_can_reset(user):
    """Whether a password reset may be started for this account.

    Suspended and never-verified accounts are refused as well as deleted
    and deactivated ones: a suspension is an admin decision that should
    reach every credential path, and mailing a code to an address whose
    ownership was never confirmed sends mail the platform cannot vouch
    for. The refusal is invisible to the caller -- request_password_reset
    returns the same decoy payload for all four reasons, so this is not an
    account-status oracle. See docs/decisions/0020-two-factor-corrections.
    """
    return (
        user is not None
        and user.deleted_at is None
        and user.is_active
        and user.suspended_at is None
        and user.is_verified
    )


def request_password_reset(email):
    """Start a password-reset challenge for a registered, active account.

    Returns a challenge payload either way: a real one when the email
    belongs to an account that may reset, and an indistinguishable decoy
    otherwise, so the caller cannot use this to probe for accounts. The
    verification code only ever reaches a real account, by email.
    """
    email = str(email or "").strip().lower()

    user = (
        User.query.filter_by(email=email).first()
        if email
        else None
    )

    if _account_can_reset(user):
        try:
            return _create_delivery_challenge(
                user,
                PASSWORD_RESET_PURPOSE,
                EMAIL_METHOD,
            )

        except (TwoFactorError, TwoFactorConfigurationError):
            current_app.logger.exception(
                "Password reset delivery failed for a registered account"
            )

    return {
        "challenge_token": secrets.token_urlsafe(32),
        "method": EMAIL_METHOD,
    }


def reset_password(challenge_token, code, new_password):
    """Consume a password-reset challenge and set a new password hash."""
    new_password = str(new_password or "")

    if len(new_password) < PASSWORD_RESET_MIN_LENGTH:
        raise TwoFactorError(
            "Password must be at least "
            f"{PASSWORD_RESET_MIN_LENGTH} characters long"
        )

    challenge = _get_active_challenge(
        challenge_token,
        PASSWORD_RESET_PURPOSE,
    )

    user = challenge.user

    if not _account_can_reset(user):
        challenge.consumed_at = utcnow()

        db.session.commit()

        raise TwoFactorError("This account can no longer be reset")

    if not _verify_challenge_code(
        challenge,
        user,
        code,
    ):
        _record_failed_attempt(challenge)

        raise TwoFactorError("Verification code is invalid")

    user.password = generate_password_hash(new_password)

    # Every token issued before now is dead — a stolen session cannot
    # outlive the password it was riding on (CL-09).
    user.tokens_revoked_at = utcnow()

    # Single use — the challenge cannot be replayed.
    challenge.consumed_at = utcnow()

    db.session.commit()

    return user


def start_setup(user, method=None):
    if not method:
        method = EMAIL_METHOD

    method = str(method).strip().lower()

    if method not in SUPPORTED_METHODS:
        raise TwoFactorError("Unsupported two-factor method")

    if method == EMAIL_METHOD:
        return _create_delivery_challenge(
            user,
            SETUP_PURPOSE,
            EMAIL_METHOD,
        )

    secret = pyotp.random_base32()

    encrypted_secret = encrypt_totp_secret(secret)

    payload = _create_totp_challenge(
        user,
        SETUP_PURPOSE,
        encrypted_secret,
    )

    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name=current_app.config["TWO_FACTOR_ISSUER"],
    )

    payload["manual_key"] = secret

    payload["qr_code_data_url"] = _build_qr_code_data_url(provisioning_uri)

    return payload


def create_login_challenge(user):
    # A configured second factor wins over verification_method. The two
    # fields answer different questions -- two_factor_method is the factor
    # the user chose, verification_method is how the account was confirmed
    # at registration -- and confirm_setup never rewrites the latter, so
    # reading it first downgraded every TOTP user to an emailed code.
    # See docs/decisions/0020-two-factor-corrections.md.
    if user.two_factor_enabled and user.two_factor_method in SUPPORTED_METHODS:
        if user.two_factor_method == EMAIL_METHOD:
            return _create_delivery_challenge(
                user,
                LOGIN_PURPOSE,
                EMAIL_METHOD,
            )

        return _create_totp_challenge(
            user,
            LOGIN_PURPOSE,
        )

    method = getattr(
        user,
        "verification_method",
        None,
    )

    # An account confirmed by SMS or WhatsApp before those channels were
    # removed must not be locked out of its own login: the stored method
    # can no longer deliver, so fall back to the email address the
    # account already has. Registration verified the person either way.
    if method and method not in DELIVERY_METHODS and method != TOTP_METHOD:
        method = EMAIL_METHOD

    if method in DELIVERY_METHODS:
        return _create_delivery_challenge(
            user,
            LOGIN_PURPOSE,
            method,
        )

    raise TwoFactorError("No verification method is configured")


def create_security_challenge(user):
    if (
        not user.two_factor_enabled
        or user.two_factor_method not in SUPPORTED_METHODS
    ):
        raise TwoFactorError("Two-factor authentication is not enabled")

    if user.two_factor_method == EMAIL_METHOD:
        return _create_delivery_challenge(
            user,
            SECURITY_PURPOSE,
            EMAIL_METHOD,
        )

    return _create_totp_challenge(
        user,
        SECURITY_PURPOSE,
    )


def _get_active_challenge(challenge_token, purpose):
    if not challenge_token:
        raise TwoFactorError("Verification challenge is required")

    challenge = TwoFactorChallenge.query.filter_by(
        token_hash=_token_hash(challenge_token),
        purpose=purpose,
        consumed_at=None,
    ).first()

    if not challenge:
        raise TwoFactorError(
            "Verification challenge is invalid " "or has already been used"
        )

    if challenge.expires_at <= utcnow():
        challenge.consumed_at = utcnow()

        db.session.commit()

        raise TwoFactorError("Verification challenge has expired")

    if (
        challenge.attempt_count
        >= current_app.config["TWO_FACTOR_MAX_ATTEMPTS"]
    ):
        challenge.consumed_at = utcnow()

        db.session.commit()

        raise TwoFactorRateLimitError("Too many verification attempts")

    return challenge


def _record_failed_attempt(challenge):
    challenge.attempt_count += 1

    if (
        challenge.attempt_count
        >= current_app.config["TWO_FACTOR_MAX_ATTEMPTS"]
    ):
        challenge.consumed_at = utcnow()

    db.session.commit()


def _matching_totp_counter(secret, code, valid_window=1):
    """The TOTP time step ``code`` verifies against, or None.

    ``pyotp.TOTP.verify`` only answers yes/no, so enforcing one-time use
    means finding *which* step matched. This walks the same window verify()
    walks -- the current step plus/minus ``valid_window`` -- and compares
    each step's code in constant time.
    """
    code = _normalize_code(code)

    if not code:
        return None

    totp = pyotp.TOTP(secret)

    step_seconds = totp.interval

    current_step = int(datetime.now(timezone.utc).timestamp()) // step_seconds

    for offset in range(-valid_window, valid_window + 1):
        step = current_step + offset

        if hmac.compare_digest(totp.at(step * step_seconds), code):
            return step

    return None


def _claim_totp_counter(user, counter):
    """Claim ``counter`` as this user's newest accepted TOTP time step.

    RFC 6238 s5.2: a code is accepted at most once. Consuming the challenge
    is not enough on its own -- an attacker who observes a code can open a
    *fresh* challenge and replay it there for the rest of the window. The
    last accepted step is a high-water mark, and steps only move forward,
    so refusing anything at or below it closes the replay.

    The comparison belongs *in* the statement. Read-compare-write loses
    updates: two logins presenting the same code can both read the old
    value, both find it lower, and both accept -- exactly the oversell
    shape from ADR 0007. Here the database picks the winner, and a
    rowcount of 0 means somebody else claimed this step first, which is
    precisely the replay we are refusing.

    Returns True when this call claimed the step.
    """
    claimed = db.session.execute(
        update(User)
        .where(
            User.id == user.id,
            or_(
                User.two_factor_last_totp_counter.is_(None),
                User.two_factor_last_totp_counter < counter,
            ),
        )
        .values(two_factor_last_totp_counter=counter)
        .execution_options(synchronize_session=False)
    )

    return claimed.rowcount == 1


def _verify_challenge_code(challenge, user, code):
    code = _normalize_code(code)

    if challenge.method in DELIVERY_METHODS:
        return bool(code) and check_password_hash(
            challenge.code_hash,
            code,
        )

    encrypted_secret = (
        challenge.totp_secret_encrypted
        if challenge.purpose == SETUP_PURPOSE
        else user.two_factor_totp_secret
    )

    try:
        secret = decrypt_totp_secret(encrypted_secret)

    except TwoFactorError:
        return False

    counter = _matching_totp_counter(secret, code)

    if counter is None:
        return False

    return _claim_totp_counter(user, counter)


def _consume_recovery_code(user, code):
    normalized_code = _normalize_recovery_code(code)

    if not normalized_code:
        return False

    recovery_codes = TwoFactorRecoveryCode.query.filter_by(
        user_id=user.id,
        used=False,
    ).all()

    for recovery_code in recovery_codes:
        if check_password_hash(
            recovery_code.code_hash,
            normalized_code,
        ):
            recovery_code.used = True

            recovery_code.used_at = utcnow()

            return True

    return False


def _verify_challenge(challenge, user, code, use_recovery_code):
    if use_recovery_code:
        is_valid = _consume_recovery_code(
            user,
            code,
        )

    else:
        is_valid = _verify_challenge_code(
            challenge,
            user,
            code,
        )

    if not is_valid:
        _record_failed_attempt(challenge)

        raise TwoFactorError("Verification code is invalid")

    challenge.consumed_at = utcnow()


def verify_login_challenge(challenge_token, code, use_recovery_code=False):
    challenge = _get_active_challenge(
        challenge_token,
        LOGIN_PURPOSE,
    )

    _verify_challenge(
        challenge,
        challenge.user,
        code,
        use_recovery_code,
    )

    db.session.commit()

    return challenge.user


def verify_security_challenge(
    user, challenge_token, code, use_recovery_code=False
):
    challenge = _get_active_challenge(
        challenge_token,
        SECURITY_PURPOSE,
    )

    if challenge.user_id != user.id:
        raise TwoFactorError(
            "Verification challenge " "does not belong to this user"
        )

    _verify_challenge(
        challenge,
        user,
        code,
        use_recovery_code,
    )

    db.session.commit()


def _format_recovery_code():
    raw_code = secrets.token_hex(8).upper()

    return "-".join(
        raw_code[index: index + 4]
        for index in range(
            0,
            16,
            4,
        )
    )


def generate_recovery_codes(user, count=10):
    TwoFactorRecoveryCode.query.filter_by(user_id=user.id).delete()

    plaintext_codes = [_format_recovery_code() for _ in range(count)]

    for code in plaintext_codes:
        db.session.add(
            TwoFactorRecoveryCode(
                user_id=user.id,
                code_hash=generate_password_hash(
                    _normalize_recovery_code(code)
                ),
            )
        )

    return plaintext_codes


def confirm_setup(user, challenge_token, code):
    challenge = _get_active_challenge(
        challenge_token,
        SETUP_PURPOSE,
    )

    if challenge.user_id != user.id:
        raise TwoFactorError(
            "Verification challenge " "does not belong to this user"
        )

    if not _verify_challenge_code(
        challenge,
        user,
        code,
    ):
        _record_failed_attempt(challenge)

        raise TwoFactorError("Verification code is invalid")

    user.two_factor_enabled = True

    user.two_factor_method = challenge.method

    user.two_factor_totp_secret = (
        challenge.totp_secret_encrypted
        if challenge.method == TOTP_METHOD
        else None
    )

    challenge.consumed_at = utcnow()

    recovery_codes = generate_recovery_codes(user)

    db.session.commit()

    return recovery_codes


def _resend_delivery_code(challenge_token, purpose):
    challenge = _get_active_challenge(
        challenge_token,
        purpose,
    )

    if challenge.method not in DELIVERY_METHODS:
        raise TwoFactorError("This verification method cannot be resent")

    now = utcnow()

    cooldown = current_app.config["TWO_FACTOR_EMAIL_RESEND_COOLDOWN_SECONDS"]

    if challenge.last_sent_at:
        elapsed_seconds = (now - challenge.last_sent_at).total_seconds()

        if elapsed_seconds < cooldown:
            raise TwoFactorRateLimitError(
                "Please wait before requesting another code",
                retry_after=int(cooldown - elapsed_seconds),
            )

    if (
        challenge.send_count
        >= current_app.config["TWO_FACTOR_MAX_EMAIL_SENDS"]
    ):
        raise TwoFactorRateLimitError("Too many verification codes requested")

    code = _generate_verification_code()

    challenge.code_hash = generate_password_hash(code)

    challenge.expires_at = _challenge_expiration()

    challenge.attempt_count = 0

    challenge.send_count += 1

    challenge.last_sent_at = now

    try:
        _send_verification_code(
            challenge.user,
            challenge.method,
            code,
        )

        db.session.commit()

    except (
        TwoFactorError,
        TwoFactorConfigurationError,
    ):
        db.session.rollback()
        raise

    except Exception as error:
        db.session.rollback()

        raise TwoFactorConfigurationError(
            "Unable to resend the verification code"
        ) from error

    return {
        "expires_at": (challenge.expires_at.isoformat()),
        "retry_after": cooldown,
    }


def resend_login_code(challenge_token):
    return _resend_delivery_code(
        challenge_token,
        LOGIN_PURPOSE,
    )


def resend_login_email_code(challenge_token):
    return resend_login_code(challenge_token)


def resend_registration_email_code(challenge_token):
    return resend_registration_code(challenge_token)


def disable_two_factor(user):
    user.two_factor_enabled = False

    user.two_factor_method = None

    user.two_factor_totp_secret = None

    TwoFactorRecoveryCode.query.filter_by(user_id=user.id).delete()

    db.session.commit()
