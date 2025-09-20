# K2 Notion General Manager Bot

## Project Overview

The **K2 Notion General Manager Bot** is a production-grade conversational AI system that provides personalized leadership guidance through Telegram. The bot dynamically adapts its communication style based on individual user profiles stored in Notion databases, incorporating personality traits like MBTI types, Enneagram profiles, and other relevant characteristics to deliver targeted, outcome-oriented management advice.

## Author & Licensing

**Author:** Ladios Satō  
**Email:** ladiossato@gmail.com  
**Version:** 1.0.1-Production  
**License:** All Rights Reserved  

---

### Copyright Notice

**Copyright (c) 2025 Ladios Satō. All rights reserved.**

This software is the proprietary and confidential property of Ladios Satō. No part of this software may be reproduced, distributed, or transmitted in any form or by any means, including photocopying, recording, or other electronic or mechanical methods, without the prior written permission of the author, except in the case of brief quotations embodied in critical reviews and certain other noncommercial uses permitted by copyright law.

### Licensing Terms

- **Commercial Use:** Prohibited without explicit written permission
- **Distribution:** Prohibited without explicit written permission  
- **Modification:** Prohibited without explicit written permission
- **Private Use:** Allowed for authorized users only
- **Patent Use:** Not granted

For licensing inquiries, commercial use permissions, or custom development requests, contact: **ladiossato@gmail.com**

### Disclaimer

This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall Ladios Satō be liable for any claim, damages or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the software or the use or other dealings in the software.

---

## Features

### Core Functionality
- **🤖 AI-Powered Conversations:** GPT-4 integration with dynamic personality adaptation
- **👥 User Authorization:** Notion-based access control with granular permissions
- **🧠 Memory System:** Persistent conversation history with configurable context windows
- **🔒 Private Chat Enforcement:** Automatic redirection of group messages to private conversations
- **⚡ Rate Limiting:** Built-in protection against API abuse and spam
- **📊 Professional Logging:** Comprehensive request tracing and error handling
- **🚀 Production Ready:** Railway-compatible deployment with health checks

### Advanced Features  
- **Personality Adaptation:** Leverages MBTI, Enneagram, and custom profile data
- **Context-Aware Responses:** Maintains conversation continuity across sessions
- **Admin Commands:** User management and system diagnostics
- **Graceful Error Handling:** Comprehensive fallback systems
- **Multi-Format Support:** Handles various Notion property types

## System Requirements

- **Python:** 3.8 or higher
- **Operating System:** Linux, macOS, or Windows
- **Memory:** Minimum 512MB RAM
- **Storage:** 100MB free space for logs and conversations
- **Network:** Stable internet connection for API access

## Installation & Setup

### 1. Clone or Download Project Files

Ensure you have all the required files:
```
k2_notion_general_manager.py    # Main application
config.py                       # Configuration management
file_operations.py             # Conversation persistence
openai_integration.py          # AI chat logic
system_prompt.txt              # AI personality definition
requirements.txt               # Python dependencies
.env.sample                    # Environment template
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the environment template and configure your credentials:

```bash
cp .env.sample .env
```

Edit `.env` with your actual credentials:

```env
# Required Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
NOTION_TOKEN=your_notion_integration_token
EMPLOYEES_DB_ID=your_employees_database_id
OPENAI_API_KEY=your_openai_api_key

