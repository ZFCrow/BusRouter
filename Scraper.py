import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import logging
import re
from tqdm import tqdm
from DBManager import DatabaseManager 
from creds.constants import dblink 

class Scraper:
    def __init__(self, dbManager = None):
        if dbManager is None: 
            print ("No dbManager provided") 
        
        #get list of hotelName from db
        self.dbManager = dbManager
        self.hotelnames = self.get_hotel_names() 
        self.stars = [] 
    
    def get_hotel_names(self):
        # Get all documents from the 'hotels' collection
        documents = self.dbManager.get_all_documents('hotel')
        print (documents) 
        # Extract the 'name' value from each document and put it in a list if there is no 'starRating' column
        hotel_names = []
        
        for doc_id, doc_data in tqdm(documents.items(), desc="Processing hotels", unit="hotel"):
            name = doc_data.get('name')
            star_rating = doc_data.get('starRating', None)  # Check for the presence of 'starRating'
            
            # Append the name only if 'starRating' is not present
            if name and star_rating is None:
                hotel_names.append(name)
        
        print (hotel_names) 
        return hotel_names
    
    def scrape(self):
        logging.getLogger().setLevel(logging.CRITICAL)
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Uncomment to run headless
        # chrome_options.add_argument("--log-level=3")  # Suppress DevTools messages
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            for hotelname in tqdm(self.hotelnames, desc="Scraping hotels", unit="hotel"):
                print(hotelname)
                
                # Add hotel name to Google search
                driver.get("https://www.google.com/")
                
                element = driver.find_element(By.XPATH, '//textarea[@title="Search"]')
                element.send_keys(f"{hotelname} hotel" if "hotel" not in hotelname.lower() else hotelname)
                element.send_keys(Keys.RETURN)
                
                time.sleep(2)
                try:
                    element = driver.find_element(By.XPATH, '//span[@class="E5BaQ"]')
                    print(element.text)
                    star = element.text
                except:
                    try:
                        element = driver.find_element(By.XPATH, '//span[@class="YhemCb"]')
                        print(f"{element.text} through 2nd xpath")
                        star = element.text
                    except:
                        print("No rating found")
                        star = None
                
                # Append the star rating to the list
                self.stars.append((hotelname, star))
        finally:
            # Close the driver
            driver.quit()
    
    def extract_star(self):
        cleaned_stars = []
        for hotel_name, item in tqdm(self.stars, desc="Extracting stars", unit="hotel"): 
            if item is None:
                cleaned_stars.append((hotel_name, None))
            else:
                # Extract the number part of the star rating
                match = re.findall(r'[0-9]+', item)
                if match:
                    cleaned_stars.append((hotel_name, int(match[0])))
                else:
                    cleaned_stars.append((hotel_name, None))
        self.stars = cleaned_stars
    
    def update_database_with_stars(self):
        for hotel_name, star in tqdm(self.stars, desc="Updating database", unit="hotel"):
            if star is not None:
                self.dbManager.update_document_by_field('hotel', 'name', hotel_name, {'starRating': star})
            
            else:
                print(f"Star rating not found for {hotel_name}")
                # make the star rating -1 
                self.dbManager.update_document_by_field('hotel', 'name', hotel_name, {'starRating': -1})
    
    def full_run(self):
        self.scrape()
        self.extract_star()
        self.update_database_with_stars() 

if __name__ == "__main__":
    x = Scraper(dbManager=DatabaseManager("creds/creds.json", dblink))
    x.full_run() 
