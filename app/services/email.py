import logging

logger = logging.getLogger(__name__)


class EmailService:
    async def send_password_reset_email(self, email: str, reset_link: str) -> None:
        logger.info("Password reset link for %s: %s", email, reset_link)