const { chromium } = require('@playwright/test');
const fs = require('fs');

const MEET_URL = process.env.MEET_URL;
const LEAVE_AFTER_MINUTES = parseInt(process.env.LEAVE_AFTER_MINUTES || '30', 10);

(async () => {
  // Recreate storage_state.json from the secret
  const stateB64 = process.env.PLAYWRIGHT_STATE_B64;
  if (!MEET_URL) throw new Error("MEET_URL not set");
  if (!stateB64) throw new Error("PLAYWRIGHT_STATE_B64 not set");
  fs.writeFileSync('storage_state.json', Buffer.from(stateB64, 'base64'));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ storageState: 'storage_state.json' });
  const page = await context.newPage();

  console.log("Opening Meet:", MEET_URL);
  await page.goto(MEET_URL, { waitUntil: 'domcontentloaded' });

  // Dismiss cookie banner if present
  const consent = page.locator('button:has-text("I agree"), button:has-text("Accept")');
  if (await consent.first().isVisible()) await consent.first().click();

  // Pre-mute best effort
  await page.keyboard.press('Control+E').catch(()=>{});
  await page.keyboard.press('Control+D').catch(()=>{});

  // Click a join button; treat Ask to join as success (host may still need to admit)
  const joinBtn = page.locator('button:has-text("Join now"), button:has-text("Join meeting"), button:has-text("Ask to join")');
  const visible = await joinBtn.first().isVisible();
  if (visible) await joinBtn.first().click();

  await page.screenshot({ path: 'meet_after_join.png' });
  console.log("Screenshot saved. Waiting to auto-leave...");

  await page.waitForTimeout(LEAVE_AFTER_MINUTES * 60 * 1000);

  const leaveBtn = page.locator('button[aria-label="Leave call"], button:has-text("Leave")');
  if (await leaveBtn.first().isVisible()) await leaveBtn.first().click();

  await browser.close();
  console.log("Done.");
})();
