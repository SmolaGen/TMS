# QA Fix Request

**Status**: REJECTED
**Date**: 2026-01-22
**QA Session**: 1

## Critical Issues to Fix

### 1. Missing Database Migration
**Problem**: You added `customer_telegram_id` to the `Order` model in `src/database/models.py`, but you did not create an Alembic migration for it.
**Location**: `alembic/versions/`
**Required Fix**: Generate a new migration file using Alembic that adds the `customer_telegram_id` column to the `orders` table.
**Verification**: QA will check for the existence of a valid migration file in `alembic/versions/`.

### 2. Missing "Approaching Delivery" and ETA Updates
**Problem**: The spec requires notifications for when the driver is "approaching" and "ETA updates". Currently, only status-change notifications are implemented.
**Location**: `src/services/notification_service.py`, `src/services/order_workflow.py`
**Required Fix**: 
- Implement logic to send a notification when the driver is "approaching" the destination (e.g., 5-10 minutes away).
- Include ETA information in the status notifications (e.g., "Driver is en route, estimated arrival in 15 minutes").
**Verification**: QA will check for new notification types and ETA content in messages.

## Major Issues to Fix

### 3. Customer Webhooks
**Problem**: The implementation plan mentioned extending `WebhookService` for customer notifications, but the code currently only supports `contractor.webhook_url`.
**Location**: `src/services/webhook_service.py`
**Required Fix**: Add support for sending webhooks to a customer-provided URL if available (e.g., if a `customer_webhook_url` field is added or if it's passed dynamically).
**Verification**: Test that a webhook is sent even if `contractor_id` is null but a customer webhook destination is provided.

## After Fixes

Once fixes are complete:
1. Commit with message: "fix: add migration and approaching/ETA notifications (qa-requested)"
2. QA will automatically re-run
