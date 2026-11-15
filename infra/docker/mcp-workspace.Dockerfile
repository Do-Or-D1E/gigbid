FROM gigbid-python-base:latest
EXPOSE 8103
CMD ["python", "-m", "mcp_servers.workspace.server", "--port", "8103"]
