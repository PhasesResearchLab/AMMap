import igraph as ig
import plotly.graph_objs as go
import numpy as np

def plotGraph(edges: list):
    """
    Plots a 3D graph using the given list of edges.
    Args:
        edges (list): A list of edge tuples, where each tuple represents a connection between two nodes.
    Returns:
        None. Displays an interactive 3D plot of the graph.
    Notes:
        - The function uses igraph for graph construction and layout calculation.
        - Plotly is used for rendering the 3D visualization.
        - Node positions are determined using the Kamada-Kawai layout in 3D.
        - Each edge is visualized as a semi-transparent line, and nodes are shown as blue markers.
    """
    # Lets generate some seed positions for the nodes
    G = ig.Graph(edges)
    layout = G.layout_kamada_kawai(dim=3)
    layout_array = np.array(layout.coords)
    # Create edge traces
    edge_traces = []
    for edge in G.es:
        start, end = edge.tuple
        x0, y0, z0 = layout_array[start]
        x1, y1, z1 = layout_array[end]
        width = 5
        edge_trace = go.Scatter3d(x=[x0, x1], y=[y0, y1], z=[z0, z1],
                                line=dict(width=width, color='lightgray'),
                                opacity=0.2,
                                hoverinfo='none', mode='lines')
        edge_traces.append(edge_trace)

    node_trace = go.Scatter3d(x=layout_array[:, 0], y=layout_array[:, 1], z=layout_array[:, 2],
                            mode='markers',
                            marker=dict(size=3, 
                                        opacity=0.5,
                                        line=None,
                                        color='blue'),
                            
                            text=[f"Node {i}" for i in range(len(layout_array))],
                            hoverinfo='text')

    # Create figure
    fig = go.Figure(data=edge_traces + [node_trace])

    # Update layout
    fig.update_layout(
        title='3D Graph with Feasibility Types',
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
        ),
        showlegend=False,
        margin=dict(l=0, r=0, b=0, t=0),
        width=800
    )

    fig.show()