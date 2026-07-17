# PathMatrix_SOI_2026

---

## Overview

PathMatrix is an intelligent route optimization platform that combines graph algorithms with real-world geospatial routing. It provides optimized solutions for sightseeing route planning and dynamic ride-sharing through two specialized routing engines.

---

## Problem Statement

### Part A: Sightseeing Route Optimization

Design an intelligent sightseeing route planner that identifies the best path between a start and destination while selecting suitable intermediate attractions. The system considers travel distance, attraction satisfaction, and category diversity to generate an optimized itinerary.

### Part B: Dynamic Ride Sharing with Flexible Routing

Develop a dynamic ride-sharing system that efficiently integrates new ride requests into an existing route while satisfying pickup, drop-off, and maximum detour constraints.

---

## Our Approach

PathMatrix is built around two intelligent routing engines that solve optimization problems on both custom graphs and real-world road networks.

### Real-Time Geospatial Engine

The Real-Time Geospatial Engine uses **OpenStreetMap (OSM)** and the **TomTom Routing API** to compute realistic driving routes with traffic-aware travel distances. The optimized path is visualized on an interactive map for easy analysis.

### General Matrix Engine

The General Matrix Engine models locations as a weighted graph and applies graph algorithms to evaluate possible routes. It selects the optimal path by considering distance, routing constraints, and overall efficiency.

---

## Key Technologies

- Python
- Streamlit
- Graph Algorithms
- OpenStreetMap (OSM)
- TomTom Routing API
- Folium (Interactive Maps)
- Custom CSS

---

## Live Demo

🔗 **PathMatrix Web App:**  
https://soi2026-pathmatrix.streamlit.app/


---

## Team
- Greedy Solvers






