FROM gigbid-python-base:latest
EXPOSE 8101
CMD ["python", "-m", "mcp_servers.portfolio.server", "--port", "8101"]
