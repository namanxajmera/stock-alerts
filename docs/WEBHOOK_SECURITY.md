# Webhook Security Guide

This document explains the enhanced webhook security implementation for the Stock Alerts Telegram bot.

## Overview

The application now implements Telegram's recommended security practices for webhook validation:

1. **Secret Token Validation**: Uses `X-Telegram-Bot-Api-Secret-Token` header
2. **Request Validation**: Validates JSON structure and required fields
3. **Timing Attack Protection**: Uses `hmac.compare_digest()` for secure comparisons

## Security Improvements

### Before (Vulnerable)
- Simple string comparison for secret tokens
- Minimal request validation
- Susceptible to timing attacks and spoofing

### After (Secure)
- Timing-safe token comparison using `hmac.compare_digest()`
- Comprehensive request structure validation
- Enhanced error logging for security monitoring
- Cryptographically secure token generation

## Environment Variables

To enable webhook security, set the following environment variable:

```bash
TELEGRAM_WEBHOOK_SECRET=your_secure_secret_token_here
```

### Generating a Secure Secret Token

You can generate a secure secret token using the built-in utility:

```python
from webhook_handler import WebhookHandler
secret_token = WebhookHandler.generate_webhook_secret()
print(f"Generated secret token: {secret_token}")
```

Or use the provided script:

```bash
python3 -c "from webhook_handler import WebhookHandler; print(WebhookHandler.generate_webhook_secret())"
```

## Webhook Setup with Telegram

When setting up your webhook with Telegram, include the secret token:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/webhook",
    "secret_token": "your_secure_secret_token_here"
  }'
```

## Validation Process

The enhanced validation process checks:

1. **Secret Token**: Validates `X-Telegram-Bot-Api-Secret-Token` header if configured
2. **Request Body**: Ensures non-empty request data
3. **JSON Structure**: Validates proper JSON format
4. **Required Fields**: Checks for `update_id` field
5. **Field Types**: Validates `update_id` is an integer

## Error Handling

The webhook validator now provides detailed error logging:

- `Missing X-Telegram-Bot-Api-Secret-Token header`
- `Invalid secret token in webhook request`
- `Empty webhook request received`
- `Invalid JSON in webhook request`
- `Invalid webhook data: missing update_id`
- `Invalid webhook data: update_id must be integer`

## Testing

Run the validation tests to verify security improvements:

```bash
source venv/bin/activate
python test_webhook_validation.py
```

## Security Best Practices

1. **Use Strong Secrets**: Always use cryptographically secure tokens
2. **Rotate Secrets**: Periodically rotate webhook secret tokens
3. **Monitor Logs**: Watch for validation failures that could indicate attacks
4. **HTTPS Only**: Ensure webhooks are served over HTTPS
5. **Rate Limiting**: Implement rate limiting for webhook endpoints

## Migration Guide

### For Existing Deployments

1. Generate a new secret token:
   ```python
   from webhook_handler import WebhookHandler
   new_secret = WebhookHandler.generate_webhook_secret()
   ```

2. Update your environment variables:
   ```bash
   export TELEGRAM_WEBHOOK_SECRET="your_new_secret_token"
   ```

3. Update your Telegram webhook configuration:
   ```bash
   curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-domain.com/webhook", "secret_token": "your_new_secret_token"}'
   ```

4. Deploy the updated application

### Verification

After deployment, verify the webhook is working:

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

The response should show your webhook URL and confirm the secret token is set.

## Troubleshooting

### Common Issues

1. **403 Forbidden responses**: Check that the secret token in your environment matches the one configured with Telegram
2. **Missing header errors**: Ensure Telegram is sending the `X-Telegram-Bot-Api-Secret-Token` header
3. **JSON validation errors**: Verify the webhook URL is correct and accessible

### Debug Mode

Enable debug logging to see detailed validation information:

```python
import logging
logging.getLogger('StockAlerts.WebhookHandler').setLevel(logging.DEBUG)
```

## Related Files

- `webhook_handler.py`: Main webhook validation logic
- `routes/webhook_routes.py`: Webhook endpoint handler
- `test_webhook_validation.py`: Security validation tests