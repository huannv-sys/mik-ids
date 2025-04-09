import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional, Tuple
import streamlit as st
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def human_readable_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable string representation
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def plot_bandwidth_over_time(df: pd.DataFrame) -> go.Figure:
    """
    Create a line chart of bandwidth usage over time
    
    Args:
        df: DataFrame with bandwidth usage data
        
    Returns:
        Plotly figure object
    """
    if df.empty:
        return go.Figure()
    
    # Ensure timestamp is in datetime format
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Create a new dataframe with aggregated data
    agg_df = df.groupby('timestamp').agg({
        'tx_bytes': 'sum',
        'rx_bytes': 'sum'
    }).reset_index()
    
    # Convert bytes to megabits (for easier reading)
    agg_df['tx_mbits'] = agg_df['tx_bytes'] * 8 / 1_000_000
    agg_df['rx_mbits'] = agg_df['rx_bytes'] * 8 / 1_000_000
    
    # Create figure
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=agg_df['timestamp'],
        y=agg_df['tx_mbits'],
        mode='lines',
        name='Upload (Mbps)',
        line=dict(color='blue')
    ))
    
    fig.add_trace(go.Scatter(
        x=agg_df['timestamp'],
        y=agg_df['rx_mbits'],
        mode='lines',
        name='Download (Mbps)',
        line=dict(color='green')
    ))
    
    fig.update_layout(
        title='Bandwidth Usage Over Time',
        xaxis_title='Time',
        yaxis_title='Bandwidth (Mbps)',
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def plot_ip_traffic_bar_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """
    Create a bar chart of IP traffic
    
    Args:
        df: DataFrame with IP traffic data
        top_n: Number of top IPs to show
        
    Returns:
        Plotly figure object
    """
    if df.empty:
        return go.Figure()
    
    # Sort by total bytes and get top N
    df = df.sort_values('total_bytes', ascending=False).head(top_n)
    
    # Create stacked bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df['ip_address'],
        y=df['total_rx_bytes'],
        name='Download',
        marker_color='green'
    ))
    
    fig.add_trace(go.Bar(
        x=df['ip_address'],
        y=df['total_tx_bytes'],
        name='Upload',
        marker_color='blue'
    ))
    
    # Add text labels for human-readable sizes
    annotations = []
    for i, row in df.iterrows():
        annotations.append(dict(
            x=row['ip_address'],
            y=row['total_bytes'],
            text=human_readable_size(row['total_bytes']),
            font=dict(family="Arial", size=12),
            showarrow=False,
            yshift=10
        ))
    
    fig.update_layout(
        title=f'Top {top_n} IPs by Traffic Volume',
        xaxis_title='IP Address',
        yaxis_title='Bytes',
        barmode='stack',
        annotations=annotations,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Use log scale for y-axis as traffic can vary greatly
    fig.update_yaxes(type="log")
    
    return fig

def plot_protocol_pie_chart(protocol_counts: Dict[str, int]) -> go.Figure:
    """
    Create a pie chart of protocol distribution
    
    Args:
        protocol_counts: Dictionary with protocol counts
        
    Returns:
        Plotly figure object
    """
    if not protocol_counts:
        return go.Figure()
    
    labels = list(protocol_counts.keys())
    values = list(protocol_counts.values())
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.3,
        hoverinfo='label+percent',
        textinfo='label+value'
    )])
    
    fig.update_layout(
        title='Connection Distribution by Protocol',
        showlegend=True
    )
    
    return fig

def plot_interface_bandwidth(df: pd.DataFrame) -> go.Figure:
    """
    Create a bar chart of bandwidth by interface
    
    Args:
        df: DataFrame with bandwidth data by interface
        
    Returns:
        Plotly figure object
    """
    if df.empty:
        return go.Figure()
    
    # Aggregate data by interface
    agg_df = df.groupby('interface').agg({
        'tx_bytes': 'max',
        'rx_bytes': 'max'
    }).reset_index()
    
    # Convert to GB for readability
    agg_df['tx_gb'] = agg_df['tx_bytes'] / 1_000_000_000
    agg_df['rx_gb'] = agg_df['rx_bytes'] / 1_000_000_000
    
    # Create figure
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=agg_df['interface'],
        y=agg_df['tx_gb'],
        name='Upload (GB)',
        marker_color='blue'
    ))
    
    fig.add_trace(go.Bar(
        x=agg_df['interface'],
        y=agg_df['rx_gb'],
        name='Download (GB)',
        marker_color='green'
    ))
    
    fig.update_layout(
        title='Bandwidth Usage by Interface',
        xaxis_title='Interface',
        yaxis_title='Bandwidth (GB)',
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_connection_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Create a heatmap of connections between source and destination IPs
    
    Args:
        df: DataFrame with connection data
        
    Returns:
        Plotly figure object
    """
    if df.empty:
        return go.Figure()
    
    # Create a pivot table of connections
    pivot_df = df.pivot_table(
        index='src_address', 
        columns='dst_address', 
        values='count', 
        aggfunc='sum',
        fill_value=0
    )
    
    # Limit to top 15 sources and destinations for readability
    top_sources = df.groupby('src_address')['count'].sum().nlargest(15).index
    top_destinations = df.groupby('dst_address')['count'].sum().nlargest(15).index
    
    pivot_df = pivot_df.loc[pivot_df.index.isin(top_sources), pivot_df.columns.isin(top_destinations)]
    
    # Create the heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale='Viridis',
        hoverongaps=False
    ))
    
    fig.update_layout(
        title='Connection Heatmap (Source to Destination)',
        xaxis_title='Destination IP',
        yaxis_title='Source IP',
        height=600
    )
    
    return fig
