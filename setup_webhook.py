#!/usr/bin/env python3
"""
Webhook Setup Utility

This script helps set up secure webhooks for the Telegram bot with proper
secret token configuration.
"""
import os
import sys
import requests
from webhook_handler import WebhookHandler


def setup_webhook():
    """Set up or update the Telegram webhook with security."""
    print("🔧 Telegram Webhook Setup Utility")
    print("=" * 40)
    
    # Get bot token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set")
        print("Please set your bot token: export TELEGRAM_BOT_TOKEN='your_bot_token'")
        return False
    
    # Get webhook URL
    webhook_url = input("Enter your webhook URL (e.g., https://yourdomain.com/webhook): ").strip()
    if not webhook_url:
        print("❌ Error: Webhook URL is required")
        return False
    
    if not webhook_url.startswith('https://'):
        print("⚠️  Warning: Webhook URL should use HTTPS for security")
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm != 'y':
            return False
    
    # Check if secret token exists
    existing_secret = os.getenv('TELEGRAM_WEBHOOK_SECRET')
    
    if existing_secret:
        print(f"📝 Found existing secret token: {existing_secret[:10]}...")
        use_existing = input("Use existing secret token? (Y/n): ").strip().lower()
        if use_existing in ['', 'y', 'yes']:
            secret_token = existing_secret
        else:
            secret_token = WebhookHandler.generate_webhook_secret()
            print(f"🔑 Generated new secret token: {secret_token}")
    else:
        secret_token = WebhookHandler.generate_webhook_secret()
        print(f"🔑 Generated new secret token: {secret_token}")
        print("\n📋 Add this to your environment variables:")
        print(f"export TELEGRAM_WEBHOOK_SECRET='{secret_token}'")
    
    # Set up webhook with Telegram
    print(f"\n🚀 Setting up webhook with Telegram...")
    
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    payload = {
        "url": webhook_url,
        "secret_token": secret_token
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get('ok'):
            print("✅ Webhook configured successfully!")
            print(f"   URL: {webhook_url}")
            print(f"   Secret: {secret_token[:10]}...")
        else:
            print(f"❌ Error setting webhook: {result.get('description', 'Unknown error')}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Network error setting webhook: {e}")
        return False
    
    # Verify webhook setup
    print("\n🔍 Verifying webhook configuration...")
    try:
        verify_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
        response = requests.get(verify_url, timeout=10)
        response.raise_for_status()
        
        info = response.json()
        if info.get('ok'):
            webhook_info = info.get('result', {})
            print("📊 Webhook Status:")
            print(f"   URL: {webhook_info.get('url', 'Not set')}")
            print(f"   Has Secret: {'Yes' if webhook_info.get('has_custom_certificate') or secret_token else 'No'}")
            print(f"   Pending Updates: {webhook_info.get('pending_update_count', 0)}")
            
            if webhook_info.get('last_error_message'):
                print(f"   Last Error: {webhook_info.get('last_error_message')}")
        else:
            print("❌ Could not verify webhook status")
            
    except requests.RequestException as e:
        print(f"⚠️  Could not verify webhook (but setup may still be successful): {e}")
    
    print("\n✨ Webhook setup complete!")
    print("\n📋 Next steps:")
    print("1. Make sure your webhook endpoint is running and accessible")
    print("2. Test the bot by sending it a message")
    print("3. Check your application logs for webhook validation messages")
    
    if not existing_secret or secret_token != existing_secret:
        print(f"\n🔐 Don't forget to update your environment:")
        print(f"export TELEGRAM_WEBHOOK_SECRET='{secret_token}'")
    
    return True


def remove_webhook():
    """Remove the current webhook."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set")
        return False
    
    print("🗑️  Removing webhook...")
    
    api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    try:
        response = requests.post(api_url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get('ok'):
            print("✅ Webhook removed successfully!")
        else:
            print(f"❌ Error removing webhook: {result.get('description', 'Unknown error')}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Network error removing webhook: {e}")
        return False
    
    return True


def check_webhook():
    """Check current webhook status."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set")
        return False
    
    print("🔍 Checking webhook status...")
    
    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get('ok'):
            info = result.get('result', {})
            print("\n📊 Current Webhook Configuration:")
            print(f"   URL: {info.get('url', 'Not set')}")
            print(f"   Has Secret Token: {'Yes' if info.get('has_custom_certificate') else 'Unknown'}")
            print(f"   Pending Updates: {info.get('pending_update_count', 0)}")
            print(f"   Max Connections: {info.get('max_connections', 40)}")
            
            if info.get('allowed_updates'):
                print(f"   Allowed Updates: {', '.join(info.get('allowed_updates'))}")
            
            if info.get('last_error_date'):
                print(f"   Last Error Date: {info.get('last_error_date')}")
                print(f"   Last Error Message: {info.get('last_error_message', 'Unknown')}")
            else:
                print("   ✅ No recent errors")
                
        else:
            print(f"❌ Error checking webhook: {result.get('description', 'Unknown error')}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Network error checking webhook: {e}")
        return False
    
    return True


def main():
    """Main function."""
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        if action in ['remove', 'delete']:
            remove_webhook()
        elif action in ['check', 'status']:
            check_webhook()
        elif action in ['setup', 'configure']:
            setup_webhook()
        else:
            print(f"Unknown action: {action}")
            print("Usage: python setup_webhook.py [setup|check|remove]")
    else:
        print("Choose an action:")
        print("1. Setup/Update webhook")
        print("2. Check webhook status")
        print("3. Remove webhook")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            setup_webhook()
        elif choice == '2':
            check_webhook()
        elif choice == '3':
            remove_webhook()
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()