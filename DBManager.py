import firebase_admin
from firebase_admin import credentials, db, firestore, storage 
import urllib.parse
from creds.constants import dblink, firebaseStorageBucket

class DatabaseManager:
    def __init__(self, key_path, db_url):
        # Initialize Firebase if not already initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': db_url,
                'storageBucket': firebaseStorageBucket
            })
        self.db = db
        self.fireStoreDB = firestore.client() 
        self.bucket  = storage.bucket() 
    
    def add_document(self, collection_name, data):
        # Add a document to a collection (push generates a unique key)
        ref = self.db.reference(collection_name)
        new_ref = ref.push(data)
        print(f"Document successfully added with key: {new_ref.key}")
        return new_ref.key
    
    def get_document(self, collection_name, document_id):
        # Retrieve a document from a collection
        ref = self.db.reference(f"{collection_name}/{document_id}")
        data = ref.get()
        if data:
            print(f"Document data: {data}")
            return data
        else:
            print("No such document!")
            return None
    
    def update_document(self, collection_name, document_id, data):
        # Update a document in a collection
        ref = self.db.reference(f"{collection_name}/{document_id}")
        ref.update(data)
        print(f"Document {document_id} successfully updated in {collection_name} collection.")
    
    def update_document_by_field(self, collection_name, field_name, field_value, data):
        ref = self.db.reference(collection_name)
        encoded_field_value = field_value # Initialize encoded_field_value with field_value 
        if isinstance(field_value, str): 
            encoded_field_value = urllib.parse.quote(field_value, safe='') # Encode special characters in field_value for query
        query = ref.order_by_child(field_name).equal_to(encoded_field_value).get()
        
        if not query:
            print(f"No documents found in {collection_name} collection with {field_name} = {field_value}.")
            #add  the document to the collection 
            ref.push(data) 
            print (f"Document {data} successfully added to {collection_name} collection.") 
            return
        
        # Update the matched document(s)
        for key in query.keys():
            ref.child(key).update(data)
            print(f"Document {key} successfully updated in {collection_name} collection.")
    
    def delete_document(self, collection_name, document_id):
        # Delete a document from a collection
        ref = self.db.reference(f"{collection_name}/{document_id}")
        ref.delete()
        print(f"Document {document_id} successfully deleted from {collection_name} collection.")
    
    def delete_document_by_field(self, collection_name, field_name, field_value):
        ref = self.db.reference(collection_name)
        encoded_field_value = urllib.parse.quote(field_value, safe='') # Encode special characters in field_value for query
        query = ref.order_by_child(field_name).equal_to(encoded_field_value).get()
        
        if not query:
            print(f"Delete Operation: No documents found in {collection_name} collection with {field_name} = {field_value}.")
            return
        
        # Delete the matched document(s)
        for key in query.keys():
            ref.child(key).delete()
            print(f"Document {key} successfully deleted from {collection_name} collection.")
    
    def get_all_documents(self, collection_name):
        # Retrieve all documents in a collection
        ref = self.db.reference(collection_name)
        data = ref.get()
        if data:
            return data
        else:
            print(f"No documents found in {collection_name} collection!")
            return None
    
    def find_document_by_field(self, collection_name, field_name, field_value):
        # Retrieve documents where field_name equals field_value
        ref = self.db.reference(collection_name)
        data = ref.order_by_child(field_name).equal_to(field_value).get()
        if data:
            for key, value in data.items():
                print(f'{key} => {value}')
            return data
        else:
            print(f"No documents found with {field_name} = {field_value} in {collection_name} collection!")
            return None
    
    def deleteCollection (self, collection_name):
        ref = self.db.reference(collection_name)
        ref.delete()
        print (f"Collection {collection_name} successfully deleted") 
#=======================================================================================================
# firestore methods 
    def add_document_firestore(self, collection_name, data):
        # Add a document to a collection (push generates a unique key)
        ref = self.fireStoreDB.collection(collection_name)
        new_ref = ref.add(data)
        print(f"Document successfully added with key: {new_ref.key}")
        return new_ref.key 
    
    def addImageToStorage(self, imagePath, storagePath): 
        blob = self.bucket.blob(storagePath)
        blob.upload_from_filename(imagePath)
        print (f"Image {imagePath} uploaded to storage") 
        blob.make_public()
        print (f"Image {imagePath} made public") 
        return blob.public_url 

if __name__ == "__main__":
    db_manager = DatabaseManager("creds/creds.json", dblink)
    
    #load the graph after retrieving from the database 
    # doc = db_manager.find_document_by_field("map", "name", "Singapore") 
    # print (doc)
    # print (doc.values())
    
    allHotels = db_manager.get_all_documents("hotel")
    print (len(allHotels))
