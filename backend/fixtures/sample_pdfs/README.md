# Sample notice fixtures

This directory keeps small official-document fixtures used by backend tests and
local extraction checks.

Tracked fixtures:

- `lh_detail_page.html`: LH detail page snapshot used to verify PDF discovery.
- `public_sale_notice_611.pdf`: public-sale notice sample used to verify option
  and payment-schedule extraction.
- `rent_notice_506.pdf`: rental notice sample kept as an exclusion/reference
  fixture for service-target filtering.

Large or newly downloaded PDFs should stay out of Git unless they are deliberate
test fixtures. Runtime downloads are cached under `backend/.cache/official_pdfs`.
