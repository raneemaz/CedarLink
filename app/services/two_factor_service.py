import base64
import hashlib
import io
import re
import secrets
import smtplib
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.two_factor_challenge import TwoFactorChallenge
from app.models.two_factor_recovery_code import TwoFactorRecoveryCode
from app.models.user import User

EMAIL_METHOD = "email"
SMS_METHOD = "sms"
WHATSAPP_METHOD = "whatsapp"
TOTP_METHOD = "totp"

DELIVERY_METHODS = {
    EMAIL_METHOD,
    SMS_METHOD,
    WHATSAPP_METHOD,
}

SUPPORTED_METHODS = {
    EMAIL_METHOD,
    TOTP_METHOD,
}

LOGIN_PURPOSE = "login"
SETUP_PURPOSE = "setup"
SECURITY_PURPOSE = "security"
REGISTRATION_PURPOSE = "registration"
PASSWORD_RESET_PURPOSE = "password_reset"

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


def _verification_message(code):
    ttl_seconds = current_app.config["TWO_FACTOR_CHALLENGE_TTL_SECONDS"]

    ttl_minutes = max(
        1,
        ttl_seconds // 60,
    )

    return (
        f"Your CedarLink verification code is: {code}\n\n"
        f"It expires in {ttl_minutes} minutes. "
        "Do not share this code with anyone."
    )


def send_email_verification_code(user, code):
    message = EmailMessage()

    message["Subject"] = "Your CedarLink verification code"

    message["From"] = (
        current_app.config.get("MAIL_FROM") or "no-reply@cedarlink.local"
    )

    message["To"] = user.email

    message.set_content(_verification_message(code))

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


def _twilio_request(url, account_sid, auth_token, data):
    encoded_data = urllib.parse.urlencode(data).encode("utf-8")

    credentials = base64.b64encode(
        f"{account_sid}:{auth_token}".encode()
    ).decode("utf-8")

    request_object = urllib.request.Request(
        url,
        data=encoded_data,
        method="POST",
        headers={
            "Authorization": (f"Basic {credentials}"),
            "Content-Type": ("application/x-www-form-urlencoded"),
        },
    )

    try:
        with urllib.request.urlopen(
            request_object,
            timeout=15,
        ) as response:
            return response.read()

    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        OSError,
    ) as error:
        raise TwoFactorConfigurationError(
            "Unable to send the verification code. " "Please try again later."
        ) from error


def send_sms_verification_code(user, code):
    if not user.phone:
        raise TwoFactorError("A phone number is required for SMS verification")

    if current_app.config.get(
        "SMS_SUPPRESS_SEND",
        False,
    ):
        current_app.logger.warning(
            "Development SMS verification code " "for %s: %s",
            user.phone,
            code,
        )

        return

    account_sid = current_app.config.get("TWILIO_ACCOUNT_SID")

    auth_token = current_app.config.get("TWILIO_AUTH_TOKEN")

    from_number = current_app.config.get("TWILIO_SMS_FROM")

    if not all(
        [
            account_sid,
            auth_token,
            from_number,
        ]
    ):
        raise TwoFactorConfigurationError(
            "SMS verification requires "
            "TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, and "
            "TWILIO_SMS_FROM"
        )

    url = (
        "https://api.twilio.com/2010-04-01/"
        f"Accounts/{account_sid}/Messages.json"
    )

    _twilio_request(
        url,
        account_sid,
        auth_token,
        {
            "To": user.phone,
            "From": from_number,
            "Body": _verification_message(code),
        },
    )


def send_whatsapp_verification_code(user, code):
    if not user.phone:
        raise TwoFactorError(
            "A phone number is required for WhatsApp verification"
        )

    if current_app.config.get(
        "WHATSAPP_SUPPRESS_SEND",
        False,
    ):
        current_app.logger.warning(
            "Development WhatsApp verification code " "for %s: %s",
            user.phone,
            code,
        )

        return

    account_sid = current_app.config.get("TWILIO_ACCOUNT_SID")

    auth_token = current_app.config.get("TWILIO_AUTH_TOKEN")

    from_number = current_app.config.get("TWILIO_WHATSAPP_FROM")

    if not all(
        [
            account_sid,
            auth_token,
            from_number,
        ]
    ):
        raise TwoFactorConfigurationError(
            "WhatsApp verification requires "
            "TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, and "
            "TWILIO_WHATSAPP_FROM"
        )

    url = (
        "https://api.twilio.com/2010-04-01/"
        f"Accounts/{account_sid}/Messages.json"
    )

    _twilio_request(
        url,
        account_sid,
        auth_token,
        {
            "To": (
                user.phone
                if user.phone.startswith("whatsapp:")
                else f"whatsapp:{user.phone}"
            ),
            "From": (
                from_number
                if from_number.startswith("whatsapp:")
                else f"whatsapp:{from_number}"
            ),
            "Body": _verification_message(code),
        },
    )


def _send_verification_code(user, method, code):
    if method == EMAIL_METHOD:
        send_email_verification_code(
            user,
            code,
        )
        return

    if method == SMS_METHOD:
        send_sms_verification_code(
            user,
            code,
        )
        return

    if method == WHATSAPP_METHOD:
        send_whatsapp_verification_code(
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

    if method in {
        SMS_METHOD,
        WHATSAPP_METHOD,
    }:
        extra["phone"] = user.phone

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
    elif method in {SMS_METHOD, WHATSAPP_METHOD}:
        payload["phone"] = phone

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
    return (
        user is not None
        and user.deleted_at is None
        and user.is_active
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
    method = getattr(
        user,
        "verification_method",
        None,
    )

    if method in DELIVERY_METHODS:
        return _create_delivery_challenge(
            user,
            LOGIN_PURPOSE,
            method,
        )

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

    return pyotp.TOTP(secret).verify(
        code,
        valid_window=1,
    )


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
