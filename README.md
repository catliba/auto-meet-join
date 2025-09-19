# AutoJoinMeet

An automated Google Meet joiner that runs on GitHub Actions.

## Setup

1. **Fork this repository** to your GitHub account

2. **Set up GitHub Secrets** in your repository:
   - Go to Settings → Secrets and variables → Actions
   - Add the following secrets:
     - `MEET_URL`: The Google Meet URL you want to join
     - `GUEST_NAME`: The name to use when joining as a guest (optional, defaults to "Caleb Li")

3. **Configure the schedule** in `.github/workflows/meet.yml`:
   - The current cron schedule is set to run at 4:30 AM PT (11:30 UTC)
   - Modify the cron expression as needed for your timezone

4. **Test the workflow**:
   - Go to Actions tab in your repository
   - Click "Auto-Join Google Meet" workflow
   - Click "Run workflow" to test manually

## How it works

- The bot joins the Google Meet as a guest
- It automatically mutes microphone and camera
- It stays in the meeting for the specified duration (default: 1 minute in GitHub Actions)
- It automatically leaves the meeting when done

## Files

- `meet_auto_join.py`: Main Python script
- `requirements.txt`: Python dependencies
- `.github/workflows/meet.yml`: GitHub Actions workflow configuration

## Notes

- The bot runs in headless mode (no GUI) on GitHub Actions
- Screenshots are saved for debugging purposes
- The bot handles various Google Meet UI changes automatically
