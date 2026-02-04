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
