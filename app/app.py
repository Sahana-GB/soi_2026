import streamlit as st
import requests
import math
import time
import folium
import os
from geopy.geocoders import Nominatim 

st.set_page_config(layout="wide", page_title="PATHMATRIX", page_icon="🗺️", initial_sidebar_state="expanded")

if "bg_start" not in st.session_state:
    st.session_state.bg_start = "S"

if "app_page" not in st.session_state:
    st.session_state.app_page = "front"

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
css_path = os.path.join(root_dir, "style.css")

if os.path.exists(css_path):
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    st.error("CSS file not found at the root level!")

TOMTOM_API_KEY = st.secrets["TOMTOM_API_KEY"]

if "app_page" not in st.session_state:
    st.session_state.app_page = "front"
if "app_mode" not in st.session_state:
    st.session_state.app_mode = None

if st.session_state.app_page == "front":
    st.markdown("""
        <div style="text-align:center;">
            <h1 class="typing-text">Welcome To PathMatrix</h1>
        </div>
    """, unsafe_allow_html=True)

st.write("")

if "global_src" not in st.session_state: st.session_state.global_src = ""
if "global_dest" not in st.session_state: st.session_state.global_dest = ""
if "budget" not in st.session_state: st.session_state.budget = 50
if "threshold" not in st.session_state: st.session_state.threshold = 1
if "num_stops" not in st.session_state: st.session_state.num_stops = 0
if "stops_storage" not in st.session_state: st.session_state.stops_storage = {}
if "capacity" not in st.session_state: st.session_state.capacity = 4
if "flexibility" not in st.session_state: st.session_state.flexibility = 15
if "num_requests" not in st.session_state: st.session_state.num_requests = 0
if "requests_storage" not in st.session_state: st.session_state.requests_storage = {}
if "step_ag" not in st.session_state: st.session_state.step_ag = 1
if "stops_count_ag" not in st.session_state: st.session_state.stops_count_ag = 1
if "raw_matrix_ag" not in st.session_state: st.session_state.raw_matrix_ag = {}
if "step_bg" not in st.session_state: st.session_state.step_bg = 1
if "raw_matrix_bg" not in st.session_state: st.session_state.raw_matrix_bg = {}
if "saved_bg_requests" not in st.session_state: st.session_state.saved_bg_requests = []

def render_page_header(title, unique_suffix, back_target_page=None, back_target_step_var=None, back_target_step_val=None):
    
    title_col, button_col = st.columns([8.2, 1.8])
    
    with title_col:
        st.markdown(f"<h1 style='margin:0; font-size:2.2rem;'>{title}</h1>", unsafe_allow_html=True)
        
    with button_col:
        
        if st.session_state.app_page == "execution":
            if st.button("🎛️ Switch Engine", key=f"switch_btn_{unique_suffix}", use_container_width=True):
                st.session_state.app_page = "hub"
                st.rerun()
                
        
        if back_target_page or back_target_step_var:
            if st.button("⬅️ Back", key=f"back_btn_{unique_suffix}", use_container_width=True):
                if back_target_page:
                    st.session_state.app_page = back_target_page
                if back_target_step_var and back_target_step_val is not None:
                    st.session_state[back_target_step_var] = back_target_step_val
                st.rerun()

def run_a(origin, destination, budget, threshold, intermediates, distance_matrix):
    total_dist = 0.0
    current = origin
    route = [{"name": origin}]
    total_score = 0.0
    category_counts = {}
    k = 0.1
    
    unvisited = list(intermediates)
    
    while unvisited:
        best_next = None
        best_dist_step = float('inf')
        
        for sight in unvisited:
            node_id = sight["name"]
            if current in distance_matrix and node_id in distance_matrix[current]:
                d_step = distance_matrix[current][node_id]
                if d_step < best_dist_step:
                    best_dist_step = d_step
                    best_next = sight
                    
        if best_next is None:
            break
            
        node_id = best_next["name"]
        
        dist_to_dest = distance_matrix.get(node_id, {}).get(destination, 0.0)
        if total_dist + best_dist_step + dist_to_dest > budget:
            unvisited.remove(best_next)
            continue
            
        total_dist += best_dist_step
        route.append({"name": node_id})
        
        s_effective = best_next["score"] * math.exp(-k * best_dist_step)
        cat = best_next.get("category", "")
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if category_counts[cat] > threshold:
                s_effective *= 0.9
                
        total_score += s_effective
        current = node_id
        unvisited.remove(best_next)

    if current in distance_matrix and destination in distance_matrix[current]:
        total_dist += distance_matrix[current][destination]
    route.append({"name": destination})
    
    if total_dist > budget:
        return {"route": [], "score": 0.0, "distance": total_dist}
    return {"route": route, "score": total_score, "distance": total_dist}

