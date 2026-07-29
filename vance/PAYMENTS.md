# Switch UPI Payment Flow

## How it works

1. **Employer posts a hiring request** (role + headcount) via the employer app
2. **Payment modal opens automatically** — shows ₹2,000 × headcount as the total
3. **Employer pays** via UPI deep link (mobile) or QR scan (desktop)
4. **Employer submits 12-digit UTR** from their UPI app transaction history
5. **Admin manually verifies** UTR at `/admin/payments/pending?admin_key=<ADMIN_API_KEY>`
6. **Status updates** flow back to the employer's bookings list

## Payment statuses

| Status | Meaning |
|---|---|
| `pending` | Payment record created, employer hasn't paid yet |
| `awaiting_verification` | Employer submitted a UTR, needs admin check |
| `verified` | Admin confirmed payment received |
| `failed` | Admin rejected (UTR mismatch, wrong amount, etc.) |
| `duplicate` | A newer payment was initiated for the same request |

## Admin verification (manual process)

1. Go to `https://api.relayy.world/admin/payments/pending?admin_key=<ADMIN_API_KEY>`
2. Each row shows: employer phone, amount, UTR, time submitted
3. Open your UPI/bank portal and search for the UTR
4. Click **Verify** (with optional notes) or **Reject** (requires reason)
5. Export CSV any time for daily reconciliation

## How to verify a UTR

- Log into your bank's business banking portal / Paytm for Business / GPay for Business
- Search transaction by UTR number (12 digits)
- Confirm the amount matches and the payment was to your UPI VPA
- Click Verify in the admin panel

## Environment variables

```bash
UPI_VPA=switchlocally@paytm        # Your UPI VPA (required)
ADMIN_API_KEY=your-secret-key      # Protects admin endpoints (required)
SLACK_WEBHOOK_URL=https://hooks... # Optional: Slack alerts on UTR submission
```

## Known limitations (v1)

- **No auto-reconciliation** — every UTR must be manually verified by an admin
- **No webhook from banks** — we rely on employer-submitted UTR, not bank confirmation
- **No partial payment handling** — payment is all-or-nothing per hiring request
- **UTR uniqueness enforced by DB** — prevents duplicate submissions but not forged UTRs
- **No refund flow** — handle refunds manually via bank transfer

## Files

| File | Purpose |
|---|---|
| `utils/upi.py` | UPI deep-link generator |
| `models/sql_models.py` | `UPIPayment` SQLAlchemy model |
| `api/switch_payment_routes.py` | FastAPI routes (initiate, confirm, admin) |
| `Switch/src/components/UPIPaymentModal.jsx` | React payment UI |
| `scripts/add_upi_payments_table.py` | Manual migration script |
