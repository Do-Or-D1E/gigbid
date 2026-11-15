FROM gigbid-python-base:latest
CMD ["arq", "worker.arq_worker.WorkerSettings"]
