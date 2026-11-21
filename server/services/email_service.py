import logging
import smtplib
from email.message import EmailMessage

from config import PASSWORD_RESET_EXPIRE_MINUTES, SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER

logger = logging.getLogger("uvicorn.error")


def send_password_reset_email(to: str, link: str) -> None:
    """Email a password-reset link.

    With no SMTP_HOST configured nothing is sent: the link is written to the server log instead
    (local development only). Failures are logged, never raised, so they can't leak whether an
    account exists.
    """
    if not SMTP_HOST:
        logger.warning("SMTP not configured. Password reset link for %s: %s", to, link)
        return

    message = EmailMessage()
    message["Subject"] = "Reset your Budget Tracker password"
    message["From"] = SMTP_FROM
    message["To"] = to
    message.set_content(
        "Someone asked to reset the password for your Budget Tracker account.\n\n"
        f"Open this link to choose a new password (valid for {PASSWORD_RESET_EXPIRE_MINUTES} minutes, "
        f"one use only):\n\n{link}\n\n"
        "If this wasn't you, ignore this email. Your password has not been changed."
    )
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(message)
    except Exception:
        logger.exception("Could not send password reset email to %s", to)
