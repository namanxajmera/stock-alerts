"""Validation utilities for stock ticker symbols and other data."""
import re
from typing import Tuple


def validate_ticker_symbol(ticker: str) -> Tuple[bool, str]:
    """Validate that the ticker symbol is in a valid format."""
    if not ticker:
        return False, "Ticker symbol cannot be empty"
    
    # Remove whitespace and convert to uppercase
    ticker = ticker.strip().upper()
    
    # Basic validation: 1-5 characters, letters and numbers only
    if not re.match(r'^[A-Z0-9]{1,5}$', ticker):
        return False, "Ticker symbol must be 1-5 characters, letters and numbers only"
    
    # Check for common invalid patterns
    if ticker.isdigit():
        return False, "Ticker symbol cannot be all numbers"
    
    return True, ticker