# Optional Configuration  
OPENAI_MODEL=gpt-4-0125-preview
MAX_TOKENS=500
PORT=8000
```

### 4. Notion Database Setup

Your Notion employee database must include these properties:

#### Required Properties:
- **Name** (Title) - Employee full name
- **active** (Checkbox) - Whether employee is active
- **telegram_user_id** (Number) - User's Telegram ID
- **can_chat_bot** (Checkbox) - AI chat access permission
- **context_lines** (Number) - Conversation memory length (default: 20)
- **admin** (Checkbox) - Admin privileges for user management commands

#### Optional Profile Properties:
- **telegram_handle** (Rich Text) - @username
- **MBTI_Type** (Select) - Myers-Briggs personality type
- **Enneagram_Type** (Select) - Enneagram personality type  
- **Role** (Rich Text) - Job title or position
- **Department** (Select) - Organizational department
- **Communication_Style** (Multi-select) - Preferred communication approaches
- **Goals** (Rich Text) - Current objectives or focus areas
- **Notes** (Rich Text) - Additional context for AI personality adaptation

### 5. Telegram Bot Setup

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Get your bot token and add it to `.env`
3. Set bot privacy to enabled (allows group message detection)
4. Configure bot commands (optional):
   - `/start` - Welcome message
   - `/help` - Show help information  
   - `/status` - System diagnostics

## Usage Instructions

### Starting the Bot

```bash
# Run the bot
python k2_notion_general_manager.py

# Check health status (if running on server)
curl http://localhost:8000/health
```

### Admin Commands & User Management

The bot includes comprehensive admin functionality for managing user access directly through Telegram. Admin privileges are controlled via the `admin` checkbox in your Notion database.

#### Primary Admin Setup
- **Primary Admin ID**: 6904183057 (hardcoded, always has admin access)
- **Additional Admins**: Set `admin=true` in Notion database
- **Auto-refresh**: Admin list updates when privileges are changed

#### Admin Commands (Work in Group Chats)

**Basic User Management:**
- **`/add @username`** - Give existing user bot access
- **`/remove @username`** - Remove bot access from user
- **`/activate @username`** - Activate existing user
- **`/deactivate @username`** - Deactivate user (removes all access)

**Advanced User Management:**
- **`/add_id {telegram_user_id}`** - Add completely new user by Telegram ID
- **`/make_admin @username`** - Grant admin privileges
- **`/remove_admin @username`** - Remove admin privileges (cannot remove primary admin)

**Utility Commands:**
- **`/admin_help`** - Show admin command help
- **`/users`** - List all users with status (private chat only)
- **`/refresh_admins`** - Reload admin list from database

#### User Management Workflow

**For Existing Users in Database:**
1. Admin types `/add @username` in any group chat
2. Bot finds user in Notion database by telegram handle
3. Sets `can_chat_bot=true` and `active=true`
4. User can now access AI conversations

**For New Users Not in Database:**
1. Get user's Telegram ID (they can send `/start` to bot, ID appears in logs)
2. Admin types `/add_id {user_id}` in group chat
3. Bot fetches user data from Telegram API
4. Creates new Notion database entry with full access

**For Removing Access:**
- `/remove @username` - Removes only bot access
- `/deactivate @username` - Removes all access and deactivates

### User Access Management

Users must be added to your Notion employee database with the following steps:

1. **Add Employee Record:** Create new database entry with Name and active=true
2. **Get Telegram ID:** User sends `/start` to bot, check logs for their ID  
3. **Configure Access:** Set `telegram_user_id` and `can_chat_bot=true`
4. **Customize Experience:** Add personality profile data for adaptation

### Admin Commands

For authorized administrators (configure admin IDs in code):

- **`/users`** - List all users in database with access status
- **`/status`** - Comprehensive system diagnostics  

### Getting Telegram User IDs

To efficiently collect Telegram user IDs from your team:

1. **Have each team member start the bot:** They send `/start` to your bot
2. **Check bot logs:** Their user ID will appear in the logs  
3. **Batch update:** Use the admin `/users` command to see who needs database updates
4. **Alternative method:** Create a temporary "ID collection" mode that logs all incoming user IDs

## File Structure

```
project/
├── k2_notion_general_manager.py    # Main application entry point
├── config.py                       # Environment and configuration management
├── file_operations.py             # Conversation file handling  
├── openai_integration.py          # OpenAI API integration and rate limiting
├── system_prompt.txt              # AI personality and behavior definition
├── requirements.txt               # Python package dependencies
├── .env.sample                    # Environment variable template
├── .env                           # Your actual environment configuration (create this)
├── conversations/                 # Auto-created directory for chat logs
├── gm_bot.log                     # Application log file (auto-created)
└── README.md                      # This documentation file
```

## API Integration Details

### OpenAI Integration
- **Model:** GPT-4-0125-Preview (configurable)
- **Context Management:** Dynamic conversation history inclusion
- **Error Handling:** Comprehensive fallback responses
- **Rate Limiting:** 2-second intervals between user requests

### Notion Integration  
- **Database Queries:** Efficient user lookup with 5-minute caching
- **Property Extraction:** Supports all Notion field types
- **Batch Operations:** Admin user management capabilities
- **Error Recovery:** Graceful handling of API timeouts

### Telegram Integration
- **Long Polling:** Reliable message delivery
- **Group Detection:** Automatic private chat redirection
- **Command Processing:** Extensible command system
- **Typing Indicators:** Professional user experience

## Deployment Options

### Local Development
```bash
python k2_notion_general_manager.py
```

### Production Server (Linux)
```bash
# Using screen/tmux for persistence
screen -S gm-bot
python k2_notion_general_manager.py

