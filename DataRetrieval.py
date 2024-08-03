import osmnx as ox 
import os 
import pandas as pd
from tqdm import tqdm 
from Scraper import Scraper
from DBManager import DatabaseManager 
from creds.constants import dblink 
from ERP import ERP 
from pyproj import Transformer 
from rtree import index as rindex 
import requests
import tempfile 
#load the graph then retrieve the edges and save them in a file 
class DataRetrieval:
    def __init__(self, update = False): 
        self.graph_filename = 'sgDrive.graphml'
        self.placeName = 'Singapore, Singapore'
        self.targettedNodes = {}
        self.G = None 
        self.DB = DatabaseManager("creds/creds.json", dblink)
        self.update = update
        #!=====================================================================================================
        self.loadGraph()  #! setting update to true will download the graph, false will load the graph 
        #!===================================================================================================== 
        
        #! set up nodeindex and edgeindex for spatial operations 
        self.nodeIndex = None 
        self.edgeIndex = None 
        #!===================================================================================================== 
        
        if self.update: #! if update is true, retrieve all the nodes and scrape the hotel stars for the hotels without stars 
            self.setUpNodeIndex() 
            self.retrieveAirportTerminalNodes() 
            self.retrieveHotelNodes()
            self.importERPData() 
            self.Scrape = Scraper(dbManager = self.DB) 
            self.Scrape.full_run() 
    
    def loadGraph(self):  
        # if update = true, not update = false 
        # if update = false, not update = true 
        # if update is True, i want to download the graph, so not update must be false 
        if not self.update: 
            doc = self.DB.find_document_by_field("graph", "name", "Singapore")
            if doc:
                doc = list(doc.values())
                link = doc[0]['url'] 
                
                res = requests.get(link) 
                if res.status_code == 200: 
                    with tempfile.TemporaryDirectory() as tmpdirname: 
                        temp_file = os.path.join(tmpdirname, 'sgDrive.graphml') 
                        with open(temp_file, 'wb') as f: 
                            f.write(res.content) 
                        self.G = ox.load_graphml(temp_file) 
                        os.remove(temp_file) 
                        print ("Graph loaded") 
                
                return
        
        self.downloadGraph()
        self.update = True
    
    def downloadGraph(self):    
        print ("Downloading graph") 
        self.G = ox.graph_from_place(self.placeName, network_type='drive', simplify=False)
        crs = self.G.graph['crs'] 
        print (f"Graph crs: {crs}") 
        self.saveGraph() 
    
    def retrieveFileName(self): 
        #check the log folder for the last overall text file and add a number to it
        files = os.listdir('log')
        files = [file for file in files if 'overall' in file] 
        if files: 
            files.sort(key=lambda x: int(x.split('.')[0].split('overall')[1]))
            #get the last file 
            lastFile = files[-1] 
            print (f"last file: {lastFile}") 
            #get the number 
            number = int(lastFile.split('.')[0].split('overall')[1]) + 1
            if number >10: 
                #delete all overall files 
                for file in files: 
                    os.remove(f'log/{file}') 
                number = 1  
            return f'log/overall{number}.txt' 
        else: 
            return 'log/overall1.txt' 
    
    def retrieveHotelNodes(self):         
        self.retrieveNodes(tags = {'tourism': 'hotel'})    
    
    def retrieveAirportTerminalNodes(self):
        self.retrieveNodes(tags = {'aeroway': 'terminal'}) 
    
    def setUpNodeIndex(self): 
        self.projectGraphtoUTM() 
        nodes = [] 
        for node, data in tqdm(self.G.nodes(data=True), desc="Setting up node index"): 
            #! this is actually NOT lon lat but x y in UTM 
            lon = data['x'] 
            lat = data['y']
            nodes.append((lon, lat, node))
        self.nodeIndex = rindex.Index()  
        for pos, (lon, lat, node) in tqdm(enumerate(nodes), desc="Inserting nodes into index"): 
            self.nodeIndex.insert(pos, (lon, lat, lon, lat), obj=node) 
    
    def setUpEdgeIndex(self):
        self.projectGraphtoUTM() 
        
        edges = []
        for u, v, key, data  in tqdm(self.G.edges(keys=True, data=True), desc="Setting up edge index"): 
            mid_lat = (self.G.nodes[u]['y'] + self.G.nodes[v]['y']) / 2
            mid_lon = (self.G.nodes[u]['x'] + self.G.nodes[v]['x']) / 2
            edges.append((mid_lon, mid_lat, u, v, key))
        
        self.edgeIndex = rindex.Index()
        for pos, (mid_lon, mid_lat, u, v, key) in tqdm(enumerate(edges), desc="Inserting edges into index"): 
            self.edgeIndex.insert(pos, (mid_lon, mid_lat, mid_lon, mid_lat), obj=(u, v, key))
    
    def projectGraphtoUTM(self): 
        if self.G.graph['crs'] == 'epsg:4326': 
            self.G = ox.project_graph(self.G) 
            print ("Graph projected to UTM for accurate spatial operations") 
        else: 
            print ("Graph already projected to UTM") 
    
    def projectGraphtoEPSG4326(self): 
        if self.G.graph['crs'] != 'epsg:4326': 
            self.G = ox.project_graph(self.G, to_crs='EPSG:4326') 
            print ("Graph re-projected to geographic coordinates (EPSG:4326)") 
        else: 
            print ("Graph already projected to geographic coordinates (EPSG:4326)") 
    
    def updateNearestNode(self,node, collectionName, attemptCounter = 1):
        # get lat lon of the node if it exist in self.G.nodes
        # if the self.indexNode is not empty, get the nearest node to the lat lon of the placeName 
        #else we need to set up the indexNode 
        #convert graph to UTM 
        self.projectGraphtoUTM() 
        numberofnearest = attemptCounter * 10   
        if node in self.G.nodes: 
            nodeData = self.G.nodes[node] 
            #after projection, the x and y are the UTM coordinates
            y = nodeData['y'] 
            x = nodeData['x'] 
            
            if not self.nodeIndex: 
                self.setUpNodeIndex() 
            nearestNode = list(self.nodeIndex.nearest((x, y, x, y), numberofnearest, objects=True))[numberofnearest-1].object 
            print (f"Nearest node to {node} is {nearestNode}") 
            #update to database 
            self.DB.update_document_by_field(collectionName,'node', node, {'node': nearestNode}) 


    def retrieveNodes(self, tags):
        print ("Retrieving nodes for tags: ", tags)  
        # If tag only has one key, use the value as header 
        if len(tags) == 1: 
            header = list(tags.values())[0] 
        
        places = ox.geometries_from_place(self.placeName, tags=tags) 
        # Remove all places with no name 
        places = places.dropna(subset=['name'])
        
        # Create a transformer to convert from EPSG:4326 to the projected CRS
        projected_crs = self.G.graph['crs']
        transformer = Transformer.from_crs("EPSG:4326", projected_crs, always_xy=True)
        
        for index, place in tqdm(places.iterrows(), total=places.shape[0], desc="Processing nodes"):
            # Get the centroid of the place
            centroid = place['geometry'].centroid.coords[0]
            # Transform the centroid coordinates to the projected CRS
            lon_proj, lat_proj = transformer.transform(centroid[0], centroid[1])
            # Find the nearest node using the spatial index
            nearest_node = list(self.nodeIndex.nearest((lon_proj, lat_proj, lon_proj, lat_proj), 10, objects=True))
            node = nearest_node[0].object
            nearestNode2 = nearest_node[9].object   
            
            # Change place name to None if it is NaN
            place_name = place['name'] if pd.notna(place['name']) else None
            self.targettedNodes[place_name] = node
        
        # Look for the collection in the database, and then compare the data, to see which are new and which are removed 
        removed, added = self.fireBaseComparision(header)  
        # Remove those that are removed from the database 
        if removed: 
            for name, node in removed.items(): 
                self.DB.delete_document_by_field(header, 'name', name)
        
        # Add those that are added to the database
        if added:
            for name, node in added.items():
                document_data = {
                    'name': name,
                    'node': node
                }
                self.DB.add_document(header, document_data)
        self.targettedNodes = {} 
    
    def fireBaseComparision(self,collectionName):
        #same as dataComparison but for firebase 
        # compare the name and node, if the name is the same, check if the node is the same
        # the collection will have 3 fields, name, node, star rating but my data only has name and node so compare just those 2 fields
        # {'hotelname': 'hotelnode'} for the old data
        #get all the documents in the collection 
        existingData = self.DB.get_all_documents(collectionName) 
        
        if not existingData: 
            return None, self.targettedNodes
        
        # Ensure existingData is in the correct format
        if isinstance(existingData, dict):
            print (existingData) 
        # Convert existing data to a dictionary with 'name' as the key and 'node' as the value
        existingDict = {}
        for docID, docData in existingData.items(): 
            existingDict[docData['name']] = docData['node'] 
            
            # Convert old data to sets of tuples for comparison
        newData = set(self.targettedNodes.items())
        existingDataSet = set(existingDict.items())
        
        # Find differences
        added = newData - existingDataSet
        removed = existingDataSet - newData
        
        # Convert sets back to dictionaries for easier interpretation
        removedDict = {name: node for name, node in removed}
        addedDict = {name: node for name, node in added}
        
        print(f"Data removed from the original DB: {removedDict}")
        print(f"Data added to the new DB: {addedDict}")
        
        return removedDict, addedDict
    
    def saveGraph(self):
        ox.save_graphml(self.G, self.graph_filename) 
        self.DB.delete_document_by_field("graph", "name", "Singapore")
        imageUrl = self.DB.addImageToStorage(self.graph_filename, f"graph/{self.graph_filename}") 
        self.DB.add_document("graph", {"name": "Singapore", "url": imageUrl}) 
        print ("Graph uploaded to storage") 
    
    def importERPData(self):
        erp = ERP(data=self) 
        erp.userUpdateGraphFlow() 
        self.saveGraph() 
        print ("ERP data stored") 

if __name__ == '__main__': 
    #! you run with either update or no updates
    #! if with updates, it will download the graph and update all the nodes 
    #! without updates, it will just load the graph
    x = DataRetrieval(update = True)