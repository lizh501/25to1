import argparse
import os
import re
import time
from pathlib import Path
from zipfile import ZipFile

import requests
from bs4 import BeautifulSoup

from stage1_common import load_env_file


SOURCE_CONFIG = {
    "asos": {
        "page_url": "https://data.kma.go.kr/data/grnd/selectAsosRltmList.do?pgmNo=36&tabNo=1",
        "default_station_id": "100",
    },
    "aws": {
        "page_url": "https://data.kma.go.kr/data/grnd/selectAwsRltmList.do?pgmNo=56&tabNo=1",
        "default_station_id": "116",
    },
}


def resolve_input_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path

    cwd_candidate = Path.cwd() / path
    if cwd_candidate.exists():
        return cwd_candidate.resolve()

    workspace_candidate = Path(__file__).resolve().parents[2] / path
    if workspace_candidate.exists():
        return workspace_candidate.resolve()

    return cwd_candidate.resolve()


def fetch_with_retry(session: requests.Session, method: str, url: str, **kwargs) -> requests.Response:
    last_error = None
    for attempt in range(5):
        try:
            response = session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as exc:  # pragma: no cover - network flakiness is expected here
            last_error = exc
            wait_seconds = 2 + attempt
            print(f"RETRY {attempt + 1}/5 {method} {url}: {exc}")
            time.sleep(wait_seconds)
    raise RuntimeError(f"Failed after retries: {method} {url}") from last_error


def build_target_name(source: str, station_id: str | None, frequency: str, year: int, month: int | None = None) -> str:
    station_text = str(station_id or SOURCE_CONFIG[source]["default_station_id"])
    src = source.upper()
    if frequency == "mi":
        if month is None:
            raise ValueError("month is required for minute data")
        month_text = f"{year:04d}-{month:02d}"
        return f"SURFACE_{src}_{station_text}_{frequency.upper()}_{month_text}_{month_text}_"
    return f"SURFACE_{src}_{station_text}_{frequency.upper()}_{year:04d}_{year:04d}_"


