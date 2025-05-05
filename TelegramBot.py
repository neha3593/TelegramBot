import openai
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager  # Added
import time
import os

# Setup API keys
openai.api_key = "GIVE YOUR OPEN AI API KEY"
telegram_bot_token = "GIVE YOUR TELEGRAM BOT TOKEN"

# Function to scrape a page and find all internal links recursively using Selenium
def crawl_ibm_docs(start_url, max_pages=100):
    visited = set()
    all_text = ""

    # Setup Selenium headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run without opening browser window
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Correct Service using webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    def scrape(url):
        nonlocal all_text
        try:
            if url in visited or len(visited) >= max_pages:
                return
            visited.add(url)

            print(f"Scraping: {url}")
            driver.get(url)
            time.sleep(2)  # Wait for page to load JavaScript

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Extract all <p> paragraphs
            paragraphs = soup.find_all('p')
            page_text = "\n".join(p.get_text() for p in paragraphs)
            all_text += "\n" + page_text

            # Find all internal links
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(url, href)
                if 'ibm.com/docs' in full_url and full_url not in visited:
                    scrape(full_url)

        except Exception as e:
            print(f"Error scraping {url}: {e}")

    # Start scraping
    scrape(start_url)

    # Cleanup
    driver.quit()

    return all_text

# Telegram message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_question = update.message.text

    # Starting IBM Documentation Page
    start_url = "https://www.ibm.com/think/topics/cobol"  # Replace with your real page


    # Crawl IBM Docs
    ibm_text = crawl_ibm_docs(start_url, max_pages=5)  # limit to 5 pages for now

    if not ibm_text.strip():
        await update.message.reply_text("Sorry, I couldn't retrieve IBM documentation at the moment.")
        return

    # Create prompt
    prompt = f"""
You have access to the following IBM documentation collected from multiple pages:

{ibm_text[:12000]}   # Limit characters to avoid token overflow


Answer the following question based only on this documentation:

Question: {user_question}
"""

    # Call OpenAI
    client = openai.OpenAI(api_key=openai.api_key)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant answering based on IBM documentation only."},
            {"role": "user", "content": prompt}
        ]
    )

    answer = response.choices[0].message.content

    # Send answer back to Telegram
    await update.message.reply_text(answer)

# Main Telegram bot startup
def main():
    app = ApplicationBuilder().token(telegram_bot_token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Advanced IBM Selenium Crawler Chatbot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
