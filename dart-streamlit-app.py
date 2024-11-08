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
    label: str = None

class DARTSystem:
    def __init__(self):
        self.stops: Dict[str, BusStop] = {}
        self.buses: Dict[str, Bus] = {}
        self.colors = {
            'Bus_0': {'name': 'Express Red Line', 'color': '#FF4B4B'},
            'Bus_1': {'name': 'Rapid Blue Line', 'color': '#4B8BFF'},
            'Bus_2': {'name': 'Green Circuit', 'color': '#4BFF4B'},
            'Bus_3': {'name': 'Orange Loop', 'color': '#FFB74B'},
            'Bus_4': {'name': 'Purple Connect', 'color': '#B74BFF'}
        }
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
            route_color=self.colors[bus_id]['color'],
            label=self.colors[bus_id]['name']
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
        remaining_capacity = bus.capacity
        
        remaining_demands = {
            stop_id: max(0, stop.demand - self.assigned_demands.get(stop_id, 0))
            for stop_id, stop in self.stops.items()
        }
        
        if sum(remaining_demands.values()) == 0:
            remaining_demands = {
                stop_id: stop.demand for stop_id, stop in self.stops.items()
            }
        
        route = [bus.current_stop]
        current_stop = bus.current_stop
        
        while len(route) < max_stops and remaining_capacity > 0:
            best_score = -1
            next_stop = None
            
            for stop_id, demand in remaining_demands.items():
                if stop_id not in route:
                    distance = self._calculate_distance(
                        self.stops[current_stop].location,
                        self.stops[stop_id].location
                    )
                    if distance == 0:
                        distance = 0.1
                    
                    demand_score = demand / bus.capacity
                    distance_score = 1 / distance
                    coverage_score = 1 if stop_id not in [b.current_stop for b in self.buses.values()] else 0
                    
                    score = (0.4 * demand_score + 
                            0.4 * distance_score + 
                            0.2 * coverage_score)
                    
                    if score > best_score:
                        best_score = score
                        next_stop = stop_id
            
            if next_stop is None:
                break
            
            route.append(next_stop)
            pickup = min(remaining_demands[next_stop], remaining_capacity)
            remaining_capacity -= pickup
            self.assigned_demands[next_stop] = self.assigned_demands.get(next_stop, 0) + pickup
            current_stop = next_stop
        
        return route

    def update_all_routes(self):
        self.assigned_demands = {}
        bus_ids = sorted(self.buses.keys())
        
        for bus_id in bus_ids:
            route = self.find_optimal_route(bus_id)
            self.buses[bus_id].route = route

    def get_state_dataframe(self):
        """Get current state as a DataFrame for visualization"""
        data = []
        
        # Add stops
        for stop_id, stop in self.stops.items():
            data.append({
                'type': 'stop',
                'name': stop_id,
                'latitude': stop.location.latitude,
                'longitude': stop.location.longitude,
                'demand': stop.demand,
                'size': 20 + stop.demand/2  # Size based on demand
            })
        
        return pd.DataFrame(data)

def main():
    st.set_page_config(layout="wide")
    st.title("DART System Simulation")
    st.write("Dynamic Adaptive Route Transit System")
    
    # Initialize system
    if 'dart_system' not in st.session_state:
        st.session_state.dart_system = DARTSystem()
        
        chennai_stops = [
            ("CMBT",     13.0694, 80.1000),
            ("CENTRAL",  13.0827, 80.2707),
            ("T_NAGAR",  12.9500, 80.2341),
            ("EGMORE",   13.0732, 80.4000),
            ("ADYAR",    13.2000, 80.2565)
        ]
        
        for stop_id, lat, lon in chennai_stops:
            st.session_state.dart_system.add_stop(stop_id, lat, lon)
            
        for i in range(5):
            st.session_state.dart_system.add_bus(f"Bus_{i}", "CMBT", 60)
    
    # Sidebar controls
    st.sidebar.header("Stop Demands")
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
        
        # Display current state
        state_df = st.session_state.dart_system.get_state_dataframe()
        
        # Display routes
        st.write("### Current Routes")
        
        # Create columns for bus display
        cols = st.columns(5)
        for idx, (bus_id, bus) in enumerate(st.session_state.dart_system.buses.items()):
            with cols[idx]:
                st.markdown(f"<p style='color: {bus.route_color}'>{bus.label}</p>", unsafe_allow_html=True)
                if bus.route:
                    st.write(" → ".join(bus.route))
                else:
                    st.write("Standby")
        
        # Display map
        st.write("### Stop Locations")
        st.map(state_df, latitude='latitude', longitude='longitude', size='size')
        
        # Display demand table
        st.write("### Current Demands")
        demand_df = pd.DataFrame({
            'Stop': list(demands.keys()),
            'Current Demand': list(demands.values())
        })
        st.dataframe(demand_df, hide_index=True)
    
    # System metrics
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
        - Display updated system status
        - Show current demands and metrics
    3. The system shows:
        - Color-coded bus routes
        - Stop locations on map
        - Current demands at each stop
    4. Routes are optimized based on:
        - Current demand at each stop
        - Distance between stops
        - Bus capacity and current load
        - Overall system efficiency
    """)

if __name__ == "__main__":
    main()
