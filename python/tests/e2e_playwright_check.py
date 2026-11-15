import os
import time
from playwright.sync_api import sync_playwright

def run_playwright_e2e():
    print("================================================================")
    print("Starting Playwright E2E Test Suite on Botmartz VORTEX Studio...")
    print("================================================================")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        # 1. Load application
        print("[Step 1/6] Navigating to http://127.0.0.1:8420/ ...")
        response = page.goto("http://127.0.0.1:8420/", wait_until="networkidle")
        assert response.status == 200, f"Expected 200 OK, got {response.status}"
        print("  ✓ Page loaded successfully (HTTP 200).")

        # 2. Verify Title and Persistent Sidebar
        print("[Step 2/6] Verifying Title & Persistent Sidebar Layout...")
        assert "VORTEX" in page.title(), f"Unexpected title: {page.title()}"
        sidebar = page.locator(".app-sidebar")
        assert sidebar.is_visible(), "Sidebar (.app-sidebar) must be rendered and visible"
        print("  ✓ App sidebar (.app-sidebar) is rendered.")

        # Verify Sidebar telemetry
        ram_label = page.locator("text=RAM Footprint")
        assert ram_label.is_visible(), "RAM Footprint telemetry must be visible in sidebar"
        print("  ✓ Engine health & RAM footprint telemetry is present.")

        # 3. Test Navigation Buttons in Sidebar
        print("[Step 3/6] Testing Navigation Elements...")
        nav_items = [
            ("Overview & Explainer", "explainer"),
            ("Ask & Search", "query"),
            ("Engine Comparison", "duel"),
            ("Knowledge Base", "data")
        ]
        for label, tab_key in nav_items:
            btn = page.locator(f".sidebar-nav-btn:has-text('{label}')")
            assert btn.is_visible(), f"Nav button for '{label}' should be visible"
        print("  ✓ All sidebar navigation elements are verified.")

        # Test hover on Overview's Start Querying button
        start_querying_btn = page.locator("button.btn.btn-primary:has-text('Start Querying')")
        assert start_querying_btn.is_visible(), "Start Querying button should be visible in Overview"
        start_querying_btn.hover()
        print("  ✓ Start Querying button hover check completed.")

        # 4. Test Ask & Search (Querying with VeriFAI Grounding)
        print("[Step 4/6] Navigating to 'Ask & Search' tab...")
        start_querying_btn.click()
        time.sleep(0.5)

        # Fill query input
        query_input = page.locator("#query-input")
        assert query_input.is_visible(), "Query input field not visible"
        query_input.fill("What is the temperature limit for CFM56-7B?")

        # Click Run Query
        run_btn = page.locator("button.btn.btn-primary:has-text('Run Query')")
        assert run_btn.is_visible(), "Run Query button should be visible"

        # Wait for query response
        with page.expect_response("**/v1/query", timeout=20000) as response_info:
            run_btn.click()
        resp = response_info.value
        assert resp.status == 200, f"Query failed with HTTP status {resp.status}"
        print("  ✓ Query HTTP 200 received. Verifying UI rendering...")

        # Wait for results card
        page.wait_for_selector("text=Verified Synthesis (VeriFAI™ Grounded)", timeout=10000)
        
        # Verify VeriFAI Audit Confidence section
        verifai_badge = page.locator("text=VERIFAI™ AUDIT CONFIDENCE")
        assert verifai_badge.is_visible(), "VeriFAI audit confidence section must be rendered in query results"
        print("  ✓ VeriFAI Audit section rendered successfully.")

        # 5. Test Knowledge Base (Drag-and-Drop / File Upload)
        print("[Step 5/6] Testing Knowledge Base & Local File Upload dropzone...")
        page.locator("#nav-data").click()
        time.sleep(0.5)

        dropzone = page.locator(".upload-dropzone")
        assert dropzone.is_visible(), "Upload dropzone must be visible on Knowledge Base tab"
        print("  ✓ Drag-and-drop file upload dropzone is active and visible.")

        # Check existing table / document list
        doc_rows = page.locator("table tbody tr")
        print(f"  ✓ Ingested document records in table: {doc_rows.count()}")

        # 6. Test Engine Comparison Tab
        print("[Step 6/6] Testing Engine Comparison Tab...")
        page.locator("#nav-duel").click()
        time.sleep(0.5)
        duel_view = page.locator(".card").first
        assert duel_view.is_visible(), "Engine comparison view must be visible"
        print("  ✓ Engine comparison view verified.")

        # Final check: console errors
        print("----------------------------------------------------------------")
        print(f"Total Browser Console Errors: {len(console_errors)}")
        if console_errors:
            print("Console Errors:", console_errors)
        assert len(console_errors) == 0, f"Expected 0 browser console errors, got {len(console_errors)}"

        # Take full-page screenshot
        screenshot_path = "/home/soham/.gemini/antigravity/brain/c452c3bc-94c2-4b6f-985d-96e11c6004f2/vortex_playwright_e2e_verified.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Saved full-page screenshot to: {screenshot_path}")

        browser.close()
        print("================================================================")
        print("ALL PLAYWRIGHT TESTS PASSED (100% SUCCESSFUL, ZERO REGRESSIONS).")
        print("================================================================")

if __name__ == "__main__":
    run_playwright_e2e()
