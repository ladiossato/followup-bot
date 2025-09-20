# K2 GM Bot - GitHub to Railway Deployment Guide

## Prerequisites

- GitHub account
- Railway account (sign up at railway.app)
- Git installed locally
- All environment variables ready

## Step 1: Create GitHub Repository

### Option A: Create New Repository on GitHub
1. Go to github.com and create a new repository
2. Repository name: `k2-gm-bot` (or your preferred name)
3. Set to Private (recommended for production bots)
4. Don't initialize with README (we'll push existing code)

### Option B: Using Git Command Line
```bash
# Navigate to your project directory
cd /path/to/your/bot/files

# Initialize git repository
git init

# Add all files
git add .

# Make initial commit
git commit -m "Initial commit - K2 GM Bot with HHG system prompt"

# Add remote origin (replace with your repository URL)
git remote add origin https://github.com/yourusername/k2-gm-bot.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 2: Prepare Environment Variables

Create a list of your environment variables (don't commit these to GitHub):

### Required Environment Variables:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
NOTION_TOKEN=your_notion_integration_token
EMPLOYEES_DB_ID=your_employees_database_id
OPENAI_API_KEY=your_openai_api_key
```

### Optional Environment Variables:
```
OPENAI_MODEL=gpt-4o-mini-2024-07-18
MAX_TOKENS=500
PORT=8000
```

## Step 3: Deploy to Railway

### Method 1: Deploy from GitHub (Recommended)

1. **Login to Railway**
   - Go to https://railway.app
   - Sign in with GitHub account

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `k2-gm-bot` repository

3. **Configure Environment Variables**
   - Go to your project dashboard
   - Click on your service
   - Go to "Variables" tab
   - Add all your environment variables one by one:
     - `TELEGRAM_BOT_TOKEN`
     - `NOTION_TOKEN`
     - `EMPLOYEES_DB_ID`
     - `OPENAI_API_KEY`
     - `OPENAI_MODEL` (set to `gpt-4o-mini-2024-07-18`)
     - `PORT` (set to `8000`)

4. **Deploy**
   - Railway will automatically detect Python and install dependencies
   - Build process will use `requirements.txt`
   - App will start using the command in `Procfile`

### Method 2: Railway CLI (Alternative)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project in your bot directory
cd /path/to/your/bot/files
railway init

# Set environment variables
railway variables set TELEGRAM_BOT_TOKEN=your_token_here
railway variables set NOTION_TOKEN=your_notion_token
railway variables set EMPLOYEES_DB_ID=your_db_id
railway variables set OPENAI_API_KEY=your_openai_key
railway variables set OPENAI_MODEL=gpt-4o-mini-2024-07-18
railway variables set PORT=8000

# Deploy
railway up
```

## Step 4: Verify Deployment

1. **Check Deployment Status**
   - In Railway dashboard, monitor the "Deployments" tab
   - Look for successful build and deploy status

2. **Check Application Logs**
   - Go to your service in Railway
   - Click "Logs" tab
   - Look for startup messages:
     ```
     K2 NOTION GENERAL MANAGER BOT
     Health check server running on port 8000
     Starting 10x Output General Manager Bot polling
     ```

3. **Test Health Endpoint**
   - Railway will provide a public URL
   - Test: `https://your-app-name.railway.app/health`
   - Should return JSON with status information

4. **Test Bot Functionality**
   - Send `/start` to your Telegram bot
   - Verify it responds with welcome message
   - Test with authorized user from your Notion database

## Step 5: Configure Automatic Deployments

Railway automatically redeploys when you push to your GitHub repository:

```bash
# Make changes to your code
# Commit changes
git add .
git commit -m "Update bot configuration"

# Push to GitHub
git push origin main

# Railway will automatically detect changes and redeploy
```

## Step 6: Monitor and Maintain

### Railway Dashboard Monitoring:
- **Metrics**: CPU, Memory, Network usage
- **Logs**: Real-time application logs
- **Variables**: Environment variable management
- **Deployments**: Build and deployment history

### Bot Logs Monitoring:
- Check logs for conversation processing
- Monitor OpenAI API usage and costs
- Watch for authentication or authorization issues

### Cost Management:
- Railway: Monitor usage-based billing
- OpenAI: Track API usage in OpenAI dashboard
- Set up alerts for unexpected usage spikes

## Troubleshooting Common Issues

### Build Failures:
- Check `requirements.txt` for correct dependencies
- Verify Python version compatibility
- Check Railway build logs for specific errors

### Runtime Errors:
- Verify all environment variables are set correctly
- Check that Telegram bot token is valid
- Ensure Notion database permissions are correct
- Verify OpenAI API key has sufficient credits

### Bot Not Responding:
- Check Railway logs for error messages
- Verify bot is not blocked by Telegram
- Test individual components (Notion, OpenAI APIs)

### Connection Issues:
- Ensure Railway app is running (not sleeping)
- Check health endpoint accessibility
- Verify webhook endpoints if using webhooks

## Security Best Practices

1. **Never commit secrets to GitHub**
   - Use `.gitignore` to exclude `.env` files
   - Store all secrets in Railway environment variables

2. **Use private repositories**
   - Keep bot code in private GitHub repositories
   - Limit access to necessary team members

3. **Regularly rotate API keys**
   - Update Telegram bot tokens periodically
   - Rotate Notion and OpenAI API keys

4. **Monitor access logs**
   - Review bot usage patterns
   - Monitor for unauthorized access attempts

## File Structure for Deployment

Your repository should have this structure:
```
k2-gm-bot/
├── k2_notion_general_manager.py    # Main application
├── config.py                      # Configuration management
├── openai_integration.py          # Fixed OpenAI integration
├── file_operations.py             # File handling
├── system_prompt.txt              # HHG system prompt
├── requirements.txt               # Python dependencies
├── Procfile                       # Railway process definition
├── railway.json                   # Railway configuration
├── .gitignore                     # Git ignore rules
├── README.md                      # Documentation
└── FIXES_SUMMARY.md              # Update summary
```

## Deployment Commands Summary

```bash
# Initial setup
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/k2-gm-bot.git
git push -u origin main

# For updates
git add .
git commit -m "Description of changes"
git push origin main
```

Your bot will be live and automatically managed by Railway with this setup!