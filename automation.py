import asyncio
import logging
import os
import playwright
import random
import re
import requests
import shutil
import time
import uuid
from loguru import logger
from playwright.async_api import async_playwright, Page
from playwright.sync_api import sync_playwright
import csv
import sys

################################################################################################
# This program loads in prompts from CSV file and implements them in commercial diffusion model. 
# Once the images are created this program also upscales them and then downloads them
# to the Generated Images folder 
################################################################################################


# Get logger for this file
logger = logging.getLogger(__name__)
# Set logging level to INFO
logger.setLevel(logging.INFO)

# Define a custom log format without %(asctime)s
log_format = logging.Formatter('[%(levelname)s] [%(pathname)s:%(lineno)d] - %(message)s - [%(process)d:%(thread)d]')

file_handler = logging.FileHandler('automation.log', mode='a')  # Create file handler
file_handler.setFormatter(log_format)  # Set log format for file handler
logger.addHandler(file_handler)  # Add file handler to logger

console_handler = logging.StreamHandler()  # Create console handler
console_handler.setFormatter(log_format)  # Set log format for console handler
logger.addHandler(console_handler)  # Add console handler to logger

# Add condition to check if the current log statement is the same as the previous log statement, if so then don't log it
class NoRepeatFilter(logging.Filter):
    """Filter to ignore repeated log messages."""
    def __init__(self, name=''):
        """Initialize the filter.
        Args:
            name (str): Name of the filter.
        """
        super().__init__(name)
        self.last_log = None

    def filter(self, record):
        """Filter out repeated log messages.
        Args:
            record (LogRecord): Log record to be filtered.
        Returns:
            bool: True if log message is not a repeat, False otherwise.
        """

        # Ignore the %(asctime)s field when comparing log messages
        current_log = record.getMessage().split(' - ', 1)[-1]
        if current_log == self.last_log:
            return False
        self.last_log = current_log
        return True

# Create an instance of the NoRepeatFilter and add it to the logger
no_repeat_filter = NoRepeatFilter()
logger.addFilter(no_repeat_filter)

# Function to load the start point variable from a file
def load_variable():
    filename = "start_point.txt"
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return file.read().strip()
    else:
        return None

# Function to save the start point variable to a file
def save_variable(value):
    filename = "start_point.txt"
    with open(filename, 'w') as file:
        file.write(str(value))

# Function to download upscaled images
async def download_upscaled_images(page, prompt_text: str):
    try:
        # Define the CSS class for the message
        message_class = 'message__80c10'
        # Find all elements with the specified class
        messages = await page.query_selector_all(f'div.{message_class}')

        # Check that messages contain upscaled images
        last_four_messages = messages[-4:]
        check = 0
        for message in last_four_messages:
            message_text = await message.evaluate_handle('(node) => node.innerText')
            message_text = str(message_text)
            if 'Vary' in message_text and 'Web' in message_text:
                check +=1
        
        if check ==4:
            try:
                image_elements = await page.query_selector_all('a.originalLink__94d5d')
                last_four_images = image_elements[-4:] # Grab upscaled images
                os.makedirs('Generated Images', exist_ok=True)  # Create image directory if it doesn't exist
                
                # Download upscaled images
                for image in last_four_images:
                    src = await image.get_attribute('href')
                    url = src
                    response = re.sub(r'[^a-zA-Z0-9\s]', '', prompt_text)
                    response = response.replace(' ', '_').replace(',', '_')
                    response = re.sub(r'[\<>:"/|?*]', '', response)
                    response = response.replace('\n\n', '_')
                    response = response[:50].rstrip('. ')
                    file_name = f'{response}_{str(uuid.uuid1())}.png' # Append image title with unique identifier to stop overwriting

                    download_response = requests.get(url, stream=True)

                    with open(os.path.join('Generated Images', file_name), 'wb') as out_file:
                        shutil.copyfileobj(download_response.raw, out_file)
                
                logger.info("Images downloaded successfully.")
                await asyncio.sleep(random.randint(30, 40))

            except Exception as e:
                logger.info(f"An error occurred while downloading the images: {e}")

        else:
            await download_upscaled_images(page, prompt_text)

    except Exception as e:
        logger.info(f"An error occurred while finding the last message: {e}")