# Or using systemd service (create service file)
sudo systemctl start gm-bot
```

### Railway Deployment
```bash
# Railway automatically detects Python and installs requirements
# Ensure PORT environment variable is set
# Health check available at /health endpoint
```

### Docker Deployment (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "k2_notion_general_manager.py"]
```

## Monitoring & Maintenance

### Log Files
- **Application logs:** `gm_bot.log`
- **Conversation logs:** `conversations/*.txt`
- **Error tracking:** Comprehensive exception logging

### Health Monitoring
- **Health endpoint:** `GET /health`
- **Status command:** `/status` in Telegram
- **Log monitoring:** Watch for ERROR level messages

### Performance Optimization
- **User caching:** 5-minute TTL for Notion queries
- **Rate limiting:** Prevents API overuse
- **Memory management:** Conversation file rotation

## Security Considerations

### Access Control
- Notion-based user authorization  
- Private chat enforcement
- Rate limiting protection
- Admin command restrictions

### Data Privacy
- Local conversation storage
- Secure API key management
- No data sharing with third parties
- GDPR considerations for EU users

### API Security
- Environment variable credential storage
- Request timeout protection
- Error message sanitization
- Audit trail via logging

## Troubleshooting

### Common Issues

**Bot not responding:**
- Check Telegram bot token validity
- Verify bot is not blocked by Telegram
- Review recent error logs

**User authorization failing:**
- Confirm user exists in Notion database
- Verify `active=true` and `can_chat_bot=true`
- Check `telegram_user_id` matches exactly

**OpenAI errors:**
- Verify API key and billing status
- Check rate limit status
- Monitor token usage

**Notion connectivity issues:**
- Confirm integration token permissions
- Verify database ID accuracy  
- Check Notion API status

### Debug Mode

Enable detailed logging:
```python
# In config.py, temporarily change logging level
logging.basicConfig(level=logging.DEBUG)
```

### Getting Support

For technical support, bug reports, or feature requests:

1. **Check logs first:** Review `gm_bot.log` for error details
2. **Gather system info:** Include Python version, OS, error messages
3. **Contact:** ladiossato@gmail.com with subject "GM Bot Support"
4. **Include:** Relevant log excerpts (sanitize sensitive data)

## Future Roadmap

- **Enhanced Analytics:** Conversation metrics and usage statistics
- **Multi-language Support:** Localized personality adaptation  
- **Advanced Scheduling:** Proactive check-ins and reminders
- **Integration Expansion:** Slack, Teams, and other platforms
- **Custom Personality Models:** Organization-specific AI training

---

## Contact Information

**Ladios Satō**  
**Email:** ladiossato@gmail.com  
**Project:** K2 Notion General Manager Bot  
**License Inquiries:** Commercial licensing available upon request  

---

*This documentation is part of the K2 Notion General Manager Bot project and is subject to the same licensing terms as the software itself.*