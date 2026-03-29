FROM python:3.12-slim
WORKDIR /app
COPY receiver.py .
RUN mkdir -p /data/gps
ENV DATA_DIR=/data/gps
CMD ["python3", "receiver.py"]
