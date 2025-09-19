import os, time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

MEET_URL = os.environ["MEET_URL"]
LEAVE_AFTER_MINUTES = int(os.environ.get("LEAVE_AFTER_MINUTES", "30"))
GUEST_NAME = os.environ.get("GUEST_NAME", "Caleb Li")  # default if not set

def make_driver():
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-plugins")
    opts.add_argument("--disable-images")
    opts.add_argument("--disable-javascript")
    opts.add_argument("--use-fake-ui-for-media-stream")
    opts.add_argument("--use-fake-device-for-media-stream")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--window-size=1280,900")
    
    # Try to use ChromeDriverManager for automatic driver management
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        d = webdriver.Chrome(service=service, options=opts)
    except ImportError:
        # Fallback to system ChromeDriver
        d = webdriver.Chrome(options=opts)
    
    d.set_window_size(1280, 900)
    return d

def click_if_present(driver, xpath, timeout=2):
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        el.click()
        return True
    except Exception:
        return False

def fill_guest_name_if_prompted(driver, name: str) -> bool:
    """
    If Meet shows a 'Your name' prompt for guests, fill it.
    Returns True if a name field was found and filled.
    """
    name_xpaths = [
        "//input[@aria-label='Your name']",
        "//input[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'name')]",
        "//input[contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'name')]",
        "//input[@name='pn']",
        "//input[@type='text' and not(@aria-hidden='true')]",
    ]
    for xp in name_xpaths:
        try:
            field = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, xp))
            )
            # sometimes an iframe is present; try to switch to it quickly
        except Exception:
            continue
        try:
            field.clear()
            field.send_keys(name)
            # Some flows require 'Continue' or pressing Enter before Join
            # Try a couple of likely buttons:
            clicked = (
                click_if_present(driver, "//button[.//span[contains(.,'Continue')]]", 1)
                or click_if_present(driver, "//button[contains(.,'Continue')]", 1)
            )
            if not clicked:
                field.send_keys(Keys.ENTER)
            return True
        except Exception:
            # keep hunting other selectors
            pass
    return False

def mute_shortcuts(driver):
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body.click()
        for combo in [(Keys.CONTROL, 'd'), (Keys.CONTROL, 'e')]:
            body.send_keys(combo[0] + combo[1])
    except Exception:
        pass

def join_meeting(driver):
    driver.get(MEET_URL)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # If Google shows a guest-name prompt, fill it now
    filled = fill_guest_name_if_prompted(driver, GUEST_NAME)
    print(f"Guest name filled: {filled}", flush=True)

    # Pre-mute mic/cam (best effort)
    mute_shortcuts(driver)

    # Try the various join buttons
    join_xpaths = [
        "//button[.//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'join now')]]",
        "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'join now')]/ancestor::button",
        "//button[.//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ask to join')]]",
        "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ask to join')]/ancestor::button",
        "//button[contains(@aria-label,'Join') or contains(@data-mdc-dialog-action,'join')]",
    ]
    joined = False
    t0 = time.time()
    while time.time() - t0 < 90 and not joined:
        for xp in join_xpaths:
            if click_if_present(driver, xp, timeout=2):
                joined = True
                break
        if not joined:
            time.sleep(1)

    print("JOINED" if joined else "WAITING ROOM / NOT JOINED", flush=True)
    return datetime.now()

def leave_meeting(driver):
    leave_xpaths = [
        "//button[@aria-label='Leave call']",
        "//button[.//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'leave')]]",
        "//button[contains(@data-mdc-dialog-action,'leave')]",
    ]
    for xp in leave_xpaths:
        if click_if_present(driver, xp, timeout=2):
            print("LEFT via button", flush=True)
            return
    driver.close()
    print("LEFT by closing tab", flush=True)

def main():
    print(f"Starting AutoJoinMeet at {datetime.now()}", flush=True)
    print(f"Meet URL: {MEET_URL}", flush=True)
    print(f"Guest name: {GUEST_NAME}", flush=True)
    print(f"Will leave after: {LEAVE_AFTER_MINUTES} minutes", flush=True)
    
    d = None
    try:
        print("Creating Chrome driver...", flush=True)
        d = make_driver()
        print("Driver created successfully", flush=True)
        
        print("Joining meeting...", flush=True)
        start = join_meeting(d)
        deadline = start + timedelta(minutes=LEAVE_AFTER_MINUTES)
        print("Will leave at:", deadline, flush=True)
        
        while datetime.now() < deadline:
            time.sleep(5)
            
        # Optional proof:
        try:
            d.save_screenshot("meet_after_join.png")
            print("Screenshot saved", flush=True)
        except Exception as e:
            print(f"Could not save screenshot: {e}", flush=True)
            
        print("Leaving meeting...", flush=True)
        leave_meeting(d)
        print("Successfully completed", flush=True)
        
    except Exception as e:
        print(f"Error occurred: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise
    finally:
        if d:
            try: 
                d.quit()
                print("Driver closed", flush=True)
            except Exception as e:
                print(f"Error closing driver: {e}", flush=True)

if __name__ == "__main__":
    main()
