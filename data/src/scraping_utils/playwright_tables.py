"""Playwright helpers for scraping paginated tables."""

from __future__ import annotations

from typing import Iterable
import time
import os

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


class PlaywrightSession:
    def __init__(self):
        self._playwright = sync_playwright().start()
        headless_env = os.environ.get("HEADLESS", "").strip()
        headless = headless_env == "1"
        slow_mo_value = os.environ.get("PW_SLOW_MO", "").strip()
        slow_mo = int(slow_mo_value) if slow_mo_value.isdigit() else 0
        self._browser = self._playwright.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
        )
        self.page = self._browser.new_page()

    def get(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded")

    @property
    def current_url(self) -> str:
        return self.page.url

    def quit(self) -> None:
        try:
            self.page.close()
        except Exception:
            pass
        try:
            self._browser.close()
        except Exception:
            pass
        try:
            self._playwright.stop()
        except Exception:
            pass


def build_driver() -> PlaywrightSession:
    return PlaywrightSession()


def click_consent_in_context(page, xpaths: Iterable[str]) -> bool:
    # Fast-path known consent button class
    consent_button = page.locator("button.fc-cta-consent")
    if consent_button.count():
        try:
            consent_button.first.click(timeout=3000, force=True)
            return True
        except Exception:
            pass
    for xpath in xpaths:
        locator = page.locator(f"xpath={xpath}")
        if locator.count() == 0:
            continue
        try:
            locator.first.click(timeout=3000, force=True)
            return True
        except Exception:
            continue
    # Fallback: click by visible consent text
    text_locator = page.get_by_text("Consent", exact=False)
    if text_locator.count():
        try:
            text_locator.first.click(timeout=3000, force=True)
            return True
        except Exception:
            pass
    return False


def accept_consent(page, xpaths: Iterable[str]) -> None:
    try:
        try:
            page.wait_for_selector("button.fc-cta-consent", timeout=3000)
        except Exception:
            pass
        if click_consent_in_context(page, xpaths):
            return
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                frame.wait_for_selector("button.fc-cta-consent", timeout=3000)
            except Exception:
                pass
            if click_consent_in_context(frame, xpaths):
                return
    except Exception:
        return


def get_table(page, table_id: str):
    return page.locator(f"#{table_id}")


def wait_for_table_rows(
    page,
    table_id: str,
    timeout: int = 12,
    first_cell_not: str | None = None,
    first_row_not: str | None = None,
):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            page.wait_for_selector(f"#{table_id} tbody tr", timeout=1000)
            table = get_table(page, table_id)
            rows = table.locator("tbody tr")
            if rows.count() == 0:
                continue
            first_cells = rows.first.locator("td")
            if first_cells.count() == 0:
                continue
            first_text = (first_cells.nth(0).inner_text() or "").strip()
            if not first_text:
                continue
            if first_cell_not and first_text == first_cell_not:
                continue
            if first_row_not:
                row_signature = "\t".join(
                    cell.inner_text().strip() for cell in first_cells.all()
                )
                if row_signature == first_row_not:
                    continue
            return table
        except PlaywrightTimeoutError:
            continue
    raise PlaywrightTimeoutError("Timed out waiting for table rows")


def normalize_headers(headers: list[str], expected_len: int) -> list[str]:
    normalized: list[str] = []
    for idx, header in enumerate(headers, start=1):
        normalized.append(header or f"Column_{idx}")
    while len(normalized) < expected_len:
        normalized.append(f"Column_{len(normalized) + 1}")
    if len(normalized) > expected_len:
        normalized = normalized[:expected_len]
    return normalized


def extract_rows(
    page,
    table_id: str,
    headers: list[str] | None,
    first_cell_not: str | None = None,
    first_row_not: str | None = None,
):
    table = wait_for_table_rows(
        page, table_id, first_cell_not=first_cell_not, first_row_not=first_row_not
    )
    raw_headers = [
        cell.inner_text().strip() for cell in table.locator("thead th").all()
    ]
    body_rows = table.locator("tbody tr").all()
    rows: list[list[str]] = []
    max_cells = 0
    for row in body_rows:
        cells = [cell.inner_text().strip() for cell in row.locator("td").all()]
        max_cells = max(max_cells, len(cells))
        rows.append(cells)

    if headers is None:
        headers = normalize_headers(raw_headers, max_cells)
    else:
        headers = normalize_headers(headers, max_cells)

    row_dicts = []
    for cells in rows:
        if len(cells) < len(headers):
            cells = cells + [""] * (len(headers) - len(cells))
        elif len(cells) > len(headers):
            cells = cells[: len(headers)]
        row_dicts.append(dict(zip(headers, cells)))

    return headers, row_dicts


def print_page_head(headers: list[str], page_rows: list[dict], label: str, rows: int = 5) -> None:
    print(f"{label} headers: {headers}")
    for index, row in enumerate(page_rows[:rows], start=1):
        cells = [row.get(header, "") for header in headers]
        print(f"{label} row {index}: {cells}")


def find_next_control(page, next_icon_d: str, fallback_xpaths: Iterable[str] | None = None):
    xpath = (
        f"//*[local-name()='path' and @d='{next_icon_d}']"
        "/ancestor::*[self::button or self::a or @role='button'][1]"
    )
    locator = page.locator(f"xpath={xpath}")
    for idx in range(locator.count()):
        element = locator.nth(idx)
        try:
            if not element.is_visible() or not element.is_enabled():
                continue
        except Exception:
            continue
        return element
    for fallback in fallback_xpaths or []:
        fallback_locator = page.locator(f"xpath={fallback}")
        for idx in range(fallback_locator.count()):
            element = fallback_locator.nth(idx)
            try:
                if element.is_visible() and element.is_enabled():
                    return element
            except Exception:
                continue
    return None


def current_page_marker(page) -> str:
    selectors = [
        "//*[@aria-current='page']",
        "//a[@aria-current='page']",
        "//button[@aria-current='page']",
    ]
    for selector in selectors:
        locator = page.locator(f"xpath={selector}")
        if locator.count():
            text = locator.first.inner_text().strip()
            if text:
                return text
    return ""


def first_row_signature(page, table_id: str) -> str:
    try:
        table = get_table(page, table_id)
        first_row = table.locator("tbody tr").first
        cells = [cell.inner_text().strip() for cell in first_row.locator("td").all()]
        if not cells:
            return ""
        return "\t".join(cells)
    except Exception:
        return ""


def row_signature(headers: list[str], row: dict, skip_headers: set[str] | None = None) -> str:
    skip = skip_headers or set()
    return "\t".join(
        row.get(header, "")
        for header in headers
        if header not in skip
    )


def page_signature(
    page,
    table_id: str,
    headers: list[str] | None,
    page_rows: list[dict] | None,
    skip_headers: set[str] | None = None,
) -> tuple[str, str, str]:
    first_row_sig = ""
    if page_rows and headers:
        first_row_sig = row_signature(headers, page_rows[0], skip_headers=skip_headers)
    if not first_row_sig:
        first_row_sig = first_row_signature(page, table_id)
    page_marker = current_page_marker(page)
    return (page.url, page_marker, first_row_sig)


def go_to_next_page(
    page,
    table_id: str,
    next_icon_d: str,
    first_row_sig: str,
    page_marker: str,
    timeout: int = 8,
    wait_timeout: int = 10,
) -> bool:
    fallback_xpaths = [
        "//a[@rel='next']",
        "//button[@aria-label='Next' or @title='Next']",
        "//*[@role='button' and (@aria-label='Next' or @title='Next')]",
    ]
    deadline = time.time() + timeout
    button = None
    while time.time() < deadline and button is None:
        button = find_next_control(page, next_icon_d, fallback_xpaths)
        if button is None:
            time.sleep(0.25)
    if button is None:
        return False
    current_url = page.url
    try:
        button.scroll_into_view_if_needed()
    except Exception:
        pass
    try:
        button.click()
    except Exception:
        try:
            page.evaluate("(el) => el.click()", button)
        except Exception:
            return False
    wait_deadline = time.time() + wait_timeout
    while time.time() < wait_deadline:
        if page.url != current_url:
            return True
        if first_row_signature(page, table_id) and first_row_signature(page, table_id) != first_row_sig:
            return True
        if current_page_marker(page) and current_page_marker(page) != page_marker:
            return True
        time.sleep(0.25)
    return False


class PaginatedTableScraper:
    def __init__(
        self,
        table_id: str,
        next_icon_d: str,
        consent_xpaths: Iterable[str] | None = None,
        page_url_field: str | None = None,
        skip_signature_headers: set[str] | None = None,
    ) -> None:
        self.table_id = table_id
        self.next_icon_d = next_icon_d
        self.consent_xpaths = list(consent_xpaths or [])
        self.page_url_field = page_url_field
        self.skip_signature_headers = skip_signature_headers or set()

    def build_driver(self) -> PlaywrightSession:
        return build_driver()

    def accept_consent(self, page) -> None:
        if not self.consent_xpaths:
            return
        accept_consent(page, self.consent_xpaths)

    def add_page_url(
        self, headers: list[str], rows: list[dict], page_url: str
    ) -> list[str]:
        if not self.page_url_field:
            return headers
        if self.page_url_field not in headers:
            headers = headers + [self.page_url_field]
        for row in rows:
            row[self.page_url_field] = page_url
        return headers

    def scrape_with_driver(
        self, driver: PlaywrightSession, url: str
    ) -> tuple[list[str], list[dict]]:
        driver.get(url)
        page = driver.page
        self.accept_consent(page)
        headers, page_rows = extract_rows(page, self.table_id, headers=None)
        headers = self.add_page_url(headers, page_rows, driver.current_url)
        page_num = 1
        print_page_head(headers, page_rows, f"Page {page_num}")
        all_rows: list[dict] = []
        all_rows.extend(page_rows)
        seen_pages = set()
        signature = page_signature(
            page,
            self.table_id,
            headers,
            page_rows,
            skip_headers=self.skip_signature_headers,
        )
        seen_pages.add(signature)
        while True:
            first_row_sig = signature[2]
            page_marker = signature[1]
            if not go_to_next_page(
                page,
                self.table_id,
                self.next_icon_d,
                first_row_sig,
                page_marker,
            ):
                print(f"Page {page_num + 1} not found.")
                break
            try:
                headers, page_rows = extract_rows(
                    page,
                    self.table_id,
                    headers=headers,
                    first_row_not=first_row_sig,
                )
            except PlaywrightTimeoutError:
                print(f"Page {page_num + 1} not found.")
                break
            headers = self.add_page_url(headers, page_rows, driver.current_url)
            page_num += 1
            signature = page_signature(
                page,
                self.table_id,
                headers,
                page_rows,
                skip_headers=self.skip_signature_headers,
            )
            if signature in seen_pages:
                print(f"Page {page_num} repeats a prior page; stopping.")
                break
            seen_pages.add(signature)
            print_page_head(headers, page_rows, f"Page {page_num}")
            all_rows.extend(page_rows)
        return headers, all_rows
