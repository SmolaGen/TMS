# Remove hardcoded secrets from source code

## Overview

The src/config.py file contains hardcoded default values for critical secrets including JWT_SECRET_KEY, TELEGRAM_BOT_TOKEN, SECRET_KEY, and database credentials. These secrets are visible in source code and will be committed to version control, exposing production credentials.

## Rationale

Hardcoded secrets are a critical security vulnerability (OWASP A07). Anyone with access to the repository can extract these credentials and gain unauthorized access to the Telegram bot, impersonate users via JWT tokens, or access the database directly.

---
*This spec was created from ideation and is pending detailed specification.*
