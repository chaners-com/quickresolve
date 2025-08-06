#!/usr/bin/env python3
"""
QuickResolve CLI Tool
Command-line interface for managing QuickResolve services
"""

import argparse
import json
import sys
import time
from typing import Optional

import requests

# Default configuration
DEFAULT_MANAGEMENT_URL = "http://localhost:8004"
DEFAULT_SNAPSHOT_URL = "http://localhost:8003"

class QuickResolveCLI:
    """CLI tool for QuickResolve management"""
    
    def __init__(self, management_url: str = DEFAULT_MANAGEMENT_URL, 
                 snapshot_url: str = DEFAULT_SNAPSHOT_URL):
        self.management_url = management_url
        self.snapshot_url = snapshot_url
    
    def _make_request(self, url: str, method: str = "GET", data: Optional[dict] = None) -> dict:
        """Make HTTP request with error handling"""
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Error: Cannot connect to {url}")
            print("   Make sure the service is running and accessible")
            sys.exit(1)
        except requests.exceptions.Timeout:
            print(f"❌ Error: Request timeout for {url}")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    
    def status(self):
        """Show status of all services"""
        print("🔍 Checking QuickResolve services status...")
        
        try:
            # Check management service
            health_data = self._make_request(f"{self.management_url}/health")
            
            print(f"\n📊 QuickResolve Status:")
            print(f"   Overall Status: {'🟢 Healthy' if health_data['status'] == 'healthy' else '🔴 Unhealthy'}")
            print(f"   Services: {health_data['healthy_services']}/{health_data['total_services']} healthy")
            
            print(f"\n📋 Service Details:")
            for service in health_data['services']:
                status_icon = "🟢" if service['health'] else "🔴"
                print(f"   {status_icon} {service['name']:<20} {service['status']:<10} {service['uptime'] or 'N/A'}")
            
            # Check snapshot service
            try:
                snapshot_health = self._make_request(f"{self.snapshot_url}/health")
                print(f"\n📸 Snapshot Service:")
                print(f"   Status: {'🟢 Healthy' if snapshot_health['status'] == 'healthy' else '🔴 Unhealthy'}")
                print(f"   Qdrant Connected: {'✅' if snapshot_health['qdrant_connected'] else '❌'}")
                print(f"   Snapshots: {snapshot_health['snapshots_count']}")
                if snapshot_health['last_snapshot']:
                    print(f"   Last Snapshot: {snapshot_health['last_snapshot']}")
            except:
                print(f"\n📸 Snapshot Service: ❌ Not accessible")
            
        except Exception as e:
            print(f"❌ Error getting status: {e}")
            sys.exit(1)
    
    def shutdown(self, force: bool = False):
        """Perform graceful shutdown"""
        if not force:
            print("⚠️  This will stop all QuickResolve services.")
            response = input("Are you sure? (y/N): ")
            if response.lower() != 'y':
                print("Shutdown cancelled.")
                return
        
        print("🛑 Initiating graceful shutdown...")
        
        try:
            result = self._make_request(f"{self.management_url}/shutdown", method="POST")
            
            print(f"✅ Shutdown completed successfully!")
            print(f"   Duration: {result['duration_seconds']:.2f} seconds")
            print(f"   Services stopped: {len(result['services_stopped'])}")
            
            for service in result['services_stopped']:
                print(f"   - {service}")
                
        except Exception as e:
            print(f"❌ Shutdown failed: {e}")
            sys.exit(1)
    
    def restart_service(self, service_name: str):
        """Restart a specific service"""
        print(f"🔄 Restarting {service_name}...")
        
        try:
            result = self._make_request(f"{self.management_url}/services/{service_name}/restart", method="POST")
            print(f"✅ {service_name} restarted successfully!")
            
        except Exception as e:
            print(f"❌ Failed to restart {service_name}: {e}")
            sys.exit(1)
    
    def create_snapshot(self):
        """Create a new snapshot"""
        print("📸 Creating new snapshot...")
        
        try:
            result = self._make_request(f"{self.snapshot_url}/snapshots", method="POST")
            
            if result['success']:
                snapshot_info = result['snapshot_info']
                print(f"✅ Snapshot created successfully!")
                print(f"   File: {snapshot_info['filename']}")
                print(f"   Size: {snapshot_info['size_bytes']} bytes")
                print(f"   Type: {snapshot_info['snapshot_type']}")
            else:
                print(f"❌ Failed to create snapshot: {result['message']}")
                
        except Exception as e:
            print(f"❌ Error creating snapshot: {e}")
            sys.exit(1)
    
    def list_snapshots(self):
        """List available snapshots"""
        print("📋 Available snapshots:")
        
        try:
            snapshots = self._make_request(f"{self.snapshot_url}/snapshots")
            
            if not snapshots:
                print("   No snapshots found")
                return
            
            for snapshot in snapshots:
                size_mb = snapshot['size_bytes'] / (1024 * 1024)
                print(f"   📄 {snapshot['filename']}")
                print(f"      Size: {size_mb:.2f} MB")
                print(f"      Created: {snapshot['created_at']}")
                print(f"      Type: {snapshot['snapshot_type']}")
                print()
                
        except Exception as e:
            print(f"❌ Error listing snapshots: {e}")
            sys.exit(1)
    
    def download_snapshot(self, filename: str, output_path: Optional[str] = None):
        """Download a snapshot"""
        if not output_path:
            output_path = filename
        
        print(f"⬇️  Downloading snapshot: {filename}")
        
        try:
            response = requests.get(f"{self.snapshot_url}/snapshots/{filename}", stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Snapshot downloaded to: {output_path}")
            
        except Exception as e:
            print(f"❌ Error downloading snapshot: {e}")
            sys.exit(1)
    
    def restore_snapshot(self, filename: str, force: bool = False):
        """Restore from snapshot"""
        if not force:
            print("⚠️  This will restore Qdrant data from snapshot and may overwrite current data.")
            response = input("Are you sure? (y/N): ")
            if response.lower() != 'y':
                print("Restore cancelled.")
                return
        
        print(f"🔄 Restoring from snapshot: {filename}")
        
        try:
            result = self._make_request(f"{self.snapshot_url}/snapshots/{filename}/restore", method="POST")
            
            if result['success']:
                print(f"✅ Snapshot restored successfully!")
            else:
                print(f"❌ Failed to restore snapshot: {result['message']}")
                
        except Exception as e:
            print(f"❌ Error restoring snapshot: {e}")
            sys.exit(1)
    
    def cleanup_snapshots(self):
        """Clean up old snapshots"""
        print("🧹 Cleaning up old snapshots...")
        
        try:
            result = self._make_request(f"{self.snapshot_url}/cleanup", method="POST")
            
            if result['success']:
                print(f"✅ Cleanup completed successfully!")
            else:
                print(f"❌ Cleanup failed: {result['message']}")
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="QuickResolve CLI - Manage your QuickResolve deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  quickresolve-cli.py status                    # Show all services status
  quickresolve-cli.py shutdown                  # Graceful shutdown
  quickresolve-cli.py restart qdrant           # Restart Qdrant service
  quickresolve-cli.py snapshot create          # Create new snapshot
  quickresolve-cli.py snapshot list            # List snapshots
  quickresolve-cli.py snapshot download file.tar.gz  # Download snapshot
  quickresolve-cli.py snapshot restore file.tar.gz   # Restore snapshot
        """
    )
    
    parser.add_argument(
        "--management-url",
        default=DEFAULT_MANAGEMENT_URL,
        help=f"Management service URL (default: {DEFAULT_MANAGEMENT_URL})"
    )
    
    parser.add_argument(
        "--snapshot-url", 
        default=DEFAULT_SNAPSHOT_URL,
        help=f"Snapshot service URL (default: {DEFAULT_SNAPSHOT_URL})"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show status of all services')
    
    # Shutdown command
    shutdown_parser = subparsers.add_parser('shutdown', help='Graceful shutdown of all services')
    shutdown_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Restart command
    restart_parser = subparsers.add_parser('restart', help='Restart a specific service')
    restart_parser.add_argument('service', help='Service name to restart')
    
    # Snapshot commands
    snapshot_parser = subparsers.add_parser('snapshot', help='Snapshot management')
    snapshot_subparsers = snapshot_parser.add_subparsers(dest='snapshot_command', help='Snapshot commands')
    
    snapshot_subparsers.add_parser('create', help='Create new snapshot')
    snapshot_subparsers.add_parser('list', help='List available snapshots')
    snapshot_subparsers.add_parser('cleanup', help='Clean up old snapshots')
    
    download_parser = snapshot_subparsers.add_parser('download', help='Download snapshot')
    download_parser.add_argument('filename', help='Snapshot filename')
    download_parser.add_argument('--output', help='Output path (default: filename)')
    
    restore_parser = snapshot_subparsers.add_parser('restore', help='Restore from snapshot')
    restore_parser.add_argument('filename', help='Snapshot filename')
    restore_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize CLI
    cli = QuickResolveCLI(args.management_url, args.snapshot_url)
    
    # Execute command
    if args.command == 'status':
        cli.status()
    elif args.command == 'shutdown':
        cli.shutdown(force=args.force)
    elif args.command == 'restart':
        cli.restart_service(args.service)
    elif args.command == 'snapshot':
        if args.snapshot_command == 'create':
            cli.create_snapshot()
        elif args.snapshot_command == 'list':
            cli.list_snapshots()
        elif args.snapshot_command == 'cleanup':
            cli.cleanup_snapshots()
        elif args.snapshot_command == 'download':
            cli.download_snapshot(args.filename, args.output)
        elif args.snapshot_command == 'restore':
            cli.restore_snapshot(args.filename, args.force)
        else:
            snapshot_parser.print_help()
            sys.exit(1)

if __name__ == "__main__":
    main() 