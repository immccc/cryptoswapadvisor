# Crypto Swap Advisor Bot

An independent, non-custodial cryptocurrency trading bot that works both through Telegram and via API-based webhooks.

## About

Crypto Swap Advisor brings transparency to the crypto trading space. The project's objective is to create a trading bot focused on savings and capital preservation with easier configuration than existing alternatives. Unlike other bots that trade on your behalf, this bot provides signals and leaves the responsibility of executing trades to you.

## Features

- Non-custodial: your funds stay in your wallet
- Telegram bot interface for easy interaction
- API-based access through webhooks for custom integrations
- Transparent trading signals with full user control
- Focus on capital preservation and savings growth
- Simple configuration compared to existing alternatives

## Product Launch

- [Product Hunt](https://www.producthunt.com/products/invest-forget)
- [Indie Hackers](https://www.indiehackers/product/invest-and-forget)

## Why This Is Open Source

## Why This Is Open Source

This project achieved its technical goal: a complete, non-custodial signal bot. The whole stack of API, webhooks, Telegram integration, a backtesting engine, and a coin-confidence scoring service is built and shipped solo alongside a full-time Staff Engineer role. So I'm open-sourcing it instead of pursuing commercialization, after diggint a bit into that area. For what I noticed, crypto tools face a structural trust and distribution problem that has little to do with the product itself.

## Installation

### Prerequisites

- Docker and Docker Compose installed
- Git

### Setup

1. Clone the repository:

```bash
git clone https://github.com/immccc/cryptoswapadvisor.git
cd cryptoswapadvisor
```

2. Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your configuration (database credentials, Telegram bot token, API keys, etc.).

3. Build and start the services:

```bash
docker compose -f compose-local.yml up --build -d
```

This will start:
- PostgreSQL database
- Redis
- Svix webhook server
- Bot service
- API service
- Register service
- Backtest broker
- Coin confidence calculator

4. Check the logs to verify everything is running:

```bash
docker compose -f compose-local.yml logs -f
```

### Configuration

Make sure to configure the following in your `.env` file:

- `SQL_USER`, `SQL_PASSWORD`, `SQL_DB`: Database credentials
- `REDIS_HOST`, `REDIS_PORT`: Redis connection details
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from BotFather
- `SVIX_JWT_SECRET`: Secret for webhook authentication
- Any API keys required for crypto data providers

## Disclaimer

This bot provides trading signals only. It does not hold or manage your funds. Always do your own research before making investment decisions. You are solely responsible for any trades you execute based on the signals provided.

## License

See the LICENSE file for details.
