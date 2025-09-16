FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app

# Configure UV for container environment
ENV UV_SYSTEM_PYTHON=1 UV_COMPILE_BYTECODE=1



COPY requirements.txt requirements.txt
# Install from requirements file
RUN uv pip install -r requirements.txt




RUN uv pip install aws-opentelemetry-distro>=0.10.1


# Set AWS region environment variable

ENV AWS_REGION=us-east-1
ENV AWS_DEFAULT_REGION=us-east-1


# Signal that this is running in Docker for host binding logic
ENV DOCKER_CONTAINER=1

ENV OTEL_PYTHON_DISTRO=aws_distro
ENV OTEL_PYTHON_CONFIGURATOR=aws_configurator
ENV OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://xray.us-east-1.amazonaws.com/v1/traces
ENV OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
ENV OTEL_RESOURCE_ATTRIBUTES=service.name={agent_name}
ENV AGENT_OBSERVABILITY_ENABLED=true
ENV OTEL_EXPORTER_OTLP_LOGS_HEADERS=x-aws-log-group=bedrock-agentcore-observability,x-aws-log-stream=default,x-aws-metric-namespace=bedrock-agentcore
ENV OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=bedrock-agentcore,strands-agents,strands-agents-tools,boto3sqs,botocore,requests,urllib3,httpx,aiohttp-client,asyncio,threading,logging,system_metrics,psutil,sqlite3,redis,pymongo,sqlalchemy,django,flask,tornado,pyramid,falcon,starlette,fastapi,websockets

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

# Copy entire project (respecting .dockerignore)
COPY . .

# Use the full module path

CMD ["opentelemetry-instrument", "python", "-m", "banking_agent"]
