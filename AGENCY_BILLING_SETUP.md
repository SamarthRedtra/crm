# Agency Billing Setup

## Configure Billing Settings

1. Open CRM Settings and go to `Billing Settings`.
2. Set the default currency and invoice due days.
3. Add the Stripe publishable key, secret key, and webhook secret.
4. Set `Addon Charge Timing`:
   - `daily_accrual` (default): fixed add-ons are accrued by scheduler and invoiced in period close.
   - `upfront_immediate`: fixed add-ons are charged immediately when enabled or increased in agency settings.
5. Choose the Stripe collection method:
   - `send_invoice` for manual monthly payment through Stripe-hosted invoices.
   - `charge_automatically` if agencies will store a default payment method.

## Configure Stripe

1. Create a webhook endpoint in Stripe pointing to:

   `/api/method/crm.api.redtra.billing.stripe_webhook`

2. Subscribe the endpoint to these events:
   - `checkout.session.completed`
   - `invoice.paid`
   - `invoice.payment_failed`

## Scheduler Requirements

The billing flow depends on the bench scheduler and Redis services:

- `crm.api.redtra.billing.run_daily_agency_billing`
- `crm.api.redtra.billing.close_previous_month_agency_billing`

These jobs are wired in `crm/hooks.py` (`daily_long` and `monthly_long`).
Make sure Redis and the scheduler are running before expecting accruals or monthly invoice generation.
When `Addon Charge Timing` is `upfront_immediate`, daily scheduler still handles agent-level accruals, but fixed add-ons are not re-accrued in the daily job to avoid duplicate billing.

## Data Setup

1. Create `Agent Level` rows with daily rates.
2. Create `Billing Addon` rows for daily, monthly, or usage-based services.
3. Link each billable agency agent to an `Agent Level`.
4. Set `Agency Role` on agents:
   - `Admin` can manage billing
   - `Manager` can manage the agency/team
   - `Agent` has standard agency access

## Agency Admin Flow

1. Agency admin opens `/crm/agency-onboarding`.
2. Admin completes agency profile and billing details.
3. Admin optionally connects Stripe billing setup.
4. Admin completes onboarding and can then use `Agency Profile` and `Agency Billing` inside CRM Settings.

## Cutover to Upfront Addon Charging

1. Confirm Stripe keys are configured and webhook is active.
2. Set `Addon Charge Timing = upfront_immediate` in `Agency Billing Settings`.
3. Announce cutover date; only addon enable/increase events after cutover are charged upfront.
4. Keep monthly close enabled for non-addon accruals and historical open accruals.

## Workspace Shortcuts

- Property Management workspace includes billing shortcuts (setup, settings, levels, addons, invoices, accruals).
- Billing setup shortcut opens `/desk/agency_billing_setup`.
