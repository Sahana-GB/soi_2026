import streamlit as st
import folium
import requests
import sys
import os
import time
from geopy.geocoders import Nominatim

# Configuration setup for Streamlit layout
st.set_page_config(page_title="PathMatrix Planner - OSRM Engine", layout="wide")

# Workspace path overrides
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from part_a import run_a
from part_b import run_b 

# --- PERSISTENT SESSION STATE INITIALIZATION ---
if "global_src" not in st.session_state:
    st.session_state.global_src = "IIT Dharwad"
if "global_dest" not in st.session_state:
    st.session_state.global_dest = "Hubli Junction"

# Module 1 Data Cache (Sightseeing)
if "budget" not in st.session_state:
    st.session_state.budget = 100.0
if "threshold" not in st.session_state:
    st.session_state.threshold = 2
if "num_stops" not in st.session_state:
    st.session_state.num_stops = 2
if "stops_storage" not in st.session_state:
    st.session_state.stops_storage = {}

# Module 2 Data Cache (Ride Sharing)
if "capacity" not in st.session_state:
    st.session_state.capacity = 4
if "flexibility" not in st.session_state:
    st.session_state.flexibility = 20.0
if "num_requests" not in st.session_state:
    st.session_state.num_requests = 1
if "requests_storage" not in st.session_state:
    st.session_state.requests_storage = {}


# --- SIDEBAR INTERFACE CONTROL ---
st.sidebar.title("🎮 Dashboard Control")

