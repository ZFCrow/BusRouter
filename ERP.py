# basically just have functions that allows user to upload geojson files and then read them to get gantry numbers and their midpoints
import re 
import geopandas as gpd 
import osmnx as ox 
from tqdm import tqdm 
from pyproj import Transformer
from rtree import index
import random

class ERP:
    def __init__(self, file_path='Data/default.geojson', data = None  ):
        if data is None: 
            from DataRetrieval import DataRetrieval 
            self.data = DataRetrieval(update = False) 
        else:
            self.data = data 
        
        self.erpData = []
        self.geojson_file = file_path
        self.gdf = None 
        self.erpWithZones = None
    
    # Function to extract GNTRY_NUM from the Description field
    def extract_gantry_num(self,description):
        match = re.search(r'<th>GNTRY_NUM<\/th> <td>(.*?)<\/td>', description)
        if match:
            #remove the space in the gantry number
            return match.group(1).replace(" ", "") 
        
        return 'N/A'
    
    # Function to get the midpoint of the coordinates
    def get_midpoint(self,coords):
        latitudes = [coord[1] for coord in coords]
        longitudes = [coord[0] for coord in coords]
        return sum(latitudes) / len(latitudes), sum(longitudes) / len(longitudes)
    
    def processData(self): 
        for idx, row in self.gdf.iterrows():
            coordinates = row.geometry.coords[:]
            lat, lon = self.get_midpoint(coordinates)
            description_html = row['Description']
            gantry_num = self.extract_gantry_num(description_html)
            self.erpData.append((gantry_num, lat, lon)) 
    
    def computeGantryCharges(self):
        # the charges ranges from 0.5 to 2.5 in multiples of 0.5
        # randomly assign charges to the gantries
        charge = random.choice([0.5, 1.0, 1.5, 2.0, 2.5])
        return charge
    
    def storeERPData(self):
        if self.erpData:
            if self.data.edgeIndex is None: 
                self.data.setUpEdgeIndex() 
            idx = self.data.edgeIndex 
            
            # Create a transformer to convert from EPSG:4326 to the projected CRS
            projected_crs = self.data.G.graph['crs']
            transformer = Transformer.from_crs("EPSG:4326", projected_crs, always_xy=True)
            
            # Initialize all edges with default values
            for u, v, key, data in self.data.G.edges(keys=True, data=True):
                data['ERPcharge'] = 0.00
            
            for gantry_num, lat, lon in tqdm(self.erpData, desc="Storing ERP data in the graph"):
                charge = self.computeGantryCharges() 
                # Transform the input coordinates to the projected CRS
                lon_proj, lat_proj = transformer.transform(lon, lat)
                
                # Find the nearest edge using the spatial index
                nearest = list(idx.nearest((lon_proj, lat_proj, lon_proj, lat_proj), 1, objects=True))
                u, v, key = nearest[0].object
                
                # Put the data onto the edge
                self.data.G[u][v][key]['gantry_num'] = gantry_num
                self.data.G[u][v][key]['ERPcharge'] = charge 
    
    def uploadERPDatatoDB (self):
        if self.erpData:
            self.data.DB.deleteCollection('ERP')
            for gantry_num, lat, lon in tqdm(self.erpData, desc="Uploading ERP data to the database"):
                self.data.DB.add_document('ERP', {'gantry_num': gantry_num, 'lat': lat, 'lon': lon}) 
    
    def retreiveERPDatafromDB(self): 
        self.erpData = [] 
        data = self.data.DB.get_all_documents('ERP') 
        if data:
            for item in data.values():
                gantry_num = item['gantry_num']
                lat = item['lat']
                lon = item['lon']
                self.erpData.append((gantry_num, lat, lon))
        
        print (self.erpData) 
    
    def userUploadERPFlow(self):
        self.gdf = gpd.read_file(self.geojson_file)
        self.processData() 
        self.uploadERPDatatoDB() 
    
    def userUpdateGraphFlow(self):
        #retrieve data from db 
        #store erpdata on the map
        self.retreiveERPDatafromDB() 
        if self.erpData: #this should be blank if theres nothing in the db
            self.storeERPData()
        else:
            self.userUploadERPFlow() 
            print (self.erpData)
            self.storeERPData() 

if __name__ == "__main__":
    erp = ERP() 
    erp.userUpdateGraphFlow() 
