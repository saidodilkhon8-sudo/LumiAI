# LumiAI

## Deploy on Render (free test setup)

LumiAI uses Telegram long polling. The included `render.yaml` runs it as a free
Render **Web Service** with a small `/health` endpoint because free plans do not
include Background Workers or persistent disks.

This is for testing only: free services can sleep when idle, and the SQLite
database is on an ephemeral filesystem. Bot availability may be interrupted,
and database contents can be lost when the service restarts or redeploys.
For reliable operation and persistent SQLite data, use a paid Background Worker
with a persistent disk.

1. Push this project to a GitHub repository. Keep `.env` out of Git; it is ignored by `.gitignore`.
2. In Render, choose **New → Blueprint** and connect the repository.
3. Set the prompted environment variables:
   - `BOT_TOKEN`: Telegram bot token from BotFather.
   - `GROQ_API_KEY`: API key from Groq.
   - `DEFAULT_MODEL`: an available model ID for your Groq account.
4. Apply the Blueprint. Check the service's logs in Render to confirm it starts.

## Run locally

Create a `.env` file using `.env.example`, fill in the required credentials, then run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app
```
