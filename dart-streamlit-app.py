import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
import time
import altair as alt

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
        """Find optimal route with better demand distribution"""
        bus = self.buses[bus_id]
        remaining_capacity = bus.capacity
        
        # Calculate remaining demands
        remaining_demands = {
            stop_id: max(0, stop.demand - self.assigned_demands.get(stop_id, 0))
            for stop_id, stop in self.stops.items()
        }
        
        # If no remaining demands, try to distribute buses evenly
        if sum(remaining_demands.values()) == 0:
            remaining_demands = {
                stop_id: stop.demand for stop_id, stop in self.stops.items()
            }
        
        # Start from current stop
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
                    
                    # Enhanced scoring system
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
        """Update routes for all buses with improved distribution"""
        self.assigned_demands = {}
        bus_ids = sorted(self.buses.keys())
        
        # Calculate total system demand
        total_demand = sum(stop.demand for stop in self.stops.values())
        
        # Assign initial starting positions if needed
        if all(len(self.stops) >= 5 for _ in range(5)):
            start_positions = list(self.stops.keys())[:5]
            for bus_id, start_pos in zip(bus_ids, start_positions):
                self.buses[bus_id].current_stop = start_pos
        
        # Calculate routes for each bus
        for bus_id in bus_ids:
            route = self.find_optimal_route(bus_id)
            if not route:  # If no optimal route found, assign a backup route
                available_stops = [stop_id for stop_id in self.stops.keys()
                                 if stop_id not in [b.current_stop for b in self.buses.values()]]
                if available_stops:
                    self.buses[bus_id].current_stop = available_stops[0]
                    route = self.find_optimal_route(bus_id)
            self.buses[bus_id].route = route

    def get_animation_frame(self, progress):
        """Create animation frame data"""
        frame_data = []
        
        # Add stops
        for stop_id, stop in self.stops.items():
            frame_data.append({
                'type': 'stop',
                'id': stop_id,
                'latitude': stop.location.latitude,
                'longitude': stop.location.longitude,
                'demand': stop.demand
            })
        
        # Add buses with interpolated positions
        for bus_id, bus in self.buses.items():
            if bus.route and len(bus.route) > 1:
                route_idx = min(int(progress * (len(bus.route) - 1)), len(bus.route) - 2)
                sub_progress = (progress * (len(bus.route) - 1)) % 1
                
                # Get current and next stop
                current_stop = self.stops[bus.route[route_idx]]
                next_stop = self.stops[bus.route[route_idx + 1]]
                
                # Interpolate position
                lat = current_stop.location.latitude + (next_stop.location.latitude - current_stop.location.latitude) * sub_progress
                lon = current_stop.location.longitude + (next_stop.location.longitude - current_stop.location.longitude) * sub_progress
                
                frame_data.append({
                    'type': 'bus',
                    'id': bus_id,
                    'latitude': lat,
                    'longitude': lon,
                    'color': bus.route_color
                })
        
        return pd.DataFrame(frame_data)

def create_animation_chart(frame_data):
    """Create Altair chart for animation frame"""
    
    # Base chart
    base = alt.Chart(frame_data).encode(
        x='longitude:Q',
        y='latitude:Q'
    )
    
    # Stops layer
    stops = base.transform_filter(
        alt.datum.type == 'stop'
    ).mark_circle(size=100).encode(
        color=alt.value('red'),
        tooltip=['id', 'demand']
    )
    
    # Buses layer
    buses = base.transform_filter(
        alt.datum.type == 'bus'
    ).mark_square(size=50).encode(
        color='color:N',
        tooltip=['id']
    )
    
    # Combine layers
    return (stops + buses).properties(
        width=600,
        height=400
    ).configure_view(
        stroke=None
    )

def main():
    st.title("DART System Simulation")
    st.write("Dynamic Adaptive Route Transit System")
    
    # Initialize system
    if 'dart_system' not in st.session_state:
        st.session_state.dart_system = DARTSystem()
        
        # Add Chennai stops
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
    demands = {}
    for stop_id in st.session_state.dart_system.stops:
        demands[stop_id] = st.sidebar.slider(
            f"{stop_id} Demand",
            0, 100, 20,
            key=f"demand_{stop_id}"
        )
    
    # Animation container
    animation_container = st.empty()
    
    # Update button
    if st.sidebar.button("Update Routes"):
        # Update demands
        for stop_id, demand in demands.items():
            st.session_state.dart_system.stops[stop_id].demand = demand
        
        # Calculate new routes
        st.session_state.dart_system.update_all_routes()
        
        # Display initial routes
        st.write("### Route Assignments")
        for bus_id, bus in st.session_state.dart_system.buses.items():
            if bus.route:
                st.write(f"{bus_id}: {' → '.join(bus.route)}")
            else:
                st.write(f"{bus_id}: Standby")
        
        # Animate bus movements
        frames = 50
        for i in range(frames):
            progress = i / (frames - 1)
            
            # Get frame data
            frame_data = st.session_state.dart_system.get_animation_frame(progress)
            
            # Create and display chart
            chart = create_animation_chart(frame_data)
            animation_container.altair_chart(chart)
            
            time.sleep(0.1)
    
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
        - Show animated bus movements
        - Display system metrics
    3. The animation shows:
        - Red circles: Bus stops
        - Colored squares: Buses moving along routes
        - Size of stops indicates demand
    4. Routes are optimized based on:
        - Current demand at each stop
        - Distance between stops
        - Bus capacity
        - System-wide efficiency
    """)

if __name__ == "__main__":
    main()
