# Enhanced Cognee - User Manual

A step-by-step guide for everyday users. No technical knowledge needed.

---

## 1. What is Enhanced Cognee?

Enhanced Cognee is your personal AI memory system. It stores notes,
decisions, facts, and anything else you want remembered, and lets you (or
your AI assistant) search and browse them later through a friendly web
dashboard.

Everything runs on YOUR computer. Your data never leaves your machine.

---

## 2. What you need before installing

| Requirement | Why | Where to get it |
|-------------|-----|-----------------|
| A computer with 8 GB+ RAM | The system runs several small databases | - |
| About 5 GB free disk space | For the app and your data | - |
| Docker Desktop (free) | Runs the system's components safely in the background | https://www.docker.com/products/docker-desktop/ |

Installing Docker Desktop:

1. Open the link above and click "Download Docker Desktop" for your system
   (Windows, Mac, or Linux).
2. Run the downloaded file and follow the prompts (accept the defaults).
3. Restart your computer if asked.
4. Start "Docker Desktop" once from your Start menu / Applications. Wait
   until it says "Docker Desktop is running" (a whale icon appears in your
   system tray / menu bar).

You only do this once.

---

## 3. Installing Enhanced Cognee

### Windows

1. Download `EnhancedCognee-Setup-<version>.exe` from the project's
   Releases page.
2. Double-click it. If Windows shows a blue "protected your PC" message,
   click "More info" then "Run anyway".
3. Follow the installer (Next, Next, Install). Leave "Create a desktop
   icon" ticked.
4. When it finishes, "Enhanced Cognee" appears in your Start menu and on
   your desktop.

### Mac

1. Download `EnhancedCognee-<version>.dmg` from the Releases page.
2. Double-click the file, then drag the "EnhancedCognee" icon onto the
   "Applications" folder shown next to it.
3. Open it from Applications. The first time, if macOS warns about an app
   from the internet, right-click the app and choose "Open", then "Open"
   again.

### Linux

1. Download `EnhancedCognee-<version>-x86_64.AppImage` from the Releases
   page.
2. Right-click the file, choose Properties > Permissions, and tick "Allow
   executing file as program" (or run `chmod +x` on it).
3. Double-click to run.

   Alternative: download the `.tar.gz`, extract it, and run `./install.sh`
   inside -- this adds "Enhanced Cognee" to your application menu.

---

## 4. Starting the system (every time)

1. Open "Enhanced Cognee" (desktop icon / Start menu / Applications).
2. The launcher window opens and checks Docker:
   - If Docker is not running, the launcher tries to start it for you.
   - If Docker is not installed, click "Get Docker Desktop" and see
     section 2 above.
3. Click "Start Enhanced Cognee".
   - THE FIRST TIME ONLY: the system downloads its components (about
     2 GB). This can take 5-15 minutes depending on your internet. The
     activity log at the bottom shows progress. Later starts take under a
     minute.
4. When everything is ready, your web browser opens the dashboard
   automatically at: http://localhost:9050
   (You can also click "Open Dashboard" any time.)

To stop: click "Stop Enhanced Cognee" in the launcher. Your memories are
kept safe and will be there next time.

---

## 5. Using the dashboard

The dashboard runs in your web browser. The left sidebar has these pages:

### Dashboard (home)
Shows totals (memories, agents, sessions), recent activity, and a system
status panel with four green/red dots -- one per database. All green means
everything is healthy.

### Memories
Your main workspace.
- "Add Memory" button (top right): type or paste anything you want stored
  -- a note, a decision, a piece of research. Optionally pick a type
  (e.g. decision, discovery) to keep things organized.
- Click any memory to see its full content, details, and related
  memories.
- Tick checkboxes to select several memories, then export or delete them
  together.
- Use the filter panel to narrow by type, agent, or date.

### Search
Type what you are looking for in plain words -- you do not need exact
matches. Results are ranked by relevance.

### Sessions
If you use Enhanced Cognee with an AI assistant (like Claude), each
conversation can be tracked as a session. Click a session to see the
memories created during it on a timeline.

### Analytics
Charts of your memory activity: how many memories you have, of which
types, and an activity calendar showing your busiest days.

### Agents
Lists every "agent" (you, your AI assistants, or tools) that has stored
memories, with counts. Click one to see only its memories.

### Settings
Switch between light and dark mode, and test the connection to the
system's databases.

---

## 6. Frequently asked questions

**Where is my data stored?**
On your computer, inside Docker's storage. Stopping or reinstalling the
app does not delete it.

**How do I completely remove my data?**
Open a terminal/command prompt and run:
`docker compose -p enhanced-cognee down -v`
(The `-v` removes the data volumes. This cannot be undone.)

**Can I use it from another device?**
By default the system only listens on your own computer (localhost) for
safety. Remote access requires a technical setup -- see
`docs/operations/PRODUCTION_DEPLOYMENT_GUIDE.md`.

**Does it need the internet?**
Only for the first download and updates. Day-to-day use is fully local.

**How do I update?**
Install the new version over the old one (Windows/Mac) or replace the
AppImage (Linux). Your data is untouched. The launcher refreshes the
system components automatically on the next start.

---

## 7. Troubleshooting

| Problem | What to do |
|---------|------------|
| Launcher says "Docker is not installed" | Install Docker Desktop (section 2), then reopen the launcher. |
| Launcher says "Docker is installed but not running" | Start Docker Desktop manually, wait for the whale icon, then reopen the launcher. |
| "Start" fails with a download error | Check your internet connection and try again -- the first start downloads about 2 GB. |
| Browser shows "site can't be reached" at localhost:9050 | The services may still be starting. Wait a minute and refresh. If it persists, stop and start again from the launcher. |
| A status dot on the Dashboard page is red | Click Stop, then Start in the launcher. If it stays red, restart Docker Desktop and try again. |
| Everything is slow | Make sure your computer has at least 8 GB RAM and that Docker Desktop's resource settings (Settings > Resources) allow at least 4 GB memory. |
| I forgot to stop it -- is that bad? | No. It idles with very little CPU. Stop it whenever you like. |

Still stuck? Check the launcher's activity log (bottom of the window) --
it usually names the failing component -- and report an issue with that
text on the project's GitHub Issues page.

---

## 8. For technical users (optional)

- The launcher's runtime files live in:
  - Windows: `%LOCALAPPDATA%\EnhancedCognee`
  - macOS: `~/Library/Application Support/EnhancedCognee`
  - Linux: `~/.local/share/enhanced-cognee`
- REST API: http://localhost:8000 (interactive docs at /docs)
- Databases (localhost only): PostgreSQL 25432, Qdrant 26333, ArcadeDB
  22480 (HTTP) / 27687 (Bolt), Valkey 26379
- MCP server integration for Claude Code and other IDEs: see
  `docs/guides/CROSS_IDE_INSTALLATION.md`
- Developer setup from source: see `docs/QUICK_START.md`
