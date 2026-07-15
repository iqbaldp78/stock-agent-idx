import re
with open('/home/hamboo/my-product/stock-agent-idx/scheduler.py', 'r') as f:
    content = f.read()

# Add func
if "run_ihsg_performance_check" not in content:
    func_str = """
def run_ihsg_performance_check():
    logger.info("=== IHSG PERFORMANCE CHECK START ===")
    try:
        import subprocess
        result = subprocess.run(["python", "scripts/validate_ihsg_performance.py"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"IHSG Performance Check failed: {result.stderr}")
        else:
            for line in result.stdout.split('\\n'):
                if line.strip(): logger.info(f"  {line}")
    except Exception as e:
        logger.error(f"IHSG Performance Check error: {e}")
    logger.info("=== IHSG PERFORMANCE CHECK END ===")

def main():"""
    content = content.replace("def main():", func_str)

# Add schedule
if "ihsg_performance_check" not in content:
    sched_str = """
    scheduler.add_job(
        run_ihsg_performance_check,
        CronTrigger(day_of_week="mon-fri", hour=18, minute=0),
        id="ihsg_performance_check",
        name="IHSG Accuracy Validation",
    )

    try:"""
    content = content.replace("    try:", sched_str)

with open('/home/hamboo/my-product/stock-agent-idx/scheduler.py', 'w') as f:
    f.write(content)