# Function to get the last message from the provided page.
async def get_last_message(page) -> str:
    """
    Parameters:
        - page: The page from which to fetch the last message.
    Returns:
        - str: The text of the last message.
    """

    try:
        message_class = 'message__80c10'  # Define the CSS class for the message
        messages = await page.query_selector_all(f'div.{message_class}') # Find all elements with the specified class

        if not messages:
            logger.error("No messages found on the page.")
            raise ValueError("No messages found on the page.")
        
        #take text from last message sent
        last_message = messages[-1]
        last_message_text = await last_message.evaluate('(node) => node.innerText')

        if not last_message_text:
            logger.error("Last message text cannot be empty.")
            raise ValueError("Last message text cannot be empty.")
        
        last_message_text = str(last_message_text)
        return last_message_text 
    
    except Exception as e:
        logger.error(f"Error occurred: {e} while getting the last message.")
        raise e

#  Main function that starts the bot and interacts with the page.
async def main(bot_command: str, channel_url: str, PROMPT: str):
    """
    Parameters:
    - bot_command (str): The command for the bot to execute.
    - channel_url (str): The URL of the channel where the bot should operate.
    - PROMPT (str): The prompt text.

    Returns:
    - None
    """
    try:
        browser = None
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto("https://www.discord.com/login")

            # Get credentials securely
            with open("credentials.txt", "r") as f: #CHANGE FOR SPECIFIC PATH
                email = f.readline()
                password = f.readline()
            if not email or not password:
                logger.error("Email or password not provided in credentials.txt.")
                raise ValueError("Email or password not provided in credentials.txt.")
            
            await page.fill("input[name='email']", email)
            await asyncio.sleep(random.randint(1, 5))
            await page.fill("input[name='password']", password)
            await asyncio.sleep(random.randint(1, 5))
            await page.click("button[type='submit']")
            await asyncio.sleep(random.randint(5, 10))
            await page.wait_for_url("https://discord.com/channels/@me", timeout=15000)
            logger.info("Successfully logged into Discord.")
            await asyncio.sleep(random.randint(1, 5))
            
            start_point = load_variable()

            if start_point is None:
             # If the variable is not stored, initialize it
                 start_point = 0
            else:
                 # If the variable is stored, use the stored value
                 start_point = int(start_point)

            num_images = 2 # Determine number of images to be generated

            # Automate image generation
            for i in range(num_images):
                j = start_point + i
                PROMPT = prompts[j]
                await open_discord_channel(page, channel_url, bot_command, PROMPT)
                logger.info(f"Iteration {i+1} completed.")
            new_start_point = str(start_point + num_images)
            save_variable(new_start_point) # Save updated start point for next time program is run
            logger.info(f"new start point =  {new_start_point}")
            
    except Exception as e:
        logger.error(f"Error occurred: {e} while executing the main function.")
        raise e
    finally:
        if browser:
            await browser.close()
      
# Function to open a Discord channel and send a bot command.
async def open_discord_channel(page, channel_url: str, bot_command: str, PROMPT: str):
    """
    Parameters:
    - page: The page object representing the current browser context.
    - channel_url (str): The URL of the channel to open.
    - bot_command (str): The bot command to send.
    - PROMPT (str): The prompt text.

    Returns:
    - None
    """
    try:
        await page.goto(f"{channel_url}") # Open discord website
        await asyncio.sleep(random.randint(1, 5))
        await page.wait_for_load_state("networkidle")
        logger.info("Successfully opened the appropriate channel.")

        logger.info("Entering the specified bot command.")
        await send_bot_command(page, bot_command, PROMPT) # Enter prompt in chat
    
    except Exception as e:
        logger.error(f"An error occurred while opening the channel and entering the bot command: {e}")
        raise e


# Function to select an upscale option based on the provided text.
async def select_upscale_option(page, option_text: str):
    """
    Parameters:
    - page: The page object representing the current browser context.
    - option_text (str): The text of the upscale option to select.

    Returns:
    - None
    """
    try:
        upscale_option = page.locator(f"button:has-text('{option_text}')").locator("nth=-1")
        if not upscale_option:
            logger.error(f"No upscale option found with text: {option_text}.")
            raise ValueError(f"No upscale option found with text: {option_text}.")
        
        await upscale_option.click()
        logger.info(f"Successfully clicked {option_text} upscale option.")
    
    except Exception as e:
        logger.error(f"An error occurred while selecting the upscale option: {e}")
        raise e

