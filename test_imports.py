import sys
print("Python version:", sys.version)

try:
    import streamlit as st
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    import plotly.express as px
    import networkx as nx
    
    print("\nSuccessfully imported all packages:")
    print(f"streamlit version: {st.__version__}")
    print(f"numpy version: {np.__version__}")
    print(f"pandas version: {pd.__version__}")
    print(f"plotly version: {go.__version__}")
    print(f"networkx version: {nx.__version__}")
    
except ImportError as e:
    print("Error importing packages:", str(e))
    sys.exit(1)
