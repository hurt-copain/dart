import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

@dataclass
class BusStop:
    id: str
    waiting_passengers: int
    connected_stops: List[str]

@dataclass
class Bus:
    id: str
    capacity: int
    current_stop: str
    route: List[str] = None

class DARTSystem:
    def __init__(self, num_stops: int, num_buses: int):
        self.num_stops = num_stops
        self.num_buses = num_buses
        self.stops: Dict[str, BusStop] = {}
        self.buses: List[Bus] = []
        self.network_graph = nx.Graph()
        self.pos = None

    def initialize_network(self):
        # Create stops
        for i in range(self.num_stops):
            stop_id = f"Stop_{i}"
            possible_connections = [f"Stop_{j}" for j in range(self.num_stops) if j != i]
            num_connections = np.random.randint(2, 4)
            connected_stops = np.random.choice(
                possible_connections, 
                size=min(num_connections, len(possible_connections)), 
                replace=False
            ).tolist()
            
            self.stops[stop_id] = BusStop(
                id=stop_id,
                waiting_passengers=np.random.randint(10, 100),
                connected_stops=connected_stops
            )
            
            # Add to network graph
            self.network_graph.add_node(stop_id, demand=self.stops[stop_id].waiting_passengers)
            for conn in connected_stops:
                self.network_graph.add_edge(stop_id, conn)
        
        # Initialize buses
        for i in range(self.num_buses):
            self.buses.append(Bus(
                id=f"Bus_{i}",
                capacity=50,
                current_stop=f"Stop_0"
            ))
        
        # Calculate layout
        self.pos = nx.spring_layout(self.network_graph)

    def calculate_routes(self) -> Dict[str, List[str]]:
        routes = {}
        covered_stops = set()
        
        # Calculate demand scores
        demand_scores = {
            stop_id: stop.waiting_passengers 
            for stop_id, stop in self.stops.items()
        }
        
        # Sort stops by demand
        high_demand_stops = sorted(
            demand_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Assign routes to buses
        for bus in self.buses:
            if not high_demand_stops:
                break
            
            # Start from highest demand uncovered stop
            start_stop = None
            for stop_id, _ in high_demand_stops:
                if stop_id not in covered_stops:
                    start_stop = stop_id
                    break
            
            if start_stop is None:
                continue
                
            route = [start_stop]
            current_stop = start_stop
            covered_stops.add(start_stop)
            
            # Build route
            while len(route) < 5:
                next_stop = self._find_next_best_stop(
                    current_stop,
                    covered_stops,
                    demand_scores
                )
                
                if next_stop is None:
                    break
                
                route.append(next_stop)
                covered_stops.add(next_stop)
                current_stop = next_stop
            
            routes[bus.id] = route
        
        return routes

    def _find_next_best_stop(self, current_stop: str, covered_stops: set, 
                            demand_scores: Dict[str, int]) -> Optional[str]:
        best_score = -1
        best_stop = None
        
        for next_stop in self.stops[current_stop].connected_stops:
            if next_stop in covered_stops:
                continue
            
            demand_factor = demand_scores[next_stop]
            connection_factor = len(self.stops[next_stop].connected_stops)
            coverage_factor = sum(1 for stop in self.stops[next_stop].connected_stops 
                                if stop not in covered_stops)
            
            score = (0.5 * demand_factor +
                    0.3 * connection_factor +
                    0.2 * coverage_factor)
            
            if score > best_score:
                best_score = score
                best_stop = next_stop
        
        return best_stop

def create_network_plot(system: DARTSystem, routes: Optional[Dict[str, List[str]]] = None):
    fig = go.Figure()
    
    # Add edges
    for edge in system.network_graph.edges():
        x0, y0 = system.pos[edge[0]]
        x1, y1 = system.pos[edge[1]]
        fig.add_trace(go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(color='lightgray', width=1),
            hoverinfo='none'
        ))
    
    # Add routes
    if routes:
        colors = px.colors.qualitative.Set3[:len(routes)]
        for (bus_id, route), color in zip(routes.items(), colors):
            for i in range(len(route)-1):
                x0, y0 = system.pos[route[i]]
                x1, y1 = system.pos[route[i+1]]
                fig.add_trace(go.Scatter(
                    x=[x0, x1],
                    y=[y0, y1],
                    mode='lines',
                    name=bus_id,
                    line=dict(color=color, width=3),
                    hoverinfo='text',
                    text=f"{bus_id}: {route[i]} → {route[i+1]}"
                ))
    
    # Add nodes
    node_x = []
    node_y = []
    node_text = []
    node_size = []
    
    for node in system.network_graph.nodes():
        x, y = system.pos[node]
        node_x.append(x)
        node_y.append(y)
        demand = system.stops[node].waiting_passengers
        node_text.append(f"{node}<br>Demand: {demand}")
        node_size.append(demand)
    
    fig.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        name='Bus Stops',
        marker=dict(
            size=15,
            color=node_size,
            colorscale='YlOrRd',
            showscale=True,
            colorbar=dict(title='Passenger Demand')
        ),
        text=[node.split('_')[1] for node in system.network_graph.nodes()],
        hovertext=node_text,
        hoverinfo='text'
    ))
    
    fig.update_layout(
        showlegend=True,
        hovermode='closest',
        margin=dict(b=20,l=5,r=5,t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        title="DART System Network"
    )
    
    return fig

def show_route_analysis(system: DARTSystem, routes: Dict[str, List[str]]):
    st.write("### Route Analysis")
    
    for bus_id, route in routes.items():
        with st.expander(f"{bus_id} Details"):
            total_demand = sum(system.stops[stop].waiting_passengers for stop in route)
            coverage = len(route) / system.num_stops
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Stops Covered", len(route))
            with col2:
                st.metric("Total Demand", total_demand)
            with col3:
                st.metric("Coverage", f"{coverage:.1%}")
            
            st.write("Route:", " → ".join(route))
            
            demands = [system.stops[stop].waiting_passengers for stop in route]
            df = pd.DataFrame({
                'Stop': route,
                'Demand': demands
            }).set_index('Stop')
            st.bar_chart(df)

def main():
    st.set_page_config(layout="wide")
    st.title("DART System Simulation")
    st.write("""
    ### Dynamic Adaptive Route Transit System
    Applying computer networking principles to optimize bus routing
    """)
    
    # Sidebar controls
    st.sidebar.header("System Parameters")
    num_stops = st.sidebar.slider("Number of Stops", 5, 15, 10)
    num_buses = st.sidebar.slider("Number of Buses", 2, 8, 5)
    
    # Initialize system
    if 'system' not in st.session_state or st.sidebar.button("Reset System"):
        st.session_state.system = DARTSystem(num_stops, num_buses)
        st.session_state.system.initialize_network()
        st.session_state.routes = None
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("Calculate Routes"):
            st.session_state.routes = st.session_state.system.calculate_routes()
        
        fig = create_network_plot(st.session_state.system, st.session_state.routes)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.write("### System Information")
        
        total_demand = sum(stop.waiting_passengers 
                          for stop in st.session_state.system.stops.values())
        st.metric("Total System Demand", total_demand)
        
        if st.session_state.routes:
            covered_stops = set().union(*st.session_state.routes.values())
            coverage = len(covered_stops) / num_stops
            st.metric("System Coverage", f"{coverage:.1%}")
    
    if st.session_state.routes:
        show_route_analysis(st.session_state.system, st.session_state.routes)
    
    with st.expander("How It Works"):
        st.write("""
        The DART system uses network-inspired principles to optimize bus routing:
        
        1. **Demand Analysis** (50% weight)
        - Like network traffic analysis
        - Prioritizes high-demand stops
        
        2. **Connectivity** (30% weight)
        - Like network node importance
        - Considers stop connections
        
        3. **Coverage** (20% weight)
        - Like network exploration
        - Ensures system-wide service
        """)

if __name__ == "__main__":
    main()
