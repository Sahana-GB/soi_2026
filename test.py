import streamlit as st
import time

# Dynamic imports of algorithmic engines
from part_a import find_all_valid_routes_part_a
from part_b import find_optimal_global_route

# ==========================================
# 🖥️ GLOBAL FRONTEND NAVIGATION INTERFACE
# ==========================================
with st.sidebar:
    st.header("Application Hub")
    app_mode = st.radio("Choose:",
        ["Sightseeing Route Planning ", "Dynamic Ride Sharing System "]
    )

# ------------------------------------------------------------------
# RENDER SIGHTSEEING INTERFACE (PART A)
# ------------------------------------------------------------------
if app_mode == "Sightseeing Route Planning ":
    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.title("🗺️ Route Evaluation System")
    with top_col2:
        if st.button("🔄 Reset ", type="secondary", use_container_width=True):
            keys_to_clear = ["step_a", "stops_count_a", "raw_matrix_a", "saved_budget_a", "saved_threshold_a", "saved_start_node_a", "saved_end_node_a", "saved_locations_a"]
            for key in keys_to_clear:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

    if "step_a" not in st.session_state: st.session_state.step_a = 1
    if "stops_count_a" not in st.session_state: st.session_state.stops_count_a = 1
    if "raw_matrix_a" not in st.session_state: st.session_state.raw_matrix_a = {}

    if st.session_state.step_a == 1:
        st.subheader("Enter Parameters")
        
        col1, col2 = st.columns(2)
        budget = col1.number_input("Distance Budget (km)", min_value=1, value=int(st.session_state.get("saved_budget_a", 20)), step=1)
        threshold = col2.number_input("Category Threshold (n)", min_value=1, value=st.session_state.get("saved_threshold_a", 1), step=1)

        t1, t2 = st.columns(2)
        start_node = t1.text_input(" Start Node ", value=st.session_state.get("saved_start_node_a", "Hotel"))
        end_node = t2.text_input(" End Node ", value=st.session_state.get("saved_end_node_a", "Hilltop"))
        
        st.write("#### Add Intermediate Stops")
        locations_list = []
        old_locs = st.session_state.get("saved_locations_a", [])
        
        for i in range(st.session_state.stops_count_a):
            r1, r2, r3 = st.columns([2, 1.2, 1.5])
            d_name = old_locs[i]["name"] if i < len(old_locs) else ""
            d_score = old_locs[i]["score"] if i < len(old_locs) else 0
            d_cat = old_locs[i]["category"] if i < len(old_locs) else "Food"
            
            name = r1.text_input(f"Stop #{i+1} Name", value=d_name, placeholder="e.g., Castle", key=f"aname_{i}")
            score = r2.number_input(f"Base Score", min_value=0, value=int(d_score), step=1, key=f"ascore_{i}")
            category = r3.selectbox(f"Category", ["Food", "Historical", "Nature"], index=["Food", "Historical", "Nature"].index(d_cat), key=f"acat_{i}")
            
            if name.strip():
                locations_list.append({"name": name.strip(), "score": score, "category": category})

        if st.button("➕ Add More Stops"):
            st.session_state.saved_locations_a = locations_list
            st.session_state.stops_count_a += 1
            st.rerun()
                
        if st.button("Distance Matrix ➡️", type="primary", use_container_width=True):
            if not start_node.strip() or not end_node.strip():
                st.error("Please ensure your Start and End nodes have names.")
            elif len(locations_list) == 0:
                st.warning("Please configure at least one intermediate location stop before proceeding.")
            else:
                st.session_state.saved_budget_a = budget
                st.session_state.saved_threshold_a = threshold
                st.session_state.saved_start_node_a = start_node
                st.session_state.saved_end_node_a = end_node
                st.session_state.saved_locations_a = locations_list
                st.session_state.step_a = 2
                st.rerun()

    elif st.session_state.step_a == 2:
        st.subheader("🔢 Distance Matrix")
        
        if st.button("⬅️ Back"):
            st.session_state.step_a = 1
            st.rerun()
            
        start_node = st.session_state.saved_start_node_a
        end_node = st.session_state.saved_end_node_a
        locations_list = st.session_state.saved_locations_a
        budget = st.session_state.saved_budget_a
        threshold = st.session_state.saved_threshold_a

        all_nodes = [start_node] + [loc["name"] for loc in locations_list] + [end_node]
        n = len(all_nodes)
        
        if not st.session_state.raw_matrix_a:
            raw_matrix = {u: {v: 0 for v in all_nodes} for u in all_nodes}
        else:
            raw_matrix = st.session_state.raw_matrix_a

        for i in range(n):
            cols = st.columns(n)
            for j in range(n):
                u, v = all_nodes[i], all_nodes[j]
                if i == j:
                    cols[j].text_input(f"{u}→{v}", value="0", disabled=True, key=f"ma_{i}_{j}")
                elif j > i:
                    old_val = raw_matrix.get(u, {}).get(v, 4)
                    val = cols[j].number_input(f"{u} → {v}", min_value=0, value=int(old_val), step=1, key=f"ma_{i}_{j}")
                    raw_matrix[u][v] = int(val)
                    raw_matrix[v][u] = int(val)  
                else:
                    cols[j].text_input(f"{u}→{v}", value=str(raw_matrix[v][u]), disabled=True, key=f"ma_{i}_{j}")

        if st.button("Lets Find The Route", type="primary", use_container_width=True):
            st.session_state.raw_matrix_a = raw_matrix
            st.session_state.step_a = 3
            st.rerun()

    elif st.session_state.step_a == 3:
        st.subheader("Evaluated Route Combinations")
        if st.button("⬅️ Back"):
            st.session_state.step_a = 2
            st.rerun()
        
        start_node = st.session_state.saved_start_node_a
        end_node = st.session_state.saved_end_node_a
        locations_list = st.session_state.saved_locations_a
        budget = st.session_state.saved_budget_a
        threshold = st.session_state.saved_threshold_a
        raw_matrix = st.session_state.raw_matrix_a

        results = find_all_valid_routes_part_a(start_node, end_node, budget, threshold, locations_list, raw_matrix)
        
        if results:
            best_route = results[0]
            best_distance = best_route['Total Distance (km)']
            filtered_results = [r for r in results if r['Total Distance (km)'] == best_distance]
            
            st.success(f"Discovered {len(results)} valid configurations within budget bounds.")
            st.info(f"**🎖️ Final Optimal Route:**\n### {best_route['Route Sequence']}")
            
            m_dist, m_score = st.columns(2)
            m_dist.metric(label="Total Distance", value=f"{best_distance} km")
            m_score.metric(label="Total Score", value=f"{best_route['Total Score']}")
            
            st.markdown("---")
            st.markdown(f"### Possible Route Combinations with Distance = {best_distance} km")
            st.table(filtered_results)
        else:
            st.error("No valid routes found matching current parameters. Adjust constraints up.")

