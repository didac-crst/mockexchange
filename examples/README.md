# MockExchange Examples

This directory contains examples and tools that demonstrate how to use the MockExchange platform.

## Available Examples

### [Order Generator](./order-generator/)

A Dockerized order generator that simulates trading activity by generating random orders. Perfect for:

- **Load testing** - Stress test your MockExchange instance
- **Demo purposes** - Show realistic trading activity
- **Development** - Test your trading strategies against live data
- **Learning** - Understand how the platform handles different order types

**Features:**
- Continuous random order generation
- Configurable trading parameters
- Docker-based deployment
- Real-time logging and monitoring

**Quick Start:**
```bash
# Ensure MockExchange stack is running
make start

# Start the order generator
cd examples/order-generator
cp .env.example .env
# Edit .env with your API settings
./manage.sh start --reset
```

**Makefile commands:**
```bash
make order-generator              # Fresh start with reset
make order-generator-restart      # Continue without reset
make order-generator-restart-reset # Continue with reset
make order-generator-logs         # View logs
make order-generator-stop         # Stop the generator
make order-generator-status       # Check status
```

## Future Examples

We plan to add more examples including:

- **Trading Strategies** - Example algorithmic trading strategies
- **Data Feeds** - Custom price feed implementations
- **Integrations** - Third-party service integrations
- **Performance Testing** - Load and stress testing tools

## Contributing

To add a new example:

1. Create a new directory in `examples/`
2. Include a comprehensive README
3. Make it self-contained with its own dependencies
4. Follow the existing naming conventions (kebab-case)
5. Update this README with a description

## Best Practices

- **Self-contained** - Each example should have its own dependencies
- **Well-documented** - Clear README with usage instructions
- **Configurable** - Use environment variables for configuration
- **Docker-ready** - Provide Docker setup when possible
- **Production-ready** - Examples should work in real environments