def run_b(origin, destination, requests, capacity, distance_matrix):
    if origin not in distance_matrix or destination not in distance_matrix[origin]:
        return {"status": "Rejected", "message": "Routing matrix endpoints invalid."}
    
    simulated_route = [origin]
    current = origin
    total_dist = 0.0
    passenger_logs = [{"Location": origin, "Passengers": 0}]
    current_passengers = 0
    
    for r in requests:
        p_id = f"Pickup_{r['id']}"
        if current in distance_matrix and p_id in distance_matrix[current]:
            total_dist += distance_matrix[current][p_id]
            simulated_route.append(p_id)
            current_passengers += r.get("count", 1)
            if current_passengers > capacity:
                return {"status": "Rejected", "message": f"Capacity of {capacity} exceeded the vehicle capacity at {p_id}."}
            passenger_logs.append({"Location": p_id, "Passengers": current_passengers})
            current = p_id
            
    for r in requests:
        d_id = f"Drop_{r['id']}"
        if current in distance_matrix and d_id in distance_matrix[current]:
            total_dist += distance_matrix[current][d_id]
            simulated_route.append(d_id)
            current_passengers -= r.get("count", 1)
            passenger_logs.append({"Location": d_id, "Passengers": current_passengers})
            current = d_id
            
    if current in distance_matrix and destination in distance_matrix[current]:
        total_dist += distance_matrix[current][destination]
    simulated_route.append(destination)
    passenger_logs.append({"Location": destination, "Passengers": current_passengers})
    
    for r in requests:
        p_node = f"Pickup_{r['id']}"
        d_node = f"Drop_{r['id']}"
        try:
            idx_p = simulated_route.index(p_node)
            idx_d = simulated_route.index(d_node)
            sub_dist = 0.0
            for i in range(idx_p, idx_d):
                sub_dist += distance_matrix[simulated_route[i]][simulated_route[i+1]]
            direct_sub = distance_matrix.get(p_node, {}).get(d_node, 0.0)
            detour_excess = sub_dist - direct_sub
            if detour_excess > r.get("max_detour", 999.0):
                return {"status": "Rejected", "message": f"Detour excess for {r['name']} ({detour_excess:.2f} km) violates individual limits."}
        except ValueError:
            pass

    return {
        "status": "Accepted", 
        "route": simulated_route, 
        "distance": total_dist, 
        "passenger_logs": passenger_logs
    }

ORS_API_KEY = st.secrets["ORS_API_KEY"]

def fetch_live_traffic_factor(lat, lon):
    if TOMTOM_API_KEY == "YOUR_TOMTOM_API_KEY_HERE":
        return 1.0
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={TOMTOM_API_KEY}&point={lat},{lon}"
    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            flow = response.json().get("flowSegmentData", {})
            curr, free = flow.get("currentSpeed", 1), flow.get("freeFlowSpeed", 1)
            return max(1.0, round(float(free) / float(curr), 3))
    except Exception: pass
    return 1.0

def geocode_address(address_text: str):
    if not address_text or address_text.strip() == "": return None
    query = address_text.strip()
    try:
        geolocator = Nominatim(user_agent="pathmatrix_dynamic_navigation_engine")
        location = geolocator.geocode(query, timeout=5)
        if location: return [location.latitude, location.longitude]
    except Exception: pass
    try:
        url = f"https://api.openrouteservice.org/geocode/search?api_key={ORS_API_KEY}&text={query}&size=1"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            coords = response.json()['features'][0]['geometry']['coordinates']
            return [coords[1], coords[0]]
    except Exception: pass
    return None

def haversine_fallback(coord1, coord2):
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 3)

def fetch_real_road_geometry(route_coordinates):
    if not route_coordinates or len(route_coordinates) < 2: 
        return route_coordinates
    formatted_coords = [[c[1], c[0]] for c in route_coordinates]
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "coordinates": formatted_coords
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "features" in data and len(data["features"]) > 0:
                geometry = data["features"][0]["geometry"]["coordinates"]
                return [[point[1], point[0]] for point in geometry]
        else:
            print(f"ORS API Error: Status {response.status_code} - {response.text}")
    except Exception as e:
        print(f"ORS Network Connection Error: {e}")
    return route_coordinates

def fetch_osrm_matrix_segment_specific(coordinates, names, traffic_factors):
    if not coordinates or not names: return {}
    coord_string = [[c[1], c[0]] for c in coordinates]
    url = "https://api.openrouteservice.org/v2/matrix/driving-car"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, json={"locations": coord_string, "metrics": ["distance"]}, headers=headers, timeout=4)
        if response.status_code == 200:
            raw_matrix = response.json()["distances"]
            matrix = {}
            for i, row_name in enumerate(names):
                matrix[row_name] = {}
                traffic_factor = traffic_factors.get(row_name, 1.0)
                for j, col_name in enumerate(names):
                    matrix[row_name][col_name] = round((raw_matrix[i][j] / 1000.0) * traffic_factor, 3)
            return matrix
    except Exception: pass
    matrix = {}
    for i, row_name in enumerate(names):
        matrix[row_name] = {}
        traffic_factor = traffic_factors.get(row_name, 1.0)
        for j, col_name in enumerate(names):
            matrix[row_name][col_name] = round(haversine_fallback(coordinates[i], coordinates[j]) * traffic_factor, 3)
    return matrix

