FROM mcr.microsoft.com/devcontainers/anaconda:1-3

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    curl \
    ca-certificates \
    docker.io \
    docker-compose \
    && rm -rf /var/lib/apt/lists/*

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf aws awscliv2.zip

# Install Python packages with specific versions
RUN pip install --no-cache-dir \
    boto3>=1.34.0 \
    awscli>=1.32.0 \
    psycopg2-binary>=2.9.9 \
    sqlalchemy>=2.0.0 \
    pandas>=2.2.0 \
    numpy>=1.26.0 \
    matplotlib>=3.8.0 \
    scikit-learn>=1.4.0 \
    jupyter>=1.0.0 \
    python-dotenv>=1.0.0 \
    langchain>=0.1.0 \
    langchain-community>=0.0.10 \
    langchain-aws>=0.0.1 \
    Pillow>=10.0.0 \
    requests>=2.28.0

# Create a script to start services
COPY .devcontainer/start-services.sh /usr/local/bin/start-services.sh
RUN chmod +x /usr/local/bin/start-services.sh