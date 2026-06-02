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
- `newlywed_public_sale_namyangju_jinjeop2_a3_20251230.pdf`: directly
  downloaded LH newlywed public-sale notice.
- `public_sale_cheongju_jibuk_b1_remaining_20260430.pdf`: remaining-unit
  public-sale notice with no middle-payment requirement.
- `newlywed_private_public_sale_wirye_xi_resupply_20240118.pdf`: private
  participation newlywed public-sale resupply notice.
- `public_sale_ulsan_down2_a10_20251230.pdf`: standard public-sale notice
  used to verify loan and minus-option extraction.
- `public_sale_incheon_yeongjong_a24_remaining_20260330.pdf`: remaining-unit
  public-sale notice with multiple middle-payment rounds and loan columns.
- `public_sale_daejeon_daedong2_1_remaining_20260403.pdf`: large residual-sale
  table with basic and general-supply option groups.
- `rent_notice_506.pdf`: rental notice sample kept as an exclusion/reference
  fixture for service-target filtering.

Large or newly downloaded PDFs should stay out of Git unless they are deliberate
test fixtures. Runtime downloads are cached under `backend/.cache/official_pdfs`.
