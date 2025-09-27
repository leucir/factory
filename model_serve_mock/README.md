# Model Serve Mock

This directory contains a mock implementation of the model inference server that will eventually be running the actual model serving. It provides OpenAI-compatible endpoints for testing and development purposes.

## Purpose

This mock service simulates the behavior of a production model inference API without requiring access to the actual model serving infrastructure. It's designed to:

- **Enable Testing**: Allow developers to test integration points without relying on live inference APIs
- **Facilitate Development**: Provide a controlled environment that mimics real API responses
- **Support CI/CD**: Enable automated testing in environments where real model APIs aren't available

## API Endpoints

The mock service provides OpenAI-compatible endpoints:

### Completions
- **POST** `/v1/completions` - Generate text completions
- **POST** `/v1/chat/completions` - Generate chat completions

### System
- **GET** `/healthz` - Health check endpoint

## Usage

### Running the Mock Server

```bash
# Install dependencies
pip install -r requirements-app.txt

# Run the server
python main.py
```

The server will start on `http://localhost:8080`.

### Example API Calls

#### Text Completions
```bash
curl -X POST http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "prompt": "Hello, world!",
    "max_tokens": 50
  }'
```

#### Chat Completions
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "max_tokens": 50
  }'
```

## Implementation Details

- **Deterministic Responses**: The mock returns predictable responses for consistent testing
- **OpenAI Format**: Request/response structures match OpenAI API specifications
- **FastAPI Framework**: Built using FastAPI for high performance and automatic documentation
- **Health Monitoring**: Includes health check endpoint for service monitoring

## Limitations

- **Mock Responses Only**: Returns simulated responses, not actual model outputs
- **Development/Testing Only**: Not suitable for production use
- **Limited Functionality**: Implements core endpoints but may not support all OpenAI features

## Integration

This mock service is integrated into the factory's Docker images and CI/CD pipeline:

- **Docker Integration**: Packaged as part of the layered Docker images
- **CI Testing**: Used in smoke tests to verify service functionality
- **Development**: Enables local development without external dependencies

## Future Migration

This mock will eventually be replaced with a real model inference server that provides:

- **Actual Model Inference**: Real LLM model serving capabilities
- **Production Performance**: Optimized for production workloads
- **Full OpenAI Compatibility**: Complete implementation of OpenAI API features
- **Scalability**: Support for high-throughput inference requests
