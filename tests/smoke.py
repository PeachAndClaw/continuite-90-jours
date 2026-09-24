from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "test-results"
BASE_URL = "http://127.0.0.1:4173/"


def assert_no_horizontal_overflow(page, label: str) -> None:
    dimensions = page.evaluate(
        """() => ({
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth
        })"""
    )
    assert dimensions["scrollWidth"] <= dimensions["clientWidth"] + 1, (
        f"{label}: horizontal overflow "
        f"{dimensions['scrollWidth']} > {dimensions['clientWidth']}"
    )


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="/usr/bin/google-chrome",
        )

        console_errors: list[str] = []
        page_errors: list[str] = []
        desktop = browser.new_page(viewport={"width": 1440, "height": 1000})
        desktop.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        desktop.on("pageerror", lambda error: page_errors.append(str(error)))
        response = desktop.goto(BASE_URL, wait_until="networkidle")
        assert response is not None and response.ok, "The local page did not load"
        assert desktop.title() == "Carte de continuité 90 jours — Peach & Claw"
        heading = " ".join(desktop.locator("h1").inner_text().split())
        assert heading == "Un client disparaît. Qu’est-ce qui survit ?"
        assert desktop.locator("text=EXEMPLE / NON CLIENT").count() == 1
        assert desktop.locator("text=250 € HT").count() >= 2
        assert desktop.locator("text=72 heures").count() >= 2
        assert desktop.locator("script").count() == 1, "Only JSON-LD should remain"
        assert desktop.locator("[src*='tracker'], [src*='analytics']").count() == 0

        links = desktop.locator("a").evaluate_all(
            "elements => elements.map(element => element.href)"
        )
        mailto_links = [link for link in links if link.startswith("mailto:")]
        assert len(mailto_links) == 3
        parsed_mailto = urlparse(mailto_links[0])
        assert parsed_mailto.path == "giannamikaelova@gmail.com"
        mailto_query = parse_qs(parsed_mailto.query)
        assert mailto_query["subject"] == [
            "Carte de continuité 90 jours — ma situation"
        ]
        assert "Mon activité" in mailto_query["body"][0]

        for anchor in ("#carte", "#specimen", "#pour-qui", "#demande"):
            assert desktop.locator(anchor).count() == 1

        for relative_path in (
            "assets/wordmark.svg",
            "assets/emblem.svg",
            "assets/favicon.svg",
            "assets/tokens.css",
            "styles.css",
            "sitemap.xml",
        ):
            asset_response = desktop.request.get(BASE_URL + relative_path)
            assert asset_response.ok, f"Missing asset: {relative_path}"

        assert_no_horizontal_overflow(desktop, "desktop")
        desktop.screenshot(path=RESULTS / "desktop.png", full_page=True)

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(BASE_URL, wait_until="networkidle")
        assert mobile.locator("h1").is_visible()
        assert mobile.get_by_role("link", name="Vérifier ma situation").is_visible()
        assert_no_horizontal_overflow(mobile, "mobile")
        mobile.screenshot(path=RESULTS / "mobile.png", full_page=True)

        og = browser.new_page(viewport={"width": 1200, "height": 630})
        og.goto(BASE_URL + "assets/og-card.svg", wait_until="networkidle")
        og.screenshot(path=ROOT / "assets" / "og-card.png")

        assert not console_errors, f"Console errors: {console_errors}"
        assert not page_errors, f"Page errors: {page_errors}"
        browser.close()

    print("PASS desktop=1440x1000 mobile=390x844 assets=ok mailto=ok no-overflow")


if __name__ == "__main__":
    main()
