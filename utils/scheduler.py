"""Scheduler utilities for periodic stock checks."""
import logging
import pytz
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("StockAlerts.Scheduler")


def scheduled_stock_check():
    """Function to run scheduled stock checks."""
    try:
        logger.info("Starting scheduled stock check...")
        
        # Import and run the periodic checker
        from periodic_checker import PeriodicChecker
        
        checker = PeriodicChecker()
        checker.check_watchlists()
        
        logger.info("Scheduled stock check completed successfully")
        
    except Exception as e:
        logger.error(f"Error in scheduled stock check: {e}", exc_info=True)


def setup_scheduler():
    """Setup and start the APScheduler for periodic tasks."""
    # Initialize APScheduler
    scheduler = BackgroundScheduler()
    
    # Add the scheduled job - runs daily at 1 AM UTC (same as GitHub Actions)
    scheduler.add_job(
        func=scheduled_stock_check,
        trigger=CronTrigger(hour=1, minute=0, timezone=pytz.UTC),
        id='stock_check',
        name='Daily Stock Check',
        replace_existing=True
    )
    
    # Start the scheduler
    try:
        scheduler.start()
        logger.info("APScheduler started successfully - daily stock checks scheduled for 1 AM UTC")
        
        # Ensure scheduler stops when the app shuts down
        atexit.register(lambda: scheduler.shutdown())
        
        return scheduler
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        return None