if st.session_state.app_page == "front":
   
    st.markdown("""
    <style>
    .typing-container {
        text-align: center;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: center;
    }
    
    .typing-text {
        display: inline-block;
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 3rem;
        color: #ffffff;
        overflow: hidden; 
        border-right: .15em solid transparent; 
        white-space: nowrap; 
        margin: 0 auto; 
        width: 0; 
        animation: 
          typing 3s steps(22, end) forwards,
          blink-caret 0.75s step-end 4; 
    }

    @keyframes typing {
      from { width: 0 }
      to { width: 11.5em; } 
    }

    @keyframes blink-caret {
      from, to { border-color: transparent }
      50% { border-color: #818cf8; }
    }

   
    .hover-card {
        background: rgba(15, 23, 42, 0.6); 
        border-radius: 12px; 
        padding: 2rem; 
        border: 1px solid rgba(255, 255, 255, 0.08); 
        text-align: center; 
        line-height: 1.6;
        transition: all 0.4s ease-in-out;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }

    
    .hover-card:hover {
        transform: translateY(-5px); /* Gentle lift effect */
        border-color: #818cf8; /* Indigo border glow */
        box-shadow: 0 10px 30px rgba(129, 140, 248, 0.2); /* Deep glow shadow */
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 8vh;'></div>", unsafe_allow_html=True)
    
    st.markdown("<p class='subtitle-text' style='text-align:center; margin-bottom: 2rem;'>Intelligent Route Planning and Adaptive Optimization System</p>", unsafe_allow_html=True)
    
  
    c_left, c_mid, c_right = st.columns([1, 2, 1])
    with c_mid:
        
        st.markdown("""
        <div class="hover-card">
            PathMatrix is a unified optimization platform that combines graph algorithms, real-time geospatial analytics, and combinatorial optimization to solve complex routing problems. Whether optimizing ride-sharing operations or planning sightseeing routes, the platform computes efficient, data-driven paths with speed, accuracy, and scalability.
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        st.write("")
        
        btn_left, btn_center, btn_right = st.columns([1, 1.5, 1])
        with btn_center:
            if st.button("Enter", type="primary", key="front_enter_btn", use_container_width=True):
                st.session_state.app_page = "hub"
                st.rerun()
elif st.session_state.app_page == "hub":
    
    render_page_header("Select the optimization mode to continue.", "hub_scr", back_target_page="front")
    
    st.markdown("<div class='feature-divider'></div>", unsafe_allow_html=True)

    col_opt1, col_opt2 = st.columns(2)

    with col_opt1:
        st.markdown("""
        <div class='menu-card'>
            <div class='menu-icon'>🌐</div>
            <h3>Real-Time Geospatial System</h3>
            <p style='color:#94a3b8; font-size:0.9rem; min-height: 60px;'>Optimize routes using real-world road networks and live traffic conditions. Analyze travel paths with accurate geospatial data, dynamic road distances, and interactive map visualization.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch Real-Time Engine", use_container_width=True, type="primary"):
            st.session_state.app_mode = "real_time"
            st.session_state.app_page = "execution"
            st.rerun()

    with col_opt2:
        st.markdown("""
        <div class='menu-card'>
            <div class='menu-icon'>🔢</div>
            <h3>General Matrix System</h3>
            <p style='color:#94a3b8; font-size:0.9rem; min-height: 60px;'>
                Build and analyze custom network matrices without geographical constraints. Perfect for testing graph algorithms, route optimization, and combinatorial path planning.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch General Engine", use_container_width=True, type="primary"):
            st.session_state.app_mode = "general"
            st.session_state.app_page = "execution"
            st.rerun()

elif st.session_state.app_page == "execution":
    st.sidebar.title("Engine Controls")
    if st.sidebar.button("🔄 Reset", use_container_width=True):
        keys_to_flush = [
            "global_src", "global_dest", "budget", "threshold", "num_stops", "stops_storage",
            "capacity", "flexibility", "num_requests", "requests_storage",
            "step_ag", "stops_count_ag", "raw_matrix_ag", "s_b", "s_t", "s_s", "s_e", "s_locs",
            "step_bg", "raw_matrix_bg", "saved_bg_requests", "bg_start", "bg_end", "bg_cap", "num_requests_bg"
        ]
        for key in keys_to_flush:
            if key in st.session_state:
                del st.session_state[key]
        st.success("All configurations and states flushed successfully!")
        time.sleep(0.5)
        st.rerun()
    st.sidebar.markdown("---")

    mode_title = "🌐 Real-Time Spatial Engine" if st.session_state.app_mode == "real_time" else "🔢 General Network Matrix Engine"

    if st.session_state.app_mode == "real_time":
        module = st.sidebar.radio("Select Optimization Module", ["Sightseeing Route Optimization", "Dynamic Ride Sharing with Flexible Routing"])
        if "step_art" not in st.session_state: st.session_state.step_art = 1
        if "step_brt" not in st.session_state: st.session_state.step_brt = 1

        if module == "Sightseeing Route Optimization":
            if st.session_state.step_art == 1:
                render_page_header(mode_title, "art_step1", back_target_page="hub")
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.header("🏁 Route Parameters")
                    src_input = st.text_input("Source", value=st.session_state.global_src, placeholder="Enter place,state")
                    dest_input = st.text_input("Destination", value=st.session_state.global_dest, placeholder="Enter place,state")
                    st.session_state.global_src, st.session_state.global_dest = src_input, dest_input
                    
                    st.write("---")
                    st.session_state.budget = st.number_input("Max Distance Budget (km)", min_value=1, value=st.session_state.budget)
                    st.session_state.threshold = st.number_input("Category Threshold (n)", min_value=1, value=st.session_state.threshold)
                    
                    st.subheader("Intermediate Sights")
                    num_stops_input = st.number_input("Number of intermediate stops", min_value=0, max_value=15, step=1, value=st.session_state.get("num_stops", 0), key="num_stops_tracker")
                    if num_stops_input != st.session_state.get("num_stops", 0):
                        st.session_state.num_stops = num_stops_input
                        st.rerun()
                        
                    stops_data = []
                    categories_available = ["Transit", "Historical", "Nature", "Religious", "Food", "Entertainment"]
                    
                    if st.session_state.num_stops > 0:
                        for i in range(st.session_state.num_stops):
                            default_txt = st.session_state.stops_storage.get(f"txt_{i}", "")
                            default_scr = st.session_state.stops_storage.get(f"scr_{i}", 1.0)
                            default_cat = st.session_state.stops_storage.get(f"cat_{i}", categories_available[0])
                            
                            st.write(f"**Sight #{i+1}**")
                            r_col1, r_col2, r_col3 = st.columns([2, 1, 2])
                            with r_col1: s_text = st.text_input(f"Name / Address", value=default_txt, key=f"raw_s_txt_{i}")
                            with r_col2: s_score = st.number_input(f"Score", min_value=1, step=1, value=int(default_scr), key=f"raw_s_scr_{i}")
                            with r_col3: s_cat = st.selectbox(f"Category", options=categories_available, index=categories_available.index(default_cat) if default_cat in categories_available else 0, key=f"raw_s_cat_{i}")
                            
                            st.session_state.stops_storage[f"txt_{i}"], st.session_state.stops_storage[f"scr_{i}"], st.session_state.stops_storage[f"cat_{i}"] = s_text, s_score, s_cat
                            if s_text.strip():
                                stops_data.append({"text": s_text, "score": s_score, "category": s_cat, "id": f"Stop_{i}"})
                    
                    if st.button("Compute Real Road Path", type="primary", use_container_width=True):
                        if src_input and dest_input:
                            st.session_state.step_art = 2
                            st.rerun()
                        else:
                            st.error("Please provide both Source and Destination addresses.")

                with col2:
                    st.header("🗺️ Interactive Real-Road Map")
                    st.info("Provide parameter strings on the left panel to execute telemetry lines.")

            elif st.session_state.step_art == 2:
                render_page_header(mode_title, "art_step2", back_target_step_var="step_art", back_target_step_val=1)

                stops_data = []
                for i in range(st.session_state.get("num_stops", 0)):
                    s_text = st.session_state.stops_storage.get(f"txt_{i}", "")
                    s_score = st.session_state.stops_storage.get(f"scr_{i}", 1)
                    s_cat = st.session_state.stops_storage.get(f"cat_{i}", "Transit")
                    if s_text.strip():
                        stops_data.append({"text": s_text, "score": s_score, "category": s_cat, "id": f"Stop_{i}"})

                st.header("🗺️ Interactive Real-Road Map")
                with st.spinner("Calculating driving tracks and live traffic delays..."):
                    src_coords, dest_coords = geocode_address(st.session_state.global_src), geocode_address(st.session_state.global_dest)
                    if src_coords and dest_coords:
                        names_list, coords_list = ["Origin"], [src_coords]
                        algo_intermediates, display_mapping = [], {"Origin": st.session_state.global_src, "Destination": st.session_state.global_dest}
                        
                        for s in stops_data:
                            c = geocode_address(s["text"])
                            if c:
                                names_list.append(s["id"])
                                coords_list.append(c)
                                display_mapping[s["id"]] = s["text"]
                                algo_intermediates.append({"name": s["id"], "score": s["score"], "category": s["category"]})
                                
                        names_list.append("Destination")
                        coords_list.append(dest_coords)
                        
                        traffic_factors = {}
                        traffic_monitoring_data = []
                        
                        for name, coords in zip(names_list, coords_list):
                            tf = fetch_live_traffic_factor(coords[0], coords[1])
                            traffic_factors[name] = tf
                            status_label = "🟢 Smooth" if tf < 1.1 else "🟡 Moderate Delay" if tf < 1.5 else "🔴 Heavy Congestion"
                          
                            if "Stop_" in name:
                                try:
                                    stop_num = int(name.split("_")[1])
                                    display_name = f"Stop_{stop_num + 1}"
                                
                                except (ValueError, IndexError):
                                    display_name = name
                            else:
                                display_name = name

                            traffic_monitoring_data.append({
                                "Point ID": display_name,
                                "Physical Location": display_mapping.get(name, name),
                                "Live Delay Multiplier": f"{tf:.2f}x",
                                "Traffic Status": status_label
                            })
                        st.subheader("📊 Dynamic Real-Time Traffic Monitor")
                        st.table(traffic_monitoring_data)
                        
                        matrix_traffic = fetch_osrm_matrix_segment_specific(coords_list, names_list, traffic_factors)
                        matrix_normal = fetch_osrm_matrix_segment_specific(coords_list, names_list, {k: 1.0 for k in traffic_factors})
                        
                        if matrix_traffic:
                            start_time = time.time()
                            result = run_a("Origin", "Destination", st.session_state.budget, st.session_state.threshold, algo_intermediates, matrix_traffic)
                            runtime = time.time() - start_time
                            
                            if result and len(result.get("route", [])) > 0:
                                normal_distance = 0.0
                                ordered_seq = [node.get('name') if isinstance(node, dict) else node for node in result['route']]
                                for idx in range(len(ordered_seq) - 1):
                                    u, v = ordered_seq[idx], ordered_seq[idx+1]
                                    if u in matrix_normal and v in matrix_normal[u]:
                                        normal_distance += matrix_normal[u][v]
                                
                             base_duration_mins = (normal_distance / 40.0) * 60.0


                             traffic_multiplier = max(1.0, result.get('distance', normal_distance) / max(0.001, normal_distance))
                             traffic_adjusted_duration = base_duration_mins * traffic_multiplier

                             m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                             m_col1.metric("Effective Satisfaction Score", f"{max(0.0, result.get('score', 0.0)):.3f}")
                             m_col2.metric("Traffic-Adjusted Duration", f"{traffic_adjusted_duration:.1f} mins")
                             m_col3.metric("Normal Distance", f"{normal_distance:.2f} km")
                             m_col4.metric("Optimization Runtime", f"{runtime:.4f} sec")
                                
                                formatted_seq = " ➔ ".join([display_mapping.get(nid, nid) for nid in ordered_seq])
                                st.info(f"**Optimized route:** {formatted_seq}")
                                
                                coord_lookup = dict(zip(names_list, coords_list))
                                waypoints = [coord_lookup[node_id] for node_id in ordered_seq if node_id in coord_lookup]
                                
                                m = folium.Map(location=src_coords, zoom_start=11)
                                if len(waypoints) >= 2:
                                    road_lines = fetch_real_road_geometry(waypoints)
                                    if road_lines: folium.PolyLine(road_lines, color="#38bdf8", weight=6).add_to(m)
                                for node_id, latlng in coord_lookup.items():
                                    p_color = "green" if node_id == "Origin" else "red" if node_id == "Destination" else "orange"
                                    folium.Marker(location=latlng, popup=f"{display_mapping.get(node_id)}", icon=folium.Icon(color=p_color)).add_to(m)
                                st.iframe(m._repr_html_(), height=600)
                            else:
                                st.error("No valid paths satisfying the defined satisfaction criteria could be parsed within budget constraints under current traffic.")
                    else:
                        st.error("Geocoding failed. Ensure addresses are precisely written.")

        else: 
            if st.session_state.step_brt == 1:
                render_page_header(mode_title, "brt_step1", back_target_page="hub")
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.header("Parameters")
                    src_input = st.text_input("Source", value=st.session_state.global_src, placeholder="Enter place,state")
                    dest_input = st.text_input("Destination", value=st.session_state.global_dest, placeholder="Enter place,state")
                    st.session_state.global_src, st.session_state.global_dest = src_input, dest_input
                    
                    st.write("---")
                    st.session_state.capacity = st.number_input("Vehicle Max Capacity (Seats)", min_value=1, max_value=8, value=st.session_state.capacity)
                    
                    st.subheader("Passenger Requests")
                    num_requests_input = st.number_input("Number of ride requests to add", min_value=0, max_value=10, step=1, value=st.session_state.get("num_requests", 0), key="num_requests_tracker")
                    if num_requests_input != st.session_state.get("num_requests", 0):
                        st.session_state.num_requests = num_requests_input
                        st.rerun()
                        
                    requests_data = []
                    if st.session_state.num_requests > 0:
                        for i in range(1, st.session_state.num_requests + 1):
                            st.write(f"**Request #{i}**")
                            r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([1,1.8,1.8,1,1.5])
                            r_name = r_col1.text_input(f"ID", value=st.session_state.requests_storage.get(f"name_{i}", f"R{i}"), key=f"p_name_{i}")
                            r_pickup = r_col2.text_input(f"Pickup", value=st.session_state.requests_storage.get(f"pick_{i}", ""), key=f"p_pick_{i}")
                            r_drop = r_col3.text_input(f"Dropoff", value=st.session_state.requests_storage.get(f"drop_{i}", ""), key=f"p_drop_{i}")
                            r_count = r_col4.number_input(f"Seat", min_value=1, max_value=4, value=st.session_state.requests_storage.get(f"count_{i}", 1), key=f"p_cnt_{i}")
                            r_detour = r_col5.number_input(f"Detour(km)", min_value=0, step=1, value=int(st.session_state.requests_storage.get(f"detour_{i}", 15)), key=f"p_detour_{i}")
                            
                            st.session_state.requests_storage[f"name_{i}"] = r_name
                            st.session_state.requests_storage[f"pick_{i}"] = r_pickup
                            st.session_state.requests_storage[f"drop_{i}"] = r_drop
                            st.session_state.requests_storage[f"count_{i}"] = r_count
                            st.session_state.requests_storage[f"detour_{i}"] = r_detour
                            
                            if r_pickup.strip() and r_drop.strip():
                                requests_data.append({"id": i, "name": r_name if r_name.strip() else f"R_{i}", "pickup_text": r_pickup, "drop_text": r_drop, "count": r_count, "max_detour": r_detour})
                    
                    if st.button("Optimize Ride Sharing Route", type="primary", use_container_width=True):
                        if src_input and dest_input:
                            st.session_state.step_brt = 2
                            st.rerun()
                        else:
                            st.error("Please enter starting and terminating terminal points.")

                with col2:
                    st.header("🗺️ Dynamic Ride-Sharing Map")
                    st.info("Provide parameter strings on the left panel to execute telemetry lines.")

            elif st.session_state.step_brt == 2:
                render_page_header(mode_title, "brt_step2", back_target_step_var="step_brt", back_target_step_val=1)

                requests_data = []
                for i in range(1, st.session_state.get("num_requests", 0) + 1):
                    r_name = st.session_state.requests_storage.get(f"name_{i}", "")
                    r_pickup = st.session_state.requests_storage.get(f"pick_{i}", "")
                    r_drop = st.session_state.requests_storage.get(f"drop_{i}", "")
                    r_count = st.session_state.requests_storage.get(f"count_{i}", 1)
                    r_detour = st.session_state.requests_storage.get(f"detour_{i}", 15.0)
                    if r_pickup.strip() and r_drop.strip():
                        requests_data.append({"id": i, "name": r_name if r_name.strip() else f"R{i}", "pickup_text": r_pickup, "drop_text": r_drop, "count": r_count, "max_detour": r_detour})

                st.header("🗺️ Dynamic Ride-Sharing Map")
                with st.spinner("Analyzing pooling tracks and traffic..."):
                    start_time_algo = time.time()
                    src_coords, dest_coords = geocode_address(st.session_state.global_src), geocode_address(st.session_state.global_dest)
                    if src_coords and dest_coords:
                        names_list, coords_list = ["Origin"], [src_coords]
                        display_mapping = {"Origin": st.session_state.global_src, "Destination": st.session_state.global_dest}
                        
                        geocode_failed = False
                        for r in requests_data:
                            p_coords, d_coords = geocode_address(r["pickup_text"]), geocode_address(r["drop_text"])
                            if not p_coords or not d_coords:
                                geocode_failed = True; break
                            p_id, d_id = f"Pickup_{r['id']}", f"Drop_{r['id']}"
                            names_list.extend([p_id, d_id]); coords_list.extend([p_coords, d_coords])
                            display_mapping[p_id] = f"{r['name']} Pickup"; display_mapping[d_id] = f"{r['name']} Drop"
                            
                        if not geocode_failed:
                            names_list.append("Destination"); coords_list.append(dest_coords)
                            
                            traffic_factors = {}
                            traffic_monitoring_data = []
                            for name, coords in zip(names_list, coords_list):
                                tf = fetch_live_traffic_factor(coords[0], coords[1])
                                traffic_factors[name] = tf
                                status_label = "🟢 Smooth" if tf < 1.1 else "🟡 Moderate Delay" if tf < 1.5 else "🔴 Heavy Congestion"
                                traffic_monitoring_data.append({
                                    "Route Point": name,
                                    "Physical Location": display_mapping.get(name, name),
                                    "Coordinates": f"{coords[0]:.5f}, {coords[1]:.5f}",
                                    "Live Traffic Factor": f"{tf:.2f}x",
                                    "Traffic Status": status_label
                                })
                            
                            st.subheader("📊 Dynamic Real-Time Traffic Monitor")
                            st.table(traffic_monitoring_data)
                            
                            matrix_traffic = fetch_osrm_matrix_segment_specific(coords_list, names_list, traffic_factors)
                            matrix_normal = fetch_osrm_matrix_segment_specific(coords_list, names_list, {k: 1.0 for k in traffic_factors})
                            
                            if matrix_traffic:
                                result = run_b("Origin", "Destination", requests_data, st.session_state.capacity, matrix_traffic)
                                runtime_algo = time.time() - start_time_algo
                                
                                if result and result.get("status") == "Accepted":
                                    normal_distance = 0.0
                                    for idx in range(len(result["route"]) - 1):
                                        u, v = result["route"][idx], result["route"][idx+1]
                                        if u in matrix_normal and v in matrix_normal[u]:
                                            normal_distance += matrix_normal[u][v]
                                    
                                    base_duration_mins = (normal_distance / 40.0) * 60.0


                                    traffic_multiplier = max(1.0, result.get('distance', normal_distance) / max(0.001, normal_distance))
                                    traffic_adjusted_duration = base_duration_mins * traffic_multiplier

                                     m_col1, m_col2, m_col3 = st.columns(3)
                                     m_col1.metric("Traffic-Adjusted Duration", f"{traffic_adjusted_duration:.1f} mins")
                                     m_col2.metric("Normal Distance", f"{normal_distance:.2f} km")
                                     m_col3.metric("Algorithm Run Time", f"{runtime_algo:.4f} sec")
                                    
                                    formatted_seq = " ➔ ".join([display_mapping.get(nid, nid) for nid in result["route"]])
                                    st.info(f"**Optimized Ride Sharing Pathway:** {formatted_seq}")
                                    
                                    st.subheader("Passenger Count Table")
                                    clean_logs = []
                                    for entry in result["passenger_logs"]:
                                        clean_logs.append({
                                            "Location": display_mapping.get(entry["Location"], entry["Location"]),
                                            "Passengers": entry["Passengers"]
                                        })
                                    st.table(clean_logs)
                                    
                                    m = folium.Map(location=src_coords, zoom_start=11)
                                    coord_lookup = dict(zip(names_list, coords_list))
                                    waypoints = [coord_lookup[nid] for nid in result["route"] if nid in coord_lookup]
                                    
                                    if len(waypoints) >= 2:
                                        lines = fetch_real_road_geometry(waypoints)
                                        if lines: folium.PolyLine(lines, color="#818cf8", weight=6).add_to(m)
                                    for node_id, latlng in coord_lookup.items():
                                        folium.Marker(location=latlng, popup=display_mapping.get(node_id)).add_to(m)
                                    st.iframe(m._repr_html_(), height=600)
                                else: 
                                    if "exceeded at" in result.get('message', ''):
                                        st.error("exceeded the capacity")
                                    else:
                                        st.error(f"Rejected: {result.get('message')}")
                        else: st.error("Some intermediate route location lookups timed out.")

  
    elif st.session_state.app_mode == "general":
        from part_a import find_all_valid_routes_part_a
        from part_b import find_optimal_global_route
        
        app_mode_gen = st.sidebar.radio("General Mode Sub-Selection", ["Sightseeing Route Optimization", "Dynamic Ride Sharing with Flexible Routing"])
        
        if app_mode_gen == "Sightseeing Route Optimization":
            if st.session_state.step_ag == 1:
                render_page_header(mode_title, "gen_a_step1", back_target_page="hub")
                
                col1, col2 = st.columns(2)
                budget = col1.number_input("Budget (km)", min_value=1, value=st.session_state.get("s_b", 20))
                threshold = col2.number_input("Threshold (n)", min_value=1, value=st.session_state.get("s_t", 1))
                t1, t2 = st.columns(2)
                start_node = t1.text_input("Start Node", value=st.session_state.get("s_s", "start"),placeholder="eg. Start")
                end_node = t2.text_input("End Node", value=st.session_state.get("s_e", "end"),placeholder="eg. End")
                
                st.write("#### Add Intermediate Stops")
                
                num_stops_gen = st.number_input("Number of Intermediate Stops", min_value=0, max_value=15, step=1, value=st.session_state.get("stops_count_ag", 1))
                if num_stops_gen != st.session_state.get("stops_count_ag", 1):
                    st.session_state.stops_count_ag = num_stops_gen
                    st.rerun()

                locations_list = []
                saved_locs = st.session_state.get("s_locs", [])
                
                for i in range(st.session_state.stops_count_ag):
                    r1, r2, r3 = st.columns(3)
                    
                    d_name = saved_locs[i]["name"] if i < len(saved_locs) else ""
                    d_score = saved_locs[i]["score"] if i < len(saved_locs) else 10
                    d_cat = saved_locs[i]["category"] if i < len(saved_locs) else "Food"
                    
                    name = r1.text_input(f"Stop #{i+1} Name", value=d_name, key=f"g_aname_{i}")
                    score = r2.number_input(f"Score", min_value=0, value=int(d_score), key=f"g_ascore_{i}")
                    category = r3.selectbox(f"Category", ["Food", "Historical", "Nature"], index=["Food", "Historical", "Nature"].index(d_cat), key=f"g_acat_{i}")
                    if name.strip(): locations_list.append({"name": name.strip(), "score": score, "category": category})
                    
                if st.button("Distance Matrix ➡️", type="primary", use_container_width=True):
                    st.session_state.s_b, st.session_state.s_t = budget, threshold
                    st.session_state.s_s, st.session_state.s_e = start_node, end_node
                    st.session_state.s_locs = locations_list
                    st.session_state.raw_matrix_ag = {} 
                    st.session_state.step_ag = 2; st.rerun()

            elif st.session_state.step_ag == 2:
                render_page_header(mode_title, "gen_a_step2", back_target_step_var="step_ag", back_target_step_val=1)
                    
                all_nodes = [st.session_state.s_s] + [l["name"] for l in st.session_state.s_locs] + [st.session_state.s_e]
                n = len(all_nodes)
                
                current_matrix = st.session_state.raw_matrix_ag
                is_matrix_valid = (
                    isinstance(current_matrix, dict) and 
                    all(node in current_matrix for node in all_nodes) and 
                    all(all(v in current_matrix[u] for v in all_nodes) for u in all_nodes)
                )
                
                if not is_matrix_valid:
                    raw_matrix = {u: {v: 0 for v in all_nodes} for u in all_nodes}
                else:
                    raw_matrix = current_matrix
                
                st.info("Fill out connection weights between nodes:")
                for i in range(n):
                    cols = st.columns(n)
                    for j in range(n):
                        u, v = all_nodes[i], all_nodes[j]
                        if i == j: cols[j].text_input(f"{u}→{v}", "0", disabled=True, key=f"g_ma_{i}_{j}")
                        elif j > i:
                            old_val = raw_matrix.get(u, {}).get(v, 5)
                            val = cols[j].number_input(f"{u}→{v}", min_value=0, step=1, value=int(old_val), key=f"g_ma_{i}_{j}")
                            raw_matrix[u][v] = raw_matrix[v][u] = int(val)
                        else: cols[j].text_input(f"{u}→{v}", str(raw_matrix[v][u]), disabled=True, key=f"g_ma_{i}_{j}")
                        
                if st.button("Compute Combinatorial Route Paths", type="primary", use_container_width=True):
                    st.session_state.raw_matrix_ag = raw_matrix
                    st.session_state.step_ag = 3; st.rerun()

            elif st.session_state.step_ag == 3:
                render_page_header(mode_title, "gen_a_step3", back_target_step_var="step_ag", back_target_step_val=2)
                    
                res = find_all_valid_routes_part_a(
                    st.session_state.s_s, 
                    st.session_state.s_e, 
                    st.session_state.s_b, 
                    st.session_state.s_t, 
                    st.session_state.s_locs, 
                    st.session_state.raw_matrix_ag
                )
                
                if res:
                    st.success("🎉 Optimal sequences discovered successfully!")
                    
                    best_route_data = res[0]
                    best_dist = (
                        best_route_data.get('Total Distance (km)') or 
                        best_route_data.get('Total Distance') or 
                        best_route_data.get('Distance') or 
                        best_route_data.get('cost') or 0
                    )
                    best_score = (
                        best_route_data.get('Total Score') or 
                        best_route_data.get('Score') or 
                        best_route_data.get('score') or 0
                    )
                    best_seq = best_route_data.get('Route Sequence') or best_route_data.get('route')
                    
                    m_col1, m_col2 = st.columns(2)
                    with m_col1:
                        st.markdown(f"""
                        <div style='background: rgba(129, 140, 248, 0.1); border: 1px solid #818cf8; padding: 1rem; border-radius: 8px; text-align: center;'>
                            <span style='color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;'>Total Distance</span>
                            <h2 style='margin: 0; color: #818cf8;'>{best_dist} km</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    with m_col2:
                        st.markdown(f"""
                        <div style='background: rgba(129, 140, 248, 0.1); border: 1px solid #818cf8; padding: 1rem; border-radius: 8px; text-align: center;'>
                            <span style='color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;'>Total Score</span>
                            <h2 style='margin: 0; color: #818cf8;'>{best_score:.3f}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.write("")
                    formatted_seq = ' ➔ '.join(map(str, best_seq)) if isinstance(best_seq, list) else best_seq
                    st.info(f"**Route:** {formatted_seq}")
                    
                    st.markdown("---")
                    st.markdown("### 🔄 Routes with the Same Distance")
                    
                    def get_route_dist(r):
                        return r.get('Total Distance (km)') or r.get('Total Distance') or r.get('Distance') or r.get('cost')
                    
                    matching_distance_routes = [r for r in res if get_route_dist(r) == best_dist]
                    
                    if len(matching_distance_routes) > 1:
                        st.caption(f"Found {len(matching_distance_routes)} pathway variations matching the target profile:")
                        st.table(matching_distance_routes)
                    else:
                        st.caption("No variations found. This path features a unique optimal distance profile constraint.")
                        st.table([best_route_data])
                        
                    st.markdown("---")
                    st.markdown("### 📋 All Valid Permutations")
                    st.table(res)
                else: 
                    st.error("No valid route permutations satisfy your budget constraints.")

        elif app_mode_gen == "Dynamic Ride Sharing with Flexible Routing":
            if st.session_state.step_bg == 1:
                render_page_header(mode_title, "gen_b_step1", back_target_page="hub")
                
                col1, col2 = st.columns(2)
                start_node = col1.text_input("Start Node", value=st.session_state.get("bg_start", "S"))
                end_node = col2.text_input("End Node", value=st.session_state.get("bg_end", "E"))
                
                c1, c2 = st.columns(2)
                capacity = c1.number_input("Vehicle Capacity", min_value=1, value=st.session_state.get("bg_cap", 2))
                
                num_requests_gen = c2.number_input("Number of Requests", min_value=0, max_value=15, step=1, value=st.session_state.get("num_requests_bg", 2))
                if num_requests_gen != st.session_state.get("num_requests_bg", 2):
                    st.session_state.num_requests_bg = num_requests_gen
                    st.rerun()
                
                st.write("#### Dynamic Requests Configuration")
                requests_list = []
                saved_reqs = st.session_state.get("saved_bg_requests", [])
                
                for i in range(1, st.session_state.get("num_requests_bg", 2) + 1):
                    r_cols = st.columns(4)
                    d_p = saved_reqs[i-1]["pickup"] if (i-1) < len(saved_reqs) else f"P{i}"
                    d_d = saved_reqs[i-1]["dropoff"] if (i-1) < len(saved_reqs) else f"D{i}"
                    d_flex = saved_reqs[i-1]["flexibility"] if (i-1) < len(saved_reqs) else 15
                    d_dist = saved_reqs[i-1]["base_distance"] if (i-1) < len(saved_reqs) else 5
                    
                    p_label = r_cols[0].text_input(f"Pickup", value=d_p, key=f"g_p_{i}")
                    d_label = r_cols[1].text_input(f"Dropoff", value=d_d, key=f"g_d_{i}")
                    
                    flex_val = r_cols[2].number_input(f"Flexibility", min_value=0, step=1, value=int(d_flex), key=f"g_flex_{i}")
                    dist_val = r_cols[3].number_input(f"Base Distance", min_value=0, step=1, value=int(d_dist), key=f"g_dist_{i}")
                    
                    if p_label.strip() and d_label.strip():
                        requests_list.append({"pickup": p_label.strip(), "dropoff": d_label.strip(), "flexibility": flex_val, "base_distance": dist_val})
                    
                if st.button("Distance Matrix ➡️", type="primary", use_container_width=True):
                    st.session_state.bg_start, st.session_state.bg_end = start_node, end_node
                    st.session_state.bg_cap, st.session_state.saved_bg_requests = capacity, requests_list
                    st.session_state.raw_matrix_bg = {}
                    st.session_state.step_bg = 2
                    st.rerun()

            elif st.session_state.step_bg == 2:
                render_page_header(mode_title, "gen_b_step2", back_target_step_var="step_bg", back_target_step_val=1)
                    
                all_nodes = [st.session_state.bg_start]
                for r in st.session_state.saved_bg_requests: 
                    all_nodes.extend([r["pickup"], r["dropoff"]])
                all_nodes.append(st.session_state.bg_end)
                all_nodes = list(dict.fromkeys(all_nodes))
                
                n = len(all_nodes)
                
                current_matrix = st.session_state.get("raw_matrix_bg", {})
                is_matrix_valid = (
                    isinstance(current_matrix, dict) and 
                    all(node in current_matrix for node in all_nodes) and 
                    all(all(v in current_matrix[u] for v in all_nodes) for u in all_nodes)
                )
                
                if not is_matrix_valid:
                    raw_matrix = {u: {v: 0 for v in all_nodes} for u in all_nodes}
                else:
                    raw_matrix = current_matrix
                
                st.info("Fill out the connection weights between nodes:")
                for i in range(n):
                    cols = st.columns(n)
                    for j in range(n):
                        u, v = all_nodes[i], all_nodes[j]
                        if i == j: 
                            cols[j].text_input(f"{u}→{v}", "0", disabled=True, key=f"g_mb_{i}_{j}")
                        elif j > i:
                            old_val = raw_matrix.get(u, {}).get(v, 6)
                            val = cols[j].number_input(f"{u}→{v}", min_value=0, step=1, value=int(old_val), key=f"g_ma_{i}_{j}")
                            raw_matrix[u][v] = raw_matrix[v][u] = int(val)
                        else: 
                            cols[j].text_input(f"{u}→{v}", str(raw_matrix[v][u]), disabled=True, key=f"g_mb_{i}_{j}")
                        
                if st.button("Run Simulation Tracker Matrix", type="primary", use_container_width=True):
                    st.session_state.raw_matrix_bg = raw_matrix
                    st.session_state.step_bg = 3
                    st.rerun()

            elif st.session_state.step_bg == 3:
                render_page_header(mode_title, "gen_b_step3", back_target_step_var="step_bg", back_target_step_val=2)
                
             
                start_time_gen = time.time() 
                
                opt = find_optimal_global_route(
                    st.session_state.bg_start, 
                    st.session_state.bg_end, 
                    st.session_state.saved_bg_requests, 
                    st.session_state.bg_cap, 
                    st.session_state.raw_matrix_bg
                )
                
                runtime_gen = time.time() - start_time_gen 
                
                if opt:
                    st.success("Optimal pooling combinations parsed successfully.")
                    
                    m_col1, m_col2 = st.columns(2)
                    m_col1.metric("Total Travel Distance", f"{opt['distance']} km")
                    m_col2.metric("Algorithm Runtime", f"{runtime_gen:.4f} sec")
                    
                    formatted_seq = " ➔ ".join(opt['route'])
                    st.info(f"**Route:** {formatted_seq}")
                    
                    st.subheader("Passenger Count Table")
                    passenger_logs = []
                    current_passengers = 0
                    
                    pickups = [r["pickup"] for r in st.session_state.saved_bg_requests]
                    drops = [r["dropoff"] for r in st.session_state.saved_bg_requests]
                    
                    for node in opt['route']:
                        if node in pickups:
                            current_passengers += 1
                        elif node in drops:
                            current_passengers -= 1
                        passenger_logs.append({"Location": node, "Passengers": current_passengers})
                        
                    st.table(passenger_logs)
                else: 
                    st.error("No legally permitted passenger execution path exists under current capacity or detour limits.")
               
