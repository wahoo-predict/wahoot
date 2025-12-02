#!/usr/bin/env python3
"""
Mock Wahoo API Server for Local Net Testing

This server mimics the Wahoo API endpoints needed for validator testing.
Run with: python -m tests.mock_wahoo_api
"""

import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Store mock data per hotkey
MOCK_DATA: Dict[str, Dict] = {}


def generate_mock_performance_data(hotkey: str) -> Dict:
    """Generate realistic mock performance data for a hotkey"""
    # Use hotkey hash for consistent but varied data
    seed = hash(hotkey) % 10000
    random.seed(seed)
    
    return {
        "total_volume_usd": round(random.uniform(1000.0, 50000.0), 2),
        "trade_count": random.randint(50, 1000),
        "realized_profit_usd": round(random.uniform(-5000.0, 10000.0), 2),
        "unrealized_profit_usd": round(random.uniform(-500.0, 2000.0), 2),
        "win_rate": round(random.uniform(0.4, 0.85), 3) if random.random() > 0.1 else None,
        "total_fees_paid_usd": round(random.uniform(10.0, 500.0), 2),
        "open_positions_count": random.randint(0, 30),
        "last_active_timestamp": (datetime.utcnow() - timedelta(minutes=random.randint(1, 1440))).isoformat() + "Z",
        "referral_count": random.randint(0, 20),
        "referral_volume_usd": round(random.uniform(0.0, 10000.0), 2),
    }


def get_mock_validation_record(hotkey: str) -> Dict:
    """Get or generate mock validation record for a hotkey"""
    if hotkey not in MOCK_DATA:
        MOCK_DATA[hotkey] = {
            "hotkey": hotkey,
            "signature": f"mock_sig_{hash(hotkey) % 10000}",
            "message": f"mock_msg_{hash(hotkey) % 10000}",
            "performance": generate_mock_performance_data(hotkey),
            "wahoo_user_id": f"user_{hash(hotkey) % 100000}",
        }
    return MOCK_DATA[hotkey]


class MockWahooAPIHandler(BaseHTTPRequestHandler):
    """HTTP handler for mock Wahoo API endpoints"""
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path.startswith("/api/v2/event/bittensor/statistics"):
            self.handle_validation_endpoint()
        elif self.path.startswith("/events") or self.path == "/events":
            self.handle_active_event()
        else:
            self.send_error(404, f"Not Found: {self.path}")
    
    def handle_validation_endpoint(self):
        """Handle /api/v2/event/bittensor/statistics"""
        try:
            # Parse query parameters
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            # Get hotkeys from query
            hotkeys_str = params.get("hotkeys", [""])[0]
            if not hotkeys_str:
                self.send_error(400, "Missing hotkeys parameter")
                return
            
            hotkeys = [h.strip() for h in hotkeys_str.split(",") if h.strip()]
            if not hotkeys:
                self.send_error(400, "Empty hotkeys list")
                return
            
            # Generate mock data for each hotkey
            records = [get_mock_validation_record(hk) for hk in hotkeys]
            
            # Send response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(records).encode())
            
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {e}")
    
    def handle_active_event(self):
        """Handle /events - returns active event ID (matches get_active_event_id format)"""
        try:
            # Return a mock event ID in the format expected by get_active_event_id
            # It looks for: active_event_id, event_id, id, or event
            event_data = {
                "active_event_id": "test_event_local_net_123",
                "event_id": "test_event_local_net_123",  # Fallback
                "name": "Test Event for Local Net",
                "status": "active",
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(event_data).encode())
            
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {e}")
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run_mock_server(port: int = 8000, host: str = "127.0.0.1"):
    """Run the mock API server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, MockWahooAPIHandler)
    print(f"Mock Wahoo API server running on http://{host}:{port}")
    print("Endpoints:")
    print(f"  - GET http://{host}:{port}/api/v2/event/bittensor/statistics?hotkeys=<comma_separated>")
    print(f"  - GET http://{host}:{port}/events (returns active_event_id)")
    print("\nPress Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_mock_server(port=port)

