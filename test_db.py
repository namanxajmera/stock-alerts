from db_manager import DatabaseManager
from termcolor import colored

def test_database_setup():
    """Test database initialization and basic operations."""
    print(colored("\nTesting Database Setup", "cyan"))
    print(colored("=" * 50, "cyan"))

    # Initialize database manager
    db = DatabaseManager()

    # Test user operations
    print(colored("\nTesting user operations:", "yellow"))
    test_user_id = "test_user_123"
    test_name = "Test User"
    
    success = db.add_user(test_user_id, test_name)
    print(colored(f"Add user result: {success}", "green" if success else "red"))

    # Test watchlist operations
    print(colored("\nTesting watchlist operations:", "yellow"))
    test_symbols = ["AAPL", "GOOGL", "MSFT"]
    
    for symbol in test_symbols:
        success = db.add_to_watchlist(test_user_id, symbol)
        print(colored(f"Add {symbol} to watchlist result: {success}", "green" if success else "red"))
    
    watchlist = db.get_watchlist(test_user_id)
    print(colored("\nCurrent watchlist:", "yellow"))
    for item in watchlist:
        print(colored(f"Symbol: {item['symbol']}, Low: {item['alert_threshold_low']}, High: {item['alert_threshold_high']}", "cyan"))

    # Test stock cache
    print(colored("\nTesting stock cache:", "yellow"))
    success = db.update_stock_cache("AAPL", 150.0, 145.0, '{"some": "data"}')
    print(colored(f"Update stock cache result: {success}", "green" if success else "red"))

    # Test configuration
    print(colored("\nTesting configuration:", "yellow"))
    success = db.set_config("test_key", "test_value", "test_script")
    print(colored(f"Set config result: {success}", "green" if success else "red"))
    
    value = db.get_config("test_key")
    print(colored(f"Retrieved config value: {value}", "cyan"))

    # Test logging
    print(colored("\nTesting logging:", "yellow"))
    db.log_event("TEST", "Test log message", test_user_id, "AAPL")
    print(colored("Log event added", "green"))

    print(colored("\nDatabase tests completed!", "green"))
    print(colored("=" * 50, "green"))

if __name__ == "__main__":
    test_database_setup() 