# Master Control Reset Trigger
if st.sidebar.button("🏁 Start New Search", type="primary", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.write("---")
module = st.sidebar.radio("Select System Module", ["Sightseeing Route Optimization", "Dynamic Ride Sharing"])


st.title("🗺️ PathMatrix: Intelligent Route Planning Dashboard")
st.caption("IIT Dharwad — Unified Innovation Project Pipeline (Local OSRM Active)")

# --- FREE LOCAL INTEGRATION UTILITIES ---

def geocode_address(address_text: str):
    if not address_text or address_text.strip() == "":
        return None
    try:
        geolocator = Nominatim(user_agent="iit_dharwad_pathmatrix_application_final_v4")
        query = address_text.strip()
        if "dharwad" not in query.lower() and "hubli" not in query.lower() and "karnataka" not in query.lower():
            query += ", Dharwad, Karnataka, India"
            
        location = geolocator.geocode(query, timeout=6)
        if location:
            return [location.latitude, location.longitude]
            
        location = geolocator.geocode(address_text, timeout=6)
        if location:
            return [location.latitude, location.longitude]
    except Exception:
        pass
    return None

def fetch_real_road_geometry(route_coordinates):
    coord_string = ";".join([f"{c[1]},{c[0]}" for c in route_coordinates])
    url = f"http://localhost:5000/route/v1/driving/{coord_string}?overview=full&geometries=geojson"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            geometry = response.json()['routes'][0]['geometry']['coordinates']
            return [[point[1], point[0]] for point in geometry]
    except Exception:
        pass
    return route_coordinates

def fetch_osrm_matrix(coordinates, names):
    coord_string = ";".join([f"{c[1]},{c[0]}" for c in coordinates])
    url = f"http://localhost:5000/table/v1/driving/{coord_string}?annotations=distance"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            raw_matrix = response.json()["distances"]
            matrix = {}
            for i, row_name in enumerate(names):
                matrix[row_name] = {}
                for j, col_name in enumerate(names):
                    matrix[row_name][col_name] = round(raw_matrix[i][j] / 1000.0, 3)
            return matrix
    except Exception:
        pass
    return None

# --- MAIN APPLICATION DASHBOARD LAYOUT ---

if module == "Sightseeing Route Optimization":
    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("🏁 Route Parameters")
        src_input = st.text_input("Source Location", value=st.session_state.global_src)
        dest_input = st.text_input("Destination Location", value=st.session_state.global_dest)
        
        st.session_state.global_src = src_input
        st.session_state.global_dest = dest_input
        
        st.write("---")
        st.session_state.budget = st.number_input("Max Distance Budget (km)", min_value=1.0, value=st.session_state.budget)
        st.session_state.threshold = st.number_input("Category Threshold (n)", min_value=1, value=st.session_state.threshold)
        
        st.subheader("📍 Intermediate Sights")
            
        stops_data = []
        categories_available = ["Transit", "Historical", "Nature", "Religious", "Food", "Entertainment"]
        
        for i in range(st.session_state.num_stops):
            default_txt = st.session_state.stops_storage.get(f"txt_{i}", "Hubli Airport" if i==0 else "Nrupatunga Betta")
            default_scr = st.session_state.stops_storage.get(f"scr_{i}", 5.0)
            default_cat = st.session_state.stops_storage.get(f"cat_{i}", "Transit" if i==0 else "Historical")
            
            if default_cat not in categories_available:
                default_cat = categories_available[0]

            with st.expander(f"Sight Location #{i+1}", expanded=True):
                s_text = st.text_input(f"Name of Place #{i+1}", value=default_txt, key=f"raw_s_txt_{i}")
                s_score = st.number_input(f"Satisfaction Score #{i+1}", min_value=1.0, value=default_scr)
                s_cat = st.selectbox(f"Category Label #{i+1}", options=categories_available, index=categories_available.index(default_cat))
                
                st.session_state.stops_storage[f"txt_{i}"] = s_text
                st.session_state.stops_storage[f"scr_{i}"] = s_score
                st.session_state.stops_storage[f"cat_{i}"] = s_cat

                if s_text:
                    stops_data.append({"text": s_text, "score": s_score, "category": s_cat, "id": f"Stop_{i+1}"})

        b1, b2 = st.columns(2)
        with b1:
            if st.button("➕ Add Stop Slot"):
                st.session_state.num_stops += 1
                st.rerun()
        with b2:
            if st.button("➖ Remove Last Slot") and st.session_state.num_stops > 1:
                idx = st.session_state.num_stops - 1
                st.session_state.stops_storage.pop(f"txt_{idx}", None)
                st.session_state.stops_storage.pop(f"scr_{idx}", None)
                st.session_state.stops_storage.pop(f"cat_{idx}", None)
                st.session_state.num_stops -= 1
                st.rerun()

        st.write("---")
        compute_a = st.button("Compute Real Road Path", type="primary")

    with col2:
        st.header("🗺️ Interactive Real-Road Routing Map")
        
        if compute_a:
            if not src_input or not dest_input:
                st.error("Please provide both a Source and a Destination address.")
            else:
                with st.spinner("Connecting to local OSRM server and calculating driving tracks..."):
                    src_coords = geocode_address(src_input)
                    dest_coords = geocode_address(dest_input)
                    
                    if not src_coords or not dest_coords:
                        st.error("Could not geocode main endpoint pins.")
                    else:
                        names_list = ["Origin"]
                        coords_list = [src_coords]
                        algo_intermediates = []
                        display_mapping = {"Origin": src_input, "Destination": dest_input}
                        
                        for s in stops_data:
                            c = geocode_address(s["text"])
                            if c:
                                names_list.append(s["id"])
                                coords_list.append(c)
                                display_mapping[s["id"]] = s["text"]
                                algo_intermediates.append({"name": s["id"], "score": s["score"], "category": s["category"]})
                                
                        names_list.append("Destination")
                        coords_list.append(dest_coords)
                        
                        matrix = fetch_osrm_matrix(coords_list, names_list)
                        
                        if matrix:
                            start_time = time.time()
                            result = run_a("Origin", "Destination", st.session_state.budget, st.session_state.threshold, algo_intermediates, matrix)
                            runtime = time.time() - start_time

                            if not result or "route" not in result or len(result.get("route", [])) == 0:
                                st.error("❌ Route Optimization Failed! No paths match constraints.")
                            else:
                                m_col1, m_col2, m_col3 = st.columns(3)
                                m_col1.metric("Effective Satisfaction Score", f"{max(0.0, result.get('score', 0.0)):.2f}")
                                m_col2.metric("Real-Road Total Distance", f"{result.get('distance', 0.0):.2f} km")
                                m_col3.metric("Optimization Runtime", f"{runtime:.4f} sec")

                                cleaned_route = []
                                for s in result.get('route', []):
                                    cleaned_route.append(str(s.get('name', '')) if isinstance(s, dict) else str(s))
                                
                                ordered_seq = ["Origin"] + [node for node in cleaned_route if node not in ("Origin", "Destination") and node] + ["Destination"]
                                coord_lookup = dict(zip(names_list, coords_list))
                                waypoints = [coord_lookup[node_id] for node_id in ordered_seq if node_id in coord_lookup]

                                m = folium.Map(location=src_coords, zoom_start=11)
                                if len(waypoints) >= 2:
                                    road_lines = fetch_real_road_geometry(waypoints)
                                    if road_lines:
                                        folium.PolyLine(road_lines, color="#0066cc", weight=6, opacity=0.8).add_to(m)

                                for node_id, latlng in coord_lookup.items():
                                    p_color = "green" if node_id == "Origin" else "red" if node_id == "Destination" else "orange"
                                    popup_text = f"{node_id}: {display_mapping.get(node_id)}"
                                    folium.Marker(location=latlng, popup=popup_text, icon=folium.Icon(color=p_color)).add_to(m)

                                st.components.v1.html(m._repr_html_(), height=600, scrolling=False)
        else:
            st.info("Provide your itinerary items on the left side and press 'Compute Real Road Path'.")
else:
    # --- MODULE 2: DYNAMIC RIDE SHARING ---
    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("🚗 Ride Sharing Parameters")
        src_input = st.text_input("Vehicle Start Location (Origin)", value=st.session_state.global_src)
        dest_input = st.text_input("Vehicle End Location (Destination)", value=st.session_state.global_dest)
        
        st.session_state.global_src = src_input
        st.session_state.global_dest = dest_input
        
        st.write("---")
        st.session_state.capacity = st.number_input("Vehicle Max Capacity (Seats)", min_value=1, max_value=8, value=st.session_state.capacity)
        st.session_state.flexibility = st.number_input("Flexibility Margin (Max Extra km)", min_value=0.0, value=st.session_state.flexibility)
        
        st.subheader("👥 Passenger Requests")
            
        requests_data = []
        for i in range(st.session_state.num_requests):
            default_pname = st.session_state.requests_storage.get(f"name_{i}", f"Passenger_{i+1}")
            default_p_up  = st.session_state.requests_storage.get(f"pick_{i}", "Hubli Airport")
            default_p_dn  = st.session_state.requests_storage.get(f"drop_{i}", "Nrupatunga Betta")
            default_p_cnt = st.session_state.requests_storage.get(f"count_{i}", 1)

            with st.expander(f"Passenger Request #{i+1}", expanded=True):
                r_name = st.text_input(f"Passenger Name / ID #{i+1}", value=default_pname)
                r_pickup = st.text_input(f"Pickup Location #{i+1}", value=default_p_up)
                r_drop = st.text_input(f"Drop Location #{i+1}", value=default_p_dn)
                r_count = st.number_input(f"Passenger Count #{i+1}", min_value=1, max_value=4, value=default_p_cnt)
                
                st.session_state.requests_storage[f"name_{i}"] = r_name
                st.session_state.requests_storage[f"pick_{i}"] = r_pickup
                st.session_state.requests_storage[f"drop_{i}"] = r_drop
                st.session_state.requests_storage[f"count_{i}"] = r_count

                if r_pickup and r_drop:
                    requests_data.append({
                        "id": i+1, "name": r_name, "pickup_text": r_pickup, "drop_text": r_drop, "count": r_count
                    })

        rb1, rb2 = st.columns(2)
        with rb1:
            if st.button("➕ Add Ride Request"):
                st.session_state.num_requests += 1
                st.rerun()
        with rb2:
            if st.button("➖ Remove Last Request") and st.session_state.num_requests > 1:
                idx = st.session_state.num_requests - 1
                st.session_state.requests_storage.pop(f"name_{idx}", None)
                st.session_state.requests_storage.pop(f"pick_{idx}", None)
                st.session_state.requests_storage.pop(f"drop_{idx}", None)
                st.session_state.requests_storage.pop(f"count_{idx}", None)
                st.session_state.num_requests -= 1
                st.rerun()

        st.write("---")
        compute_b = st.button("Optimize Ride Sharing Route", type="primary")

    with col2:
        st.header("🗺️ Dynamic Ride-Sharing Routing Map")
        
        if compute_b:
            if not src_input or not dest_input or not requests_data:
                st.error("Please fill out all required location parameters.")
            else:
                with st.spinner("Analyzing request matrix combinations..."):
                    src_coords = geocode_address(src_input)
                    dest_coords = geocode_address(dest_input)
                    
                    if not src_coords or not dest_coords:
                        st.error("Could not geocode main endpoint lines.")
                    else:
                        names_list = ["Origin"]
                        coords_list = [src_coords]
                        display_mapping = {"Origin": src_input, "Destination": dest_input}
                        
                        # Extract active sightseeing stops
                        sightseeing_node_ids = []
                        for idx in range(st.session_state.num_stops):
                            stop_name = st.session_state.stops_storage.get(f"txt_{idx}")
                            if stop_name:
                                stop_coords = geocode_address(stop_name)
                                if stop_coords:
                                    s_id = f"Stop_{idx+1}"
                                    names_list.append(s_id)
                                    coords_list.append(stop_coords)
                                    display_mapping[s_id] = f"Sightseeing Stop: {stop_name}"
                                    sightseeing_node_ids.append(s_id)

                        # Append Ride Share Requests Coordinates
                        geocode_failed = False
                        for r in requests_data:
                            p_coords = geocode_address(r["pickup_text"])
                            d_coords = geocode_address(r["drop_text"])
                            
                            if not p_coords or not d_coords:
                                st.error(f"Failed to geocode paths for {r['name']}.")
                                geocode_failed = True
                                break
                                
                            p_id, d_id = f"Pickup_{r['id']}", f"Drop_{r['id']}"
                            names_list.extend([p_id, d_id])
                            coords_list.extend([p_coords, d_coords])
                            
                            display_mapping[p_id] = f"{r['name']} Pickup: {r['pickup_text']}"
                            display_mapping[d_id] = f"{r['name']} Drop-off: {r['drop_text']}"
                        
                        if not geocode_failed:
                            names_list.append("Destination")
                            coords_list.append(dest_coords)
                            
                            matrix = fetch_osrm_matrix(coords_list, names_list)
                            
                            if matrix:
                                start_time = time.time()
                                result = run_b("Origin", "Destination", requests_data, st.session_state.capacity, st.session_state.flexibility, matrix)
                                runtime = time.time() - start_time
                                
                                if result and result.get("status") == "Accepted":
                                    st.success("✅ Optimized Pool Route Matches Targets!")
                                    
                                    m_col1, m_col2, m_col3 = st.columns(3)
                                    m_col1.metric("Total Route Distance", f"{result['distance']:.2f} km")
                                    m_col2.metric("Extra Distance Added", f"{result['added_distance']:.2f} km")
                                    m_col3.metric("Solver Runtime", f"{runtime:.4f} sec")
                                    
                                    raw_route = result["route"]
                                    coord_lookup = dict(zip(names_list, coords_list))
                                    
                                    m = folium.Map(location=src_coords, zoom_start=10)
                                    
                                    # --- CONNECT ALL NODES SEAMLESSLY ---
                                    # We inject the sightseeing stops into the drawing sequence 
                                    # right after 'Origin' so OSRM links them on the map trace.
                                    full_mapping_sequence = []
                                    if raw_route and len(raw_route) > 0:
                                        full_mapping_sequence.append(raw_route[0]) # Origin
                                        
                                        # Add sightseeing locations in order
                                        for sid in sightseeing_node_ids:
                                            if sid not in full_mapping_sequence:
                                                full_mapping_sequence.append(sid)
                                                
                                        # Add the remaining passenger pickups/drops and destination
                                        for node in raw_route[1:]:
                                            if node not in full_mapping_sequence:
                                                full_mapping_sequence.append(node)
                                    else:
                                        full_mapping_sequence = names_list
                                    
                                    waypoints = [coord_lookup[nid] for nid in full_mapping_sequence if nid in coord_lookup]
                                    if len(waypoints) >= 2:
                                        road_lines = fetch_real_road_geometry(waypoints)
                                        if road_lines:
                                            folium.PolyLine(road_lines, color="#7030a0", weight=6, opacity=0.85).add_to(m)
                                            
                                    for node_id, latlng in coord_lookup.items():
                                        if node_id == "Origin":
                                            p_color, p_icon = "green", "play"
                                        elif node_id == "Destination":
                                            p_color, p_icon = "red", "stop"
                                        elif "Pickup" in node_id:
                                            p_color, p_icon = "blue", "user"
                                        elif "Drop" in node_id:
                                            p_color, p_icon = "cadetblue", "home"
                                        else:
                                            p_color, p_icon = "orange", "info-sign"
                                            
                                        folium.Marker(
                                            location=latlng,
                                            popup=display_mapping.get(node_id, node_id),
                                            icon=folium.Icon(color=p_color, icon=p_icon)
                                        ).add_to(m)
                                        
                                    st.components.v1.html(m._repr_html_(), height=600, scrolling=False)
                                else:
                                    msg = result.get('message', 'Constraints violated') if result else 'Calculation issue'
                                    st.error(f"❌ Route Request Rejected! {msg}")
                            else:
                                st.error("OSRM matrix unreachable. Please check Docker on Port 5000.")
        else:
            st.info("Input your passenger pooling parameters on the left side and press 'Optimize Ride Sharing Route'.")
