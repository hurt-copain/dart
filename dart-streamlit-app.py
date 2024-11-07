import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
import time

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
    current_stop: str
    capacity: int
    passengers: int = 0
    route: List[str] = None
    route_color: str = None

class DARTSystem:
    def __init__(self):
        self.stops: Dict[str, BusStop] = {}
        self.buses: Dict[str, Bus] = {}
        self.colors = ['red', 'green', 'blue', 'orange', 'purple']
        self.assigned_demands = {}
        
    def add_stop(self, stop_id: str, latitude: float, longitude: float):
        self.stops[stop_id] = BusStop(
            id=stop_id,
            location=Location(latitude, longitude)
        )
        
    def add_bus(self, bus_id: str, start_stop: str, capacity: int):
        self.buses[bus_id] = Bus(
            id=bus_id,
            current_stop=start_stop,
            capacity=capacity,
            route_color=self.colors[len(self.buses) % len(self.colors)]
        )
        
    def _calculate_distance(self, loc1: Location, loc2: Location) -> float:
        R = 6371
        lat1, lon1 = np.radians([loc1.latitude, loc1.longitude])
        lat2, lon2 = np.radians([loc2.latitude, loc2.longitude])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        return 2 * R * np.arcsin(np.sqrt(a))

    def find_optimal_route(self, bus_id: str, max_stops: int = 5) -> List[str]:
        """Find optimal route considering other buses and remaining demand"""
        bus = self.buses[bus_id]
        
        # Get remaining demands after considering other buses' routes
        remaining_demands = {
            stop_id: stop.demand for stop_id, stop in self.stops.items()
        }
        
        # Subtract already assigned demands
        for stop_id, assigned in self.assigned_demands.items():
            if stop_id in remaining_demands:
                remaining_demands[stop_id] = max(0, remaining_demands[stop_id] - assigned)
        
        active_stops = {
            stop_id: stop for stop_id, stop in self.stops.items()
            if remaining_demands[stop_id] > 0
        }
        
        if not active_stops:
            return []
            
        route = []
        current_stop = bus.current_stop
        remaining_capacity = bus.capacity - bus.passengers
        
        while len(route) < max_stops and remaining_capacity > 0 and active_stops:
            scores = {}
            for stop_id, stop in active_stops.items():
                if stop_id not in route and stop_id != current_stop:
                    distance = self._calculate_distance(
                        self.stops[current_stop].location,
                        stop.location
                    )
                    if distance == 0:
                        distance = 0.1
                    
                    # Score based on demand and distance
                    score = remaining_demands[stop_id] / distance
                    scores[stop_id] = score
            
            if not scores:
                break
            
            next_stop = max(scores.items(), key=lambda x: x[1])[0]
            route.append(next_stop)
            
            # Update assigned demands
            demand_to_assign = min(
                remaining_demands[next_stop],
                remaining_capacity
            )
            self.assigned_demands[next_stop] = self.assigned_demands.get(
                next_stop, 0
            ) + demand_to_assign
            
            current_stop = next_stop
            remaining_capacity -= demand_to_assign
            remaining_demands[next_stop] -= demand_to_assign
            
            if remaining_demands[next_stop] <= 0:
                del active_stops[next_stop]
        
        return route

    def update_all_routes(self):
        """Update routes for all buses with better distribution"""
        self.assigned_demands = {}
        bus_ids = sorted(self.buses.keys())
        
        total_demand = sum(stop.demand for stop in self.stops.values())
        if total_demand == 0:
            for bus_id in bus_ids:
                self.buses[bus_id].route = []
            return
        
        for bus_id in bus_ids:
            route = self.find_optimal_route(bus_id)
            self.buses[bus_id].route = route

def simulate_bus_movement(stop1, stop2, progress):
    """Interpolate bus position between stops"""
    lat = stop1.location.latitude + (stop2.location.latitude - stop1.location.latitude) * progress
    lon = stop1.location.longitude + (stop2.location.longitude - stop1.location.longitude) * progress
    return (lat, lon)

def main():
    st.title("DART System Simulation")
    st.write("Dynamic Adaptive Route Transit System")
    
    # Initialize system
    if 'dart_system' not in st.session_state:
        st.session_state.dart_system = DARTSystem()
        
        # Add Chennai stops with more spacing
        chennai_stops = [
            ("CMBT",     13.0694, 80.1000),
            ("CENTRAL",  13.0827, 80.2707),
            ("T_NAGAR",  12.9500, 80.2341),
            ("EGMORE",   13.0732, 80.4000),
            ("ADYAR",    13.2000, 80.2565)
        ]
        
        for stop_id, lat, lon in chennai_stops:
            st.session_state.dart_system.add_stop(stop_id, lat, lon)
            
        # Add buses starting at CMBT
        for i in range(5):
            st.session_state.dart_system.add_bus(f"Bus_{i}", "CMBT", 60)
    
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
        st.session_state.dart_system.update_all_routes()
        
        # Simulate bus movements
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for step in range(10):  # 10 steps of animation
            # Update progress
            progress = step / 9
            progress_bar.progress(progress)
            
            # Create current state visualization
            data = []
            
            # Add stops
            for stop_id, stop in st.session_state.dart_system.stops.items():
                data.append({
                    'Stop': stop_id,
                    'Latitude': stop.location.latitude,
                    'Longitude': stop.location.longitude,
                    'Demand': demands[stop_id],
                    'Type': 'Stop'
                })
            
            # Add buses with interpolated positions
            for bus_id, bus in st.session_state.dart_system.buses.items():
                if bus.route and len(bus.route) > 1:
                    route_idx = min(int(progress * len(bus.route)), len(bus.route) - 2)
                    sub_progress = (progress * len(bus.route)) % 1
                    
                    stop1 = st.session_state.dart_system.stops[bus.route[route_idx]]
                    stop2 = st.session_state.dart_system.stops[bus.route[route_idx + 1]]
                    
                    bus_pos = simulate_bus_movement(stop1, stop2, sub_progress)
                    
                    data.append({
                        'Stop': bus_id,
                        'Latitude': bus_pos[0],
                        'Longitude': bus_pos[1],
                        'Demand': 0,
                        'Type': 'Bus'
                    })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Display current state
            status_text.text(f"Simulation step {step + 1}/10")
            
            # Display routes text
            routes_text = "\nCurrent Routes:\n"
            for bus_id, bus in st.session_state.dart_system.buses.items():
                if bus.route:
                    routes_text += f"{bus_id}: {' → '.join(bus.route)}\n"
                else:
                    routes_text += f"{bus_id}: No route assigned\n"
            
            st.text(routes_text)
            
            time.sleep(0.5)  # Animation speed
            
        progress_bar.empty()
        status_text.empty()
    
    # Display system metrics
    st.write("### System Metrics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Demand", sum(demands.values()))
    with col2:
        st.metric("Active Buses", len(st.session_state.dart_system.buses))
    with col3:
        st.metric("Total Stops", len(st.session_state.dart_system.stops))

    # Add explanation
    st.write("### How it works")
    st.write("""
    1. Use the sliders to set passenger demand at each stop
    2. Click 'Update Routes' to:
        - Calculate optimal routes
        - Show bus movements
        - Display system metrics
    3. The simulation shows:
        - Route assignments for each bus
        - Step-by-step movement simulation
        - System performance metrics
    """)

if __name__ == "__main__":
    main()
