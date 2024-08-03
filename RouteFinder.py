import osmnx as ox
import folium 
from DataRetrieval import DataRetrieval 
import heapq
import itertools 
import random 
from folium.plugins import FeatureGroupSubGroup
import time
import requests 
from creds.constants import tomtom, User
from AntColony import AntColony 
import numpy as np 

class RouteFinder: 
    def __init__(self, update = False, traffic = False): 
        
        self.graph_filename = 'sgDrive.graphml'
        self.placeName = 'Singapore, Singapore '
        
        self.updateDB = update
        
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.data = DataRetrieval(update = self.updateDB) #! setting update to true will update the database with the nodes, set it to false if you do not want to update the database 
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        
        self.logFileName = self.data.retrieveFileName() 
        
        # dictionary containing the name and node
        self.source = {} 
        self.destination = {}
        
        self.optimalPath = None 
        self.optimalCost = None
        
        self.subOptimalCost = {}
        
        self.costs = {
            'length': {'optimal': None, 'alternate': None, 'destinations': {}, 'route': "", 'instructions': ""},
            'time': {'optimal': None, 'alternate': None, 'destinations': {}, 'route': "", 'instructions': ""},
            'erp': {'optimal': None, 'alternate': None, 'destinations': {}, 'route': "", 'instructions': ""}
        }
        
        self.destinations_map = {
            "length": self.costs['length']['destinations'],
            "time": self.costs['time']['destinations'],
            "erp": self.costs['erp']['destinations']
        }
        
        #colors available for the markers in folium 
        self.colors = ['purple','green','blue','red','cadetblue','orange','black','darkred','darkblue','gray','darkpurple','lightred','lightblue','beige','darkgreen','pink','lightgreen','lightgray','white']
        
        #? list of weight that the code will do 
        self.weightType = ['length', 'time', 'erp']
        
        #? the current weight type that the code is using 
        self.currentWeight = None 
        
        self.db = self.data.DB
        self.sourceCollectionName = 'terminal' 
        self.destinationCollectionName = 'hotel' 
        
        self.progress = 0   
        
        self.results = {}
        
        self.timeTrack = {} 
        
        self.attemptCounter = 1
        
        self.checkTraffic = traffic 
        self.cloggedNodes = []
        self.freeNodes = []
    
    def update_progress(self, increment, type):
        self.progress += increment
        
        if type == "restart":
            self.progress = 0
        
        elif type == "progress":
            self.progress = min(self.progress, 90)  # To keep maximum progress at 90% duing calculation
        
        elif type == "completion":
            self.progress = min(self.progress, 100)  # To keep maximum progress at 100% after calculation
        
        print(f"Progress: {self.progress}%")
    
    def get_progress(self):
        return int(self.progress)
    
    def getAttemptCounter(self):
        return self.attemptCounter
    
    def setAttemptCounter(self, value):
        self.attemptCounter = value
    
    def getUpdateDBStatus(self):
        return self.updateDB
    
    def getCheckTrafficStatus(self):
        return self.checkTraffic
    
    def ACO(self, dists):
        nodes = list(dists.keys()) 
        
        dist_matrix = np.zeros((len(dists), len(dists)))
        for i, src in enumerate(nodes):
            for j, dst in enumerate(nodes):
                dist_matrix[i][j] = dists[src][dst] 
        
        ant_colony = AntColony(dist_matrix, n_ants=10, n_best=5, n_iterations=100, decay=0.95, alpha=1, beta=2)
        shortest_path, cost = ant_colony.run()
        
        #since its an tuple representing the edge, i will take the first element of the tuple 
        path = [edge[0] for edge in shortest_path]
        # linking the path to the actual nodes 
        
        actualPath = [nodes[indices] for indices in path]
        self.optimalPath = actualPath
        self.optimalCost = cost
        self.dataLog({'optimalPath': self.optimalPath, 'optimalCost': self.optimalCost})
    
    def heldkarp(self, dists): 
        n = len(dists) 
        C = {} 
        
        # lengths passed in heldkarp: {6970584189: {6970584189: 0, 6562418315: 0.2671494674603173, 8792655504: 0.33008826130952357, 5114346207: 0.6048279122619047}, 6562418315: {6970584189: 0.27785554075396823, 6562418315: 0, 8792655504: 0.09879820999999996, 5114346207: 0.40502368583333337}, 8792655504: {6970584189: 0.32548790742063516, 6562418315: 0.09613096666666665, 8792655504: 0, 5114346207: 0.35586027746031734}, 5114346207: {6970584189: 0.6146856459523811, 6562418315: 0.39838120190476245, 8792655504: 0.339851306825397, 5114346207: 0}}
        # i need to map these nodes to integers 1 to n 
        name_to_int = {name: i+1 for i, name in enumerate(dists)} 
        int_to_name = {i: name for name, i in name_to_int.items()} 
        
        for k in range(1, n+1): 
            C[(1 << (k-1), k)] = (dists[int_to_name[1]][int_to_name[k]], 1)
        
        for subset_size in range(2, n+1): 
            for subset in itertools.combinations(range(1, n+1), subset_size): 
                bits = 0 
                for bit in subset: 
                    bits |= 1 << (bit - 1) 
                
                for k in subset: 
                    prev = bits & ~(1 << (k-1)) 
                    res = [] 
                    for m in subset: 
                        if m == 1 or m == k: 
                            continue 
                        res.append((C[(prev, m)][0] + dists[int_to_name[m]][int_to_name[k]], m))
                    if res: 
                        C[(bits, k)] = min(res) 
                    else: 
                        C[(bits, k)] = (float('inf'), -1) 
        # look into the c library where all nodes are marked as 1 and the destination is 1 
        opt, parent = C[(2**n - 1, 1)]
        bits = (2**n - 1) - 1
        
        # backtrack to find full path  
        path = []
        for i in range(n-1):
            path.append(parent)
            new_bits = bits & ~(1 << (parent - 1)) # removed the current predecessor node from the bits 
            _, parent = C[(bits, parent)] # find the new predecessor node from the current predecessor node 
            bits = new_bits #new bit should include the new predecessor node, but exclude the current predecessor node 
        path.append(1) 
        path = [int_to_name[node] for node in path] 
        #map back the node to node numbersand print the cost and path 
        self.optimalPath = list(reversed(path))
        self.optimalCost = opt 
        self.dataLog({'optimalPath': self.optimalPath, 'optimalCost': self.optimalCost})
        #return list(reversed(path)) 
    
    # a helper function to calculate totalCosts first so that i can use it in the custom dijkstra 
    def totalCosts(self):
        #for every edge, i will add a total cost attribute to it 
        for u,v,attr in self.data.G.edges(data=True):
            if self.currentWeight == 'length':
                attr['totalCost'] = attr['length']
            elif self.currentWeight == 'time': 
                defaultSpeed = 50 
                if 'maxspeed' in attr:
                    attr['totalCost'] = (attr['length'] / 1000) / float(attr['maxspeed']) 
                else:
                    attr['totalCost'] = (attr['length'] / 1000) / defaultSpeed
    
    def populateCosts(self):
        # populate the time 
        defaultSpeed = 50 
        for u,v,attr in self.data.G.edges(data=True): 
            #convert length to km 
            attr['length'] = attr['length'] / 1000
            
            if 'maxspeed' in attr:
                attr['time'] = (attr['length'] ) / float(attr['maxspeed']) 
            else: 
                attr['time'] = (attr['length'] ) / defaultSpeed 
            
            #have a ERP focused weight 
            attr['erp'] = 0.3 * attr['time'] + 0.3 * attr['length'] + 0.4 * float(attr['ERPcharge'])
            #turn 'ERPcharge' into a float 
            attr['ERPcharge'] = float(attr['ERPcharge']) 
    
    def calculateAlternateCosts(self,pathDetails): 
        # using optimalpath, calculate the route cost for each weight
        # if its erp, calculate through erpCharge, erp charges will be calculated even when erp is the current weight as the one 
        # stored in optimal cost is a mix of all the weights, not just erp 
        # so i will store full erp charge in the subOptimalCost dictionary
        for weight in self.weightType: 
            totalCost = 0 
            
            factor = 'ERPcharge' if weight == 'erp' else weight # this is because erp is just a formula, not the actual charge , so it doesnt prove anything 
            for i in range(len(self.optimalPath)): 
                source = self.optimalPath[i]
                # if source is the last node, destination will be the first node
                if i == len(self.optimalPath)-1: 
                    destination = self.optimalPath[0]
                else:
                    destination = self.optimalPath[i+1]
                #print (f"Source: {source} | Destination: {destination}")
                
                route = pathDetails[source][destination]
                
                for i in range(len(route)-1): 
                    u = route[i]
                    v = route[i+1]
                    try:
                        totalCost += self.data.G[u][v][0][factor]
                    except KeyError: 
                        #this is mainly for erpcharge as not all edges has erpcharge 
                        totalCost += 0 
            #print (f"Optimal cost for {self.currentWeight}: {self.optimalCost}") 
            #print (f"Total cost for {weight}: {totalCost}")
            self.subOptimalCost[weight] = totalCost
            #log the cost for this weighttype 
            self.dataLog({f'{weight} Cost': totalCost}) 
    
    def dijkstra(self, start_node, nodes):
        print (f"Dijkstra start node: {start_node}")
        G = self.data.G
        # Initialize distances and previous nodes
        shortest_path = {node: float('infinity') for node in G.nodes}
        previous_nodes = {node: None for node in G.nodes}
        shortest_path[start_node] = 0
        
        # Priority queue to hold nodes to explore
        priority_queue = []
        heapq.heappush(priority_queue, (0, start_node))
        
        # set of nodes to visit 
        nodesToVisit = set(nodes) 
        visited = set() 
        
        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)
            
            # Nodes can get added to the priority queue multiple times. We only
            # process a vertex the first time we remove it from the priority queue.
            if current_distance > shortest_path[current_node]:
                continue
            
            #stopper condition 
            # if all the nodes in the nodesToVisit set has been visited, then break 
            if current_node in nodesToVisit:
                visited.add(current_node) 
                if visited == nodesToVisit: 
                    break 
            
            # Explore each adjacent node to the current node
            for neighbor, attrs in G[current_node].items():
                for edgeKey, attr in attrs.items():
                    weight = attr.get('trafficWeight', attr[self.currentWeight])
                    total_distance = current_distance + weight
                    
                    # Only consider this new path if it's better
                    if total_distance < shortest_path[neighbor]:
                        shortest_path[neighbor] = total_distance
                        previous_nodes[neighbor] = current_node
                        heapq.heappush(priority_queue, (total_distance, neighbor))
            
            #print(f"Visited current node: {current_node} | Visited: {visited} ")
        
        # using the previous_nodes dictionary, we can reconstruct the path from the start node to any other node 
        paths = {}
        for node in nodesToVisit:
            path = []
            step = node
            while step is not None:
                path.append(step)
                step = previous_nodes[step]
            paths[node] = path[::-1] 
        
        # filter the costs and paths to only include the nodes in the nodesToVisit set 
        shortest_path = {node: shortest_path[node] for node in nodesToVisit} 
        print (f"Shortest path from source {start_node}: {shortest_path}")
        return shortest_path, paths 
    
    def checkPathCostsValidty(self, node, shortestPathCosts):
        # we check 2 things here whether shortestPathCosts is not infinity and whether the pathDetails route has traffic congestions 
        for key, value in shortestPathCosts.items():
            if value == float('inf'): 
                print (f"Node {key} is not reachable from node {node}, updating database")
                #check if key is in self.source or self.destination
                if key in self.source.values():
                    self.data.updateNearestNode(key, self.sourceCollectionName)
                else: 
                    self.data.updateNearestNode(key, self.destinationCollectionName) 
            
            #RERUN FLOW1/FLOW2 
                return False
            
        return True
    
    def checkPathDetailsTraffic(self, node, pathDetails): 
        congestedNodes = [] 
        print (f"Checking path details for node {node}") 
        print (f"pathDetails")
        print ("---------------------------------------------")
        print (pathDetails) 
        print ("---------------------------------------------") 
        for key,value in pathDetails.items(): 
            # each key is the destination node, value is a list of nodes covering from source to destination
            if key == node: 
                continue 
            congested = self.checkTrafficCongestion(value) 
            if congested: # it means the path from source to destination is congested , append that destination node to the congestedNodes list
                congestedNodes.append(key)
                print (f"Congestion found for source {node} to destination {key}") 
            else: 
                print (f"No congestion found for source {node} to destination {key}")
        return congestedNodes 
    
    def checkTrafficCongestion(self, route): 
        congested = False
        print (F"NUMBER of Nodes in this route: {len(route)}")
        sampledRoute = route[::len(route)//10] + [route[-1]] # sample 10% of the route + the last node 
        print (f"Number of nodes i am asking traffic for: {len(sampledRoute)}")
        # through tomtom api  
        # get the coordinates of the node 
        for node in sampledRoute:
            if node in self.cloggedNodes: 
                print (f"Node {node} is already checked to be congested, this is however the only way to the destination,skipping") 
                
                #this means the node was checked before and the fact that its still here
                # shows that the theres no other way to the destination 
                # so you continue 
                continue 
            elif node in self.freeNodes: 
                print (f"Node {node} is already checked to be free, skipping") 
                continue 
            
            lat = self.data.G.nodes[node]['lat'] 
            lon = self.data.G.nodes[node]['lon'] 
            point = f"{lat},{lon}" 
            url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={tomtom}&point={point}"
            response = requests.get(url) 
            if response.status_code == 200: 
                trafficData = response.json() 
                
                # check if traffic is congested 
                # if it is, update the edge in the database 
                # if not, continue 
                freeflow = trafficData['flowSegmentData']['freeFlowSpeed'] 
                currentSpeed = trafficData['flowSegmentData']['currentSpeed'] 
                print (f"Freeflow speed: {freeflow} | Current speed: {currentSpeed}") 
                # if current speed is less than 50% of freeflow speed, then it is congested 
                if currentSpeed < 0.5 * freeflow: 
                    congested = True # this just means that a node within the route to the destionation is congested 
                    # update all edges that have that node as a source or destination 
                    print(f"node {node} is congested, updating database")
                    self.cloggedNodes.append(node)
                    for u,v,attr in self.data.G.edges(data=True): 
                        if u == node or v == node: 
                            #attr['time'] = attr['length'] / float (currentSpeed)
                            attr['trafficWeight'] = 100000 # this is to stop the dijkstra from using this edge 
                            attr['time'] = attr['length'] / float(currentSpeed) # this is to store the actual time if the traffic is congested 
                            attr['erp'] = 0.3 * attr['trafficWeight'] + 0.3 * attr['length'] + 0.4 * float(attr['ERPcharge'])
                else: 
                    self.freeNodes.append(node) 
            else:
                print (f"Response code: {response.status_code}") 
        
        return congested
    
    def findRoute(self): 
        # this just combines the source nodes and destination nodes.
        # i then uses the custom dijkstra to find the shortest path to all nodes from each node in the list 
        # i then filter out the nodes that are not in the source or destination nodes
        #load the nodes in the destinationNodes dictionary 
        print (f"in findRoute: {self.source} | {self.destination}")
        nodes =  list(self.source.values()) + list(self.destination.values())
        print (nodes)
        
        #customshortestPath = {}
        #custompathDetails = {} 
        shortestPath = {}
        pathDetailsDict = {} 
        #shortest path to all nodes from each node 
        for node in nodes: 
            
            #!===================================================================================================================
            startTime = time.time() 
            shortestPathCosts, pathDetails = self.dijkstra(node, nodes) 
            
            if not self.checkPathCostsValidty(node, shortestPathCosts): 
                return False, False 
            # only check traffic if i am not using the time weight
            # will be in a loop of checking if traffic is congested, pluck out the congested path and rerun the dijkstra 
            if self.checkTraffic:
                updatedPathDetails = pathDetails.copy() 
                
                while True:
                    #print (f"updatedPathDetails: {updatedPathDetails}")
                    
                    congestedNodes = self.checkPathDetailsTraffic(node, updatedPathDetails)
                    if not congestedNodes: 
                        print ("No congested nodes found") 
                        break
                    else: 
                        print (f"Congested Destination found: {congestedNodes}") 
                    updatedPathCosts, updatedPathDetails = self.dijkstra(node, congestedNodes)
                    print (f"Before update: {shortestPathCosts}")
                    shortestPathCosts.update(updatedPathCosts)
                    print (f"After update: {shortestPathCosts}") 
                    pathDetails.update(updatedPathDetails) 
            
            shortestPath[node] = shortestPathCosts 
            pathDetailsDict[node] = pathDetails
            elapsedTime = time.time() - startTime 
            print (f"Time taken for normal dijkstra: {elapsedTime}")  
            #!======================================================================================================================
        #print (f"customshortestPath: {customshortestPath} | custompathDetails: {custompathDetails}") 
        print (f"shortestPath: {shortestPath} | pathDetails: {pathDetailsDict}") 
        return shortestPath, pathDetailsDict  
    
    def nodesFinder(self, source= "Changi Airport Terminal 3", destination=None): 
        sourceNodes = self.db.get_all_documents(self.sourceCollectionName) 
        destinationNodes = self.db.get_all_documents(self.destinationCollectionName)
        
        sourceNode = self.find_node(sourceNodes, source) 
        #print (f"sourceNode: {sourceNode}")
        self.source = {source: sourceNode[0]['node']} 
        #print (f"self.source: {self.source}")
        
        self.update_progress(6, "progress")
        
        if destination:
            destinationNode = self.find_node(destinationNodes, destination, multiple=True) #this is a list of dictionaries 
        else: 
            # it is every single hotel in the database 
            # look at dictionaryNodes, then convert it to a list of dictionaries 
            destinationNode = list(destinationNodes.values()) 
        
        print (f"destinationNode: {destinationNode}")
        self.destination = {node['name']: node['node'] for node in destinationNode}
        #print (f"self.destination: {self.destination}") 
        #print ("end")
        
        self.update_progress(6, "progress")
    
    def find_node(self, nodesDict, values, multiple=False):
        """
        Helper function to find nodes in the DataFrame.
        If `multiple` is True, it returns all matching nodes.
        """
        #print (f"dictionary passed from firebase to find the nodes : {nodesDict}")
        foundNodes = []
        for key, value in nodesDict.items():
            if value['name'] in values:
                foundNodes.append(value)
        return foundNodes 
    
    def hotelsPlotter(self,weightFG): 
        #plot the hotels on the map 
        # if optimal path exists then we are plotting the destination, marking them accordingly to the optimal path (different colors)
        sourceName = list(self.source.keys())[0]
        sourceNode = list(self.source.values())[0] 
        if self.optimalPath: 
            for i, node in enumerate(self.optimalPath): 
                DestinationName = ""
                # skip the source node 
                if i == 0: 
                    continue
                
                DestinationNames = [key for key, value in self.destination.items() if value == node]
                destinationNameHTML = "".join([f"<li>{name}</li>" for name in DestinationNames])
                popupHTML = f"""
                <div style="font-size:14px;">
                <b>Destination {i}</b><br>
                <ul>
                {destinationNameHTML} 
                </ul> 
                </div>
                """ 
                
                self.costs[self.currentWeight]['destinations'].update({f"Destination {i}": "".join([f"{name}" for name in DestinationNames])})
                
                folium.Marker(location=[self.data.G.nodes[node]['y'], self.data.G.nodes[node]['x']], popup=folium.Popup(popupHTML,max_width=250), icon=folium.Icon(color=self.colors[i%len(self.colors)])).add_to(weightFG)
        else:
            print ("No optimal path found") 
        # plotting the source node
        folium.Marker(location=[self.data.G.nodes[sourceNode]['y'], self.data.G.nodes[sourceNode]['x']], popup=sourceName, icon=folium.Icon(color="purple")).add_to(weightFG)
        return weightFG 
    
    def plotOptimalPath(self, pathDetails,m = None, mapType="all"): 
        #! convert graph to 4326 
        self.data.projectGraphtoEPSG4326() 
        ox.add_edge_bearings(self.data.G) #add edge bearings to the graph 
        if m is None:
            #using foluim, plot the optimal path on the map 
            m = folium.Map(location=[1.3521, 103.8198], zoom_start=12)
        
        #print (f"Optimal path: {self.optimalPath}") 
        #print (f"pathDetails: {pathDetails}") 
        
        instructionsList = [] 
        weightfg = folium.FeatureGroup(name=f'Optimal Path ({self.currentWeight})') 
        m.add_child(weightfg) 
        weightfg = self.hotelsPlotter(weightfg)
        
        #for every 2 nodes in the path, find it in the pathDetails dictionary and plot the path,polyline color changes every time 
        for i in range(len(self.optimalPath)):
            
            source = self.optimalPath[i]
            # if source is the last node, destination will be the first node
            if i == len(self.optimalPath)-1: 
                destination = self.optimalPath[0]
                color = self.colors[0]
            else:
                destination = self.optimalPath[i+1]
                color = self.colors[(i + 1) % len(self.colors)]
            
            #print (f"Source: {source} | Destination: {destination}")
            route = pathDetails[source][destination]
            
            try:
                destinationName = [key for key, value in self.destination.items() if value == destination][0]
            except IndexError:
                destinationName = list(self.source.keys())[0]
            
            instruction = self.generateDrivingInstructions(route,destinationName)
            instructionsList.append(instruction) 
            
            #print(f"using color: {self.colors[i]}")
            routeCoords = [(self.data.G.nodes[node]['y'], self.data.G.nodes[node]['x']) for node in route]
            #!polyline = folium.PolyLine(locations=routeCoords, color=color).add_to(m)
            polyline = folium.PolyLine(locations=routeCoords, color=color) 
            
            # Create a feature group for the polyline
            fg = FeatureGroupSubGroup(weightfg, f'{self.currentWeight} : Path {i + 1}') 
            m.add_child(fg) 
            polyline.add_to(fg) 
        
        # Create an HTML string for the instructions
        instructions_html = '<h4>Route Instructions</h4><ol>'
        
        destinations = list(self.destinations_map.get(self.currentWeight, {}).values())
        loop_count = 1  # Initialize loop count to keep track of path numbers
        
        # Add the first path from the source to the first destination
        source = list(self.source.keys())[0]
        first_destination = destinations[0]
        instructions_html += f'<li>Path {loop_count}: {source} to {first_destination}<ul>'
        for instruction in instructionsList[0]:
            instructions_html += f'<li>{instruction}</li>'
        instructions_html += '</ul></li>'
        loop_count += 1
        
        # Now loop through the remaining paths
        for i in range(1, len(instructionsList)):
            destination = destinations[i - 1]
            next_destination_index = i
            next_destination = destinations[next_destination_index] if next_destination_index < len(destinations) else list(self.source.keys())[0]
            instructions_html += f'<li>Path {loop_count}: {destination} to {next_destination}<ul>'
            
            for instruction in instructionsList[i]:
                instructions_html += f'<li>{instruction}</li>'
            instructions_html += '</ul></li>'
            loop_count += 1  # Increment the path counter
        
        instructions_html += '</ol>'
        
        self.costs[self.currentWeight]['instructions'] = instructions_html
        
        # Create an iframe to hold the instructions
        instructions_iframe = folium.IFrame(html=instructions_html, width=300, height=400)
        instructions_popup = folium.Popup(instructions_iframe, max_width=300)
        
        # Add the instructions popup to the map
        folium.Marker(location=[1.3521, 103.8298], popup=instructions_popup, icon=folium.Icon(icon='info-sign')).add_to(weightfg)
        
        #calculate the alternate costs so the erp charges can be displayed 
        if self.subOptimalCost == {}:
            self.calculateAlternateCosts(pathDetails) 
        
        cost_details = ""
        
        cost_details += """
                    <ul style="list-style-type: none; padding: 0;">
                    """
        
        for key, value in self.subOptimalCost.items(): 
            formatted_value = self.costFormatter(value, key)
            if self.currentWeight == key: 
                cost_details += f"<li><strong>{key.capitalize()}:</strong> {formatted_value}</li>"
                self.costs[key]['optimal'] = formatted_value
            else:
                cost_details += f"<li>{key.capitalize()}: {formatted_value}</li>"
        
        cost_details += "</ul>" 
        
        self.costs[self.currentWeight]['alternate'] = cost_details
        
        # HTML content for the popup
        html_content = f"""
        <div style="font-family: Arial, sans-serif; font-size: 14px; text-align:center;">
            {cost_details}
        </div>
        """
        
        # Add the marker with the HTML popup
        marker = folium.Marker(
            location=[1.3521, 103.8198],
            icon=folium.Icon(color='red'),
            popup=folium.Popup(html_content, max_width=300) 
            ).add_to(weightfg)
        
        return m 
    
    def costFormatter(self, cost, weight): 
        if weight == 'time':
            hours = int(cost) 
            minutes = int((cost - hours) * 60)
            return f"{hours} Hours {minutes} Minutes"
        elif weight == 'length':
            return f"{cost:.2f} KM" 
        else: #erp for now
            return f"${cost:.2f}"  
    
    def dataLog(self, data): 
        # for lengths the value is a dictionary, i want to break a line after each key value pair 
        
        with open(self.logFileName, 'a') as f: 
            for key, value in data.items(): 
                f.write(f'{key}: \n')
                if key == 'lengths':
                    for k,v in value.items(): 
                        f.write(f'{k}: {v}\n') 
                
                elif key == 'paths':
                    for k,v in value.items():  #k is the source node, v is the dictionary of destination nodes and paths
                        f.write(f'\n{k}(source): \n') 
                        for k1,v1 in v.items(): #k1 is the destination node, v1 is the path 
                            f.write(f'{k1}: {v1}\n') 
                #else is the source and destination 
                else: 
                    f.write(f'{value}\n') 
                f.write('-'*50 + '\n')
    
    def hotelsFinder(self, n=3):
        hotels = self.db.get_all_documents('hotel')
        if not hotels: 
            print ("theres no hotel document, you need to retrieve the data from osmnx and place it in the database, please use the update mode")
            return False
        
        #print (hotels) 
        hotelNames = [details['name'] for details in hotels.values()]
        hoteltoReturn = random.sample(hotelNames, n)
        #print (hoteltoReturn) 
        return hoteltoReturn
        #return n random hotels 
    
    def getTurnInstuction(self, bearing1, bearing2):
        angle_diff = bearing2 - bearing1
        
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360
        
        if -30 < angle_diff < 30:
            return "Go straight"
        elif angle_diff >= 30:
            return "Turn right"
        elif angle_diff <= -30:
            return "Turn left"
    
    def generateDrivingInstructions(self,route,destination=None):
        instructions = []
        
        for i in range(1, len(route) - 1):
            prev_edge = self.data.G[route[i - 1]][route[i]][0]
            curr_edge = self.data.G[route[i]][route[i + 1]][0]
            
            prev_bearing = prev_edge['bearing']
            curr_bearing = curr_edge['bearing']
            #print (f"prev Edge: {prev_edge} datatype: {type(prev_edge)}| curr Edge: {curr_edge} datatype: {type(curr_edge)}") 
            
            direction = self.getTurnInstuction(prev_bearing, curr_bearing)
            # instructions.append(direction)
            #put in the edge street name 
            
            # get name -> no name use ref -> no ref use highway -> unknown road 
            streetName = curr_edge.get("name",curr_edge.get("ref",curr_edge.get("highway","unknown road")))
            directions = f"{direction} onto {streetName}" 
            #print (f"directions: {directions} | prev Instruction: {instructions[-1] if instructions else None}")
            if not instructions or directions != instructions[-1]: 
                #print (f"appending directions") 
                instructions.append(directions)
            # else: 
            #     print (f"skipping directions") 
        
        instructions.append(f"You have reached your destination at {destination}")
        return instructions
    
    def getDataFromDB(self):
        sourceNodes = self.db.get_all_documents(self.sourceCollectionName) 
        destinationNodes = self.db.get_all_documents(self.destinationCollectionName)
        
        sources = {source['name']: source['node'] for source in sourceNodes.values()}
        destinations = {destination['name']: destination['node'] for destination in destinationNodes.values()}
        
        hotelStars = {hotel['name']: hotel['starRating'] for hotel in destinationNodes.values()}
        
        return sources, destinations, hotelStars
    
    def saveMap(self, m, individual=True):
        folium.LayerControl().add_to(m)
        mapStartPath = 'static/routes/'
        mapName = f'optimalRoute_{self.currentWeight}.html' if individual else 'optimalRoute.html'
        mapPath = f'{mapStartPath}{mapName}' 
        m.save(mapPath) 
        
        link = self.db.addImageToStorage(mapPath, f'maps/{User}{mapName}') 
        weight = self.currentWeight if individual else 'all' 
        
        self.db.update_document_by_field(collection_name=f'maps{User}', field_name='weight', field_value=weight, data={"link": link, "weight": weight})
        return None if individual else m 
    
    def flow1(self): 
        flow1StartTime = time.time() 
        hotels = self.hotelsFinder() #get the hotels 
        if not hotels: 
            return
        
        m1 = None 
        mAll = None
        self.nodesFinder(destination=hotels)  #find the nodes for the source and destination
        for weight in self.weightType: 
            self.subOptimalCost = {} 
            self.currentWeight = weight
            
            totalDijkstraStartTime = time.time() 
            shortestPath, pathDetails = self.findRoute() #find the shortest path and the path details
            if shortestPath == False and pathDetails == False:
                return False
            
            totalDijkstraElapsedTime = time.time() - totalDijkstraStartTime 
            # lengthAsWeights = {6970584189: {6970584189: 0, 6562418315: 0.2671494674603173, 8792655504: 0.33008826130952357, 5114346207: 0.6048279122619047}, 6562418315: {6970584189: 0.27785554075396823, 6562418315: 0, 8792655504: 0.09879820999999996, 5114346207: 0.40502368583333337}, 8792655504: {6970584189: 0.32548790742063516, 6562418315: 0.09613096666666665, 8792655504: 0, 5114346207: 0.35586027746031734}, 5114346207: {6970584189: 0.6146856459523811, 6562418315: 0.39838120190476245, 8792655504: 0.339851306825397, 5114346207: 0}}
            #log them in log/overall.txt
            self.dataLog({ 'source': self.source, 'destination': self.destination, 'lengths': shortestPath, 'paths': pathDetails})
            
            #if number of hotels >16, we doing aco
            if len(hotels) > 15:
                acoStartTime = time.time() 
                self.ACO(shortestPath) 
                acoElapsedTime = time.time() - acoStartTime 
                self.timeTrack[f"ACO({weight})"] = acoElapsedTime 
            
            else:
                heldkarpStartTime = time.time() 
                self.heldkarp(shortestPath) #find the optimal path  
                heldkarpElapsedTime = time.time() - heldkarpStartTime 
                self.timeTrack[f"Heldkarp({weight})"] = heldkarpElapsedTime
            
            self.timeTrack[f"Dijkstra({weight})"] = totalDijkstraElapsedTime
            if self.optimalPath:
                
                m1 = self.plotOptimalPath(pathDetails, m1, mapType=self.currentWeight)
                m1 = self.saveMap(m1,individual=True) 
                mAll = self.plotOptimalPath(pathDetails, mAll, mapType="all") 
        
        if mAll: 
            mAll = self.saveMap(mAll, individual=False) 
        
        flow1ElapsedTime = time.time() - flow1StartTime 
        
        #time track purposes
        print (f"Total time taken for flow1: {flow1ElapsedTime}")
        for key, value in self.timeTrack.items(): 
            print (f"{key}: {value}") 
        
        print (f"Congested nodes: {x.cloggedNodes}")
        return True # successfully ran 
    
    def flow2(self, source, destinations, routes):
        flow2StartTime = time.time() 
        
        for weight in self.weightType:
            self.costs[weight]['destinations'].clear()
        
        if not source or not destinations:
            return
        
        self.results.clear()
        
        m1 = None 
        mAll = None
        
        self.nodesFinder(source=source, destination=destinations)
        
        self.results.update({'source': list(self.source.keys())[0]})
        self.results.update({'destinations': list(self.destination.keys())})
        self.results.update({'selectedWeights': routes})
        
        self.update_progress(6, "progress")
        routecounter = 0
        
        for weight in self.weightType:
            
            if weight not in routes:  # Skip weights not selected
                continue
            
            print("Selected route types:", weight)
            routecounter += 1
            self.subOptimalCost = {}
            self.currentWeight = weight
            
            totalDijkstraStartTime = time.time() 
            shortestPath, pathDetails = self.findRoute() #find the shortest path and the path details
            
            self.update_progress(6, "progress")
            
            if shortestPath == False and pathDetails == False:
                return False
            
            totalDijkstraElapsedTime = time.time() - totalDijkstraStartTime
            
            self.update_progress(6, "progress")
            
            # lengthAsWeights = {6970584189: {6970584189: 0, 6562418315: 0.2671494674603173, 8792655504: 0.33008826130952357, 5114346207: 0.6048279122619047}, 6562418315: {6970584189: 0.27785554075396823, 6562418315: 0, 8792655504: 0.09879820999999996, 5114346207: 0.40502368583333337}, 8792655504: {6970584189: 0.32548790742063516, 6562418315: 0.09613096666666665, 8792655504: 0, 5114346207: 0.35586027746031734}, 5114346207: {6970584189: 0.6146856459523811, 6562418315: 0.39838120190476245, 8792655504: 0.339851306825397, 5114346207: 0}}
            #log them in log/overall.txt
            self.dataLog({ 'source': self.source, 'destination': self.destination, 'lengths': shortestPath, 'paths': pathDetails})
            
            self.update_progress(6, "progress")
            
            #if number of hotels >16, we doing aco
            if len(destinations) > 15:
                acoStartTime = time.time() 
                self.ACO(shortestPath) 
                acoElapsedTime = time.time() - acoStartTime 
                self.timeTrack[f"ACO({weight})"] = acoElapsedTime 
            
            else:
                heldkarpStartTime = time.time() 
                self.heldkarp(shortestPath) #find the optimal path  
                heldkarpElapsedTime = time.time() - heldkarpStartTime 
                self.timeTrack[f"Heldkarp({weight})"] = heldkarpElapsedTime
            
            self.update_progress(6, "progress")
            
            self.timeTrack[f"Dijkstra({weight})"] = totalDijkstraElapsedTime
            
            if self.optimalPath:
                m1 = self.plotOptimalPath(pathDetails, m1, mapType=self.currentWeight)
                m1 = self.saveMap(m1,individual=True) 
                mAll = self.plotOptimalPath(pathDetails, mAll, mapType="all") 
            
            # Create optimal path from dictionary
            if len(self.costs[self.currentWeight]['destinations']) > 0:
                self.costs[self.currentWeight]['route'] = list(self.source.keys())[0] + " --> "
                for value in self.costs[self.currentWeight]['destinations'].values():
                    self.costs[self.currentWeight]['route'] += value + " --> "
                self.costs[self.currentWeight]['route'] += list(self.source.keys())[0]
            
            self.results.update({f'{self.currentWeight}Cost': self.costs[self.currentWeight]['optimal']})
            self.results.update({f'{self.currentWeight}AlternateCost': self.costs[self.currentWeight]['alternate']})
            self.results.update({f'optimalPath_{self.currentWeight}': self.costs[self.currentWeight]['route']})
            self.results.update({f'optimalRouteInstructions_{self.currentWeight}': self.costs[self.currentWeight]['instructions']})
        
        if mAll: 
            mAll = self.saveMap(mAll, individual=False)
        
        flow2ElapsedTime = time.time() - flow2StartTime 
        
        #time track purposes
        print (f"Total time taken for flow2: {flow2ElapsedTime}")
        for key, value in self.timeTrack.items(): 
            print (f"{key}: {value}") 
        
        print (f"Congested nodes: {self.cloggedNodes}")
        
        # If 1 weight, add 58, 2 weights add 34, 3 weights add 10
        progressUpdates = {1: 58, 2: 34, 3: 10}
        if routecounter in progressUpdates:
            self.update_progress(progressUpdates[routecounter], "completion") # Add progress to the progress bar to complete it
            return True # successfully ran
    
    def get_results(self):
        return self.results
    

    

if __name__ == "__main__":
    x = RouteFinder(update = False)
    x.populateCosts() 
    success = False 
    while success == False and x.attemptCounter <4:
        success = x.flow1()
        x.attemptCounter += 1
