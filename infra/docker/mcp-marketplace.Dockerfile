FROM gigbid-python-base:latest
EXPOSE 8102
CMD ["python", "-m", "mcp_servers.marketplace.server", "--port", "8102"]
