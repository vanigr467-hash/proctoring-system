# 🩸 BloodBridge AI - Emergency Blood Donor Matching System

A comprehensive full-stack web application for emergency blood donor matching with real-time notifications, AI-powered donor matching, and MongoDB persistence.

## 🚀 Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed on your system
- Git (optional, for cloning)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd bloodbridge-ai
```

### 2. Environment Configuration
Copy and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start with Docker Compose
```bash
# Start all services (MongoDB + BloodBridge App)
docker-compose up -d

# View logs
docker-compose logs -f bloodbridge-app

# Stop services
docker-compose down
```

### 4. Access the Application
- **BloodBridge AI**: http://localhost:5000
- **MongoDB**: mongodb://admin:bloodbridge123@localhost:27017/bloodbridge

## 🐳 Docker Services

### MongoDB Container
- **Image**: mongo:7.0
- **Port**: 27017
- **Credentials**: admin / bloodbridge123
- **Database**: bloodbridge
- **Persistence**: Named volume `mongodb_data`

### BloodBridge App Container
- **Build**: Local Dockerfile
- **Port**: 5000
- **Python**: 3.11-slim
- **Restart Policy**: unless-stopped

## 📋 Docker Compose Configuration

The `docker-compose.yml` includes:
- MongoDB with initialization script
- BloodBridge AI application
- Networking between services
- Volume persistence for data
- Environment variable configuration

## 🔧 Development Setup

### Local Development (without Docker)
```bash
# Install dependencies
pip install -r requirements.txt

# Start MongoDB (required)
docker run -d --name bloodbridge-mongo \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=bloodbridge123 \
  mongo:7.0

# Run the application
python app.py
```

### Environment Variables
```bash
# MongoDB Configuration
MONGODB_URI=mongodb://admin:bloodbridge123@localhost:27017/bloodbridge?authSource=admin

# Flask Configuration
SECRET_KEY=bloodbridge-ultra-secure-2024-xK9$mP2#
JWT_SECRET_KEY=jwt-bb-secret-9mN$kL3@qR7
FLASK_ENV=development

# Server Configuration
HOST=0.0.0.0
PORT=5000
DEBUG=False
```

## 🏗️ Dockerfile Details

The Dockerfile includes:
- Python 3.11 slim base image
- System dependencies installation
- Python requirements installation
- Non-root user creation
- Health check endpoint
- Application startup command

## 📊 Features

- **🤖 AI-Powered Matching**: Multi-factor donor scoring algorithm
- **📍 Real-time Notifications**: WebSocket-based instant alerts
- **🔐 JWT Authentication**: Secure token-based auth system
- **📱 Responsive UI**: Modern React frontend
- **🗄️ MongoDB Integration**: Persistent data storage
- **📊 Analytics Dashboard**: Comprehensive admin analytics
- **🌐 REST API**: Full-featured API endpoints

## 🔗 API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Current user info

### Donor Management
- `GET /api/donors` - List donors
- `GET /api/donors/profile` - Get donor profile
- `PUT /api/donors/profile` - Update donor profile
- `PATCH /api/donors/availability` - Toggle availability
- `PATCH /api/donors/location` - Update location

### Blood Requests
- `GET /api/requests` - List requests
- `POST /api/requests` - Create request
- `GET /api/requests/<id>` - Get request details
- `POST /api/requests/<id>/respond` - Respond to request
- `PATCH /api/requests/<id>/status` - Update request status

### Admin
- `GET /api/admin/stats` - System statistics
- `GET /api/admin/users` - User management
- `PATCH /api/admin/users/<id>/toggle` - Toggle user status

## 🎯 Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@bloodbridge.org | admin123 |
| Donor | alice@donor.com | pass123 |
| Hospital | hospital@citygeneral.com | hosp123 |
| Patient | patient@example.com | patient123 |

## 🔍 Monitoring & Logs

### Docker Logs
```bash
# View all logs
docker-compose logs

# Follow specific service
docker-compose logs -f bloodbridge-app
docker-compose logs -f mongodb

# View last 50 lines
docker-compose logs --tail=50 bloodbridge-app
```

### Health Checks
```bash
# Application health
curl http://localhost:5000/api/health

# MongoDB connection
docker exec -it bloodbridge-mongo mongosh --eval "db.adminCommand('ping')"
```

## 🛠️ Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   ```bash
   # Check if MongoDB is running
   docker-compose ps mongodb
   
   # Restart MongoDB
   docker-compose restart mongodb
   ```

2. **Port Already in Use**
   ```bash
   # Check what's using port 5000
   netstat -tulpn | grep :5000
   
   # Kill the process or change port in .env
   ```

3. **Application Won't Start**
   ```bash
   # Check application logs
   docker-compose logs bloodbridge-app
   
   # Rebuild container
   docker-compose up --build -d bloodbridge-app
   ```

### Development Tips

- Use `docker-compose up --build` when modifying requirements.txt
- Volume `mongodb_data` persists across container restarts
- Environment variables in `.env` override defaults
- Use `docker exec -it bloodbridge-app bash` for container access

## 📁 Project Structure

```
bloodbridge-ai/
├── app.py                 # Main Flask application
├── requirements.txt         # Python dependencies
├── Dockerfile             # Application container definition
├── docker-compose.yml     # Multi-service orchestration
├── mongo-init.js        # MongoDB initialization script
├── .env                  # Environment variables (create from .env.example)
└── README.md            # This file
```

## 🔒 Security Considerations

- Change default passwords in production
- Use environment variables for sensitive data
- Enable HTTPS in production (reverse proxy)
- Regularly update base images
- Implement proper backup strategy for MongoDB

## 📈 Production Deployment

For production deployment:
1. Use managed MongoDB service (MongoDB Atlas)
2. Configure reverse proxy (nginx/Apache)
3. Enable SSL/TLS certificates
4. Set up monitoring and logging
5. Implement backup strategies
6. Use environment-specific configurations

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘️ Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review application logs for errors
