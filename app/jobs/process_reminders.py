import asyncio
from datetime import datetime, timezone
import logging

from app.core.logging import setup_logging
from app.database.session import AsyncSessionLocal
from app.services.reminder import ReminderService

logger = logging.getLogger(__name__)


async def process_reminders(now: datetime | None = None) -> int:
    async with AsyncSessionLocal() as session:
        return await ReminderService(session).process_due_reminders(
            now or datetime.now(timezone.utc)
        )


async def main() -> None:
    setup_logging()
    processed = await process_reminders()
    logger.info("Processed %s deadline reminders", processed)


if __name__ == "__main__":
    asyncio.run(main())
