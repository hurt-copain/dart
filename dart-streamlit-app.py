import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import folium_static
from dataclasses import dataclass
from typing import List, Dict, Tuple
import time

# Data structures
@dataclass
class Location:
    latitude: float
    longitude: float

@dataclass
class BusStop:
    id: str
    location: Location
    demand: int = 0
    total_served: int = 0

@dataclass
class Bus:
    id: str
    location: Location
    capacity: int
    passengers: int = 0
    route: List[str] = None

class DARTSystem:
    def __init__(self):
        self.stops: Dict[str, BusStop] = {}
        self.buses: Dict[str, Bus] = {}
        self.colors = ['red', 'green', 'blue', 'orange', 'purple']
        
    def add_stop(self, stop_id: str, latitude: float, longitude: float):
        self.stops[stop_id] = BusStop(
            id=stop_id,
            location=Location(latitude, longitude)
        )
        
    def add_bus(self, bus_id: str, latitude: float, longitude: float, capacity: int):
        self.buses[bus_id] = Bus(
            id=bus_id,
            location=Location(latitude, longitude),
            capacity=capacity
        )
        
    def _calculate_distance(self, loc1: Location, loc2: Location) -> float:
        R = 6371
        lat1, lon1 = np.radians([loc1.latitude, loc1.longitude])
        lat2, lon2 = np.radians([loc2.latitude, loc2.longitude])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        return 2 * R * np.arcsin(np.sqrt(a))
    
    def find_optimal_route(self, bus_id: str, max_stops: int = 5) -> List[str]:
        bus = self.buses[bus_id]
        current_location = bus.location
        
        active_stops = {
            stop_id: stop for stop_id, stop in self.stops.items()
            if stop.demand > 0
        }
        
        if not active_stops:
            return []
            
        route = []
        current_loc = current_location
        remaining_capacity = bus.capacity - bus.passengers
        
        while len(route) < max_stops and remaining_capacity > 0 and active_stops:
            scores = {}
            for stop_id, stop in active_stops.items():
                if stop_id not in route:
                    distance = self._calculate_distance(
                        current_loc, 
                        stop.location
                    )
                    if distance == 0:
                        distance = 0.1
                    score = stop.demand / distance
                    scores[stop_id] = score
                    
            if not scores:
                break
                
            next_stop_id = max(scores.items(), key=lambda x: x[1])[0]
            route.append(next_stop_id)
            current_loc = active_stops[next_stop_id].location
            remaining_capacity -= min(
                active_stops[next_stop_id].demand,
                remaining_capacity
            )
            del active_stops[next_stop_id]
            
        return route

def main():
    st.title("DART System Simulation")
    
    # Initialize system
    if 'dart_system' not in st.session_state:
        st.session_state.dart_system = DARTSystem()
        
        # Add Chennai stops
        chennai_stops = [
            ("CMBT",     13.0694, 80.1000),  # West
            ("CENTRAL",  13.0827, 80.2707),  # Center
            ("T_NAGAR",  12.9500, 80.2341),  # South
            ("EGMORE",   13.0732, 80.4000),  # East
            ("ADYAR",    13.2000, 80.2565)   # North
        ]
        
        for stop_id, lat, lon in chennai_stops:
            st.session_state.dart_system.add_stop(stop_id, lat, lon)
            
        # Add buses
        for i in range(5):
            st.session_state.dart_system.add_bus(
                f"Bus_{i}", 13.0694, 80.1948, capacity=60
            )
    
    # Sidebar controls
    st.sidebar.header("Stop Demands")
    
    # Demand sliders for each stop
    demands = {}
    for stop_id in st.session_state.dart_system.stops:
        demands[stop_id] = st.sidebar.slider(
            f"{stop_id} Demand",
            0, 100, 20,
            key=f"demand_{stop_id}"
        )
    
    # Update button
    if st.sidebar.button("Update Routes"):
        # Update demands
        for stop_id, demand in demands.items():
            st.session_state.dart_system.stops[stop_id].demand = demand
            
        # Calculate new routes
        for bus_id in st.session_state.dart_system.buses:
            route = st.session_state.dart_system.find_optimal_route(bus_id)
            st.session_state.dart_system.buses[bus_id].route = route
    
    # Create map
    m = folium.Map(
        location=[13.0827, 80.2000],
        zoom_start=11
    )
    
    # Add stops to map
    for stop_id, stop in st.session_state.dart_system.stops.items():
        color = 'red' if demands[stop_id] > 0 else 'green'
        folium.CircleMarker(
            location=[stop.location.latitude, stop.location.longitude],
            radius=10,
            popup=f"{stop_id}\nDemand: {demands[stop_id]}",
            color=color,
            fill=True
        ).add_to(m)
    
    # Add bus routes to map
    for i, (bus_id, bus) in enumerate(st.session_state.dart_system.buses.items()):
        if bus.route:
            route_coords = []
            for stop_id in bus.route:
                stop = st.session_state.dart_system.stops[stop_id]
                route_coords.append([
                    stop.location.latitude,
                    stop.location.longitude
                ])
            
            folium.PolyLine(
                route_coords,
                weight=2,
                color=st.session_state.dart_system.colors[i],
                popup=f"{bus_id} Route"
            ).add_to(m)
    
    # Display map
    folium_static(m)
    
    # Display routes
    st.header("Current Routes")
    for bus_id, bus in st.session_state.dart_system.buses.items():
        if bus.route:
            st.write(f"{bus_id}: {' → '.join(bus.route)}")
        else:
            st.write(f"{bus_id}: No route assigned")

if __name__ == "__main__":
    main()
