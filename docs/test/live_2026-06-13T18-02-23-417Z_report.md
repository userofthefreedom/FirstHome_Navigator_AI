# Live Cloudflare E2E And 30 User Load Check

- Frontend: https://bit-county-makers-utilize.trycloudflare.com
- API base: https://seeing-graduation-investigation-upgrading.trycloudflare.com/api
- Run: 2026-06-13T18-02-23-417Z
- Concurrent virtual users: 30

## Browser E2E

| Step | Result | Ready | Loading Gone | Total | Note |
| --- | --- | ---: | ---: | ---: | --- |
| dashboard | OK | 0.01s | 0.01s | 3.20s |  |
| profile input | OK | 0.01s | 0.01s | 0.94s |  |
| recommendations | OK | 0.01s | 0.01s | 1.26s |  |
| notice detail | OK | 0.01s | 0.01s | 1.99s |  |
| funding roadmap | OK | 0.01s | 0.01s | 3.76s |  |
| ai coach | OK | 0.01s | 0.01s | 1.79s |  |
| map | OK | 0.01s | 0.01s | 2.42s |  |
| favorites | OK | 0.01s | 0.01s | 0.96s |  |
| signup/login screen | OK | 0.99s | n/a | 0.99s | Auth page availability checked. Account mutation is intentionally not repeated in every load check. |
| chatbot open and response | OK | 0.00s | 0.00s | 2.10s |  |

## 30 User Scenario

| Endpoint | OK/Total | p50 | p90 | p95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend:home | 30/30 | 0.39s | 0.47s | 0.49s | 0.51s |
| api:housing | 28/30 | 12.12s | 105.22s | 107.19s | 108.45s |
| api:notices-active | 29/30 | 13.58s | 107.53s | 109.43s | 119.15s |
| api:map-notices | 28/30 | 10.33s | 107.56s | 108.59s | 108.82s |
| api:notice-detail | 29/30 | 12.84s | 107.89s | 108.41s | 116.17s |
| api:funding | 27/30 | 12.10s | 105.20s | 107.55s | 107.89s |
| api:ai-coach | 19/30 | 112.98s | 124.19s | 125.31s | 125.31s |
| api:chatbot | 13/30 | 110.22s | 121.91s | 122.05s | 122.05s |

## Load Failures

- api:chatbot: status=524, ms=125478, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:chatbot: status=524, ms=125470, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:chatbot: status=524, ms=125465, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:ai-coach: status=524, ms=125470, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:chatbot: status=524, ms=125452, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:housing: status=429, ms=499, 
- api:chatbot: status=524, ms=125470, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:map-notices: status=429, ms=758, 
- api:notice-detail: status=429, ms=494, 
- api:funding: status=524, ms=125502, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:chatbot: status=524, ms=125485, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:housing: status=429, ms=498, 
- api:map-notices: status=429, ms=759, 
- api:funding: status=429, ms=793, 
- api:chatbot: status=524, ms=125454, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:notices-active: status=429, ms=491, 
- api:funding: status=429, ms=789, 
- api:ai-coach: status=524, ms=125473, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:chatbot: status=524, ms=125497, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:ai-coach: status=524, ms=125477, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:chatbot: status=524, ms=125459, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:ai-coach: status=524, ms=125467, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:chatbot: status=524, ms=125458, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:ai-coach: status=524, ms=125446, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:chatbot: status=524, ms=125455, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:ai-coach: status=524, ms=125451, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:chatbot: status=524, ms=125470, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:ai-coach: status=524, ms=125452, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:chatbot: status=524, ms=125478, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti
- api:ai-coach: status=524, ms=125468, {"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/","title":"Error 524: A timeout occurred","status":524,"detail":"The origin web server did not return a complete response within the 120-second Proxy Read Timeout window. The connecti

## Screenshots

Saved under `live_2026-06-13T18-02-23-417Z`.
