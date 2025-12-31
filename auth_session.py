from playwright.sync_api import sync_playwright

OUT = "storage_state.json"

with sync_playwright() as pw:
    # Use a specific viewport to ensure the UI renders correctly
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = context.new_page()
    
    page.goto("https://hpe.atlassian.net/wiki/spaces/CPC/pages/3572960914/Project+PCAI")
    
    print("Step 1: Complete login (Okta/MFA) in the opened browser.")
    print("Step 2: Ensure you are fully redirected to the Wiki Home page.")
    print("Step 3: Press Enter here to save the session...")
    input()
    
    # Optional: Wait for a specific element that only appears when logged in
    # page.wait_for_selector("text=Create", timeout=5000) 

    # Capture the state
    context.storage_state(path=OUT)
    print(f"Successfully saved session state to {OUT}")
    
    browser.close()
