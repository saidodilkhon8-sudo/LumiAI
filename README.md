# LumiAI

## Deploy on Render

LumiAI uses Telegram long polling, so deploy it as a Render **Background Worker**.
The `render.yaml` Blueprint also attaches a persistent disk for the SQLite database.
The worker and disk require a paid Render plan.

1. Push this project to a GitHub repository. Keep `.env` out of Git; it is ignored by `.gitignore`.
2. In Render, choose **New → Blueprint** and connect the repository.
3. Set the prompted environment variables:
   - `BOT_TOKEN`: Telegram bot token from BotFather.
   - `GROQ_API_KEY`: API key from Groq.
   - `DEFAULT_MODEL`: an available model ID for your Groq account.
4. Apply the Blueprint. Check the worker's logs in Render to confirm it starts.

The SQLite database is stored at `/var/data/lumi_ai.db` on the persistent disk.

## Run locally

Create a `.env` file using `.env.example`, fill in the required credentials, then run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app
```
