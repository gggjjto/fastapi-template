# Stripe Payments

Use this recipe when a project needs subscriptions, one-time checkout, or
payment webhooks.

## Setup

```bash
make api-install
cp apps/api/.env.example apps/api/.env
```

Create products, prices, and webhook endpoints in Stripe before wiring runtime
logic.

## Env Vars

```bash
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID=
APP_PUBLIC_BASE_URL=http://localhost:8000
```

Keep publishable keys in the frontend environment only when a web app uses
Stripe.js.

## Implementation Notes

- Add an `app/billing/` domain with a checkout endpoint and a webhook endpoint.
- Verify webhook signatures before reading event payloads.
- Make webhook handlers idempotent by storing Stripe event IDs.
- Keep price IDs and product IDs in configuration or a database table; avoid
  hardcoding them in route handlers.
- Treat billing state as eventually consistent; webhook events should be the
  source of truth for subscription status.

## Verification

```bash
make api-lint
make api-format-check
make api-typecheck
make api-test
```

For local webhook smoke tests, use the Stripe CLI and verify duplicate events do
not create duplicate local records.