# Function to send a command to the bot in the chat bar.
async def send_bot_command(page, command: str, PROMPT: str):
    """
    Parameters:
    - page: The page object representing the current browser context.
    - command (str): The command to send to the bot.
    - PROMPT (str): The prompt for the command.

    Returns:
    - None
    """
    try:

        # Click on chat 
        logger.info("Clicking on chat bar.")
        chat_bar = page.get_by_role('textbox', name='Message @Midjourney Bot')
        await asyncio.sleep(random.randint(1, 5))

        # Enter imagine command 
        logger.info("Typing in bot Imagine command")
        await chat_bar.fill(command)
        await asyncio.sleep(random.randint(1, 5))
        
        # Select prompt box 
        logger.info("Selecting the prompt option")
        await page.click('div.title__139aa.text-md-normal__4afad')
        await asyncio.sleep(random.randint(1, 5))

        # Enter prompt 
        logger.info("Entering prompt...")
        emptySpanSelector = 'span.optionPillValue__07d44'
        await page.type(emptySpanSelector, PROMPT)
        await page.keyboard.press('Enter')
        logger.info(f'Successfully submitted prompt: {PROMPT}')
        await asyncio.sleep(random.randint(55, 65)) # Wait for image to be generated
        await wait_and_select_upscale_options(page, PROMPT)
        

    except Exception as e:
        logger.exception(f"An error occurred while sending the bot command: {e}")
        raise e

#  Function to start the bot with the specified parameters.
def start_bot(bot_command: str, channel_url: str, prompts):
    """
    Parameters:
    - bot_command (str): The command to send to the bot.
    - channel_url (str): The URL of the channel where the bot is located.

    Returns:
    - None
    """
    try:
        asyncio.run(main(bot_command, channel_url, prompts))

    except Exception as e:
        logger.error(f"An error occurred while starting the bot: {e}")
        raise e

    finally:
        sys.exit()

# Function to wait for and select upscale options.
async def wait_and_select_upscale_options(page, prompt_text: str):
    """
    Parameters:
    - page: The page to operate on.
    - prompt_text (str): The text of the prompt.

    Returns:
    - None
    """
    try:
        prompt_text = prompt_text.lower()

        # Repeat until upscale options are found
        while True:
            last_message = await get_last_message(page)

            # Check for 'U1' in the last message
            if 'U1' in last_message:
                logger.info("Found upscale options. Attempting to upscale all generated images.")
                try:
                    # Upscale all 4 images
                    await select_upscale_option(page, 'U1')
                    time.sleep(random.randint(3, 5))
                    await select_upscale_option(page, 'U2')
                    time.sleep(random.randint(3, 5))
                    await select_upscale_option(page, 'U3')
                    time.sleep(random.randint(3, 5))
                    await select_upscale_option(page, 'U4')
                    time.sleep(random.randint(3, 5))
                    logger.info("All generated images upscaled.")
                    time.sleep(random.randint(10, 15))

                except Exception as e:
                    logger.error(f"An error occurred while selecting upscale options: {e}")
                    raise e
                
                await download_upscaled_images(page, prompt_text) # Download images 
                break  # Exit the loop when upscaled images have been downloaded

            else:
                logger.info("Upscale options not yet available, waiting...")
                time.sleep(random.randint(3, 5))

    except Exception as e:
        logger.error(f"An error occurred while finding the last message: {e}")
        raise e

# Retrieve premade prompts from CSV file 
def get_prompts():

    csv_file_path = 'Adzy_prompts.csv' 
    target_column_index = 2  

    # List to store prompts from the prompt column
    prompt_list = []

    # Read the CSV file and extract values from the prompt column
    with open(csv_file_path, 'r', newline='') as csvfile:
        csv_reader = csv.reader(csvfile)
        for row in csv_reader:
            # Check if the row has enough columns
            if len(row) > target_column_index:
                value_from_third_column = row[target_column_index]
                prompt_list.append(value_from_third_column)

    prompt_list.pop(0)
    return prompt_list
    
if __name__ == '__main__':
    bot_command = "/imagine"
    channel_url = "https://discord.com/channels/@me/1087439749549146173"
    prompts = get_prompts()
    start_bot(bot_command, channel_url, prompts)()
