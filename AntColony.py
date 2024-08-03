import numpy as np

class AntColony:
    def __init__(self, distances, n_ants, n_best, n_iterations, decay, alpha=1, beta=1):
        self.distances = distances
        self.pheromone = np.ones(self.distances.shape) / len(distances)
        self.all_inds = range(len(distances))
        self.n_ants = n_ants
        self.n_best = n_best
        self.n_iterations = n_iterations
        self.decay = decay
        self.alpha = alpha
        self.beta = beta
    
    def run(self):
        shortest_path = None
        all_time_shortest_path = ("placeholder", np.inf)
        for i in range(self.n_iterations):
            all_paths = self.gen_all_paths()
            self.spread_pheronome(all_paths, self.n_best, shortest_path=shortest_path)
            shortest_path = min(all_paths, key=lambda x: x[1])
            if shortest_path[1] < all_time_shortest_path[1]:
                all_time_shortest_path = shortest_path            
            self.pheromone *= self.decay            
        return all_time_shortest_path
    
    def spread_pheronome(self, all_paths, n_best, shortest_path):
        sorted_paths = sorted(all_paths, key=lambda x: x[1])
        print (f"sorted_paths: {sorted_paths}") 
        for path, dist in sorted_paths[:n_best]:
            for move in path:
                print (f"move: {move}")
                print (f"self.pheromone[move]: {self.pheromone[move]}") 
                print (f"self.distances[move]: {self.distances[move]} ")
                print (f"dist: {dist}") 
                self.pheromone[move] += 1.0 / dist 
    
    def gen_path_dist(self, path):
        print (f"path: {path}") 
        total_dist = 0
        for ele in path:
            print (f"ele: {ele}")
            print (f"self.distances[ele]: {self.distances[ele]}")
            total_dist += self.distances[ele]
        return total_dist
    
    def gen_all_paths(self):
        all_paths = []
        for i in range(self.n_ants):
            path = self.gen_path(0)
            all_paths.append((path, self.gen_path_dist(path)))
        return all_paths
    
    def gen_path(self, start):
        path = []
        visited = set()
        visited.add(start)
        prev = start
        for i in range(len(self.distances) - 1):
            print (f"prev: {prev}") 
            print (f"self.pheromone[prev]: {self.pheromone[prev]}")
            print (f"self.distances[prev]: {self.distances[prev]}") 
    
            move = self.pick_move(self.pheromone[prev], self.distances[prev], visited)
            path.append((prev, move))
            prev = move
            visited.add(move)
        path.append((prev, start))  # going back to where we started    
        return path
    
    def pick_move(self, pheromone, dist, visited):
        pheromone = np.copy(pheromone)
        pheromone[list(visited)] = 0
        
        # Handle zero distances by setting them to a small positive value
        adjusted_dist = np.where(dist == 0, np.finfo(float).eps, dist)
        
        # the row is calculated by having a certain weightage of pheromone and distance 
        row = pheromone ** self.alpha * ((1.0 / adjusted_dist) ** self.beta)
        
        # Check if the row contains infinite values and handle them
        if np.isinf(row).any():
            row[np.isinf(row)] = 0  # or some other handling logic
        
        # Check if the row sum is zero to avoid division by zero
        if row.sum() == 0:
            norm_row = np.ones_like(row) / len(row)
        else:
            # this turns row into a probability distribution, so the sum of row is 1 
            norm_row = row / row.sum()
        
        # Check for NaN values in norm_row and replace them with a uniform distribution if found
        if np.isnan(norm_row).any():
            norm_row = np.ones_like(norm_row) / len(norm_row)
        
        move = np.random.choice(self.all_inds, 1, p=norm_row)[0]
        return move
