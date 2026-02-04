#!/usr/bin/env python3
"""
GitHub Webhook Listener for TGhelper bot
Listens on port 5355 for GitHub webhook notifications
"""

import os
import hmac
import hashlib
import subprocess
import logging
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Webhook secret from GitHub (should match your GitHub webhook secret)
WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET', 'blowjob')

def verify_github_signature(payload_body, signature_header):
    """Verify GitHub webhook signature"""
    if not signature_header:
        return False
    
    sha_name, signature = signature_header.split('=')
    if sha_name != 'sha256':
        return False
    
    # Create HMAC hex digest
    mac = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'), 
        msg=payload_body, 
        digestmod=hashlib.sha256
    )
    expected_signature = mac.hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

def run_update_script():
    """Run the update script"""
    script_path = os.path.join(os.path.dirname(__file__), 'update_bot.sh')
    
    if not os.path.exists(script_path):
        logger.error(f"Update script not found: {script_path}")
        return False, "Update script not found"
    
    try:
        # Run the update script with full environment
        env = os.environ.copy()
        env['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        
        result = subprocess.run(
            ['/bin/bash', script_path],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
            env=env  # Pass environment with proper PATH
        )
        
        logger.info(f"Update script output:\n{result.stdout}")
        
        if result.stderr:
            logger.error(f"Update script errors:\n{result.stderr}")
        
        success = result.returncode == 0
        message = result.stdout if success else result.stderr
        
        return success, message
        
    except subprocess.TimeoutExpired:
        logger.error("Update script timed out after 5 minutes")
        return False, "Update timed out"
    except Exception as e:
        logger.error(f"Error running update script: {e}")
        return False, str(e)
        
@app.route('/github-webhook', methods=['POST'])
def github_webhook():
    """Handle GitHub webhook POST requests"""
    # Get signature from header
    signature_header = request.headers.get('X-Hub-Signature-256')
    
    # Get payload
    payload_body = request.get_data()
    
    # Verify signature
    if not verify_github_signature(payload_body, signature_header):
        logger.warning("Invalid webhook signature")
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse JSON payload
    try:
        payload = request.get_json()
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        return jsonify({'error': 'Invalid JSON'}), 400
    
    # Check if it's a push to main branch
    event_type = request.headers.get('X-GitHub-Event', 'ping')
    logger.info(f"Received GitHub event: {event_type}")
    
    if event_type == 'ping':
        return jsonify({'message': 'pong'}), 200
    
    elif event_type == 'push':
        # Check if push is to main branch
        ref = payload.get('ref', '')
        if ref != 'refs/heads/main':
            logger.info(f"Ignoring push to branch: {ref}")
            return jsonify({'message': 'Not main branch, ignored'}), 200
        
        logger.info("Push to main branch detected. Starting update...")
        
        # Run update script
        success, message = run_update_script()
        
        if success:
            logger.info("Update completed successfully")
            return jsonify({
                'message': 'Update started successfully',
                'output': message[:500]  # Limit output length
            }), 200
        else:
            logger.error(f"Update failed: {message}")
            return jsonify({
                'error': 'Update failed',
                'details': message[:500]
            }), 500
    
    return jsonify({'message': 'Event ignored'}), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'github-webhook-listener'}), 200

@app.route('/manual-update', methods=['POST'])
def manual_update():
    """Manual update endpoint (requires secret key)"""
    secret = request.args.get('secret', '')
    
    if secret != WEBHOOK_SECRET:
        return jsonify({'error': 'Invalid secret'}), 401
    
    logger.info("Manual update triggered via API")
    
    success, message = run_update_script()
    
    if success:
        return jsonify({
            'message': 'Manual update completed',
            'output': message[:500]
        }), 200
    else:
        return jsonify({
            'error': 'Manual update failed',
            'details': message[:500]
        }), 500

if __name__ == '__main__':
    # Add GITHUB_WEBHOOK_SECRET to your .env file
    app.run(
        host='0.0.0.0',
        port=5355,
        debug=False
    )
