
# GEMINI Project: Telegram Social Media Downloader Bot

## Project Overview

This project is a Telegram bot that downloads videos from TikTok, Instagram, and YouTube and sends them to a Telegram chat. The bot listens for messages containing links from these platforms, downloads the corresponding media, and sends it back to the chat, deleting the original message with the link.

**Key Technologies:**

*   **Backend:** Python
*   **Telegram Bot Framework:** `python-telegram-bot`
*   **Social Media Downloaders:**
    *   TikTok: `pyktok`
    *   Instagram: `instaloader`
    *   YouTube: `yt-dlp`
*   **Environment Variables:** `python-dotenv`

**Project Structure:**

*   `main.py`: The main entry point of the application. It initializes the Telegram bot, handles incoming messages, and dispatches link processing to the appropriate service.
*   `tiktok_service.py`:  Handles the logic for downloading videos and photo carousels from TikTok.
*   `instagram_service.py`: Manages downloading videos from Instagram.
*   `youtube_service.py`: Responsible for downloading videos from YouTube Shorts.
*   `requirements.txt`: Lists all the necessary Python dependencies for the project.
*   `.gitignore`: Specifies files and directories to be ignored by Git.
*   `test_bot.py`, `instagram_test.py`: Test files for the bot and Instagram service.

## Building and Running

To run this project, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a `.env` file in the root directory and add your Telegram bot token:
    ```
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    ```

5.  **Run the bot:**
    ```bash
    python main.py
    ```

## Development Conventions

*   **Modular Design:** The code is organized into separate modules for each social media platform, promoting separation of concerns and maintainability.
*   **Environment Variables:** Sensitive information, such as the Telegram bot token, is managed through a `.env` file and loaded using `python-dotenv`.
*   **Error Handling:** The bot includes basic error handling to catch and report issues when processing links.
*   **Code Style:** The code generally follows standard Python conventions.
