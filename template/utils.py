"""
WAHOOPREDICT - Utility functions for hotkey verification.

Provides functions to verify Bittensor hotkey signatures.
"""

import bittensor as bt
from typing import Tuple


def verify_hotkey_signature(
    ss58_address: str,
    message: str,
    signature: str
) -> Tuple[bool, str]:
    """
    Verify a hotkey signature.
    
    This function verifies that a message was signed by the owner of the
    specified SS58 address (hotkey).
    
    Args:
        ss58_address: SS58-encoded hotkey address
        message: The message that was signed
        signature: The signature (hex-encoded)
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if signature is valid, False otherwise
        - error_message: Empty string if valid, error description if invalid
    """
    try:
        # Verify the signature using bittensor
        # The bittensor library provides wallet verification
        # We'll use the keypair verification method
        
        # Create a keypair from the SS58 address
        try:
            keypair = bt.Keypair(ss58_address=ss58_address)
        except Exception as e:
            return False, f"Invalid SS58 address: {str(e)}"
        
        # Verify the signature
        # Bittensor uses sr25519 signatures
        # The message should be the raw bytes
        message_bytes = message.encode('utf-8')
        
        # Verify signature
        # Note: This is a simplified version. In production, you may need
        # to use the actual bittensor wallet verification method
        try:
            # Use bittensor's verification if available
            if hasattr(bt, 'verify_signature'):
                is_valid = bt.verify_signature(
                    public_key=keypair.public_key,
                    message=message_bytes,
                    signature=signature
                )
            else:
                # Fallback: Use keypair's verify method if available
                # This is a placeholder - actual implementation depends on
                # bittensor library version and available methods
                is_valid = keypair.verify(message_bytes, bytes.fromhex(signature))
            
            if is_valid:
                return True, ""
            else:
                return False, "Signature verification failed"
                
        except Exception as e:
            return False, f"Signature verification error: {str(e)}"
            
    except Exception as e:
        return False, f"Verification error: {str(e)}"


def verify_hotkey_on_subnet(
    ss58_address: str,
    netuid: int,
    subtensor: "bt.subtensor.Subtensor"
) -> bool:
    """
    Verify that a hotkey is registered on the subnet.
    
    Args:
        ss58_address: SS58-encoded hotkey address
        netuid: Network UID of the subnet
        subtensor: Subtensor instance
        
    Returns:
        True if hotkey is registered on the subnet, False otherwise
    """
    try:
        metagraph = subtensor.metagraph(netuid=netuid)
        return ss58_address in metagraph.hotkeys
    except Exception as e:
        return False

