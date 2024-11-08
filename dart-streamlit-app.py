import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
import time
import plotly.graph_objects as go

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
    
    def get_animation_frame(self, progress):
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
        
        # Add buses with interpolated positions and routes
        for bus_id, bus in self.buses.items():
            if bus.route and len(bus.route) > 1:
                route_idx = min(int(progress * (len(bus.route) - 1)), len(bus.route) - 2)
                sub_progress = (progress * (len(bus.route) - 1)) % 1
                
                current_stop = self.stops[bus.route[route_idx]]
                next_stop = self.stops[bus.route[route_idx + 1]]
                
                lat = current_stop.location.latitude + (next_stop.location.latitude - current_stop.location.latitude) * sub_progress
                lon = current_stop.location.longitude + (next_stop.location.longitude - current_stop.location.longitude) * sub_progress
                
                # Add bus position
                frame_data.append({
                    'type': 'bus',
                    'id': bus.label,
                    'latitude': lat,
                    'longitude': lon,
                    'color': bus.route_color
                })
                
                # Add route lines
                for i in range(len(bus.route) - 1):
                    start = self.stops[bus.route[i]]
                    end = self.stops[bus.route[i + 1]]
                    frame_data.append({
                        'type': 'route',
                        'id': bus.label,
                        'latitude': start.location.latitude,
                        'longitude': start.location.longitude,
                        'latitude2': end.location.latitude,
                        'longitude2': end.location.longitude,
                        'color': bus.route_color
                    })
        
        return pd.DataFrame(frame_data)

def create_animation_chart(frame_data):
    fig = go.Figure()
    
    # Add route lines for each bus
    for bus_id in frame_data[frame_data['type'] == 'bus']['id'].unique():
        routes = frame_data[
            (frame_data['type'] == 'route') & 
            (frame_data['id'] == bus_id)
        ]
        if not routes.empty:
            for _, route in routes.iterrows():
                fig.add_trace(go.Scatter(
                    x=[route['longitude'], route['longitude2']],
                    y=[route['latitude'], route['latitude2']],
                    mode='lines',
                    name=f"{bus_id} Route",
                    line=dict(
                        color=route['color'],
                        width=2
                    ),
                    showlegend=(route.name == 0)  # Show legend only once per bus
                ))
    
    # Add stops
    stops = frame_data[frame_data['type'] == 'stop']
    fig.add_trace(go.Scatter(
        x=stops['longitude'],
        y=stops['latitude'],
        mode='markers+text',
        name='Bus Stops',
        text=stops['id'] + '<br>Demand: ' + stops['demand'].astype(str),
        textposition="top center",
        marker=dict(
            size=20,
            color='red',
            symbol='circle'
        )
    ))
    
    # Add buses
    buses = frame_data[frame_data['type'] == 'bus']
    for _, bus in buses.iterrows():
        fig.add_trace(go.Scatter(
            x=[bus['longitude']],
            y=[bus['latitude']],
            mode='markers+text',
            name=bus['id'],
            text=bus['id'],
            textposition="bottom center",
            marker=dict(
                size=15,
                color=bus['color'],
                symbol='square'
            )
        ))
    
    # Update layout
    fig.update_layout(
        title=dict(
            text="DART System Route Animation",
            x=0.5,
            y=0.95,
            font=dict(size=24, color='white')
        ),
        plot_bgcolor='black',
        paper_bgcolor='black',
        showlegend=True,
        width=1000,
        height=800,
        font=dict(color='white'),
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)',
            zeroline=False,
            title='Longitude',
            color='white'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)',
            zeroline=False,
            title='Latitude',
            color='white'
        ),
        legend=dict(
            font=dict(color='white'),
            bgcolor='rgba(0,0,0,0.5)'
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig

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
    
    # Animation container
    animation_container = st.empty()
    
    # Update button with simulation speed control
    st.sidebar.write("### Simulation Controls")
    animation_speed = st.sidebar.slider("Animation Speed (seconds)", 3.0, 10.0, 6.0)
    
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
                st.write(f"{bus.label}: {' → '.join(bus.route)}")
            else:
                st.write(f"{bus.label}: Standby")
        
        # Animation settings
        frames = 120  # More frames for smoother animation
        frame_delay = animation_speed / frames  # Distribute total time across frames
        
        # Progress tracking
        progress_bar = st.progress(0)
        status = st.empty()
        
        # Animation loop
        try:
            for i in range(frames):
                progress = i / (frames - 1)
                progress_bar.progress(progress)
                
                frame_data = st.session_state.dart_system.get_animation_frame(progress)
                fig = create_animation_chart(frame_data)
                animation_container.plotly_chart(fig, use_container_width=True)
                
                time.sleep(frame_delay)
                
                # Update status
                current_time = int((progress * 10) + 1)
                status.write(f"Simulation Time: {current_time} minutes")
        except Exception as e:
            st.error(f"Animation error: {str(e)}")
        finally:
            progress_bar.empty()
            status.empty()
    
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
    2. Adjust animation speed if desired (3-10 seconds)
    3. Click 'Update Routes' to:
        - Calculate optimal routes
        - Show animated bus movements with route traces
        - Display system metrics
    4. The animation shows:
        - Red circles: Bus stops with demand
        - Colored squares: Buses moving along routes
        - Colored lines: Route paths for each bus
        - Size of stops indicates demand level
    5. Routes are optimized based on:
        - Current demand at each stop
        - Distance between stops
        - Bus capacity and current load
        - Overall system efficiency
    """)

if __name__ == "__main__":
    main()
