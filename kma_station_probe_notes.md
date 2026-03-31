# KMA Station Data Probe Notes

Updated: 2026-03-31

## Goal

Fetch Stage-1 station observations (`AWS` / `ASOS`) from the official KMA data portal.

## Official entry pages

- ASOS real-time / fileset page:
  - `https://data.kma.go.kr/data/grnd/selectAsosRltmList.do?pgmNo=36&tabNo=1`
- AWS real-time / fileset page:
  - `https://data.kma.go.kr/data/grnd/selectAwsRltmList.do?pgmNo=56&tabNo=1`

## Confirmed request chain

The KMA site uses a login/session gate plus a request-purpose popup before download.

Confirmed endpoints discovered from the page HTML and linked JS:

- Login layer:
  - `https://data.kma.go.kr/cmmn/commonLoginLayer.do`
- Login AJAX:
  - `POST /login/loginAjax.do`
- Session check:
  - `POST /cmmn/loginSessionCheck.do`
- Real-time fileset request-purpose popup:
  - `POST /data/cmmn/selectPrposRltmFileSetReqstPopup.do`

## Confirmed login form field names

From `commonLoginLayer.do`:

- `loginId`
- `passwordNo`

## Confirmed fileset request fields

From the `fnRltmFileSetDownload()` JS flow:

- `ftpYn`
- `sviceSe`
- `startDt`
- `endDt`
- `dataFormCd`
- `dwldSetupPd`
- `stdrMg`
- `stnIds`
- `mddlClssCd`
- `lrgClssCd`
- `elementGroupSns`
- `filesetDtlSns`
- `elementCds`
- `startHh`
- `endHh`
- `startMt`
- `endMt`

## Current blocker

The remaining gap is not the landing page or the login endpoint itself. The hard part is the sessioned popup-to-download chain:

1. create an authenticated session
2. reproduce the request-purpose selection
3. capture the final download endpoint and exact payload

The KMA portal was reachable, but repeated reads of some linked JS assets were unstable from this environment, so the final request was not fully reconstructed yet.

## Practical next step

Resume from this note and script a `requests.Session(trust_env=False)` flow:

1. `GET /cmmn/commonLoginLayer.do`
2. `POST /login/loginAjax.do`
3. `POST /cmmn/loginSessionCheck.do`
4. `POST /data/cmmn/selectPrposRltmFileSetReqstPopup.do`
5. inspect the returned popup HTML for `reqstPurposeCd`
6. trace the final file download POST
