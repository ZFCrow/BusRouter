# Introduction
BusRouter, a smart routing system designed for an intended reduction in costs to a tourist bus operator in Singapore. 
The application also offers a way to assist bus operators in planning their routes by generat-ing the best route based on their requirements. 
This entails applying Dijkstra’s algorithm on each node that results in the formation of a distance dictionary which in turn is processed by Ant Colony Optimization or Held-Karp algorithm, 
depending on the number of destinations. 
The system optimizes routes based on three key criteria: The three criteria include length/distance, time and the minimum ERP that is required with an optional consideration of current traffic.
# System Diagram
![DSA System Diagram](https://github.com/user-attachments/assets/b5b87687-8fc6-40f2-9c40-c0a4972e4bf0)

![Firebase Schema drawio](https://github.com/user-attachments/assets/34f421d8-31f6-4dd9-ae89-7a57469fe8a7)

# Configuration

To ensure that the BusRouter application runs smoothly, you need to create a constants file to store important configuration variables. This file will contain sensitive information such as database links and storage buckets, which are essential for the application to function.

## Required Variables 

dblink: The link to your Firebase Realtime Database.  
firebaseStorageBucket: The name of your Firebase Storage bucket.  
User: The user identifier that is used in your application.  
tomtom: The API key for accessing TomTom services.

## Steps to Create the Cosntants file
Create a directory named creds at the root of your project if it doesn't already exist.
Inside the creds directory, create a file named constants.py.
Define the required variables in constants.py as shown below:

```
# creds/constants.py

dblink = "your_firebase_database_link e.g. somethingsomething.firebasedatabase.app"
firebaseStorageBucket = "your_firebase_storage_bucket_name e.g something something.appspot.com"
User = 1
tomtom = "your_tomtom_api_key"

```
