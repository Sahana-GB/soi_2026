import itertools

def compute_path_distance(node_list, distance_matrix):
    dist = 0
    for i in range(len(node_list) - 1):
        u, v = node_list[i], node_list[i+1]
        dist += distance_matrix.get(u, {}).get(v, float('inf'))
    return int(dist) if dist != float('inf') else None

def check_route_legality(full_route, requests_data, capacity, distance_matrix):
    for r in requests_data:
        p, d = r["pickup"], r["dropoff"]
        if p in full_route and d in full_route:
            if full_route.index(p) > full_route.index(d):
                return False, []

    current_passengers = 0
    passenger_log = [0] 
    pickups = [r["pickup"] for r in requests_data]
    dropoffs = [r["dropoff"] for r in requests_data]
    
    for stop in full_route[1:-1]:
        if stop in pickups:
            current_passengers += 1
        elif stop in dropoffs:
            current_passengers -= 1
            
        passenger_log.append(current_passengers)
        if current_passengers > capacity or current_passengers < 0:
            return False, []
            
    passenger_log.append(0) 
    return True, passenger_log

def find_optimal_global_route(start_node, end_node, requests_data, capacity, distance_matrix):
    mid_nodes = []
    for r in requests_data:
        mid_nodes.extend([r["pickup"], r["dropoff"]])
    
    best_route = None
    min_distance = float('inf')
    best_passenger_log = []
    
    for perm in itertools.permutations(mid_nodes):
        candidate_route = [start_node] + list(perm) + [end_node]
        is_valid, passenger_log = check_route_legality(candidate_route, requests_data, capacity, distance_matrix)
        
        if is_valid:
            total_dist = compute_path_distance(candidate_route, distance_matrix)
            if total_dist is not None and total_dist < min_distance:
                min_distance = total_dist
                best_route = candidate_route
                best_passenger_log = passenger_log
                
    if best_route:
        return {"route": best_route, "distance": min_distance, "passenger_log": best_passenger_log}
    return None
