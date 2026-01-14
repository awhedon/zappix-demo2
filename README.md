# Zappix + Aldea AI Demo

A comprehensive conversational AI health assessment demo that integrates voice AI with digital engagement. This demo showcases an end-to-end experience that begins with a voice call and seamlessly transitions into a digital interaction.

## 🎯 Demo Flow

1. **Outbound Call** - Aldea AI initiates a call to conduct a health assessment
2. **Authentication** - User authenticates using date of birth, zip code, or SSN (2 of 3)
3. **Health Assessment** - AI asks a series of health-related questions
4. **SMS Opt-in** - User opts in to receive a form review link via SMS
5. **Digital Review** - User reviews and signs the completed form
6. **Submission** - Form is submitted and emailed to the designated recipient

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Voice AI**: 
  - Deepgram (Speech-to-Text)
  - Cartesia (Text-to-Speech)
  - OpenAI GPT-4 (Conversation)
- **Telephony**: Twilio (Calls & SMS)
- **Real-time**: LiveKit
- **Storage**: Redis (Sessions), PostgreSQL (Optional)

### Frontend
- **Framework**: Next.js 14
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **Components**: React Signature Canvas

### Infrastructure
- **IaC**: Terraform
- **Frontend Hosting**: S3 + CloudFront
- **Backend Hosting**: AWS ECS (Fargate)
- **Container Registry**: Amazon ECR
- **Load Balancing**: Application Load Balancer

## 🚀 Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker
- AWS CLI configured
- Terraform 1.0+

### Local Development

1. **Clone the repository**
   ```bash
   git clone git@github.com:awhedon/zappix-demo2.git
   cd zappix-demo2
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your credentials
   uvicorn app.main:app --reload
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local with your API URL
   npm run dev
   ```

4. **Start Redis** (for session storage)
   ```bash
   docker run -d -p 6379:6379 redis:alpine
   ```

## 📋 Environment Variables

### Backend (.env)

```env
# Application
APP_ENV=development
APP_SECRET_KEY=your-secret-key
BACKEND_URL=https://zappix2-backend.aldea.ai
FRONTEND_URL=https://zappix2.aldea.ai

# LiveKit
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# Twilio
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# OpenAI
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4-turbo-preview

# Deepgram (STT)
DEEPGRAM_API_KEY=your-api-key
DEEPGRAM_BASE_URL=https://api.deepgram.com

# Cartesia (TTS)
CARTESIA_API_KEY=your-api-key
CARTESIA_BASE_URL=https://api.cartesia.ai
CARTESIA_VOICE_ID=your-voice-id

# Redis
REDIS_URL=redis://localhost:6379

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
NOTIFICATION_EMAIL=sales@zappix.com
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=https://zappix2-backend.aldea.ai
```

## 🏗️ Deployment

### Infrastructure Setup

1. **Configure Terraform variables**
   ```bash
   cd terraform/environments/production
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your configuration
   ```

2. **Deploy infrastructure**
   ```bash
   ./scripts/setup-infrastructure.sh
   ```

### Application Deployment

**Backend:**
```bash
./scripts/deploy-backend.sh
```

**Frontend:**
```bash
./scripts/deploy-frontend.sh
```

Or use GitHub Actions - push to `main` branch triggers automatic deployment.

## 📁 Project Structure

```
zappix-demo2/
├── backend/
│   ├── app/
│   │   ├── agents/          # AI conversation agents
│   │   ├── models/          # Pydantic schemas
│   │   ├── routers/         # API routes
│   │   ├── services/        # External service integrations
│   │   ├── config.py        # Configuration
│   │   └── main.py          # FastAPI application
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── lib/             # Utilities and API client
│   │   ├── pages/           # Next.js pages
│   │   └── styles/          # Global styles
│   ├── package.json
│   └── next.config.js
├── terraform/
│   ├── environments/
│   │   └── production/      # Production environment
│   └── modules/             # Reusable Terraform modules
│       ├── alb/
│       ├── cloudfront/
│       ├── ecr/
│       ├── ecs/
│       └── vpc/
├── scripts/                 # Deployment scripts
└── README.md
```

## 🌐 URLs

- **Frontend**: https://zappix2.aldea.ai
- **Backend API**: https://zappix2-backend.aldea.ai
- **Health Check**: https://zappix2-backend.aldea.ai/health
- **API Docs**: https://zappix2-backend.aldea.ai/docs

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/calls/outbound` | Initiate an outbound call |
| GET | `/api/calls/session/{session_id}` | Get session details |
| POST | `/api/calls/sms/{session_id}` | Send SMS with form link |
| GET | `/api/forms/{session_id}` | Get pre-populated form data |
| POST | `/api/forms/{session_id}/submit` | Submit signed form |
| POST | `/api/twilio/voice/{session_id}` | Twilio voice webhook |
| WS | `/api/twilio/media-stream/{session_id}` | Real-time audio stream |

## 🌍 Multilingual Support

The demo supports both English and Spanish:
- Language detection during the call
- Bilingual AI responses
- Localized form interface
- SMS messages in preferred language

## 📝 License

Copyright © 2024 Zappix + Aldea AI

## 🤝 Support

For questions or support, contact:
- Email: sales@zappix.com

