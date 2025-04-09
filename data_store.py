import sqlite3
import pandas as pd
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataStore:
    def __init__(self, db_path: str = "mikrotik_monitor.db"):
        """
        Initialize DataStore with database path
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.initialize_db()
        
    def initialize_db(self) -> None:
        """
        Initialize the database tables if they don't exist
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create traffic by IP table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ip_traffic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                tx_bytes INTEGER NOT NULL,
                rx_bytes INTEGER NOT NULL,
                total_bytes INTEGER NOT NULL,
                connections INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
            ''')
            
            # Create bandwidth usage table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bandwidth_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interface TEXT NOT NULL,
                tx_bytes INTEGER NOT NULL,
                rx_bytes INTEGER NOT NULL,
                tx_packets INTEGER NOT NULL,
                rx_packets INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
            ''')
            
            # Create active connections table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                src_address TEXT NOT NULL,
                dst_address TEXT NOT NULL,
                protocol TEXT NOT NULL,
                orig_bytes INTEGER NOT NULL,
                repl_bytes INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    def store_ip_traffic(self, traffic_data: List[Dict[str, Any]]) -> bool:
        """
        Store IP traffic data in the database
        
        Args:
            traffic_data: List of dictionaries with IP traffic information
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not traffic_data:
            return False
            
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for data in traffic_data:
                cursor.execute(
                    '''
                    INSERT INTO ip_traffic 
                    (ip_address, tx_bytes, rx_bytes, total_bytes, connections, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        data['ip_address'],
                        data['tx_bytes'],
                        data['rx_bytes'],
                        data['total_bytes'],
                        data['connections'],
                        data['timestamp']
                    )
                )
            
            conn.commit()
            logger.info(f"Stored {len(traffic_data)} IP traffic records")
            return True
        except Exception as e:
            logger.error(f"Error storing IP traffic data: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()
    
    def store_bandwidth_usage(self, bandwidth_data: Dict[str, Any]) -> bool:
        """
        Store bandwidth usage data in the database
        
        Args:
            bandwidth_data: Dictionary with interface bandwidth information
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not bandwidth_data:
            return False
            
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for interface, data in bandwidth_data.items():
                cursor.execute(
                    '''
                    INSERT INTO bandwidth_usage 
                    (interface, tx_bytes, rx_bytes, tx_packets, rx_packets, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        interface,
                        data['tx_bytes'],
                        data['rx_bytes'],
                        data['tx_packets'],
                        data['rx_packets'],
                        data['timestamp']
                    )
                )
            
            conn.commit()
            logger.info(f"Stored bandwidth usage for {len(bandwidth_data)} interfaces")
            return True
        except Exception as e:
            logger.error(f"Error storing bandwidth usage data: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()
    
    def store_active_connections(self, connection_data: List[Dict[str, Any]]) -> bool:
        """
        Store active connections data in the database
        
        Args:
            connection_data: List of dictionaries with connection information
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not connection_data:
            return False
            
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            
            for data in connection_data:
                src_address = data.get('src-address', '')
                dst_address = data.get('dst-address', '')
                protocol = data.get('protocol', '')
                orig_bytes = int(data.get('orig-bytes', 0))
                repl_bytes = int(data.get('repl-bytes', 0))
                
                cursor.execute(
                    '''
                    INSERT INTO active_connections 
                    (src_address, dst_address, protocol, orig_bytes, repl_bytes, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        src_address,
                        dst_address,
                        protocol,
                        orig_bytes,
                        repl_bytes,
                        timestamp
                    )
                )
            
            conn.commit()
            logger.info(f"Stored {len(connection_data)} active connections")
            return True
        except Exception as e:
            logger.error(f"Error storing active connections data: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_ip_traffic_history(self, ip_address: Optional[str] = None, 
                              hours: int = 24) -> pd.DataFrame:
        """
        Get IP traffic history from the database
        
        Args:
            ip_address: Optional IP address to filter by
            hours: Number of hours to look back
            
        Returns:
            DataFrame with IP traffic history
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = '''
            SELECT * FROM ip_traffic
            WHERE timestamp >= ?
            '''
            params = [
                (datetime.now() - timedelta(hours=hours)).isoformat()
            ]
            
            if ip_address:
                query += ' AND ip_address = ?'
                params.append(ip_address)
                
            query += ' ORDER BY timestamp'
            
            df = pd.read_sql_query(query, conn, params=params)
            return df
        except Exception as e:
            logger.error(f"Error getting IP traffic history: {str(e)}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
    
    def get_bandwidth_history(self, interface: Optional[str] = None, 
                             hours: int = 24) -> pd.DataFrame:
        """
        Get bandwidth usage history from the database
        
        Args:
            interface: Optional interface to filter by
            hours: Number of hours to look back
            
        Returns:
            DataFrame with bandwidth usage history
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = '''
            SELECT * FROM bandwidth_usage
            WHERE timestamp >= ?
            '''
            params = [
                (datetime.now() - timedelta(hours=hours)).isoformat()
            ]
            
            if interface:
                query += ' AND interface = ?'
                params.append(interface)
                
            query += ' ORDER BY timestamp'
            
            df = pd.read_sql_query(query, conn, params=params)
            return df
        except Exception as e:
            logger.error(f"Error getting bandwidth history: {str(e)}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
    
    def get_top_ips_by_traffic(self, limit: int = 10, 
                              hours: int = 24) -> pd.DataFrame:
        """
        Get top IPs by traffic usage from the database
        
        Args:
            limit: Number of top IPs to return
            hours: Number of hours to look back
            
        Returns:
            DataFrame with top IPs by traffic
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = '''
            SELECT ip_address, 
                   SUM(tx_bytes) as total_tx_bytes,
                   SUM(rx_bytes) as total_rx_bytes,
                   SUM(total_bytes) as total_bytes,
                   MAX(timestamp) as last_seen
            FROM ip_traffic
            WHERE timestamp >= ?
            GROUP BY ip_address
            ORDER BY total_bytes DESC
            LIMIT ?
            '''
            
            params = [
                (datetime.now() - timedelta(hours=hours)).isoformat(),
                limit
            ]
            
            df = pd.read_sql_query(query, conn, params=params)
            return df
        except Exception as e:
            logger.error(f"Error getting top IPs by traffic: {str(e)}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
    
    def get_connection_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get connection statistics from the database
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with connection statistics
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total number of connections
            cursor.execute(
                '''
                SELECT COUNT(*) FROM active_connections
                WHERE timestamp >= ?
                ''',
                [(datetime.now() - timedelta(hours=hours)).isoformat()]
            )
            total_connections = cursor.fetchone()[0]
            
            # Get connections by protocol
            cursor.execute(
                '''
                SELECT protocol, COUNT(*) as count
                FROM active_connections
                WHERE timestamp >= ?
                GROUP BY protocol
                ORDER BY count DESC
                ''',
                [(datetime.now() - timedelta(hours=hours)).isoformat()]
            )
            protocol_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get top source IPs
            cursor.execute(
                '''
                SELECT src_address, COUNT(*) as count
                FROM active_connections
                WHERE timestamp >= ?
                GROUP BY src_address
                ORDER BY count DESC
                LIMIT 10
                ''',
                [(datetime.now() - timedelta(hours=hours)).isoformat()]
            )
            top_sources = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get top destination IPs
            cursor.execute(
                '''
                SELECT dst_address, COUNT(*) as count
                FROM active_connections
                WHERE timestamp >= ?
                GROUP BY dst_address
                ORDER BY count DESC
                LIMIT 10
                ''',
                [(datetime.now() - timedelta(hours=hours)).isoformat()]
            )
            top_destinations = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                'total_connections': total_connections,
                'protocol_counts': protocol_counts,
                'top_sources': top_sources,
                'top_destinations': top_destinations
            }
        except Exception as e:
            logger.error(f"Error getting connection stats: {str(e)}")
            return {}
        finally:
            if conn:
                conn.close()
