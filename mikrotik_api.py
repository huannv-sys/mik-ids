import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from librouteros import connect
from librouteros.query import Key
import pandas as pd
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MikrotikAPI:
    def __init__(self, host: str, username: str, password: str, port: int = 8728, use_ssl: bool = False):
        """
        Initialize MikrotikAPI connection parameters

        Args:
            host: Router IP address or hostname
            username: Router username
            password: Router password
            port: API port (default 8728 for API, 8729 for API-SSL)
            use_ssl: Whether to use SSL connection
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self.api = None
        self.is_connected = False

    def connect(self) -> bool:
        """
        Connect to Mikrotik router
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            ssl_verify = None
            if self.use_ssl:
                # In production, this should be set to a proper certificate
                ssl_verify = False
                
            self.api = connect(
                host=self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                ssl_verify=ssl_verify
            )
            self.is_connected = True
            logger.info(f"Connected to Mikrotik router at {self.host}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Mikrotik router: {str(e)}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        """
        Disconnect from Mikrotik router
        """
        if self.api and hasattr(self.api, 'close'):
            self.api.close()
        self.is_connected = False
        self.api = None

    def ensure_connection(self) -> bool:
        """
        Ensure the connection to the router is active
        
        Returns:
            bool: True if connected, False otherwise
        """
        if not self.is_connected:
            return self.connect()
        return True

    def get_ip_addresses(self) -> List[Dict[str, Any]]:
        """
        Get all IP addresses from the router
        
        Returns:
            List of dict with IP address information
        """
        if not self.ensure_connection():
            return []
            
        try:
            ip_address_path = self.api.path('/ip/address')
            return list(ip_address_path)
        except Exception as e:
            logger.error(f"Error getting IP addresses: {str(e)}")
            return []
    
    def get_dhcp_leases(self) -> List[Dict[str, Any]]:
        """
        Get all DHCP leases from the router
        
        Returns:
            List of dict with DHCP lease information
        """
        if not self.ensure_connection():
            return []
            
        try:
            dhcp_lease_path = self.api.path('/ip/dhcp-server/lease')
            return list(dhcp_lease_path)
        except Exception as e:
            logger.error(f"Error getting DHCP leases: {str(e)}")
            return []

    def get_active_connections(self) -> List[Dict[str, Any]]:
        """
        Get active connections from the router
        
        Returns:
            List of dict with connection tracking information
        """
        if not self.ensure_connection():
            return []
            
        try:
            connection_path = self.api.path('/ip/firewall/connection')
            return list(connection_path)
        except Exception as e:
            logger.error(f"Error getting active connections: {str(e)}")
            return []

    def get_bandwidth_usage(self) -> Dict[str, Any]:
        """
        Get bandwidth usage from the router interfaces
        
        Returns:
            Dict with interface bandwidth information
        """
        if not self.ensure_connection():
            return {}
            
        try:
            interface_path = self.api.path('/interface')
            interfaces = list(interface_path)
            
            # Create a dictionary with interface name as key and bandwidth info as value
            bandwidth_data = {}
            for interface in interfaces:
                if 'name' in interface and 'tx-byte' in interface and 'rx-byte' in interface:
                    bandwidth_data[interface['name']] = {
                        'tx_bytes': int(interface.get('tx-byte', 0)),
                        'rx_bytes': int(interface.get('rx-byte', 0)),
                        'tx_packets': int(interface.get('tx-packet', 0)),
                        'rx_packets': int(interface.get('rx-packet', 0)),
                        'timestamp': datetime.now().isoformat()
                    }
            
            return bandwidth_data
        except Exception as e:
            logger.error(f"Error getting bandwidth usage: {str(e)}")
            return {}

    def get_traffic_by_ip(self) -> List[Dict[str, Any]]:
        """
        Get traffic usage by IP address
        
        Returns:
            List of dict with IP traffic information
        """
        if not self.ensure_connection():
            return []
            
        try:
            # This requires a firewall rule with action=passthrough and a counter
            # We'll simulate it with connection tracking for now
            connections = self.get_active_connections()
            
            # Aggregate data by IP
            ip_traffic = {}
            for conn in connections:
                src_ip = conn.get('src-address', '').split(':')[0]
                dst_ip = conn.get('dst-address', '').split(':')[0]
                
                if src_ip:
                    if src_ip not in ip_traffic:
                        ip_traffic[src_ip] = {'tx_bytes': 0, 'rx_bytes': 0, 'connections': 0}
                    ip_traffic[src_ip]['tx_bytes'] += int(conn.get('orig-bytes', 0))
                    ip_traffic[src_ip]['connections'] += 1
                
                if dst_ip:
                    if dst_ip not in ip_traffic:
                        ip_traffic[dst_ip] = {'tx_bytes': 0, 'rx_bytes': 0, 'connections': 0}
                    ip_traffic[dst_ip]['rx_bytes'] += int(conn.get('repl-bytes', 0))
                    ip_traffic[dst_ip]['connections'] += 1
            
            # Convert to list of dictionaries
            result = []
            for ip, data in ip_traffic.items():
                result.append({
                    'ip_address': ip,
                    'tx_bytes': data['tx_bytes'],
                    'rx_bytes': data['rx_bytes'],
                    'total_bytes': data['tx_bytes'] + data['rx_bytes'],
                    'connections': data['connections'],
                    'timestamp': datetime.now().isoformat()
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting traffic by IP: {str(e)}")
            return []

    def get_system_resources(self) -> Dict[str, Any]:
        """
        Get system resources from the router
        
        Returns:
            Dict with system resource information
        """
        if not self.ensure_connection():
            return {}
            
        try:
            resource_path = self.api.path('/system/resource')
            resources = list(resource_path)
            if resources:
                return resources[0]
            return {}
        except Exception as e:
            logger.error(f"Error getting system resources: {str(e)}")
            return {}
