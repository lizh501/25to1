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

## Confirmed download flow

The day-fileset download chain is now confirmed working.

Working flow:

1. `GET /cmmn/commonLoginLayer.do`
2. `POST /login/loginAjax.do`
3. `POST /cmmn/loginSessionCheck.do`
4. browse `selectAsosRltmList.do` or `selectAwsRltmList.do`
5. choose a `fileSizeMgList` entry
6. `POST /data/common/selectPrposPopup.do`
7. choose `reqstPurposeCd`
8. `POST /data/common/processDtsReqst.do`

## Confirmed purpose code for this project

- `F00408` = `학술/연구` = academic / research

## Confirmed returned file structure

The KMA response is a nested package:

1. outer application zip returned by `processDtsReqst.do`
2. inner data zip with the requested file name
3. final `CSV` inside the inner zip

CSV encoding:

- `cp949`

## Confirmed bootstrap downloads

Successfully downloaded:

- `ASOS day 2018`
  - outer zip: `25to1/data/stage1/raw/stations/SURFACE_ASOS_100_DAY_2018_2018_2019.zip`
  - extracted dir: `25to1/data/stage1/raw/stations/asos_2018`
  - final csv: `25to1/data/stage1/raw/stations/asos_2018/SURFACE_ASOS_100_DAY_2018_2018_2019.csv`
- `AWS day 2018`
  - outer zip: `25to1/data/stage1/raw/stations/SURFACE_AWS_116_DAY_2018_2018_2019.zip`
  - extracted dir: `25to1/data/stage1/raw/stations/aws_2018`
  - final csv: `25to1/data/stage1/raw/stations/aws_2018/SURFACE_AWS_116_DAY_2018_2018_2019.csv`

## Implemented local scripts

- `25to1/scripts/download_kma_station_fileset.py`
- `25to1/scripts/normalize_kma_daily_station_csv.py`
- `25to1/scripts/build_kma_station_metadata.py`
- `25to1/scripts/build_stage1_station_collocations.py`
- `25to1/scripts/list_kma_station_filesets.py`
- `25to1/scripts/fetch_kma_station_detail_pages.py`
- `25to1/scripts/build_kma_station_metadata_table.py`

## Next step

Use the normalized UTF-8 station tables plus the collocated January 2018 grid samples as the target-side bootstrap data source for Stage-1 label modeling.

## Update 2026-03-31: station expansion progress

We now also have a batch station-metadata path for ASOS candidate stations:

- candidate station list: `25to1/data/stage1/interim/kma_asos_candidate_stations_62.csv`
- fetched detail-page dir: `25to1/data/stage1/interim/kma_station_details_asos62`
- metadata table: `25to1/data/stage1/processed/stations/station_metadata_asos62.csv`

This confirms that:

- public station detail pages can be fetched in batch without the login gate
- station coordinates / elevation can be scaled beyond the original `2`-station bootstrap
- the remaining Stage-1 station bottleneck is batch daily-fileset download and normalization, not station metadata discovery
