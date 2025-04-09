import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import threading
import logging
from datetime import datetime, timedelta
import re

from mikrotik_api import MikrotikAPI
from data_store import DataStore
from visualization import (
    human_readable_size, 
    plot_bandwidth_over_time,
    plot_ip_traffic_bar_chart,
    plot_protocol_pie_chart,
    plot_interface_bandwidth,
    create_connection_heatmap
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state variables if they don't exist
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'api' not in st.session_state:
    st.session_state.api = None
if 'data_store' not in st.session_state:
    st.session_state.data_store = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'update_interval' not in st.session_state:
    st.session_state.update_interval = 60  # Default update interval in seconds
if 'auto_update' not in st.session_state:
    st.session_state.auto_update = False

# Create an event to signal the background thread to stop
if 'stop_event' not in st.session_state:
    st.session_state.stop_event = threading.Event()

# Initialize the data store
if not st.session_state.data_store:
    st.session_state.data_store = DataStore()

# Function to validate IP address
def is_valid_ip(ip):
    ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    return bool(ip_pattern.match(ip))

# Function to collect data from Mikrotik
def collect_data():
    if not st.session_state.connected or not st.session_state.api:
        return False
    
    try:
        # Get active connections
        connections = st.session_state.api.get_active_connections()
        if connections:
            st.session_state.data_store.store_active_connections(connections)
        
        # Get bandwidth usage
        bandwidth = st.session_state.api.get_bandwidth_usage()
        if bandwidth:
            st.session_state.data_store.store_bandwidth_usage(bandwidth)
        
        # Get traffic by IP
        traffic = st.session_state.api.get_traffic_by_ip()
        if traffic:
            st.session_state.data_store.store_ip_traffic(traffic)
        
        st.session_state.last_update = datetime.now()
        return True
    except Exception as e:
        logger.error(f"Error collecting data: {str(e)}")
        return False

# Function for background data collection
def background_data_collection():
    while not st.session_state.stop_event.is_set():
        if st.session_state.connected and st.session_state.auto_update:
            collect_data()
        time.sleep(st.session_state.update_interval)

# Set page configuration
st.set_page_config(
    page_title="Mikrotik Monitor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar for connection settings
st.sidebar.title("Mikrotik Monitor")

# Connection section
st.sidebar.header("Connection Settings")

host = st.sidebar.text_input("Router IP/Hostname", value="192.168.88.1")
username = st.sidebar.text_input("Username", value="admin")
password = st.sidebar.text_input("Password", type="password")
port = st.sidebar.number_input("API Port", value=8728, min_value=1, max_value=65535, step=1)
use_ssl = st.sidebar.checkbox("Use SSL", value=False)

# Connect/Disconnect button
if not st.session_state.connected:
    if st.sidebar.button("Connect"):
        if not is_valid_ip(host) and not host.startswith("http"):
            st.sidebar.error("Please enter a valid IP address or hostname")
        else:
            with st.spinner("Connecting to Mikrotik router..."):
                st.session_state.api = MikrotikAPI(host, username, password, port, use_ssl)
                if st.session_state.api.connect():
                    st.session_state.connected = True
                    # Start a background thread for data collection
                    st.session_state.stop_event.clear()
                    thread = threading.Thread(target=background_data_collection)
                    thread.daemon = True
                    thread.start()
                    # Collect initial data
                    collect_data()
                    st.sidebar.success("Connected successfully!")
                    st.rerun()
                else:
                    st.sidebar.error("Failed to connect. Check your credentials and try again.")
else:
    if st.sidebar.button("Disconnect"):
        if st.session_state.api:
            st.session_state.api.disconnect()
        st.session_state.connected = False
        st.session_state.stop_event.set()  # Signal the background thread to stop
        st.sidebar.success("Disconnected successfully!")
        st.rerun()
    
    st.sidebar.success("Connected to Mikrotik router")
    
    # Data update settings
    st.sidebar.header("Data Update Settings")
    
    st.session_state.update_interval = st.sidebar.slider(
        "Update Interval (seconds)",
        min_value=10,
        max_value=300,
        value=st.session_state.update_interval,
        step=10
    )
    
    auto_update = st.sidebar.checkbox(
        "Auto Update",
        value=st.session_state.auto_update
    )
    
    if auto_update != st.session_state.auto_update:
        st.session_state.auto_update = auto_update
    
    if st.sidebar.button("Update Now"):
        with st.spinner("Collecting data..."):
            if collect_data():
                st.sidebar.success("Data updated successfully!")
            else:
                st.sidebar.error("Failed to update data.")
    
    if st.session_state.last_update:
        st.sidebar.info(f"Last update: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")

# Main content
st.title("Mikrotik Network Monitor")

if not st.session_state.connected:
    st.info("Please connect to your Mikrotik router using the sidebar to start monitoring.")
else:
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚀 Bandwidth Overview", 
        "💻 IP Traffic", 
        "🔄 Connections", 
        "📊 Reports"
    ])
    
    with tab1:
        st.header("Bandwidth Overview")
        
        # Get bandwidth history
        bandwidth_df = st.session_state.data_store.get_bandwidth_history(hours=24)
        
        if bandwidth_df.empty:
            st.warning("No bandwidth data available. Click 'Update Now' to collect data.")
        else:
            # Display bandwidth over time chart
            st.subheader("Bandwidth Usage Over Time")
            bandwidth_fig = plot_bandwidth_over_time(bandwidth_df)
            st.plotly_chart(bandwidth_fig, use_container_width=True)
            
            # Display bandwidth by interface chart
            st.subheader("Bandwidth by Interface")
            interface_fig = plot_interface_bandwidth(bandwidth_df)
            st.plotly_chart(interface_fig, use_container_width=True)
            
            # Display current bandwidth stats in a metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            # Calculate total bandwidth
            latest_bandwidth = bandwidth_df.sort_values('timestamp', ascending=False)
            interfaces = latest_bandwidth['interface'].unique()
            
            total_rx = latest_bandwidth.groupby('interface')['rx_bytes'].max().sum()
            total_tx = latest_bandwidth.groupby('interface')['tx_bytes'].max().sum()
            
            with col1:
                st.metric("Total Download", human_readable_size(total_rx))
            
            with col2:
                st.metric("Total Upload", human_readable_size(total_tx))
            
            with col3:
                st.metric("Active Interfaces", len(interfaces))
            
            with col4:
                if st.session_state.last_update:
                    time_diff = datetime.now() - st.session_state.last_update
                    st.metric("Data Age", f"{time_diff.seconds} seconds")
    
    with tab2:
        st.header("IP Traffic Analysis")
        
        # Filter options
        hours_filter = st.selectbox(
            "Time Range",
            options=[1, 3, 6, 12, 24, 48, 72],
            index=3,
            format_func=lambda x: f"{x} hours"
        )
        
        ip_filter = st.text_input("Filter by IP (leave empty for all)")
        
        # Get IP traffic data
        if ip_filter and is_valid_ip(ip_filter):
            ip_traffic_df = st.session_state.data_store.get_ip_traffic_history(ip_address=ip_filter, hours=hours_filter)
            st.subheader(f"Traffic for IP: {ip_filter}")
        else:
            top_ips_df = st.session_state.data_store.get_top_ips_by_traffic(limit=20, hours=hours_filter)
            if top_ips_df.empty:
                st.warning("No IP traffic data available. Click 'Update Now' to collect data.")
            else:
                # Plot top IPs by traffic
                st.subheader("Top IPs by Traffic Volume")
                ip_fig = plot_ip_traffic_bar_chart(top_ips_df, top_n=10)
                st.plotly_chart(ip_fig, use_container_width=True)
                
                # Display data table
                st.subheader("IP Traffic Details")
                
                # Add human readable columns
                top_ips_df['Download'] = top_ips_df['total_rx_bytes'].apply(human_readable_size)
                top_ips_df['Upload'] = top_ips_df['total_tx_bytes'].apply(human_readable_size)
                top_ips_df['Total'] = top_ips_df['total_bytes'].apply(human_readable_size)
                
                st.dataframe(
                    top_ips_df[['ip_address', 'Download', 'Upload', 'Total', 'last_seen']],
                    use_container_width=True,
                    column_config={
                        "ip_address": "IP Address",
                        "last_seen": "Last Seen",
                    }
                )
    
    with tab3:
        st.header("Active Connections")
        
        # Connection stats
        connection_stats = st.session_state.data_store.get_connection_stats(hours=24)
        
        if not connection_stats:
            st.warning("No connection data available. Click 'Update Now' to collect data.")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Protocol Distribution")
                if connection_stats.get('protocol_counts'):
                    protocol_fig = plot_protocol_pie_chart(connection_stats['protocol_counts'])
                    st.plotly_chart(protocol_fig, use_container_width=True)
                else:
                    st.info("No protocol data available.")
            
            with col2:
                st.subheader("Connection Statistics")
                st.metric("Total Connections", connection_stats.get('total_connections', 0))
                
                st.subheader("Top Source IPs")
                if connection_stats.get('top_sources'):
                    source_df = pd.DataFrame({
                        'IP Address': list(connection_stats['top_sources'].keys()),
                        'Connections': list(connection_stats['top_sources'].values())
                    })
                    st.dataframe(source_df, use_container_width=True)
                else:
                    st.info("No source IP data available.")
                
                st.subheader("Top Destination IPs")
                if connection_stats.get('top_destinations'):
                    dest_df = pd.DataFrame({
                        'IP Address': list(connection_stats['top_destinations'].keys()),
                        'Connections': list(connection_stats['top_destinations'].values())
                    })
                    st.dataframe(dest_df, use_container_width=True)
                else:
                    st.info("No destination IP data available.")
            
            # Convert connection data for heatmap
            if connection_stats.get('top_sources') and connection_stats.get('top_destinations'):
                # Create a dataframe for the heatmap
                conn_records = []
                
                # Currently we don't have source-to-destination data in our DB schema
                # This would require modifying the data collection and storage
                # For now, we'll just show a message
                st.info("Connection heatmap requires additional data collection. This feature will be available soon.")
    
    with tab4:
        st.header("Network Reports")
        
        # Time range for reports
        report_range = st.selectbox(
            "Report Period",
            options=["Last 24 Hours", "Last Week", "Last Month"],
            index=0
        )
        
        hours_map = {
            "Last 24 Hours": 24,
            "Last Week": 24 * 7,
            "Last Month": 24 * 30
        }
        
        report_hours = hours_map.get(report_range, 24)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top Bandwidth Consumers")
            top_ips_df = st.session_state.data_store.get_top_ips_by_traffic(limit=10, hours=report_hours)
            
            if not top_ips_df.empty:
                # Add human readable columns
                top_ips_df['Download'] = top_ips_df['total_rx_bytes'].apply(human_readable_size)
                top_ips_df['Upload'] = top_ips_df['total_tx_bytes'].apply(human_readable_size)
                top_ips_df['Total'] = top_ips_df['total_bytes'].apply(human_readable_size)
                
                st.dataframe(
                    top_ips_df[['ip_address', 'Download', 'Upload', 'Total']],
                    use_container_width=True
                )
            else:
                st.info("No traffic data available for this period.")
        
        with col2:
            st.subheader("Bandwidth Usage Summary")
            
            bandwidth_df = st.session_state.data_store.get_bandwidth_history(hours=report_hours)
            
            if not bandwidth_df.empty:
                # Calculate summary statistics
                total_rx = bandwidth_df.groupby('interface')['rx_bytes'].max().sum()
                total_tx = bandwidth_df.groupby('interface')['tx_bytes'].max().sum()
                
                # Create metrics
                st.metric("Total Download", human_readable_size(total_rx))
                st.metric("Total Upload", human_readable_size(total_tx))
                st.metric("Total Traffic", human_readable_size(total_rx + total_tx))
                
                # Average usage per hour
                hours_in_period = min(report_hours, (datetime.now() - bandwidth_df['timestamp'].min().to_pydatetime()).total_seconds() / 3600)
                if hours_in_period > 0:
                    avg_hourly = (total_rx + total_tx) / hours_in_period
                    st.metric("Average Hourly Traffic", human_readable_size(avg_hourly))
            else:
                st.info("No bandwidth data available for this period.")
        
        # Export options
        st.subheader("Export Options")
        export_type = st.selectbox(
            "Select Export Type",
            options=["Bandwidth Data", "IP Traffic Data", "Connection Statistics"]
        )
        
        if st.button("Generate CSV"):
            if export_type == "Bandwidth Data":
                export_df = st.session_state.data_store.get_bandwidth_history(hours=report_hours)
                if not export_df.empty:
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        label="Download Bandwidth Data",
                        data=csv,
                        file_name=f"bandwidth_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("No bandwidth data available for export.")
            
            elif export_type == "IP Traffic Data":
                export_df = st.session_state.data_store.get_ip_traffic_history(hours=report_hours)
                if not export_df.empty:
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        label="Download IP Traffic Data",
                        data=csv,
                        file_name=f"ip_traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("No IP traffic data available for export.")
            
            elif export_type == "Connection Statistics":
                # We need to format the connection stats for export
                # This is a simplified version that just exports top sources and destinations
                connection_stats = st.session_state.data_store.get_connection_stats(hours=report_hours)
                
                if connection_stats:
                    # Create a dataframe for export
                    sources_df = pd.DataFrame({
                        'ip_address': list(connection_stats.get('top_sources', {}).keys()),
                        'connections': list(connection_stats.get('top_sources', {}).values()),
                        'type': ['source'] * len(connection_stats.get('top_sources', {}))
                    })
                    
                    dests_df = pd.DataFrame({
                        'ip_address': list(connection_stats.get('top_destinations', {}).keys()),
                        'connections': list(connection_stats.get('top_destinations', {}).values()),
                        'type': ['destination'] * len(connection_stats.get('top_destinations', {}))
                    })
                    
                    export_df = pd.concat([sources_df, dests_df])
                    
                    if not export_df.empty:
                        csv = export_df.to_csv(index=False)
                        st.download_button(
                            label="Download Connection Statistics",
                            data=csv,
                            file_name=f"connection_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.error("No connection statistics available for export.")
                else:
                    st.error("No connection statistics available for export.")

# Add a footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>Mikrotik Network Monitor | "
    "Built with Streamlit</p>", 
    unsafe_allow_html=True
)

# Stop the background thread when the app is closed
def on_shutdown():
    if 'stop_event' in st.session_state:
        st.session_state.stop_event.set()

# Register the shutdown handler
if hasattr(st, 'experimental_singleton') and callable(getattr(st, 'experimental_singleton')):
    on_shutdown = st.experimental_singleton(on_shutdown)
