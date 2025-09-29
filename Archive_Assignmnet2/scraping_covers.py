from playwright.sync_api import sync_playwright
import requests
import os
import time
from PIL import Image # NEW: Import Pillow for image manipulation

# --- Setup ---
# The target YouTube playlist URL
PLAYLIST_URL = "https://www.youtube.com/playlist?list=PL3-sRm8xAzY9gpXTMGVHJWy_FMD67NBed"
# CSS Selector for thumbnail images within the playlist video list
# This targets the main <img> tag inside the thumbnail component of each video in the list.
THUMBNAIL_SELECTOR = "ytd-playlist-video-renderer ytd-thumbnail img" 
# Output directory for downloaded images
OUTPUT_DIR = "youtube_thumbnails"

# Selector for the full playlist video row element, used for counting loaded videos
VIDEO_ROW_SELECTOR = "ytd-playlist-video-renderer"


def crop_to_16_9(file_path):
    """
    Crops the image at the given file_path to a 16:9 aspect ratio.
    It calculates the required height based on the width and removes excess 
    height equally from the top and bottom.
    """
    try:
        img = Image.open(file_path)
        width, height = img.size
        
        # Calculate the required height for a 16:9 aspect ratio based on the current width
        target_height = int(width * 9 / 16)
        
        if height > target_height:
            # Calculate the total height to remove and the margin for the crop box
            height_to_remove = height - target_height
            top_margin = height_to_remove // 2
            
            # The bottom coordinate is the full height minus the height removed from the bottom.
            # We use height_to_remove - top_margin to handle any remainder if height_to_remove is odd.
            bottom_margin = height - (height_to_remove - top_margin) 
            
            # The crop box is (left, top, right, bottom)
            crop_box = (0, top_margin, width, bottom_margin)
            
            cropped_img = img.crop(crop_box)
            cropped_img.save(file_path)
            print(f"Cropped image to {width}x{target_height} (16:9).")
        else:
            print(f"Skipping crop for 16:9. Image is already taller than or equal to 16:9.")
            
    except Exception as e:
        print(f"Error processing image {file_path}: {e}")


def download_file(url, local_filename=None):
    """Downloads a file from a URL to the local file system."""
    if not url:
        print("Error: Empty URL provided for download.")
        return None
    
    # Generate a safe filename from the URL, or use a provided name
    if local_filename is None:
        # Use the last part of the URL (e.g., hqdefault.jpg)
        local_filename = url.split("/")[-1]
        
    # Prepend the output directory to the filename
    local_path = os.path.join(OUTPUT_DIR, local_filename)

    try:
        # Use requests to download the file
        with requests.get(url, stream=True, timeout=10) as r:
            r.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Downloaded: {local_path}")
        return local_path
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {url}: {e}")
        return None


def scroll_to_end(page):
    """
    Scrolls the page repeatedly until no new video elements are loaded, 
    ensuring all lazy-loaded content is visible.
    """
    print("Scrolling to load all playlist videos...")
    last_video_count = 0
    consecutive_same_count = 0
    max_attempts = 10  # Stop after 10 attempts where no new videos are loaded

    while consecutive_same_count < max_attempts:
        # Scroll to the bottom of the page
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        
        # Wait for dynamic content to potentially load
        time.sleep(2) 
        
        # Count the number of video elements currently loaded
        current_videos = page.locator(VIDEO_ROW_SELECTOR).all()
        current_video_count = len(current_videos)

        if current_video_count > last_video_count:
            print(f"Loaded {current_video_count} videos so far...")
            last_video_count = current_video_count
            consecutive_same_count = 0  # Reset counter since new content was found
        else:
            consecutive_same_count += 1
            print(f"No new videos loaded in this attempt. Attempts remaining: {max_attempts - consecutive_same_count}")

    print(f"Finished scrolling. Total videos found: {last_video_count}")
        

def scrape_thumbnails():
    """Main function to scrape and download YouTube playlist thumbnails."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with sync_playwright() as p:
        # Launch Chromium browser (headless=False will show the browser window)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        print(f"Navigating to {PLAYLIST_URL}")
        page.goto(PLAYLIST_URL, wait_until="networkidle")

        # Scroll to ensure all videos are loaded
        scroll_to_end(page)
        
        # Find all thumbnail images using the selector
        images = page.locator(THUMBNAIL_SELECTOR).all()
        
        if not images:
            print("No images found with the specified selector. Check the playlist is public.")
            browser.close()
            return

        print(f"Found {len(images)} potential thumbnail elements. Starting targeted download...")
        
        downloaded_count = 0
        
        # Extract and download the source attribute (src) for each image
        for i, img_element in enumerate(images):
            
            # --- Targeted Waiting Loop for Lazy-Loaded Image SRC ---
            src = None
            max_wait_time = 5 # Total wait time for the attribute to populate
            wait_step = 1     # Check every 1 second
            
            # Poll for the 'src' attribute to be populated
            for attempt in range(int(max_wait_time / wait_step)):
                # Get the 'src' attribute. Playwright will fetch the current value.
                src = img_element.get_attribute("src")
                
                # Check if the source is populated and not a data URI placeholder
                if src and not src.startswith("data:"):
                    break  # URL found! Exit the waiting loop
                
                # If not found, wait and try again
                time.sleep(wait_step)
            # --- End Targeted Waiting Loop ---

            # Final check after the waiting attempts
            if not src or src.startswith("data:"):
                # Print a message for debugging why an image was skipped
                print(f"Skipping video {i+1}: Image source is still placeholder or empty after {max_wait_time}s wait.")
                continue
                
            # Clean the URL by removing query parameters (e.g., ?sqp=...)
            # This ensures we get the clean image file (like hqdefault.jpg)
            cleaned_src = src.split('?')[0]

            # YouTube thumbnail URLs are consistent, use the video index for a clean filename
            filename = f"{i+1}_thumbnail.jpg"
            
            # Download the file
            local_path = download_file(cleaned_src, filename)
            
            if local_path:
                # NEW: Crop the downloaded file to 16:9
                crop_to_16_9(local_path)
                downloaded_count += 1
            
        print(f"Scraping complete. Downloaded {downloaded_count} unique thumbnails to the '{OUTPUT_DIR}' directory.")
        browser.close()

if __name__ == "__main__":
    scrape_thumbnails()
