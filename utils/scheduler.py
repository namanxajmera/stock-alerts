"""Scheduler utilities for periodic stock checks."""

import atexit
import logging
from typing import Callable, Optional

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, current_app

logger = logging.getLogger("StockAlerts.Scheduler")


def create_scheduled_job(app: Flask) -> Callable[[], None]:
    """
    Factory function to create the scheduled job within the app context.
    This ensures the job has access to application services like PeriodicChecker.
    """

    def job_wrapper() -> None:
        """Wrapper to run the check within the Flask app context."""
        with app.app_context():
            logger.info("Starting scheduled stock check...")
            try:
                # Access the checker from the application context
                periodic_checker = getattr(current_app, "periodic_checker", None)
                if periodic_checker:
                    periodic_checker.check_watchlists()
                    logger.info("Scheduled stock check completed successfully.")
                else:
                    logger.error(
                        "PeriodicChecker not found in app context for scheduled job."
                    )
            except Exception as e:
                logger.error(f"Error in scheduled stock check: {e}", exc_info=True)

    return job_wrapper


def setup_scheduler(app: Flask) -> Optional[BackgroundScheduler]:
    """Setup and start the APScheduler for periodic tasks."""
    # Initialize APScheduler
    scheduler = BackgroundScheduler()

    # Create the job function with the application context
    job_func = create_scheduled_job(app)

    # Add the scheduled job - runs at 1 AM UTC on Mon-Thu and Sunday only
    scheduler.add_job(
        func=job_func,
        trigger=CronTrigger(
            hour=1, minute=0, day_of_week="mon,tue,wed,thu,sun", timezone=pytz.UTC
        ),
        id="stock_check",
        name="Weekly Stock Check (Mon-Thu, Sun)",
        replace_existing=True,
    )

    # Start the scheduler
    try:
        scheduler.start()
        logger.info(
            "APScheduler started successfully - stock checks scheduled for 1 AM UTC on Mon-Thu and Sunday"
        )

        # Ensure scheduler stops when the app shuts down
        atexit.register(lambda: scheduler.shutdown())

        return scheduler

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        return None