def parse_fileset_values(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [item.get("value", "") for item in soup.select('input[name="fileSizeMgList"]')]


def find_matching_fileset(
    session: requests.Session,
    source: str,
    station_id: str | None,
    frequency: str,
    year: int,
    month: int | None,
    max_pages: int,
) -> str:
    target_name = build_target_name(source, station_id, frequency, year, month)
    page_url = SOURCE_CONFIG[source]["page_url"]

    for page_idx in range(1, max_pages + 1):
        response = fetch_with_retry(
            session,
            "GET",
            f"{page_url}&pageIndex={page_idx}",
            timeout=60,
        )
        values = parse_fileset_values(response.text)
        for value in values:
            parts = value.split("^")
            if len(parts) != 4:
                continue
            _, _, file_path, _ = parts
            file_name = Path(file_path).name
            if file_name.startswith(target_name):
                print(f"MATCH page={page_idx} file={file_name}")
                return value
    raise FileNotFoundError(f"No matching KMA fileset found for {source} {frequency} {year} {month or ''}".strip())


def login(session: requests.Session, username: str, password: str) -> None:
    fetch_with_retry(session, "GET", "https://data.kma.go.kr/cmmn/commonLoginLayer.do", timeout=30)
    login_response = fetch_with_retry(
        session,
        "POST",
        "https://data.kma.go.kr/login/loginAjax.do",
        data={"loginId": username, "passwordNo": password},
        timeout=30,
    )
    if '"code": "00"' not in login_response.text:
        raise RuntimeError(f"KMA login failed: {login_response.text[:500]}")

    check_response = fetch_with_retry(
        session,
        "POST",
        "https://data.kma.go.kr/cmmn/loginSessionCheck.do",
        timeout=30,
    )
    if '"data": 2' not in check_response.text:
        raise RuntimeError(f"KMA session check failed: {check_response.text[:500]}")


def request_purpose_popup(session: requests.Session, fileset_value: str) -> tuple[dict[str, str], str]:
    file_size, fileset_sn, file_path, fileset_dtl_sn = fileset_value.split("^")
    payload = {
        "ftpYn": "N",
        "sviceSe": "F00101",
        "startDt": "",
        "endDt": "",
        "dataFormCd": "",
        "fileSizeMgs": file_size,
        "filesetSns": fileset_sn,
        "filesetDtlSns": fileset_dtl_sn,
        "fileCoursNms": file_path,
        "dwldSetupPd": "3",
        "stdrMg": "102400",
    }
    popup = fetch_with_retry(
        session,
        "POST",
        "https://data.kma.go.kr/data/common/selectPrposPopup.do",
        data=payload,
        timeout=60,
    )
    return payload, popup.text


def decode_purpose_labels(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    labels = []
    for radio in soup.select('input[name="reqstPurposeCd"]'):
        value = radio.get("value", "")
        label = soup.find("label", attrs={"for": radio.get("id")})
        label_text = label.get_text(" ", strip=True) if label else ""
        labels.append((value, label_text))
    return labels


def download_fileset(
    session: requests.Session,
    payload: dict[str, str],
    purpose_code: str,
) -> requests.Response:
    full_payload = dict(payload)
    full_payload["processSt"] = ""
    full_payload["reqstPurposeCd"] = purpose_code
    return fetch_with_retry(
        session,
        "POST",
        "https://data.kma.go.kr/data/common/processDtsReqst.do",
        data=full_payload,
        timeout=120,
    )


def extract_nested_zip(outer_zip: Path, extract_dir: Path) -> list[Path]:
    extract_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    with ZipFile(outer_zip) as outer:
        outer.extractall(extract_dir)
        outputs.extend(extract_dir / name for name in outer.namelist())

    nested_outputs = []
    for path in list(outputs):
        if path.suffix.lower() == ".zip":
            with ZipFile(path) as inner:
                inner.extractall(extract_dir)
                nested_outputs.extend(extract_dir / name for name in inner.namelist())
    outputs.extend(nested_outputs)
    return outputs


def sanitize_label(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Download KMA station filesets from the official portal.")
    parser.add_argument("--source", choices=sorted(SOURCE_CONFIG.keys()), required=True, help="Station source: asos or aws")
    parser.add_argument("--station-id", default=None, help="Station ID embedded in the fileset name, for example 100 or 116.")
    parser.add_argument("--frequency", choices=["day", "hr", "mi"], required=True, help="Fileset frequency")
    parser.add_argument("--year", type=int, required=True, help="Target year")
    parser.add_argument("--month", type=int, default=0, help="Required only for minute data")
    parser.add_argument("--purpose-code", default="F00408", help="Usage purpose code. Default is academic/research.")
    parser.add_argument("--env-file", default="25to1/configs/stage1_credentials.example.env")
    parser.add_argument("--output-dir", default="25to1/data/stage1/raw/stations")
    parser.add_argument("--extract", action="store_true", help="Extract the returned outer zip and nested data zip.")
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum fileset pages to scan")
    args = parser.parse_args()

    env_path = resolve_input_path(args.env_file)
    load_env_file(env_path)
    username = os.environ.get("KMA_USERNAME")
    password = os.environ.get("KMA_PASSWORD")
    if not username or not password:
        raise RuntimeError("Missing KMA_USERNAME / KMA_PASSWORD in environment")

    month = args.month or None
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    login(session, username, password)
    fileset_value = find_matching_fileset(
        session,
        source=args.source,
        station_id=args.station_id,
        frequency=args.frequency,
        year=args.year,
        month=month,
        max_pages=args.max_pages,
    )
    popup_payload, popup_html = request_purpose_popup(session, fileset_value)
    labels = decode_purpose_labels(popup_html)
    print("PURPOSES")
    for value, label in labels:
        print(f"  {value}: {sanitize_label(label)}")

    response = download_fileset(session, popup_payload, args.purpose_code)
    file_name = Path(popup_payload["fileCoursNms"]).name
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    outer_zip = output_dir / file_name
    outer_zip.write_bytes(response.content)
    print(f"SAVED {outer_zip} size={outer_zip.stat().st_size}")

    if args.extract:
        extract_dir = output_dir / f"{args.source}_{args.frequency}_{args.year:04d}" if month is None else output_dir / f"{args.source}_{args.frequency}_{args.year:04d}_{month:02d}"
        extracted = extract_nested_zip(outer_zip, extract_dir)
        print("EXTRACTED")
        for path in extracted:
            print(f"  {path}")


if __name__ == "__main__":
    main()
