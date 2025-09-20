#!/usr/bin/env python3
"""
==============================================================================
K2 Notion General Manager Bot
==============================================================================

A production-grade conversational AI bot with dynamic leadership personality
that adapts to individual user profiles stored in Notion databases.

Author: Ladios Satō
Email: ladiossato@gmail.com
Version: 1.0.1-Production
License: All Rights Reserved

Copyright (c) 2025 Ladios Satō. All rights reserved.

This software is the proprietary and confidential property of Ladios Satō.
No part of this software may be reproduced, distributed, or transmitted in
any form or by any means, including photocopying, recording, or other
electronic or mechanical methods, without the prior written permission of
the author, except in the case of brief quotations embodied in critical
reviews and certain other noncommercial uses permitted by copyright law.

For licensing and usage inquiries, contact: ladiossato@gmail.com

DISCLAIMER: This software is provided "as is", without warranty of any kind,
express or implied, including but not limited to the warranties of
merchantability, fitness for a particular purpose and noninfringement.
==============================================================================

Features:
- Conversational AI with OpenAI GPT-4 integration
- User authorization via Notion employee database
- Persistent conversation memory with timezone support
- Private chat enforcement with group message redirection
- Dynamic personality adaptation based on user profiles (MBTI, Enneagram, etc.)
- Comprehensive rate limiting and error handling
- Professional logging and request tracing
- Railway-ready deployment with health checks

Requirements:
- Python 3.8+
- OpenAI API key
- Notion API token and employee database
- Telegram bot token

Environment Variables Required:
- TELEGRAM_BOT_TOKEN
- NOTION_TOKEN
- EMPLOYEES_DB_ID
- OPENAI_API_KEY

Optional Environment Variables:
- OPENAI_MODEL (default: gpt-4-0125-preview)
- MAX_TOKENS (default: 500)
- PORT (default: 8000)
"""

import logging
import os
import sys
import threading
import time
import signal
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests

# Import our modular components
from config import (
    telegram_bot_token,
    notion_token,
    employees_db_id,
    openai_api_key,
    bot_persona,
    UNAUTHORIZED_MESSAGE,
    GROUP_REDIRECT_MESSAGE,
    port,
    CONTEXT_WINDOW_DEFAULT,
    ADMIN_USER_ID,
    ADMIN_USER_IDS
)

from file_operations import (
    save_conversation,
    get_recent_messages,
    conversation_exists,
    get_conversation_length
)

from openai_integration import (
    chat_with_openai,
    build_conversation_context,
    rate_limiter
)

# System info
SYSTEM_VERSION = "1.0.1-Production"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# ===== LOGGING SETUP =====
def setup_logging():
    """Setup comprehensive logging system"""
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('gm_bot.log', mode='a', encoding='utf-8')
        ]
    )
    return logging.getLogger('GMBot')

logger = setup_logging()

# ===== UTILITY FUNCTIONS =====
def generate_correlation_id():
    """Generate unique correlation ID for request tracing"""
    return str(int(time.time() * 1000))[-8:]

def is_group_chat(chat_id):
    """Check if chat is a group chat (negative ID)"""
    return chat_id < 0

def format_message_for_display(username, message, user_id="USER"):
    """Format message for conversation logging"""
    now = datetime.now()
    time_info = now.strftime("%m-%d-%Y %I:%M %p CT")
    return f"{time_info} {username} [ID: {user_id}]: --- {message}"

