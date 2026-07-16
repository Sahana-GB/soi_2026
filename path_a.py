import math
import itertools

def find_all_valid_routes_part_a(start_node, end_node, budget, threshold, intermediate_locations, distance_matrix):
    valid_routes = []
    loc_lookup = {loc["name"]: loc for loc in intermediate_locations}
    nodes_to_visit = [loc["name"] for loc in intermediate_locations if loc["name"].strip()]

    for r in range(0, len(nodes_to_visit) + 1):
        for perm in itertools.permutations(nodes_to_visit, r):
            full_path = [start_node] + list(perm) + [end_node]
            
            current_dist = 0
            current_score = 0.0
            cat_counts = {}
            is_valid = True
            
            for i in range(len(full_path) - 1):
                u = full_path[i]
                v = full_path[i+1]
                leg_dist = distance_matrix.get(u, {}).get(v, float('inf'))
                
                if v in loc_lookup:
                    loc_info = loc_lookup[v]
                    s_eff = loc_info["score"] * math.exp(-0.1 * current_dist)
                    cat = loc_info["category"]
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
                    
                    if cat_counts[cat] > threshold:
                        s_eff *= 0.9  
                        
                    current_score += s_eff
                
                current_dist += leg_dist
                if current_dist > budget:
                    is_valid = False
                    break

            if is_valid:
                valid_routes.append({
                    "Route Sequence": " → ".join(full_path),
                    "Total Distance (km)": int(current_dist),
                    "Total Score": round(current_score, 3)
                })
                
    return sorted(valid_routes, key=lambda x: x["Total Score"], reverse=True)
