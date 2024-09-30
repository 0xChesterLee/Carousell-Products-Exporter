from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from bs4 import BeautifulSoup
import pandas as pd
import os
import requests
import re
from PIL import Image
from io import BytesIO


def clean_filename(filename):
    # Define a regex pattern for invalid characters
    invalid_chars_pattern = r'[<>:"/\\|?*\x00-\x1F]'
    
    # Replace invalid characters with an underscore
    cleaned_filename = re.sub(invalid_chars_pattern, '_', filename)
    
    # Optionally, you can also strip leading/trailing whitespace and limit length
    cleaned_filename = cleaned_filename.strip()
    
    # Limit the filename length to a reasonable maximum (e.g., 255 characters)
    max_length = 255
    if len(cleaned_filename) > max_length:
        cleaned_filename = cleaned_filename[:max_length]

    # Ensure the cleaned filename is not empty
    if not cleaned_filename:
        cleaned_filename = 'default_filename'
    
    return cleaned_filename

def extract_carousell2json(username):
    # Set up the WebDriver using the ChromeDriverManager
    chrome_options = Options()
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1')

    # Set up the WebDriver using the ChromeDriverManager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Open a webpage
    driver.get('https://www.carousell.com.hk/u/{0}/'.format(username))

    # Wait for the page to load
    time.sleep(2)  # Adjust sleep time as needed

    # Scroll down until no new content is loaded
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll down to the bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait for new content to load
        time.sleep(1)  # Adjust this based on the loading time of your content

        # Calculate new scroll height and compare with last height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break  # Exit the loop if no new content is loaded
        
        last_height = new_height

    # Find the div using XPath
    xpath_expression = '//*[@id="main"]/div/div[3]'  # Replace with the actual XPath expression
    div_element = driver.find_element('xpath', xpath_expression)

    # Extract the text or inner HTML from the div
    div_content = div_element.get_attribute('innerHTML')

    # Convert the content to JSON
    data = {
        "content": div_content
    }

    # Save the data to a local JSON file
    with open('output.json', 'w') as json_file:
        json.dump(data, json_file, indent=4)

    print("Data saved to output.json")

    # Alternatively, wait for user input to close the browser
    input('Press Enter to close the browser...')

    # Close the browser
    driver.quit()

def extract_url_from_json():
    # Load the JSON data from the file
    with open('output.json', 'r') as json_file:
        data = json.load(json_file)

    # Extract the HTML content from the JSON data
    html_content = data.get("content", "")

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all <a> tags and extract their href attributes
    urls = [a['href'] for a in soup.find_all('a', href=True)]

    # Save the extracted URLs to a new text file
    with open('urls.txt', 'w') as url_file:
        for url in urls:
            url_file.write('https://www.carousell.com.hk' + url + '\n')

    print("Extracted URLs saved to urls.txt.")

def extract_carousell_product_info(url):
    # Set up the WebDriver using the ChromeDriverManager
    chrome_options = Options()
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1')

    # Set up the WebDriver using the ChromeDriverManager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Open a webpage
    driver.get(url)

    # Wait for the page to load
    time.sleep(1)  # Adjust sleep time as needed

    # Extract product details using the specified XPaths
    product_details = {}
    image_urls = []

    try:
        # Extract product name
        product_name_element = driver.find_element("xpath", '//*[@id="FieldSetField-Container-field_title"]/div/div/h1')
        product_details["product_name"] = product_name_element.text
        print(product_details["product_name"])

        # Extract product price
        product_price_element = driver.find_element("xpath", '//*[@id="FieldSetField-Container-field_price"]/div/div/div/div/h2')
        product_details["product_price"] = product_price_element.text
        print(product_details["product_price"])

        # Extract product type
        product_type_element = driver.find_element("xpath", '//*[@id="FieldSetField-Container-field_listing_details_bp_v2"]/div/div[2]/div/p/span')
        product_details["product_type"] = product_type_element.text
        print(product_details["product_type"])

        # Extract product description
        product_description_element = driver.find_element("xpath", '//*[@id="FieldSetField-Container-field_description"]/div/div/p')
        product_details["product_description"] = product_description_element.text
        print(product_details["product_description"])

        # Extract image URLs
        image_elements = driver.find_elements("xpath", '//div[@class="D_aew M_aas"]//img')
        for img in image_elements:
            src = img.get_attribute("src")
            if src:  # Ensure the src is not None or empty
                image_urls.append(src)

    except Exception as e:
        print(f"Error extracting product details: {e}")
        driver.quit()
        return

    # Create a directory to save images
    os.makedirs('images', exist_ok=True)

    # Download and save each image
    i = 0
    for img_url in image_urls:
        try:
            # Get the image content
            img_data = requests.get(img_url).content
            # Create a unique filename
            img_name = product_details["product_name"]

            img_name = img_name.replace('.jpg', '')
            img_name = img_name + str(i)
            img_name = img_name + '.jpg'

            img_name = clean_filename(img_name)
            img_name = os.path.join('images', img_name)

            # Open the image and resize it
            with Image.open(BytesIO(img_data)) as img:
                img = img.resize((512, 512), Image.LANCZOS)  # Resize to 512x512
                img.save(img_name)  # Save the resized image
                i = i + 1
        except Exception as e:
            print(f"Failed to download {img_url}: {e}")
    
    # Append the extracted details to the JSON file
    try:
        # Load existing data
        with open('product_details.json', 'r', encoding='utf-8') as json_file:
            existing_data = json.load(json_file)
            if not isinstance(existing_data, list):  # Ensure it's a list
                existing_data = []  # Reset to an empty list if it's not
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = []  # If the file doesn't exist or is empty, start with an empty list

    existing_data.append(product_details)  # Append new data

    with open('product_details.json', 'w', encoding='utf-8') as json_file:
        json.dump(existing_data, json_file, ensure_ascii=False, indent=4)

    print('{0} Saved.\n'.format(str(product_details["product_name"])))

    # Close the browser
    driver.quit()

def convert_json_to_excel():
    # Load the JSON data from the specified file
    with open('product_details.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Create a DataFrame from the JSON data
    df = pd.DataFrame(data)

    # Save the DataFrame to an Excel file
    df.to_excel('output.xlsx', index=False)

    print('Data successfully written to output.xlsx')


# Start
extract_carousell2json('ihlove')
extract_url_from_json()

with open('urls.txt', 'r') as file:
        urls = file.readlines()
for url in urls:
        url = url.strip()  # Remove any leading/trailing whitespace/newline characters
        if url:  # Check if the URL is not empty
            extract_carousell_product_info(url) 
            print(url + 'OK!')

convert_json_to_excel()

print('Program End.')