# ===== NOTION INTEGRATION =====
class NotionClient:
    """
    Handles all Notion database operations including user authorization
    and profile data extraction for personality adaptation.
    """
    
    def __init__(self):
        self.token = notion_token
        self.employees_db_id = employees_db_id
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json'
        }
        self.base_url = "https://api.notion.com/v1"
        
        # Performance caching
        self._user_cache = {}
        self._cache_expires = {}
        self._cache_ttl = 300  # 5 minutes
    
    def _make_request(self, method, path, data=None):
        """Make request to Notion API with comprehensive error handling"""
        url = f"{self.base_url}{path}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if 200 <= response.status_code < 300:
                return response.json()
            else:
                logger.error(f"Notion API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Notion request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected Notion error: {e}")
            return None
    
    def get_user_authorization(self, telegram_user_id):
        """
        Check user authorization and retrieve profile for personality adaptation.
        
        Returns:
            tuple: (authorized: bool, profile_text: str, context_lines: int, username: str)
        """
        correlation_id = generate_correlation_id()
        
        # Check cache first for performance
        cache_key = telegram_user_id
        now = time.time()
        
        if (cache_key in self._user_cache and 
            cache_key in self._cache_expires and 
            now < self._cache_expires[cache_key]):
            
            cached_result = self._user_cache[cache_key]
            logger.info(f"[{correlation_id}] Using cached authorization for user {telegram_user_id}")
            return cached_result
        
        try:
            # Query Notion for user with specific telegram_user_id
            query = {
                'filter': {
                    'and': [
                        {'property': 'active', 'checkbox': {'equals': True}},
                        {'property': 'telegram_user_id', 'number': {'equals': telegram_user_id}}
                    ]
                }
            }
            
            response = self._make_request('POST', f'/databases/{self.employees_db_id}/query', query)
            
            if not response or not response.get('results'):
                result = (False, "", CONTEXT_WINDOW_DEFAULT, "Unknown")
                self._user_cache[cache_key] = result
                self._cache_expires[cache_key] = now + self._cache_ttl
                logger.info(f"[{correlation_id}] User {telegram_user_id} not found in database")
                return result
            
            # Parse user data from Notion
            user_data = response['results'][0]
            props = user_data.get('properties', {})
            
            # Extract basic user information
            name_prop = props.get('Name', {}).get('title', [])
            username = name_prop[0]['plain_text'] if name_prop else 'Unknown'
            
            can_chat_bot = props.get('can_chat_bot', {}).get('checkbox', False)
            context_lines = props.get('context_lines', {}).get('number', CONTEXT_WINDOW_DEFAULT)
            
            # Build comprehensive profile text for personality adaptation
            profile_parts = []
            system_fields = [
                'Name', 'telegram_handle', 'telegram_user_id', 
                'can_chat_bot', 'context_lines', 'active'
            ]
            
            for field_name, field_data in props.items():
                if field_name in system_fields:
                    continue
                
                field_text = self._extract_text_from_property(field_data)
                if field_text:
                    profile_parts.append(f"{field_name}: {field_text}")
            
            profile_text = "\n".join(profile_parts)
            
            result = (
                can_chat_bot, 
                profile_text, 
                int(context_lines) if context_lines else CONTEXT_WINDOW_DEFAULT, 
                username
            )
            
            # Cache result for performance
            self._user_cache[cache_key] = result
            self._cache_expires[cache_key] = now + self._cache_ttl
            
            logger.info(f"[{correlation_id}] User {telegram_user_id} ({username}) authorization: {can_chat_bot}")
            return result
            
        except Exception as e:
            logger.error(f"[{correlation_id}] Authorization check error: {e}")
            # Return cached result if available, otherwise deny access
            if cache_key in self._user_cache:
                return self._user_cache[cache_key]
            return (False, "", CONTEXT_WINDOW_DEFAULT, "Unknown")
    
    def _extract_text_from_property(self, property_data):
        """Extract text content from various Notion property types"""
        try:
            prop_type = property_data.get('type')
            
            if prop_type == 'rich_text':
                texts = property_data.get('rich_text', [])
                return ' '.join(item['plain_text'] for item in texts if item.get('plain_text'))
            
            elif prop_type == 'title':
                titles = property_data.get('title', [])
                return ' '.join(item['plain_text'] for item in titles if item.get('plain_text'))
            
            elif prop_type == 'select':
                select_data = property_data.get('select')
                return select_data.get('name', '') if select_data else ''
            
            elif prop_type == 'multi_select':
                multi_select = property_data.get('multi_select', [])
                return ', '.join(item['name'] for item in multi_select if item.get('name'))
            
            elif prop_type == 'number':
                number = property_data.get('number')
                return str(number) if number is not None else ''
            
            elif prop_type == 'checkbox':
                checkbox = property_data.get('checkbox', False)
                return str(checkbox)
            
            elif prop_type in ['date', 'email', 'phone_number', 'url']:
                return property_data.get(prop_type, '') or ''
                
            return ''
            
        except Exception as e:
            logger.debug(f"Error extracting property text: {e}")
            return ''

    def get_all_telegram_usernames(self):
        """
        Retrieve all Telegram usernames from the employee database.
        Useful for getting a list of users for management purposes.
        
        Returns:
            list: List of dictionaries with user information
        """
        try:
            query = {
                'filter': {'property': 'active', 'checkbox': {'equals': True}},
                'sorts': [{'property': 'Name', 'direction': 'ascending'}]
            }
            
            response = self._make_request('POST', f'/databases/{self.employees_db_id}/query', query)
            
            if not response:
                return []
            
            users = []
            for page in response.get('results', []):
                props = page.get('properties', {})
                
                # Extract user information
                name_prop = props.get('Name', {}).get('title', [])
                name = name_prop[0]['plain_text'] if name_prop else 'Unknown'
                
                telegram_handle_prop = props.get('telegram_handle', {}).get('rich_text', [])
                telegram_handle = telegram_handle_prop[0]['plain_text'] if telegram_handle_prop else None
                
                telegram_user_id = props.get('telegram_user_id', {}).get('number', None)
                can_chat_bot = props.get('can_chat_bot', {}).get('checkbox', False)
                is_admin = props.get('admin', {}).get('checkbox', False)
                
                users.append({
                    'name': name,
                    'telegram_handle': telegram_handle,
                    'telegram_user_id': telegram_user_id,
                    'can_chat_bot': can_chat_bot,
                    'is_admin': is_admin,
                    'notion_id': page['id']
                })
            
            return users
            
        except Exception as e:
            logger.error(f"Error retrieving Telegram usernames: {e}")
            return []

    def get_admin_users(self):
        """Get list of admin user IDs from Notion database"""
        try:
            query = {
                'filter': {
                    'and': [
                        {'property': 'active', 'checkbox': {'equals': True}},
                        {'property': 'admin', 'checkbox': {'equals': True}}
                    ]
                }
            }
            
            response = self._make_request('POST', f'/databases/{self.employees_db_id}/query', query)
            
            if not response:
                return [ADMIN_USER_ID]  # Fallback to primary admin
            
            admin_ids = [ADMIN_USER_ID]  # Always include primary admin
            
            for page in response.get('results', []):
                props = page.get('properties', {})
                telegram_user_id = props.get('telegram_user_id', {}).get('number', None)
                if telegram_user_id and telegram_user_id not in admin_ids:
                    admin_ids.append(telegram_user_id)
            
            return admin_ids
            
        except Exception as e:
            logger.error(f"Error getting admin users: {e}")
            return [ADMIN_USER_ID]

    def find_user_by_handle(self, handle):
        """
        Find user by telegram handle.
        
        Args:
            handle: Telegram handle (with or without @)
            
        Returns:
            dict: User info or None if not found
        """
        try:
            # Clean handle (remove @ if present)
            clean_handle = handle.lstrip('@')
            
            query = {
                'filter': {
                    'property': 'telegram_handle',
                    'rich_text': {'contains': clean_handle}
                }
            }
            
            response = self._make_request('POST', f'/databases/{self.employees_db_id}/query', query)
            
            if not response or not response.get('results'):
                return None
            
            # Find exact match
            for page in response.get('results', []):
                props = page.get('properties', {})
                
                telegram_handle_prop = props.get('telegram_handle', {}).get('rich_text', [])
                stored_handle = telegram_handle_prop[0]['plain_text'] if telegram_handle_prop else None
                
                if stored_handle and stored_handle.lstrip('@').lower() == clean_handle.lower():
                    name_prop = props.get('Name', {}).get('title', [])
                    name = name_prop[0]['plain_text'] if name_prop else 'Unknown'
                    
                    return {
                        'notion_id': page['id'],
                        'name': name,
                        'telegram_handle': stored_handle,
                        'telegram_user_id': props.get('telegram_user_id', {}).get('number', None),
                        'can_chat_bot': props.get('can_chat_bot', {}).get('checkbox', False),
                        'active': props.get('active', {}).get('checkbox', False),
                        'admin': props.get('admin', {}).get('checkbox', False)
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding user by handle: {e}")
            return None

    def update_user_access(self, notion_id, telegram_user_id=None, can_chat_bot=None, active=None, admin=None):
        """
        Update user access permissions in Notion.
        
        Args:
            notion_id: Notion page ID
            telegram_user_id: Telegram user ID (optional)
            can_chat_bot: Chat bot access (optional)
            active: Active status (optional)
            admin: Admin status (optional)
            
        Returns:
            bool: Success status
        """
        try:
            properties = {}
            
            if telegram_user_id is not None:
                properties['telegram_user_id'] = {'number': telegram_user_id}
            
            if can_chat_bot is not None:
                properties['can_chat_bot'] = {'checkbox': can_chat_bot}
            
            if active is not None:
                properties['active'] = {'checkbox': active}
                
            if admin is not None:
                properties['admin'] = {'checkbox': admin}
            
            if not properties:
                return False
            
            update_data = {'properties': properties}
            
            response = self._make_request('PATCH', f'/pages/{notion_id}', update_data)
            
            success = response is not None
            if success:
                # Clear cache to force refresh
                self._user_cache.clear()
                self._cache_expires.clear()
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating user access: {e}")
            return False

    def create_user_from_telegram_data(self, user_data, telegram_user_id):
        """
        Create new user entry from Telegram user data.
        
        Args:
            user_data: Telegram user data dict
            telegram_user_id: Telegram user ID
            
        Returns:
            bool: Success status
        """
        try:
            # Extract info from Telegram data
            first_name = user_data.get('first_name', 'Unknown')
            last_name = user_data.get('last_name', '')
            username = user_data.get('username', '')
            
            full_name = f"{first_name} {last_name}".strip()
            
            properties = {
                'Name': {'title': [{'text': {'content': full_name}}]},
                'telegram_user_id': {'number': telegram_user_id},
                'active': {'checkbox': True},
                'can_chat_bot': {'checkbox': True},
                'admin': {'checkbox': False}
            }
            
            if username:
                properties['telegram_handle'] = {
                    'rich_text': [{'text': {'content': f"@{username}"}}]
                }
            
            page_data = {
                'parent': {'database_id': self.employees_db_id},
                'properties': properties
            }
            
            response = self._make_request('POST', '/pages', page_data)
            
            success = response is not None
            if success:
                # Clear cache
                self._user_cache.clear()
                self._cache_expires.clear()
                logger.info(f"Created new user: {full_name} ({telegram_user_id})")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False

# ===== TELEGRAM BOT =====
class TelegramBot:
    """
    Main Telegram bot class handling message processing, user authorization,
    and AI conversation management with comprehensive admin controls.
    """
    
    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{telegram_bot_token}"
        self.notion = NotionClient()
        self.running = False
        self.last_update_id = 0
        
        # Load admin users from database
        self.admin_users = self._load_admin_users()
    
    def _load_admin_users(self):
        """Load admin users from Notion database"""
        try:
            admin_ids = self.notion.get_admin_users()
            logger.info(f"Loaded admin users: {admin_ids}")
            return admin_ids
        except Exception as e:
            logger.error(f"Error loading admin users: {e}")
            return [ADMIN_USER_ID]  # Fallback to primary admin
    
    def start_polling(self):
        """Start polling for messages with proper error handling"""
        self.running = True
        logger.info("Starting 10x Output General Manager Bot polling")
        
        while self.running:
            try:
                updates = self._get_updates()
                if not self.running:
                    break
                    
                # Process each update synchronously to avoid asyncio conflicts
                for update in updates:
                    if not self.running:
                        break
                    self._process_update_sync(update)
                    
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt in polling loop")
                break
            except Exception as e:
                if self.running:
                    logger.error(f"Polling error: {e}")
                    time.sleep(5)
                else:
                    break
        
        logger.info("GM Bot polling stopped")
    
    def stop(self):
        """Stop the bot gracefully"""
        self.running = False
    
    def _get_updates(self):
        """Get updates from Telegram API"""
        data = {"timeout": 25}
        if self.last_update_id:
            data["offset"] = self.last_update_id + 1
        
        try:
            resp = requests.post(f"{self.base_url}/getUpdates", json=data, timeout=30)
            if resp.ok:
                result = resp.json()
                if result.get("ok"):
                    updates = result.get("result", [])
                    if updates:
                        self.last_update_id = updates[-1]["update_id"]
                    return updates
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
        
        return []
    
    def _process_update_sync(self, update):
        """Process update synchronously to avoid asyncio issues"""
        try:
            if "message" in update:
                self._handle_message_sync(update["message"])
        except Exception as e:
            logger.error(f"Error processing update: {e}")
    
    def _handle_message_sync(self, message):
        """Handle incoming message synchronously - ALWAYS log conversations"""
        user_id = message.get("from", {}).get("id")
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        username = message.get("from", {}).get("first_name", "Unknown")
        
        correlation_id = generate_correlation_id()
        
        if not user_id or not chat_id or not text:
            return
        
        # ALWAYS save conversation - regardless of authorization
        save_conversation(user_id, username, text, "USER")
        
        logger.info(f"[{correlation_id}] Message from {username} ({user_id}): {text[:50]}...")
        
        # Handle admin commands in groups (before other processing)
        if text.startswith("/") and self._is_admin_user(user_id):
            if self._handle_admin_command_sync(message, correlation_id):
                return  # Admin command was processed
        
        # Handle regular commands
        if text.startswith("/"):
            self._handle_command_sync(message, correlation_id)
            return
        
        # Check if it's a group chat - redirect to private (unless admin command)
        if is_group_chat(chat_id):
            logger.info(f"[{correlation_id}] Group message, redirecting to private")
            self._send_message_sync(chat_id, GROUP_REDIRECT_MESSAGE)
            return
        
        # Check user authorization for AI conversation
        authorized, profile_text, context_lines, db_username = self.notion.get_user_authorization(user_id)
        
        if not authorized:
            logger.info(f"[{correlation_id}] User {user_id} not authorized")
            self._send_message_sync(chat_id, UNAUTHORIZED_MESSAGE)
            return
        
        # Check rate limiting
        can_request, wait_time = rate_limiter.can_make_request(user_id)
        if not can_request:
            logger.info(f"[{correlation_id}] Rate limit hit, wait: {wait_time:.1f}s")
            self._send_message_sync(chat_id, f"Please wait {wait_time:.1f} seconds before your next message.")
            return
        
        # Process AI conversation
        self._process_ai_conversation_sync(message, correlation_id, profile_text, context_lines, db_username)
    
    def _process_ai_conversation_sync(self, message, correlation_id, profile_text, context_lines, username):
        """Process AI conversation synchronously with proper logging of all messages"""
        user_id = message.get("from", {}).get("id")
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        
        logger.info(f"[{correlation_id}] Starting AI conversation processing")
        logger.info(f"[{correlation_id}] User: {username} ({user_id}), Context lines: {context_lines}")
        
        try:
            # Send typing indicator
            logger.info(f"[{correlation_id}] Sending typing indicator")
            self._send_typing_sync(chat_id)
            
            # Get recent conversation history based on user's context_lines setting
            logger.info(f"[{correlation_id}] Loading conversation history (max {context_lines} lines)")
            recent_messages = get_recent_messages(user_id, context_lines)
            logger.info(f"[{correlation_id}] Loaded {len(recent_messages)} conversation lines")
            
            # Build conversation context for OpenAI
            logger.info(f"[{correlation_id}] Building conversation context")
            logger.info(f"[{correlation_id}] Profile text length: {len(profile_text)} chars")
            logger.info(f"[{correlation_id}] Bot persona length: {len(bot_persona)} chars")
            
            conversation = build_conversation_context(
                bot_persona,
                profile_text,
                recent_messages,
                text
            )
            logger.info(f"[{correlation_id}] Conversation context built - {len(conversation)} messages")
            
            # Get AI response
            logger.info(f"[{correlation_id}] Calling OpenAI chat function")
            response_text = chat_with_openai(conversation)
            logger.info(f"[{correlation_id}] OpenAI call completed")
            
            if response_text:
                logger.info(f"[{correlation_id}] Received response from OpenAI: {len(response_text)} chars")
                
                # Save bot response to conversation file
                save_conversation(user_id, "10x GM AI", response_text, "BOT_ID")
                logger.info(f"[{correlation_id}] Bot response saved to conversation file")
                
                # Send response to user
                logger.info(f"[{correlation_id}] Sending response to user")
                self._send_message_sync(chat_id, response_text)
                
                logger.info(f"[{correlation_id}] AI conversation completed successfully - response: {len(response_text)} chars")
            else:
                logger.error(f"[{correlation_id}] No response received from OpenAI")
                error_msg = "I'm experiencing technical difficulties. Please try again."
                
                # Save bot error response to conversation file
                save_conversation(user_id, "10x GM AI", error_msg, "BOT_ID")
                
                self._send_message_sync(chat_id, error_msg)
                
        except Exception as e:
            logger.error(f"[{correlation_id}] AI conversation error at line: {e.__traceback__.tb_lineno if e.__traceback__ else 'unknown'}")
            logger.error(f"[{correlation_id}] AI conversation error type: {type(e).__name__}")
            logger.error(f"[{correlation_id}] AI conversation error message: {str(e)}")
            logger.error(f"[{correlation_id}] AI conversation full error: {e}", exc_info=True)
            
            error_msg = "Something went wrong on my end. Please try rephrasing your message."
            
            # Save bot error response to conversation file
            save_conversation(user_id, "10x GM AI", error_msg, "BOT_ID")
            
            self._send_message_sync(chat_id, error_msg)
    
    def _handle_admin_command_sync(self, message, correlation_id):
        """
        Handle admin commands for user management.
        Returns True if admin command was processed, False otherwise.
        """
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        
        # Parse command and arguments
        parts = text.split()
        if not parts:
            return False
            
        command = parts[0].lower()
        
        # Admin commands that work in groups
        if command == "/add" and len(parts) >= 2:
            self._admin_add_user_sync(message, correlation_id)
            return True
        
        elif command == "/remove" and len(parts) >= 2:
            self._admin_remove_user_sync(message, correlation_id)
            return True
            
        elif command == "/activate" and len(parts) >= 2:
            self._admin_activate_user_sync(message, correlation_id)
            return True
            
        elif command == "/deactivate" and len(parts) >= 2:
            self._admin_deactivate_user_sync(message, correlation_id)
            return True
            
        elif command == "/add_id" and len(parts) >= 2:
            self._admin_add_by_id_sync(message, correlation_id)
            return True
            
        elif command == "/make_admin" and len(parts) >= 2:
            self._admin_make_admin_sync(message, correlation_id)
            return True
            
        elif command == "/remove_admin" and len(parts) >= 2:
            self._admin_remove_admin_sync(message, correlation_id)
            return True
            
        elif command == "/admin_help":
            self._send_admin_help_sync(chat_id)
            return True
            
        elif command == "/refresh_admins":
            self._refresh_admin_list_sync(chat_id)
            return True
        
        return False  # Not an admin command
    
    def _admin_add_user_sync(self, message, correlation_id):
        """Add user by @mention"""
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        
        # Extract @mention or handle from command
        parts = text.split()
        if len(parts) < 2:
            self._send_message_sync(chat_id, "Usage: /add @username")
            return
        
        handle = parts[1]
        
        # Check if it's a direct @mention with user data in message
        if 'entities' in message:
            for entity in message['entities']:
                if entity.get('type') == 'mention':
                    # Get user info from the mention
                    mention_text = text[entity['offset']:entity['offset'] + entity['length']]
                    if mention_text == handle:
                        # Try to get user ID from mention (if possible)
                        # For now, we'll work with the handle
                        break
        
        # Find user in Notion by handle
        user_info = self.notion.find_user_by_handle(handle)
        
        if user_info:
            # User exists, just activate them
            success = self.notion.update_user_access(
                user_info['notion_id'],
                can_chat_bot=True,
                active=True
            )
            
            if success:
                msg = f"✅ User {user_info['name']} (@{handle.lstrip('@')}) has been given bot access."
                logger.info(f"[{correlation_id}] Admin activated user: {user_info['name']}")
            else:
                msg = f"❌ Failed to update user {handle}. Check logs."
        else:
            msg = f"❌ User {handle} not found in database. Use /add_id {'{user_id}'} for new users."
        
        self._send_message_sync(chat_id, msg)
    
    def _admin_remove_user_sync(self, message, correlation_id):
        """Remove user access by @mention"""
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        
        parts = text.split()
        if len(parts) < 2:
            self._send_message_sync(chat_id, "Usage: /remove @username")
            return
        
        handle = parts[1]
        user_info = self.notion.find_user_by_handle(handle)
        
        if user_info:
            success = self.notion.update_user_access(
                user_info['notion_id'],
                can_chat_bot=False
            )
            
            if success:
                msg = f"❌ Bot access removed from {user_info['name']} (@{handle.lstrip('@')})."
                logger.info(f"[{correlation_id}] Admin removed access: {user_info['name']}")
            else:
                msg = f"❌ Failed to update user {handle}. Check logs."
        else:
            msg = f"❌ User {handle} not found in database."
        
        self._send_message_sync(chat_id, msg)
    
    def _admin_activate_user_sync(self, message, correlation_id):
        """Activate user by @mention"""
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        
        parts = text.split()
        if len(parts) < 2:
            self._send_message_sync(chat_id, "Usage: /activate @username")
            return
        
        handle = parts[1]
        user_info = self.notion.find_user_by_handle(handle)
        
        if user_info:
            success = self.notion.update_user_access(
                user_info['notion_id'],
                active=True
            )
            
            if success:
                msg = f"✅ User {user_info['name']} (@{handle.lstrip('@')}) has been activated."
                logger.info(f"[{correlation_id}] Admin activated user: {user_info['name']}")
            else:
                msg = f"❌ Failed to activate user {handle}. Check logs."
        else:
            msg = f"❌ User {handle} not found in database."
        
        self._send_message_sync(chat_id, msg)
    
    def _admin_deactivate_user_sync(self, message, correlation_id):
        """Deactivate user by @mention"""
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        
        parts = text.split()
        if len(parts) < 2:
            self._send_message_sync(chat_id, "Usage: /deactivate @username")
            return
        
        handle = parts[1]
        user_info = self.notion.find_user_by_handle(handle)
        
        if user_info:
            success = self.notion.update_user_access(
                user_info['notion_id'],
                active=False,
                can_chat_bot=False
            )
            
            if success:
                msg = f"❌ User {user_info['name']} (@{handle.lstrip('@')}) has been deactivated."
                logger.info(f"[{correlation_id}] Admin deactivated user: {user_info['name']}")
            else:
                msg = f"❌ Failed to deactivate user {handle}. Check logs."
        else:
            msg = f"❌ User {handle} not found in database."
        
        self._send_message_sync(chat_id, msg)
    
    def _admin_add_by_id_sync(self, message, correlation_id):
        """Add user by Telegram user ID (for new users not in database)"""
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        
        parts = text.split()
        if len(parts) < 2:
            self._send_message_sync(chat_id, "Usage: /add_id {user_id}")
            return
        
        try:
            target_user_id = int(parts[1])
        except ValueError:
            self._send_message_sync(chat_id, "❌ Invalid user ID. Must be a number.")
            return
        
        # Try to get user info from Telegram
        try:
            user_data = self._get_telegram_user_info(target_user_id)
            
            if user_data:
                success = self.notion.create_user_from_telegram_data(user_data, target_user_id)
                
                if success:
                    name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
                    username = user_data.get('username', 'No handle')
                    msg = f"✅ Created and activated user: {name} (@{username}) - ID: {target_user_id}"
                    logger.info(f"[{correlation_id}] Admin created user: {name} ({target_user_id})")
                else:
                    msg = f"❌ Failed to create user with ID {target_user_id}. Check logs."
            else:
                msg = f"❌ Could not fetch user data for ID {target_user_id}. User may have blocked bot."
        
        except Exception as e:
            logger.error(f"[{correlation_id}] Error adding user by ID: {e}")
            msg = f"❌ Error processing user ID {target_user_id}: {str(e)}"
        
        self._send_message_sync(chat_id, msg)
    
    def _admin_make_admin_sync(self, message, correlation_id):
        """Make user admin by @mention"""
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        
        parts = text.split()
        if len(parts) < 2:
            self._send_message_sync(chat_id, "Usage: /make_admin @username")
            return
        
        handle = parts[1]
        user_info = self.notion.find_user_by_handle(handle)
        
        if user_info:
            success = self.notion.update_user_access(
                user_info['notion_id'],
                admin=True,
                active=True,
                can_chat_bot=True
            )
            
            if success:
                msg = f"👑 {user_info['name']} (@{handle.lstrip('@')}) is now an admin."
                logger.info(f"[{correlation_id}] Admin promoted user: {user_info['name']}")
                # Refresh admin list
                self.admin_users = self._load_admin_users()
            else:
                msg = f"❌ Failed to make {handle} an admin. Check logs."
        else:
            msg = f"❌ User {handle} not found in database."
        
        self._send_message_sync(chat_id, msg)
    
    def _admin_remove_admin_sync(self, message, correlation_id):
        """Remove admin privileges by @mention"""
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        
        parts = text.split()
        if len(parts) < 2:
            self._send_message_sync(chat_id, "Usage: /remove_admin @username")
            return
        
        handle = parts[1]
        user_info = self.notion.find_user_by_handle(handle)
        
        if user_info:
            # Prevent removing primary admin
            if user_info.get('telegram_user_id') == ADMIN_USER_ID:
                msg = f"❌ Cannot remove admin privileges from primary admin."
                self._send_message_sync(chat_id, msg)
                return
            
            success = self.notion.update_user_access(
                user_info['notion_id'],
                admin=False
            )
            
            if success:
                msg = f"👤 Admin privileges removed from {user_info['name']} (@{handle.lstrip('@')})."
                logger.info(f"[{correlation_id}] Admin demoted user: {user_info['name']}")
                # Refresh admin list
                self.admin_users = self._load_admin_users()
            else:
                msg = f"❌ Failed to remove admin from {handle}. Check logs."
        else:
            msg = f"❌ User {handle} not found in database."
        
        self._send_message_sync(chat_id, msg)
    
    def _get_telegram_user_info(self, user_id):
        """Get user info from Telegram API"""
        try:
            data = {"user_id": user_id}
            resp = requests.post(f"{self.base_url}/getChat", json=data, timeout=30)
            
            if resp.ok:
                result = resp.json()
                if result.get("ok"):
                    return result.get("result")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting Telegram user info: {e}")
            return None
    
    def _send_admin_help_sync(self, chat_id):
        """Send admin help message"""
        text = (
            "<b>🛠 Admin Commands - User Management</b>\n\n"
            "<b>Basic Commands:</b>\n"
            "/add @username - Give user bot access\n"
            "/remove @username - Remove bot access\n"
            "/activate @username - Activate user\n"
            "/deactivate @username - Deactivate user\n\n"
            "<b>Advanced Commands:</b>\n"
            "/add_id {user_id} - Add new user by Telegram ID\n"
            "/make_admin @username - Grant admin privileges\n"
            "/remove_admin @username - Remove admin privileges\n\n"
            "<b>Utility Commands:</b>\n"
            "/users - List all users (works in private chat)\n"
            "/admin_help - Show this help\n"
            "/refresh_admins - Reload admin list\n\n"
            "<b>Usage Notes:</b>\n"
            "• Commands work in group chats for admins\n"
            "• Use @mentions when user exists in database\n"
            "• Use /add_id for completely new users\n"
            "• All changes update Notion database immediately"
        )
        self._send_message_sync(chat_id, text)
    
    def _refresh_admin_list_sync(self, chat_id):
        """Refresh admin user list from database"""
        self.admin_users = self._load_admin_users()
        msg = f"✅ Admin list refreshed. Current admins: {len(self.admin_users)}"
        self._send_message_sync(chat_id, msg)
        """Handle bot commands synchronously"""
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        command = text.split()[0].lower()
        
        if command == "/start":
            self._send_welcome_sync(chat_id)
        elif command == "/help":
            self._send_help_sync(chat_id)
        elif command == "/status":
            self._send_status_sync(chat_id)
        elif command == "/users" and self._is_admin_user(message.get("from", {}).get("id")):
            self._send_users_list_sync(chat_id)
        else:
            msg = ("I don't recognize that command. Try /help for available commands, "
                   "or just send me a message to start our conversation.")
            self._send_message_sync(chat_id, msg)
    def _handle_command_sync(self, message, correlation_id):
        """Handle bot commands synchronously"""
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        command = text.split()[0].lower()
        
        if command == "/start":
            self._send_welcome_sync(chat_id)
        elif command == "/help":
            self._send_help_sync(chat_id)
        elif command == "/status":
            self._send_status_sync(chat_id)
        elif command == "/users" and self._is_admin_user(message.get("from", {}).get("id")):
            self._send_users_list_sync(chat_id)
        else:
            msg = ("I don't recognize that command. Try /help for available commands, "
                   "or just send me a message to start our conversation.")
            self._send_message_sync(chat_id, msg)
    
    def _is_admin_user(self, user_id):
        """Check if user is admin using dynamic admin list"""
        return user_id in self.admin_users
    
    def _send_users_list_sync(self, chat_id):
        """Send list of all users (admin command)"""
        try:
            users = self.notion.get_all_telegram_usernames()
            
            if not users:
                self._send_message_sync(chat_id, "No users found in database.")
                return
            
            message = "<b>Telegram Users in Database:</b>\n\n"
            
            for user in users:
                status = "✅ Authorized" if user['can_chat_bot'] else "❌ Not Authorized"
                handle = f"@{user['telegram_handle']}" if user['telegram_handle'] else "No handle"
                user_id = user['telegram_user_id'] if user['telegram_user_id'] else "No ID"
                
                message += f"<b>{user['name']}</b>\n"
                message += f"  Handle: {handle}\n"
                message += f"  User ID: {user_id}\n"
                message += f"  Status: {status}\n\n"
            
            # Send in chunks if too long
            if len(message) > 4000:
                chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for chunk in chunks:
                    self._send_message_sync(chat_id, chunk)
            else:
                self._send_message_sync(chat_id, message)
                
        except Exception as e:
            logger.error(f"Error getting users list: {e}")
            self._send_message_sync(chat_id, "Error retrieving users list.")
    
    def _send_message_sync(self, chat_id, text):
        """Send message to chat synchronously"""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            resp = requests.post(f"{self.base_url}/sendMessage", json=data, timeout=30)
            return resp.ok
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def _send_typing_sync(self, chat_id):
        """Send typing indicator synchronously"""
        try:
            data = {"chat_id": chat_id, "action": "typing"}
            requests.post(f"{self.base_url}/sendChatAction", json=data, timeout=10)
        except:
            pass  # Non-critical
    
    def _send_welcome_sync(self, chat_id):
        """Send welcome message"""
        text = (
            f"<b>10x Output General Manager Bot v{SYSTEM_VERSION}</b>\n\n"
            "I'm your AI-powered General Manager assistant, created by Ladios Satō. "
            "I adapt my leadership style to you personally based on what I learn from our conversations and provide clear, outcome-oriented guidance.\n\n"
            "<b>Key features:</b>\n"
            "• Personalized experience that improves over time\n"
            "• Persistent conversation memory\n"
            "• Private conversations only (no group chats)\n"
            "• Focused on outcomes and accountability\n"
            "• Professional-grade security and privacy\n\n"
            "Just send me a message to start our conversation!"
        )
        self._send_message_sync(chat_id, text)
    
    def _send_help_sync(self, chat_id):
        """Send help message"""
        text = (
            "<b>10x Output General Manager Bot Help</b>\n\n"
            "<b>Commands:</b>\n"
            "/start - Welcome message and introduction\n"
            "/help - Show this help information\n"
            "/status - System status and diagnostics\n\n"
            "<b>How to use:</b>\n"
            "• Send me any message to start chatting\n"
            "• I remember our conversation history\n"
            "• My responses adapt based on our conversation history\n"
            "• Group messages are automatically redirected to private chat\n\n"
            "<b>Access Control:</b>\n"
            "Your access is controlled via your employee profile in our Notion database. "
            "If you don't have access, contact ladiossato@gmail.com with subject '10x GM AI Access'.\n\n"
            "<b>Privacy:</b>\n"
            "All conversations are logged locally and processed securely through OpenAI's API."
        )
        self._send_message_sync(chat_id, text)
    
    def _send_status_sync(self, chat_id):
        """Send system status"""
        try:
            # Test basic connectivity
            test_response = requests.get("https://api.openai.com/v1/models", 
                                       headers={"Authorization": f"Bearer {openai_api_key}"}, 
                                       timeout=10)
            openai_status = "✅ Connected" if test_response.status_code == 200 else "⚠️ Issues"
        except:
            openai_status = "❌ Error"
        
        try:
            notion_test = self.notion._make_request('GET', f'/databases/{employees_db_id}')
            notion_status = "✅ Connected" if notion_test else "❌ Error"
        except:
            notion_status = "❌ Error"
        
        text = (
            f"<b>10x GM Bot System Status</b>\n\n"
            f"• Version: {SYSTEM_VERSION}\n"
            f"• Author: Ladios Satō\n"
            f"• OpenAI API: {openai_status}\n"
            f"• Notion API: {notion_status}\n"
            f"• Conversation System: ✅ Active\n"
            f"• Rate Limiting: ✅ Active\n"
            f"• Bot Status: ✅ Running\n\n"
            f"• Uptime: {self._get_uptime()}\n"
            f"• Memory Usage: Available\n\n"
            f"All core systems operational"
        )
        
        self._send_message_sync(chat_id, text)
    
    def _get_uptime(self):
        """Get bot uptime (placeholder - implement if needed)"""
        return "Available"

# ===== MAIN APPLICATION =====
class GMBotApp:
    """
    Main application class that orchestrates all bot components
    and handles graceful startup/shutdown procedures.
    """
    
    def __init__(self):
        self.bot = TelegramBot()
        self.running = False
        self.server = None
        
        logger.info(f"10x Output General Manager Bot v{SYSTEM_VERSION} by Ladios Satō - Initialized")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()
        sys.exit(0)
    
    def stop(self):
        """Stop all components gracefully"""
        self.running = False
        
        if self.bot:
            self.bot.stop()
        
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except:
                pass
        
        logger.info("10x Output General Manager Bot stopped successfully")
    
    def run(self):
        """Run the main application"""
        logger.info("Starting 10x Output General Manager Bot - Production Mode")
        self.running = True
        
        # Start health check server for Railway deployment
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/health':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {
                        "status": "healthy",
                        "version": SYSTEM_VERSION,
                        "author": "Ladios Satō",
                        "timestamp": datetime.now().isoformat()
                    }
                    self.wfile.write(str(response).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Suppress HTTP access logs
        
        try:
            # Start health check server in background thread
            self.server = HTTPServer(('0.0.0.0', port), HealthHandler)
            server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            server_thread.start()
            
            logger.info(f"Health check server running on port {port}")
            logger.info("All systems initialized - Starting message polling")
            
            # Start bot polling (this will block until interrupted)
            self.bot.start_polling()
            
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received - Shutting down")
        except Exception as e:
            logger.error(f"Critical error in main application: {e}")
        finally:
            self.stop()

# ===== ENTRY POINT =====
def main():
    """
    Application entry point with comprehensive error handling
    and professional logging.
    """
    logger.info("="*70)
    logger.info("K2 NOTION GENERAL MANAGER BOT")
    logger.info(f"Version: {SYSTEM_VERSION}")
    logger.info("Author: Ladios Satō <ladiossato@gmail.com>")
    logger.info("Copyright (c) 2025 - All Rights Reserved")
    logger.info("="*70)
    
    # Validate required environment variables
    required_vars = [
        'TELEGRAM_BOT_TOKEN', 'NOTION_TOKEN', 
        'EMPLOYEES_DB_ID', 'OPENAI_API_KEY'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    
    app = GMBotApp()
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\nGraceful shutdown requested by user...")
        logger.info("User requested shutdown via KeyboardInterrupt")
    except Exception as e:
        logger.error(f"Unexpected critical error: {e}", exc_info=True)
        print(f"\nCritical error occurred: {e}")
    finally:
        app.stop()
        logger.info("Application shutdown complete")

if __name__ == "__main__":
    main()