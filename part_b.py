"""
PathMatrix — Part B: Dynamic Ride Sharing with Flexible Routing
===================================================================
Handles ride requests arriving dynamically and inserts them into the
existing route WITHOUT recomputing the whole route from scratch.
"""

import itertools

def run_b(origin, destination, requests_list, capacity, flexibility_margin, matrix):
    """
    Finds the optimal path sequence to satisfy all ride requests under strict
    pickup-before-drop, vehicle capacity, and flexibility margin constraints.
    """
    # Baseline direct distance from Origin to Destination
    if origin not in matrix or destination not in matrix:
        return {"status": "Rejected", "message": "Invalid matrix keys", "route": [], "distance": 0.0}
        
    baseline_distance = matrix[origin][destination]
    max_allowed_distance = baseline_distance + flexibility_margin
    
    # Identify all nodes that must be visited
    # For every request, we have a unique pickup ID and drop ID
    visit_nodes = []
    pickup_to_drop = {}
    node_passenger_delta = {} # Tracks how many people enter/exit at this specific node
    
    for req in requests_list:
        p_id = f"Pickup_{req['id']}"
        d_id = f"Drop_{req['id']}"
        
        visit_nodes.extend([p_id, d_id])
        pickup_to_drop[p_id] = d_id
        
        # Pickups add passengers, drops subtract them
        node_passenger_delta[p_id] = req['count']
        node_passenger_delta[d_id] = -req['count']

    best_route = []
    min_distance = float('inf')
    
    # Generate all permutations of the pickup and drop nodes
    # (Since the number of requests is typically small, full permutation is highly efficient)
    for perm in itertools.permutations(visit_nodes):
        # Enforce Constraint 1: Pickup before Drop
        valid_order = True
        node_indices = {node: idx for idx, node in enumerate(perm)}
        
        for p_id, d_id in pickup_to_drop.items():
            if node_indices[p_id] > node_indices[d_id]:
                valid_order = False
                break
                
        if not valid_order:
            continue
            
        # Enforce Constraint 2: Running Capacity Check
        current_load = 0
        capacity_violated = False
        
        for node in perm:
            current_load += node_passenger_delta[node]
            if current_load > capacity or current_load < 0:
                capacity_violated = True
                break
                
        if capacity_violated:
            continue
            
        # Calculate full sequential route distance: Origin -> Permutation -> Destination
        current_distance = 0.0
        current_node = origin
        
        for next_node in perm:
            current_distance += matrix[current_node][next_node]
            current_node = next_node
        current_distance += matrix[current_node][destination]
        
        # Find the absolute shortest route among all valid configurations
        if current_distance < min_distance:
            min_distance = current_distance
            best_route = list(perm)

    # Enforce Constraint 3: Flexibility Margin
    if min_distance <= max_allowed_distance and best_route:
        return {
            "status": "Accepted",
            "route": [origin] + best_route + [destination],
            "distance": round(min_distance, 2),
            "baseline": round(baseline_distance, 2),
            "added_distance": round(min_distance - baseline_distance, 2)
        }
    else:
        return {
            "status": "Rejected",
            "message": f"No valid route found within flexibility margin of {flexibility_margin} km.",
            "route": [],
            "distance": round(min_distance, 2) if best_route else 0.0,
            "baseline": round(baseline_distance, 2)
        }
