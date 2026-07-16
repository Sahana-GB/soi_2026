import math

def calculate_effective_score(raw_score, distance_travelled, category_count, threshold):
    
    decay_factor = math.exp(-0.005 * distance_travelled)
    effective_score = raw_score * decay_factor
    
    
    if category_count > threshold:
        effective_score *= 0.90
        
    return round(effective_score, 4)

def run_a(source, destination, budget, threshold, locations, matrix):
    best_itinerary = {
        "score": -1.0,
        "distance": 0.0,
        "route": [],
        "breakdown": []
    }
    
    
    loc_pool = {loc['name']: loc for loc in locations if 'name' in loc}
    pool_names = list(loc_pool.keys())
    
    def backtrack(current_node, current_dist, current_score, visited_sequence, category_tracker, detailed_breakdown):
        
        dist_to_end = matrix[current_node][destination]
        total_projected_distance = current_dist + dist_to_end
        
       
        if total_projected_distance <= budget:
            if current_score > best_itinerary["score"]:
                best_itinerary["score"] = current_score
                best_itinerary["distance"] = round(total_projected_distance, 2)
                best_itinerary["route"] = list(visited_sequence)
                best_itinerary["breakdown"] = list(detailed_breakdown)
                

        for next_node in pool_names:
            if next_node not in visited_sequence:
                dist_to_next = matrix[current_node][next_node]
                new_distance = current_dist + dist_to_next
                
               
                if new_distance + matrix[next_node][destination] > budget:
                    continue
                    
                node_cat = loc_pool[next_node]['category']
                category_tracker[node_cat] = category_tracker.get(node_cat, 0) + 1
                
                raw_s = loc_pool[next_node]['score']
                eff_s = calculate_effective_score(raw_s, new_distance, category_tracker[node_cat], threshold)
                
                step_log = {
                    "id": next_node,
                    "dist_before": round(new_distance, 2),
                    "raw_score": raw_s,
                    "eff_score": eff_s
                }
                
                visited_sequence.append(next_node)
                detailed_breakdown.append(step_log)
                
                backtrack(next_node, new_distance, current_score + eff_s, visited_sequence, category_tracker, detailed_breakdown)
                
               
                visited_sequence.pop()
                detailed_breakdown.pop()
                category_tracker[node_cat] -= 1
                if category_tracker[node_cat] == 0:
                    del category_tracker[node_cat]

    if source in matrix:
        backtrack(source, 0.0, 0.0, [], {}, [])
        
    return best_itinerary
