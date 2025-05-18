import time
import pandas as pd
import re
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager


def scrape_phivolcs_twitter(url="https://x.com/phivolcs_dost", max_tweets=40, scroll_pause_time=2,
                            max_scroll_attempts=200, no_new_tweets_threshold=10):
    """
    Scrapes earthquake information tweets from PHIVOLCS Twitter/X account with improved reliability.

    Args:
        url (str): URL of the PHIVOLCS Twitter/X page
        max_tweets (int): Maximum number of tweets to scrape
        scroll_pause_time (int): Time to pause between scrolls
        max_scroll_attempts (int): Maximum number of scroll attempts
        no_new_tweets_threshold (int): Stop after this many scroll attempts with no new tweets

    Returns:
        DataFrame: DataFrame containing earthquake information tweets
    """
    print("Setting up the Chrome driver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Hide automation
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    # Initialize the Chrome driver with explicit waits
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()

    print(f"Navigating to {url}...")
    driver.get(url)

    # Extended initial wait for page to load with randomization
    initial_wait = 8 + random.random() * 4  # Between 8-12 seconds
    print(f"Waiting {initial_wait:.2f} seconds for page to load...")
    time.sleep(initial_wait)

    # List to store tweet data and set to track seen tweet URLs
    tweets_data = []
    seen_tweet_urls = set()
    scroll_attempts = 0
    consecutive_no_new_tweets = 0

    # Get initial viewport height
    viewport_height = driver.execute_script("return window.innerHeight")

    # Create a WebDriverWait instance for finding elements
    wait = WebDriverWait(driver, 10)

    try:
        print("Scrolling through the feed to capture recent tweets...")
        while len(tweets_data) < max_tweets and scroll_attempts < max_scroll_attempts:
            # Use more robust XPATH to find tweets
            try:
                tweet_elements = wait.until(
                    EC.presence_of_all_elements_located((By.XPATH,
                                                         "//article[contains(@data-testid, 'tweet') or contains(@class, 'tweet') or contains(@role, 'article')]"))
                )
            except TimeoutException:
                print("Timeout while waiting for tweets to load")
                # Try a different approach if the first one fails
                try:
                    tweet_elements = driver.find_elements(By.XPATH,
                                                          "//div[contains(@data-testid, 'cellInnerDiv')]//article")
                except:
                    tweet_elements = []

            tweets_found_this_scroll = 0

            for tweet in tweet_elements:
                if len(tweets_data) >= max_tweets:
                    break

                try:
                    # More robust method to extract tweet text
                    tweet_text = ""

                    # Try multiple approaches to find the tweet text
                    text_elements = tweet.find_elements(By.XPATH,
                                                        ".//div[contains(@data-testid, 'tweetText')]")

                    if not text_elements:
                        # Alternative selector
                        text_elements = tweet.find_elements(By.XPATH,
                                                            ".//div[contains(@lang, 'en') or contains(@lang, 'tl')]")

                    for text_element in text_elements:
                        tweet_text += text_element.text + " "

                    tweet_text = tweet_text.strip()

                    # Skip if no text was found
                    if not tweet_text:
                        continue

                    # More flexible earthquake tweet detection
                    if any(keyword in tweet_text.upper() for keyword in [
                        "EARTHQUAKE", "MAGNITUDE", "LINDOL", "INTENSITY", "PHIVOLCS", "SEISMIC", "TREMOR"
                    ]):
                        # Extract time of posting with better error handling
                        time_elements = tweet.find_elements(By.CSS_SELECTOR, 'time')
                        datetime_str = None

                        if time_elements:
                            try:
                                datetime_str = time_elements[0].get_attribute('datetime')
                            except:
                                # Try to get the tweet time from the time element text
                                datetime_str = time_elements[0].text

                        # Get tweet URL with better error handling
                        tweet_url = None
                        try:
                            # Check multiple possible link patterns
                            tweet_links = tweet.find_elements(By.CSS_SELECTOR, 'a[href*="/status/"]')
                            if not tweet_links:
                                # Try alternative way to find links
                                tweet_links = tweet.find_elements(By.CSS_SELECTOR, 'a[role="link"]')

                            for link in tweet_links:
                                href = link.get_attribute('href')
                                if href and '/status/' in href:
                                    tweet_url = href
                                    break
                        except Exception as e:
                            print(f"Error extracting tweet URL: {e}")

                        # Only process tweets with a valid URL that we haven't seen before
                        if tweet_url and tweet_url not in seen_tweet_urls:
                            seen_tweet_urls.add(tweet_url)

                            # Parse earthquake information
                            earthquake_info = parse_earthquake_tweet(tweet_text)

                            # Create a data dictionary for this tweet
                            tweet_data = {
                                'tweet_text': tweet_text,
                                'datetime': datetime_str,
                                'tweet_url': tweet_url,
                                **earthquake_info
                            }

                            tweets_data.append(tweet_data)
                            tweets_found_this_scroll += 1
                            print(f"Earthquake tweet found! Total: {len(tweets_data)}")

                except StaleElementReferenceException:
                    # The page was updated during processing
                    print("Encountered stale element - page updated during processing")
                    break

                except Exception as e:
                    print(f"Error processing individual tweet: {e}")

            # Variable scroll distance with randomization to appear more human-like
            scroll_factor = 0.7 + random.random() * 0.4  # Between 0.7-1.1
            scroll_distance = viewport_height * scroll_factor

            # Use a smoother scrolling mechanism
            driver.execute_script(f"""
                window.scrollBy({{
                    top: {scroll_distance},
                    left: 0,
                    behavior: 'smooth'
                }});
            """)

            # Variable wait time between scrolls
            actual_pause = scroll_pause_time + random.random() * 2  # Add 0-2 seconds randomly
            time.sleep(actual_pause)

            scroll_attempts += 1

            # Track if we're not finding new tweets
            if tweets_found_this_scroll == 0:
                consecutive_no_new_tweets += 1
                print(f"No new tweets found in this scroll. Consecutive count: {consecutive_no_new_tweets}")
            else:
                consecutive_no_new_tweets = 0

            # Safety break if we've scrolled several times with no new tweets
            if consecutive_no_new_tweets >= no_new_tweets_threshold:
                print(f"No new tweets found after {no_new_tweets_threshold} consecutive scrolls. Stopping.")
                break

            # Provide progress updates
            print(
                f"Scroll attempt {scroll_attempts}/{max_scroll_attempts}. Found {len(tweets_data)}/{max_tweets} tweets.")

            # Occasionally refresh the page if we're not finding enough tweets
            if scroll_attempts % 30 == 0 and len(tweets_data) < max_tweets * 0.5:
                print("Refreshing the page to try to find more tweets...")
                driver.refresh()
                time.sleep(initial_wait)  # Wait for page to reload

    except Exception as e:
        print(f"An error occurred during scraping: {e}")

    finally:
        # Close the browser
        print("Closing browser...")
        driver.quit()

    # Convert to DataFrame
    df = pd.DataFrame(tweets_data)

    # Add timestamp of when scraping was performed
    now = datetime.now()
    df['scrape_datetime'] = now.strftime("%Y-%m-%d %H:%M:%S")

    # Sort tweets by datetime to ensure most recent first
    if not df.empty and 'datetime' in df.columns:
        try:
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
            df = df.sort_values('datetime', ascending=False).reset_index(drop=True)
        except Exception as e:
            print(f"Error sorting by datetime: {e}")

    print(f"Successfully scraped {len(df)} earthquake tweets.")
    return df


def parse_earthquake_tweet(tweet_text):
    """
    Improved parser for earthquake information from tweet text with better pattern matching

    Returns a dictionary with extracted earthquake details
    """
    info = {
        'magnitude': None,
        'depth': None,
        'location': None,
        'date_time': None,
        'intensity': None
    }

    # Improved regex patterns with more variations

    # Magnitude patterns
    magnitude_patterns = [
        r'Magnitude\s*[=:]\s*(\d+\.?\d*)',
        r'M[=:]\s*(\d+\.?\d*)',
        r'M\s+(\d+\.?\d*)',
        r'Magnitude\s+(\d+\.?\d*)'
    ]

    for pattern in magnitude_patterns:
        match = re.search(pattern, tweet_text, re.IGNORECASE)
        if match:
            info['magnitude'] = match.group(1)
            break

    # Depth patterns
    depth_patterns = [
        r'Depth\s*[=:]\s*(\d+\s*km)',
        r'D[=:]\s*(\d+\s*km)',
        r'Depth\s+(\d+\s*km)',
        r'depth of\s+(\d+\s*km)'
    ]

    for pattern in depth_patterns:
        match = re.search(pattern, tweet_text, re.IGNORECASE)
        if match:
            info['depth'] = match.group(1)
            break

    # Location patterns
    location_patterns = [
        r'Location\s*[=:]\s*([^\n]+)',
        r'L[=:]\s*([^\n]+)'
    ]

    for pattern in location_patterns:
        match = re.search(pattern, tweet_text, re.IGNORECASE)
        if match:
            info['location'] = match.group(1).strip()
            break

    # Date and Time patterns
    datetime_patterns = [
        r'Date\s*and\s*Time\s*[=:]\s*([^\n]+)',
        r'Date[=:]\s*([^\n]+)',
        r'Occurred on\s*([^\n]+)'
    ]

    for pattern in datetime_patterns:
        match = re.search(pattern, tweet_text, re.IGNORECASE)
        if match:
            info['date_time'] = match.group(1).strip()
            break

    # Intensity patterns (new)
    intensity_patterns = [
        r'Intensity\s*[=:]\s*([^\n]+)',
        r'Reported Intensity\s*[=:]\s*([^\n]+)'
    ]

    for pattern in intensity_patterns:
        match = re.search(pattern, tweet_text, re.IGNORECASE)
        if match:
            info['intensity'] = match.group(1).strip()
            break

    return info


def extract_info_from_text(text):
    """
    More detailed extraction of earthquake information using regex patterns

    Args:
        text (str): Tweet text

    Returns:
        dict: Dictionary with extracted information
    """
    info = {
        "Date and Time": None,
        "Magnitude": None,
        "Depth": None,
        "Location": None,
        "Intensity": None
    }

    # Break text into lines for line-by-line processing
    lines = text.split('\n')

    # Process each line
    for line in lines:
        # Date and Time patterns
        if any(keyword in line for keyword in ["Date and Time:", "Date:", "Occurred on"]):
            match = re.search(r"(?:Date and Time:|Date:|Occurred on)?\s*([\d\w\s:\.]+(?:AM|PM|UTC)?)", line,
                              re.IGNORECASE)
            if match:
                info["Date and Time"] = match.group(1).strip()

        # Magnitude patterns
        elif "Magnitude" in line:
            match = re.search(r"Magnitude\s*[=:]\s*([0-9.]+)", line, re.IGNORECASE)
            if match:
                info["Magnitude"] = match.group(1).strip()

        # Depth patterns
        elif "Depth" in line:
            match = re.search(r"Depth\s*[=:]\s*([0-9]+\s*km)", line, re.IGNORECASE)
            if match:
                info["Depth"] = match.group(1).strip()

        # Location patterns
        elif "Location" in line:
            match = re.search(r"Location\s*[=:]\s*(.*)", line, re.IGNORECASE)
            if match:
                info["Location"] = match.group(1).strip()

        # Intensity patterns (new)
        elif "Intensity" in line:
            match = re.search(r"(?:Reported )?Intensity\s*[=:]\s*(.*)", line, re.IGNORECASE)
            if match:
                info["Intensity"] = match.group(1).strip()

    # Try to parse from the full text if line-by-line approach didn't find everything
    if not info["Date and Time"]:
        match = re.search(r"Date and Time:\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
        if match:
            info["Date and Time"] = match.group(1).strip()

    if not info["Magnitude"]:
        match = re.search(r"Magnitude\s*[=:]\s*([0-9.]+)", text, re.IGNORECASE)
        if match:
            info["Magnitude"] = match.group(1).strip()

    if not info["Depth"]:
        match = re.search(r"Depth\s*[=:]\s*([0-9]+\s*km)", text, re.IGNORECASE)
        if match:
            info["Depth"] = match.group(1).strip()

    if not info["Location"]:
        match = re.search(r"Location\s*[=:]\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
        if match:
            info["Location"] = match.group(1).strip()

    if not info["Intensity"]:
        match = re.search(r"(?:Reported )?Intensity\s*[=:]\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
        if match:
            info["Intensity"] = match.group(1).strip()

    return info


def clean_earthquake_data(df):
    """
    Apply the cleaning function to the dataframe with improved error handling

    Args:
        df (DataFrame): DataFrame with tweet data

    Returns:
        DataFrame: Cleaned DataFrame with extracted information
    """
    if df.empty or 'tweet_text' not in df.columns:
        print("No valid tweet data to clean")
        return pd.DataFrame()

    # Apply the cleaning function
    extracted_data = df["tweet_text"].apply(extract_info_from_text)
    cleaned_df = pd.DataFrame(extracted_data.tolist())

    # Add original URLs and datetime from the source dataframe
    if 'tweet_url' in df.columns:
        cleaned_df['tweet_url'] = df['tweet_url'].values

    if 'datetime' in df.columns:
        cleaned_df['tweet_datetime'] = df['datetime'].values

    if 'scrape_datetime' in df.columns:
        cleaned_df['scrape_datetime'] = df['scrape_datetime'].values

    # Drop rows with all missing core earthquake data (keep rows with at least one piece of data)
    core_columns = ["Date and Time", "Magnitude", "Depth", "Location"]
    cleaned_df = cleaned_df.dropna(subset=core_columns, how='all')

    return cleaned_df


def save_to_csv(df, filename, delimiter=','):
    """
    Save the DataFrame to a CSV file with error handling

    Args:
        df (DataFrame): DataFrame to save
        filename (str): Output filename
        delimiter (str): Delimiter character (default is comma)
    """
    try:
        # Create a timestamped filename to avoid overwriting previous results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_with_timestamp = f"{filename.split('.')[0]}_{timestamp}.{filename.split('.')[1]}"

        df.to_csv(filename_with_timestamp, index=False, sep=delimiter, encoding='utf-8')
        print(f"Data saved to {filename_with_timestamp}")

    except Exception as e:
        print(f"Error saving data to CSV: {e}")


def main():
    print(f"Starting PHIVOLCS earthquake information scraper at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")

    # Configure before running
    max_tweets = 40
    scroll_pause_time = 2.5  # Slightly longer pauses between scrolls
    max_scroll_attempts = 300  # More scroll attempts to reach target
    no_new_tweets_threshold = 15  # Stop after this many scrolls with no new tweets

    # Step 1: Scrape tweets with improved parameters
    raw_df = scrape_phivolcs_twitter(
        max_tweets=max_tweets,
        scroll_pause_time=scroll_pause_time,
        max_scroll_attempts=max_scroll_attempts,
        no_new_tweets_threshold=no_new_tweets_threshold
    )

    if not raw_df.empty:
        print(f"Successfully scraped {len(raw_df)} earthquake information tweets.")

        # Save the raw data
        raw_output_file = "phivolcs_earthquake_data_raw.csv"
        save_to_csv(raw_df, raw_output_file)

        # Step 2: Clean the data
        print("Cleaning and extracting structured data...")
        cleaned_df = clean_earthquake_data(raw_df)

        # Save the cleaned data with semicolon delimiter
        cleaned_output_file = "earthquake_data_cleaned.csv"
        save_to_csv(cleaned_df, cleaned_output_file, delimiter=';')

        # Configure pandas to display all columns and content
        pd.set_option('display.max_columns', None)  # Show all columns
        pd.set_option('display.width', None)  # Don't limit width
        pd.set_option('display.max_colwidth', None)  # Don't truncate column content

        # Display sample of results
        print("\nFull view of cleaned data:")
        print(cleaned_df.head(10))  # Show just top 10 rows to avoid console overflow

        print(f"\nTotal earthquake tweets scraped: {len(raw_df)}")
        print(f"Total structured records after cleaning: {len(cleaned_df)}")

    else:
        print("No earthquake information tweets were found.")


if __name__ == "__main__":
    main()