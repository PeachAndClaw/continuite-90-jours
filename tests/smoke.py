from pathlib import Path
import csv
import json
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "test-results"
BASE_URL = "http://127.0.0.1:4173/"
CANONICAL_URL = "https://peachandclaw.github.io/continuite-90-jours/"


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
        requested_urls: list[str] = []
        desktop = browser.new_page(viewport={"width": 1440, "height": 1000})
        desktop.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        desktop.on("pageerror", lambda error: page_errors.append(str(error)))
        desktop.on("request", lambda request: requested_urls.append(request.url))
        response = desktop.goto(BASE_URL, wait_until="networkidle")
        assert response is not None and response.ok, "The local page did not load"
        assert desktop.title() == "Carte de continuité 90 jours — Peach & Claw"
        heading = " ".join(desktop.locator("h1").inner_text().split())
        assert heading == "Un revenu baisse. Qu’est-ce qui tient ?"
        assert desktop.locator("text=EXEMPLE / NON CLIENT").count() == 1
        assert desktop.locator("text=250 € HT").count() >= 2
        assert desktop.locator("text=72 heures").count() >= 2
        assert desktop.locator("script").count() == 1, "Only JSON-LD should remain"
        assert desktop.locator("[src*='tracker'], [src*='analytics']").count() == 0
        assert desktop.locator("link[href*='fonts.googleapis.com'], link[href*='fonts.gstatic.com']").count() == 0
        assert desktop.locator("a[href*='stripe'], a[href*='paypal']").count() == 0
        assert desktop.locator("form, input, textarea").count() == 0
        page_text = desktop.locator("body").inner_text()
        assert "résultat garanti" not in page_text.lower()
        assert "ROI" not in page_text
        assert desktop.locator(".hero__facts[role='list'] [role='listitem']").count() == 4
        assert desktop.locator("#questions details").count() == 8
        assert "Coupable" not in page_text
        assert "ordre sûr" not in page_text.lower()
        assert desktop.get_by_role("link", name="Auditer le spécimen").is_visible()

        assert desktop.locator("meta[name='description']").get_attribute("content")
        assert desktop.locator("meta[name='robots']").get_attribute("content") == "index,follow,max-image-preview:large"
        assert desktop.locator("link[rel='canonical']").get_attribute("href") == CANONICAL_URL
        assert desktop.locator("link[hreflang='fr-FR']").get_attribute("href") == CANONICAL_URL
        assert desktop.locator("meta[property='og:image']").get_attribute("content") == CANONICAL_URL + "assets/og-card.png"

        schema = json.loads(desktop.locator("script[type='application/ld+json']").text_content())
        graph = schema["@graph"]
        graph_types = {item["@type"] for item in graph}
        assert {"Organization", "WebSite", "WebPage", "Service", "FAQPage"} <= graph_types
        service = next(item for item in graph if item["@type"] == "Service")
        assert service["offers"]["price"] == "250"
        assert service["offers"]["priceCurrency"] == "EUR"
        faq = next(item for item in graph if item["@type"] == "FAQPage")
        assert len(faq["mainEntity"]) == 8

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
            "assets/fonts/manrope-latin.woff2",
            "assets/fonts/unbounded-latin.woff2",
            "assets/fonts/ibm-plex-mono-500-latin.woff2",
            "assets/fonts/ibm-plex-mono-600-latin.woff2",
            "robots.txt",
            "sitemap.xml",
            "llms.txt",
            "transparence.html",
            "specimen.html",
            "assets/specimen-registre.csv",
        ):
            asset_response = desktop.request.get(BASE_URL + relative_path)
            assert asset_response.ok, f"Missing asset: {relative_path}"

        assert_no_horizontal_overflow(desktop, "desktop")
        assert {
            urlparse(url).netloc for url in requested_urls
        } == {"127.0.0.1:4173"}, f"Unexpected runtime hosts: {requested_urls}"
        desktop.screenshot(path=RESULTS / "desktop.png", full_page=True)

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(BASE_URL, wait_until="networkidle")
        assert mobile.locator("h1").is_visible()
        assert mobile.get_by_role("link", name="Vérifier ma situation").is_visible()
        assert_no_horizontal_overflow(mobile, "mobile")
        mobile.screenshot(path=RESULTS / "mobile.png", full_page=True)

        transparency = browser.new_page(viewport={"width": 1280, "height": 900})
        transparency_response = transparency.goto(BASE_URL + "transparence.html", wait_until="networkidle")
        assert transparency_response is not None and transparency_response.ok
        assert transparency.get_by_role("heading", name="Transparence, hébergement et données").is_visible()
        assert transparency.locator("text=Aucun paiement ne doit être effectué").count() == 1
        assert transparency.locator("text=héberge localement ses polices").count() == 1
        assert transparency.locator("link[href*='fonts.googleapis.com'], link[href*='fonts.gstatic.com']").count() == 0
        assert_no_horizontal_overflow(transparency, "transparency")

        specimen = browser.new_page(viewport={"width": 1440, "height": 1000})
        specimen_response = specimen.goto(BASE_URL + "specimen.html", wait_until="networkidle")
        assert specimen_response is not None and specimen_response.ok
        assert specimen.get_by_role("heading", name="Une décision auditable, ligne par ligne").is_visible()
        assert specimen.locator("text=52,3 jours").count() == 1
        assert specimen.locator("text=91,3 jours").count() == 1
        assert specimen.locator("text=NON CLIENT").count() == 1
        assert specimen.locator("table tbody tr").count() == 6
        assert specimen.get_by_role("link", name="Télécharger toutes les lignes").is_visible()
        assert_no_horizontal_overflow(specimen, "specimen")
        specimen.screenshot(path=RESULTS / "specimen.png", full_page=True)

        specimen_mobile = browser.new_page(viewport={"width": 390, "height": 844})
        specimen_mobile.goto(BASE_URL + "specimen.html", wait_until="networkidle")
        assert specimen_mobile.locator("h1").is_visible()
        assert_no_horizontal_overflow(specimen_mobile, "specimen mobile")
        specimen_mobile.screenshot(path=RESULTS / "specimen-mobile.png", full_page=True)

        with (ROOT / "assets" / "specimen-registre.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        assert len(rows) == 19
        totals: dict[str, int] = {}
        for row in rows:
            category = row["Categorie"]
            totals[category] = totals.get(category, 0) + int(row["Montant_mensuel_EUR"])
        assert totals == {"Vital": 1380, "Support": 620, "Gelable": 250, "Supprimable": 160}
        assert sum(totals.values()) == 2410

        og = browser.new_page(viewport={"width": 1200, "height": 630})
        og.goto(BASE_URL + "assets/og-card.svg", wait_until="networkidle")
        og.screenshot(path=ROOT / "assets" / "og-card.png")

        assert not console_errors, f"Console errors: {console_errors}"
        assert not page_errors, f"Page errors: {page_errors}"
        browser.close()

    print("PASS desktop/mobile specimen=auditable totals=2410 assets=ok mailto=ok no-overflow")


if __name__ == "__main__":
    main()
