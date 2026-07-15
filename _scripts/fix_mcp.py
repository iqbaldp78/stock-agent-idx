import yaml
import os

with open(os.path.expanduser('~/.hermes/config.yaml'), 'r') as f:
    config = yaml.safe_load(f)

config['mcp_servers']['postgres']['args'] = ['-y', '@modelcontextprotocol/server-postgres', 'postgresql://stockuser:stockpassword@localhost:5121/stockagent']

with open(os.path.expanduser('~/.hermes/config.yaml'), 'w') as f:
    yaml.safe_dump(config, f)
