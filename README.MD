# Stars Payment System

A FastAPI-based Telegram bot system designed for handling Telegram Stars payments with MongoDB data persistence. The system supports multiple bots running simultaneously, provides webhook handling for Telegram bot interactions, and stores all payment transactions and user data in MongoDB for analytics and reporting.

## Project Overview

The Stars Payment System is a comprehensive solution for managing Telegram Stars payments across multiple Telegram bots. It provides a unified API for handling payments, user management, and transaction tracking. The system is built with modern Python technologies and follows microservices architecture principles.

### Core Components

- **FastAPI Application**: RESTful API server handling webhooks and bot management
- **MongoDB Database**: Persistent storage for users, transactions, and bot configurations
- **Telegram Bot Integration**: Multiple bot support with aiogram framework
- **Payment Processing**: Telegram Stars payment handling and validation
- **Webhook Management**: Automatic webhook configuration and validation

## Features

- **Multi-bot Support**: Manage multiple Telegram bots simultaneously
- **FastAPI Integration**: RESTful API with automatic webhook handling
- **MongoDB Integration**: Persistent data storage for users, transactions, and analytics
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Secure Webhooks**: Token-based authentication for webhook endpoints
- **Telegram Stars Integration**: Built specifically for Telegram Stars payment system
- **Environment Configuration**: Flexible configuration through environment variables
- **Transaction Tracking**: Complete audit trail of all payment transactions
- **User Management**: Comprehensive user profiles and payment history
- **Analytics Ready**: Data structure optimized for reporting and analytics

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Telegram bot tokens (obtain from [@BotFather](https://t.me/botfather))
- MongoDB (included in Docker Compose setup)

### Environment Setup

1. Create a `.env` file in the project root:

```env
# API Configuration
API_URL=https://your-domain.com
API_KEY=your_secure_api_key
TELEGRAM_SECRET=your_telegram_webhook_secret

# MongoDB Configuration
MONGODB_URL=mongodb://mongodb:27017
MONGODB_DATABASE=stars_payment_system
MONGODB_USERNAME=admin
MONGODB_PASSWORD=secure_password

# Bot Tokens (add as many as needed)
BOT_TOKEN_1=your_first_bot_token_here
BOT_TOKEN_2=your_second_bot_token_here
# BOT_TOKEN_N=additional_bot_tokens...
```

### Running the Application

Start the application with Docker Compose:

```bash
docker-compose up -d --force-recreate --remove-orphans --build
```

The application will be available at:
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MongoDB**: http://localhost:8001

### Stopping the Application

```bash
docker-compose down
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_URL` | Public URL where your API is accessible | `https://api.example.com` |
| `API_KEY` | Secret key for API authentication | `example_api_key` |
| `TELEGRAM_SECRET` | Secret token for webhook validation | `example_telegram_secret` |
| `MONGODB_URL` | MongoDB connection string | `mongodb://mongodb:27017` |
| `MONGODB_DATABASE` | Database name | `stars_payment_system` |
| `MONGODB_USERNAME` | MongoDB username | `admin` |
| `MONGODB_PASSWORD` | MongoDB password | `secure_password` |
| `BOT_TOKEN_*` | Telegram bot tokens (use BOT_TOKEN_1, BOT_TOKEN_2, etc.) | Required |

### Webhook Configuration

The system automatically sets up webhooks for all configured bots. Webhooks are configured at:
```
{API_URL}/bot/{bot_id}/webhook
```

## Development

### Local Development Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables
4. Start MongoDB locally or use Docker:
   ```bash
   docker run -d --name mongodb -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=secure_password mongo:latest
   ```
5. **For local development, you need ngrok running on port 8000** to expose your local server for Telegram webhooks:
   ```bash
   ngrok http 8000
   ```
   Use the ngrok URL as your `API_URL` in the `.env` file.

6. Run the application:
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

## Technologies Used

- **FastAPI** - Modern, fast web framework for APIs
- **MongoDB** - NoSQL database for flexible data storage
- **Motor** - Async MongoDB driver for Python
- **aiogram** - Async Telegram Bot API framework
- **Pydantic** - Data validation and settings management
- **Docker** - Containerization
- **Python 3.11** - Programming language

## Security Features

- **Webhook Validation**: All incoming webhooks are validated using Telegram's secret token
- **API Authentication**: Secure API access with key-based authentication
- **Data Encryption**: Sensitive data is encrypted at rest
- **Input Validation**: All inputs are validated using Pydantic models

## License

This project is licensed under the [MIT License](LICENSE).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
6. Submit a pull request

## Support

For issues and questions, please create an issue in the project repository.
