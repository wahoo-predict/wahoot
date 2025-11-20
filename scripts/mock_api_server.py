#!/usr/bin/env python3
"""
Mock WAHOO API Server

Simulates the WAHOO Predict API endpoint that returns validation data.
Runs in the background and serves data to the validator.
"""

import json
import random
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import logging

from wahoo.validator.mock_data import generate_mock_validation_data, create_real_api_format_example

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store of "registered" miners (simulates miners that registered on subnet)
REGISTERED_MINERS = {
    "5Dnh2o9x9kTRtfeF5g3W4uzfzWNeGD1EJo4aCtibAESzP2iE": True,
    "5FddqPQUhEFeLqVNbenAj6EDRKuqgezciN9TmTgBmNABsj53": True,
    "5E2WWRc41ekrak33NjqZZ338s2sEX5rLCnZXEGKfD52PMqod": True,
    "5EaNWwsjZpoM6RDwgKoukSHJZ2yyEHmGGXogRejdBwCNV9SP": True,
    "5De1Fkvq9g4idEzvr8h8WEEQa1xAeaXfA2TZfYMKgdMm4Qai": True,
}

# Real API format data (your example)
REAL_DATA = create_real_api_format_example()


class MockAPIHandler(BaseHTTPRequestHandler):
    """HTTP handler for mock WAHOO API."""
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        # Validation endpoint
        if path == "/api/v2/event/bittensor/statistics":
            self.handle_validation_endpoint(query_params)
        # Events endpoint
        elif path == "/events":
            self.handle_events_endpoint()
        else:
            self.send_error(404, "Not Found")
    
    def handle_validation_endpoint(self, query_params):
        """Handle validation data requests."""
        hotkeys_param = query_params.get("hotkeys", [""])[0]
        if not hotkeys_param:
            self.send_error(400, "Missing hotkeys parameter")
            return
        
        hotkeys = [hk.strip() for hk in hotkeys_param.split(",") if hk.strip()]
        
        if not hotkeys:
            self.send_error(400, "Empty hotkeys list")
            return
        
        logger.info(f"API: Received request for {len(hotkeys)} hotkeys")
        
        # Generate response data
        response_data = []
        
        for hotkey in hotkeys:
            # Check if miner is "registered" (simulates real scenario)
            if hotkey in REGISTERED_MINERS:
                # Use real data if available, otherwise generate mock
                real_item = next((item for item in REAL_DATA if item["hotkey"] == hotkey), None)
                if real_item:
                    response_data.append(real_item)
                else:
                    # Generate mock data for registered miner
                    from wahoo.validator.models import ValidationRecord
                    mock_record = generate_mock_validation_data([hotkey])[0]
                    # Convert to API format
                    response_data.append({
                        "hotkey": hotkey,
                        "signature": mock_record.signature or f"sig_{random.randint(1000, 9999)}",
                        "message": mock_record.message or f"message_{random.randint(1000, 9999)}",
                        "performance": {
                            "total_volume_usd": str(mock_record.performance.total_volume_usd),
                            "realized_profit_usd": str(mock_record.performance.realized_profit_usd),
                            "unrealized_profit_usd": mock_record.performance.unrealized_profit_usd or 0,
                            "trade_count": mock_record.performance.trade_count or 0,
                            "open_positions_count": mock_record.performance.open_positions_count or 0,
                        }
                    })
            else:
                # Miner not registered - return empty or skip
                logger.debug(f"API: Hotkey {hotkey[:20]}... not registered, skipping")
        
        # Send response
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode())
        
        logger.info(f"API: Returning data for {len(response_data)} miners")
    
    def handle_events_endpoint(self):
        """Handle events endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        response = {
            "active_event_id": "wahoo_test_event",
            "events": [
                {"id": "wahoo_test_event", "name": "Test Event", "active": True}
            ]
        }
        self.wfile.write(json.dumps(response).encode())


def run_mock_api_server(port=8000, host="localhost"):
    """Run the mock API server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, MockAPIHandler)
    
    logger.info("=" * 70)
    logger.info("Mock WAHOO API Server")
    logger.info("=" * 70)
    logger.info(f"Server running on http://{host}:{port}")
    logger.info(f"Registered miners: {len(REGISTERED_MINERS)}")
    logger.info("")
    logger.info("Endpoints:")
    logger.info(f"  GET http://{host}:{port}/api/v2/event/bittensor/statistics?hotkeys=<hotkey1>,<hotkey2>")
    logger.info(f"  GET http://{host}:{port}/events")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 70)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down mock API server...")
        httpd.shutdown()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Mock WAHOO API Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--host", type=str, default="localhost", help="Host to bind to")
    parser.add_argument("--duration", type=int, default=0, help="Run for N seconds (0 = forever)")
    
    args = parser.parse_args()
    
    if args.duration > 0:
        # Run for specified duration in background thread
        server_thread = threading.Thread(
            target=run_mock_api_server,
            args=(args.port, args.host),
            daemon=True
        )
        server_thread.start()
        logger.info(f"Server started, will run for {args.duration} seconds...")
        time.sleep(args.duration)
        logger.info("Duration reached, stopping server...")
    else:
        # Run forever
        run_mock_api_server(args.port, args.host)


if __name__ == "__main__":
    main()

