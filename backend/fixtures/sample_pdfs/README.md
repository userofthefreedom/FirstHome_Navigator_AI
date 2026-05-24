# Sample notice fixtures

This directory keeps small official-document fixtures used by backend tests and
local extraction checks.

Tracked fixtures:

- `lh_detail_page.html`: LH detail page snapshot used to verify PDF discovery.
- `public_sale_notice_611.pdf`: public-sale notice sample used to verify option
  and payment-schedule extraction.
- `private_public_sale_wangsuk_atera_a1_20260430.pdf`: recent LH
  private-participation public-sale notice.
- `newlywed_public_sale_siheung_hajung_a1_20260430.pdf`: recent LH newlywed
  public-sale notice.
- `newlywed_public_sale_incheon_gyeyang_a9_20260430.pdf`: second recent LH
  newlywed public-sale notice with a different table layout.
- `public_sale_namyangju_wangsuk2_a3_corrected_20260430.pdf`: candidate
  standard public-sale notice for parser expansion.
- `private_public_sale_wangsuk_prugio_b2_20250729.pdf`: candidate
  private-participation public-sale notice for parser expansion.
- `rent_notice_506.pdf`: rental notice sample kept as an exclusion/reference
  fixture for service-target filtering.

Large or newly downloaded PDFs should stay out of Git unless they are deliberate
test fixtures. Runtime downloads are cached under `backend/.cache/official_pdfs`.
