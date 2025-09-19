const { chromium } = require('@playwright/test');
const fs = require('fs');

const MEET_URL = process.env.MEET_URL;
const LEAVE_AFTER_MINUTES = parseInt(process.env.LEAVE_AFTER_MINUTES || '5', 10); // short while debugging
const STATE_B64 = process.env.PLAYWRIGHT_STATE_B64;

function log(msg){ console.log(`[meet] ${msg}`); }

async function save(page, name) {
  await page.screenshot({ path: `${name}.png`, fullPage: true }).catch(()=>{});
  const html = await page.content().catch(()=> '');
  fs.writeFileSync(`${name}.html`, html);
  log(`Saved ${name}.png and ${name}.html`);
}

(async () => {
  if (!MEET_URL) throw new Error("Missing MEET_URL");
  if (!STATE_B64) throw new Error("Missing PLAYWRIGHT_STATE_B64");

  // Recreate storage_state.json from secret
  fs.writeFileSync('storage_state.json', Buffer.from(STATE_B64, 'base64'));

  // Start trace to replay steps later
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    storageState: 'storage_state.json',
    locale: 'en-US',
    timezoneId: 'America/Los_Angeles'
  });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });

  const page = await context.newPage();

  // 0) Console logs from the page (helpful for blocked errors)
  page.on('console', m => log(`console[${m.type()}] ${m.text()}`));

  // 1) Confirm we are signed in
  log('Opening accounts.google.com to verify sign-in…');
  await page.goto('https://accounts.google.com/', { waitUntil: 'domcontentloaded' });
  await save(page, '01_accounts');

  const isSignedIn = await page.locator('img[aria-label*="Google Account"], a[href*="SignOutOptions"]').first().isVisible()
                    || await page.getByText(/Security issues found|Manage your Google Account/i).first().isVisible();
  log(`Signed-in check: ${isSignedIn ? 'YES' : 'NO'}`);
  if (!isSignedIn) {
    log('Not signed in. Your storage_state may be expired/invalid.');
    await context.tracing.stop({ path: 'trace.zip' });
    await browser.close();
    process.exit(1);
  }

  // 2) Go to Meet pre-join
  const meetUrl = MEET_URL.includes('?') ? MEET_URL : `${MEET_URL}?pli=1`;
  log(`Opening Meet: ${meetUrl}`);
  await page.goto(meetUrl, { waitUntil: 'domcontentloaded' });

  // Try dismissing cookie/consent
  const consent = page.locator('button:has-text("I agree"), button:has-text("Accept"), [data-testid="cookie-policy-accept"]');
  if (await consent.first().isVisible()) { await consent.first().click().catch(()=>{}); }

  // Pre-mute best effort (won’t fail run if unsupported)
  await page.keyboard.press('Control+E').catch(()=>{});
  await page.keyboard.press('Control+D').catch(()=>{});

  await save(page, '02_meet_loaded');

  // 3) Look for join buttons (multiple variants)
  const join = page.locator(
    'button:has-text("Join now"), button:has-text("Join meeting"), button:has-text("Ask to join"), ' +
    'button[aria-label*="Join"], div[role="button"]:has-text("Join")'
  );
  const joinVisible = await join.first().isVisible();
  log(`Join button visible: ${joinVisible}`);

  if (!joinVisible) {
    // Look for common block states
    const cannotJoin = await page.getByText(/You can’t join this video call|You can't join this video call/i).first().isVisible();
    const needHost = await page.getByText(/This call is restricted|Only people with access|Not allowed/i).first().isVisible();
    log(`Blocked message: cannotJoin=${cannotJoin} needHost=${needHost}`);

    await save(page, '03_meet_no_join');
    await context.tracing.stop({ path: 'trace.zip' });
    await browser.close();
    process.exit(cannotJoin || needHost ? 2 : 3);
  }

  // 4) Click join/ask-to-join and capture proof
  log('Clicking join…');
  await join.first().click({ timeout: 10000 }).catch(()=>{});
  await page.waitForTimeout(2000);
  await save(page, '04_after_click');

  // 5) Wait, then try to leave
  log(`Waiting ${LEAVE_AFTER_MINUTES} minute(s) before leaving…`);
  await page.waitForTimeout(LEAVE_AFTER_MINUTES * 60 * 1000);

  const leave = page.locator('button[aria-label="Leave call"], button:has-text("Leave")');
  if (await leave.first().isVisible()) {
    await leave.first().click().catch(()=>{});
    log('Leave clicked.');
  } else {
    log('Leave button not found; closing.');
  }

  await context.tracing.stop({ path: 'trace.zip' });
  await browser.close();
  log('Done.');
})();
