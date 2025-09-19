import os, time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

MEET_URL = os.environ["MEET_URL"]  # set as GitHub Secret
LEAVE_AFTER_MINUTES = int(os.environ.get("LEAVE_AFTER_MINUTES", "30"))

def make_driver():
    opts = webdriver.ChromeOptions()
    # Headless for CI:
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--use-fake-ui-for-media-stream")  # auto-dismiss media prompt
    driver = webdriver.Chrome(options=opts)  # Selenium Manager grabs driver
    driver.set_window_size(1280, 900)
    return driver

def mute_shortcuts(driver):
    body = driver.find_element(By.TAG_NAME, "body")
    body.click()
    for combo in [(Keys.CONTROL, 'd'), (Keys.CONTROL, 'e')]:
        body.send_keys(combo[0] + combo[1])

def click_if_present(driver, xpath, timeout=3):
    try:
        btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        btn.click()
        return True
    except Exception:
        return False

def join_meeting(driver):
    driver.get(MEET_URL)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    try: mute_shortcuts(driver)
    except: pass

    join_xpaths = [
        "//button[.//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'join now')]]",
        "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'join now')]/ancestor::button",
        "//button[.//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ask to join')]]",
        "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ask to join')]/ancestor::button",
        "//button[contains(@aria-label, 'Join') or contains(@data-mdc-dialog-action, 'join')]",
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
    print("JOINED" if joined else "WAITING ROOM / NOT JOINED")
    return datetime.now()

def leave_meeting(driver):
    leave_xpaths = [
        "//button[@aria-label='Leave call']",
        "//button[.//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'leave')]]",
        "//button[contains(@data-mdc-dialog-action, 'leave')]",
    ]
    for xp in leave_xpaths:
        if click_if_present(driver, xp, timeout=2):
            print("LEFT via button")
            return
    driver.close()
    print("LEFT by closing tab")

def main():
    d = make_driver()
    try:
        start = join_meeting(d)
        deadline = start + timedelta(minutes=LEAVE_AFTER_MINUTES)
        while datetime.now() < deadline:
            time.sleep(5)
        leave_meeting(d)
    finally:
        try: d.quit()
        except: pass

if __name__ == "__main__":
    if not MEET_URL or "meet.google.com" not in MEET_URL:
        raise SystemExit("Set MEET_URL env var to your full Meet link")
    main()
