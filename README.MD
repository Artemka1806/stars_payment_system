# Stars Payment System

A FastAPI-based Telegram bot system designed for handling Telegram Stars payments. The system supports multiple bots running simultaneously and provides webhook handling for Telegram bot interactions.

## Features

- **Multi-bot Support**: Manage multiple Telegram bots simultaneously
- **FastAPI Integration**: RESTful API with automatic webhook handling
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Secure Webhooks**: Token-based authentication for webhook endpoints
- **Telegram Stars Integration**: Built specifically for Telegram Stars payment system
- **Environment Configuration**: Flexible configuration through environment variables

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Telegram bot tokens (obtain from [@BotFather](https://t.me/botfather))

### Environment Setup

1. Create a `.env` file in the project root:

```env
# API Configuration
API_URL=https://your-domain.com
API_KEY=your_secure_api_key
TELEGRAM_SECRET=your_telegram_webhook_secret

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
| `BOT_TOKEN_*` | Telegram bot tokens (use BOT_TOKEN_1, BOT_TOKEN_2, etc.) | Required |

### Webhook Configuration

The system automatically sets up webhooks for all configured bots. Webhooks are configured at:
```
{API_URL}/bot/{bot_id}/webhook
```

## API Endpoints

- `GET /` - Welcome message
- `POST /bot/{id}/webhook` - Telegram webhook handler for specific bot
- `GET /docs` - Interactive API documentation

## Development

### Local Development Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables
4. **For local development, you need ngrok running on port 8000** to expose your local server for Telegram webhooks:
   ```bash
   ngrok http 8000
   ```
   Use the ngrok URL as your `API_URL` in the `.env` file.

5. Run the application:
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

## Technologies Used

- **FastAPI** - Modern, fast web framework for APIs
- **aiogram** - Async Telegram Bot API framework
- **Pydantic** - Data validation and settings management
- **Docker** - Containerization
- **Python 3.11** - Programming language

## License

This project is licensed under the terms specified in the LICENSE file.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please create an issue in the project repository.