# ------------------------------------------------------------------
# RENDER DYNAMIC RIDE SHARING INTERFACE (PART B)
# ------------------------------------------------------------------
elif app_mode == "Dynamic Ride Sharing System ":
    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.title("Dynamic Ride Sharing System")
    with top_col2:
        if st.button("🔄 Reset", type="secondary", use_container_width=True):
            keys_to_clear = ["step_b", "saved_b_requests", "raw_matrix_b", "saved_b_start", "saved_b_end", "saved_b_capacity", "num_requests_count", "all_nodes_b"]
            for key in keys_to_clear:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

    if "step_b" not in st.session_state: st.session_state.step_b = 1
    if "saved_b_requests" not in st.session_state: st.session_state.saved_b_requests = []
    if "raw_matrix_b" not in st.session_state: st.session_state.raw_matrix_b = {}

    if st.session_state.step_b == 1:
        st.subheader("Enter Parameters")
        
        col1, col2 = st.columns(2)
        start_node = col1.text_input("Start (e.g. S)", value=st.session_state.get("saved_b_start", "S"))
        end_node = col2.text_input("Destination (e.g. E)", value=st.session_state.get("saved_b_end", "E"))
        
        c1, c2 = st.columns(2)
        capacity = c1.number_input("Vehicle Passenger Capacity (C)", min_value=1, value=st.session_state.get("saved_b_capacity", 2), step=1)
        num_requests = c2.number_input("Total Ride Requests (M)", min_value=1, value=st.session_state.get("num_requests_count", 2), step=1)
        
        st.markdown("---")
        st.write("#### Ride Requests Parameters Entry")
        
        requests_list = []
        old_reqs = st.session_state.saved_b_requests
        
        for i in range(num_requests):
            r1, r2, r3, r4 = st.columns(4)
            d_p = old_reqs[i]["pickup"] if i < len(old_reqs) else f"P{i+1}"
            d_d = old_reqs[i]["dropoff"] if i < len(old_reqs) else f"D{i+1}"
            d_bd = old_reqs[i]["base_dist"] if i < len(old_reqs) else 5
            d_fl = old_reqs[i]["flexibility"] if i < len(old_reqs) else 2
            
            p_label = r1.text_input(f"Req #{i+1} Pickup", value=d_p, key=f"p_{i}")
            d_label = r2.text_input(f"Req #{i+1} Dropoff", value=d_d, key=f"d_{i}")
            base_dist = r4.number_input(f"Base Distance (dist_{i+1})", min_value=1, value=int(d_bd), step=1, key=f"bd_{i}")
            flexibility = r3.number_input(f"Flexibility Margin (Δ_{i+1})", min_value=0, value=int(d_fl), step=1, key=f"fl_{i}")
            
            requests_list.append({"pickup": p_label, "dropoff": d_label, "base_dist": int(base_dist), "flexibility": int(flexibility)})

        if st.button("Distance Matrix ➡️", type="primary", use_container_width=True):
            st.session_state.saved_b_start = start_node
            st.session_state.saved_b_end = end_node
            st.session_state.saved_b_capacity = capacity
            st.session_state.num_requests_count = num_requests
            st.session_state.saved_b_requests = requests_list
            st.session_state.step_b = 2
            st.rerun()

    elif st.session_state.step_b == 2:
        st.subheader("🔢 Distance Matrix")
        
        if st.button("⬅️ Back", type="secondary"):
            st.session_state.step_b = 1
            st.rerun()
            
        start_node = st.session_state.saved_b_start
        end_node = st.session_state.saved_b_end
        requests_list = st.session_state.saved_b_requests

        all_nodes = [start_node]
        for r in requests_list:
            if r["pickup"] not in all_nodes: all_nodes.append(r["pickup"])
            if r["dropoff"] not in all_nodes: all_nodes.append(r["dropoff"])
        if end_node not in all_nodes: all_nodes.append(end_node)
        
        n = len(all_nodes)
        
        if not st.session_state.raw_matrix_b or set(st.session_state.raw_matrix_b.keys()) != set(all_nodes):
            raw_matrix = {u: {v: 0 for v in all_nodes} for u in all_nodes}
        else:
            raw_matrix = st.session_state.raw_matrix_b

        st.info("Fill out the upper triangular portion")

        for i in range(n):
            cols = st.columns(n)
            for j in range(n):
                u, v = all_nodes[i], all_nodes[j]
                if i == j:
                    cols[j].text_input(f"{u}→{v}", value="0", disabled=True, key=f"mb_{i}_{j}")
                elif j > i:
                    old_val = raw_matrix.get(u, {}).get(v, 4)
                    val = cols[j].number_input(f"{u} → {v}", min_value=0, value=int(old_val), step=1, key=f"mb_{i}_{j}")
                    raw_matrix[u][v] = int(val)
                    raw_matrix[v][u] = int(val)
                else:
                    cols[j].text_input(f"{u}→{v}", value=str(raw_matrix[v][u]), disabled=True, key=f"mb_{i}_{j}")

        if st.button("Deploy to Live Real-Time Simulator Dashboard", type="primary", use_container_width=True):
            st.session_state.raw_matrix_b = raw_matrix
            st.session_state.all_nodes_b = all_nodes
            st.session_state.step_b = 3
            st.rerun()

    elif st.session_state.step_b == 3:
        if st.button("⬅️ Back", type="secondary"):
            st.session_state.step_b = 2
            st.rerun()
            
        start_node = st.session_state.saved_b_start
        end_node = st.session_state.saved_b_end
        capacity = st.session_state.saved_b_capacity
        requests_list = st.session_state.saved_b_requests
        raw_matrix = st.session_state.raw_matrix_b
        all_nodes = st.session_state.all_nodes_b
        
        optimal_data = find_optimal_global_route(start_node, end_node, requests_list, capacity, raw_matrix)
        col_left, col_right = st.columns([2, 1])
        
        with col_right:
            st.markdown("### Inject Real-Time Request")
            p_dyn = st.text_input("Pickup", value="P_New")
            d_dyn = st.text_input("Dropoff", value="D_New")
            bd_dyn = st.number_input("Base Distance", min_value=1, value=4, step=1)
            fl_dyn = st.number_input("Flexibility", min_value=0, value=3, step=1)
            
            if st.button("Inject Request into Fleet"):
                raw_matrix[p_dyn] = {k: 5 for k in all_nodes + [p_dyn, d_dyn]}
                raw_matrix[d_dyn] = {k: 5 for k in all_nodes + [p_dyn, d_dyn]}
                for k in all_nodes:
                    raw_matrix[k][p_dyn] = 5
                    raw_matrix[k][d_dyn] = 5
                raw_matrix[p_dyn][d_dyn] = bd_dyn
                raw_matrix[d_dyn][p_dyn] = bd_dyn
                
                new_req = {"pickup": p_dyn, "dropoff": d_dyn, "base_dist": int(bd_dyn), "flexibility": int(fl_dyn)}
                test_opt = find_optimal_global_route(start_node, end_node, requests_list + [new_req], capacity, raw_matrix)
                
                if test_opt:
                    st.session_state.saved_b_requests.append(new_req)
                    st.session_state.all_nodes_b.extend([p_dyn, d_dyn])
                    st.session_state.raw_matrix_b = raw_matrix
                    st.success("Injected successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Injection dropped!")

        with col_left:
            st.markdown("### 🏁 Live Route Execution Simulator")
            
            if optimal_data:
                current_active_route = optimal_data["route"]
                total_computed_distance = optimal_data["distance"]
                validation_log = optimal_data["passenger_log"]
                
                st.success("### Optimization Results Output")
                st.info(f"**🏆 Final Calculated Optimal Route:**\n### {' ➔ '.join(current_active_route)}")
                st.metric(label="Total Distance", value=f"{total_computed_distance} km")
                st.markdown("---")
                
                sim_btn = st.button("▶️ Telemetry Traversal Animation")
                status_box = st.empty()
                metric_box = st.empty()
                visual_box = st.empty()
                
                if sim_btn:
                    accumulated_dist = 0
                    total_route_len = len(current_active_route)
                    
                    for i in range(total_route_len - 1):
                        u, v = current_active_route[i], current_active_route[i+1]
                        leg_dist = raw_matrix[u][v]
                        accumulated_dist += leg_dist
                        
                        current_passengers = validation_log[i+1] if i+1 < len(validation_log) else 0
                        status_box.info(f"Vehicle Status: En Route from **{u}** ➔ **{v}** ({leg_dist} km)")
                        
                        with metric_box:
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Next Stop", v)
                            m2.metric("Odometer Tracking", f"{accumulated_dist} km")
                            m3.metric("Passenger Load", f"{current_passengers} / {capacity}")
                        
                        with visual_box:
                            timeline_html = "<div style='display: flex; align-items: center; justify-content: space-around; background-color: #1a1c23; padding: 20px; border-radius: 8px; border: 2px solid #ff4b4b; color: white; font-family: sans-serif;'>"
                            for idx, node in enumerate(current_active_route):
                                if node == u or node == v:
                                    color = "#ff4b4b"
                                    style = "font-weight: bold; font-size: 20px;"
                                else:
                                    color = "#0068c9"
                                    style = "font-size: 16px;"
                                
                                timeline_html += f"<div style='text-align: center; color: {color}; {style}'>{node}</div>"
                                if idx < total_route_len - 1:
                                    arrow_color = "#ff4b4b" if (current_active_route[idx] == u and current_active_route[idx+1] == v) else "#4a5568"
                                    timeline_html += f"<div style='color: {arrow_color}; font-weight: bold; font-style: normal;'> ➔ </div>"
                            timeline_html += "</div>"
                            st.markdown(timeline_html, unsafe_allow_html=True)
                        
                        time.sleep(2)
                    status_box.success("🏁 Arrival Complete! Final Route Safely Executed.")
                else:
                    status_box.warning("Simulation idle. Click 'Start Telemetry Traversal Animation' to watch live track tracking.")
            else:
                st.error("❌ Feasibility Error: No legal path combination satisfies constraints for this input dataset layout.")
