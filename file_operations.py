# file_operations.py - GM Bot File Operations
import os
from datetime import datetime
import pytz
import re

def ensure_conversations_dir():
    """Ensure conversations directory exists"""
    if not os.path.exists("conversations"):
        os.makedirs("conversations")

def sanitize_filename(filename):
    """Sanitize filename by removing invalid characters"""
    # Remove invalid filename characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove extra spaces and limit length
    sanitized = sanitized.strip()[:50]
    return sanitized if sanitized else "unknown_user"

def save_conversation(user_id, author_name, content, author_id="USER"):
    """
    Save conversation message to file named after the user.
    
    Args:
        user_id: Telegram user ID (used in the log line)
        author_name: Display name of the author (used for filename)
        content: Message content
        author_id: ID to use in the log ("USER", "BOT_ID", or actual user ID)
    """
    ensure_conversations_dir()
    
    # Use author name for filename, sanitize it
    safe_filename = sanitize_filename(author_name)
    filepath = f"conversations/{safe_filename}.txt"
    
    # Format message with timestamp and actual user ID
    now = datetime.now(pytz.timezone("America/Chicago"))
    time_info = now.strftime("%m-%d-%Y %I:%M %p CT")
    
    # Show actual user ID in the log line
    display_id = str(user_id) if author_id == "USER" else author_id
    formatted_message = f"{time_info} {author_name} [ID: {display_id}]: --- {content}\n"
    
    try:
        with open(filepath, "a", encoding="utf-8") as file:
            file.write(formatted_message)
        print(f"DEBUG: Saved message to {filepath}")
    except Exception as e:
        print(f"Error saving conversation: {e}")

def get_recent_messages(user_id, message_count=10):
    """
    Get recent messages from conversation file using user_id to find the file.
    
    Args:
        user_id: Telegram user ID 
        message_count: Number of recent messages to retrieve
    
    Returns:
        list: List of recent message strings
    """
    # First try to find the file by looking for the user ID in all conversation files
    conversations_dir = "conversations"
    if not os.path.exists(conversations_dir):
        return []
    
    target_file = None
    user_id_str = str(user_id)
    
    # Search through all conversation files to find one containing this user ID
    try:
        for filename in os.listdir(conversations_dir):
            if filename.endswith('.txt'):
                filepath = os.path.join(conversations_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as file:
                        content = file.read()
                        if f"[ID: {user_id_str}]:" in content:
                            target_file = filepath
                            break
                except Exception:
                    continue
        
        if not target_file:
            print(f"DEBUG: No conversation file found for user ID {user_id}")
            return []
        
        # Read the found file
        with open(target_file, "r", encoding="utf-8") as file:
            lines = file.readlines()
            
        # Filter out empty lines and lines with ID pattern
        user_messages = [line.strip() for line in lines if line.strip() and "ID:" in line]
        # Extract the last 'message_count' messages
        recent = user_messages[-message_count:]
        print(f"DEBUG: Loaded {len(recent)} messages from {target_file}")
        return recent
        
    except Exception as e:
        print(f"Error reading conversation file: {e}")
        return []

def read_file(filepath):
    """
    Read file and return lines.
    
    Args:
        filepath: Path to file
    
    Returns:
        list: List of lines or empty list if file doesn't exist
    """
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                return file.readlines()
        except Exception as e:
            print(f"Error reading file {filepath}: {e}")
    return []

def conversation_exists(user_id):
    """Check if conversation file exists for user by searching for their ID"""
    conversations_dir = "conversations"
    if not os.path.exists(conversations_dir):
        return False
    
    user_id_str = str(user_id)
    
    try:
        for filename in os.listdir(conversations_dir):
            if filename.endswith('.txt'):
                filepath = os.path.join(conversations_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as file:
                        content = file.read()
                        if f"[ID: {user_id_str}]:" in content:
                            return True
                except Exception:
                    continue
    except Exception:
        pass
    
    return False

def get_conversation_length(user_id):
    """Get number of lines in conversation file for user"""
    conversations_dir = "conversations"
    if not os.path.exists(conversations_dir):
        return 0
    
    user_id_str = str(user_id)
    
    try:
        for filename in os.listdir(conversations_dir):
            if filename.endswith('.txt'):
                filepath = os.path.join(conversations_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as file:
                        content = file.read()
                        if f"[ID: {user_id_str}]:" in content:
                            lines = content.split('\n')
                            return len([line for line in lines if line.strip()])
                except Exception:
                    continue
    except Exception:
        pass
    
    return 0

def archive_conversation(user_id):
    """Archive conversation file with timestamp"""
    conversations_dir = "conversations"
    if not os.path.exists(conversations_dir):
        return False
    
    user_id_str = str(user_id)
    
    try:
        for filename in os.listdir(conversations_dir):
            if filename.endswith('.txt'):
                filepath = os.path.join(conversations_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as file:
                        content = file.read()
                        if f"[ID: {user_id_str}]:" in content:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            base_name = filename.replace('.txt', '')
                            archive_path = f"{conversations_dir}/{base_name}_archived_{timestamp}.txt"
                            os.rename(filepath, archive_path)
                            print(f"Archived conversation to {archive_path}")
                            return True
                except Exception:
                    continue
    except Exception as e:
        print(f"Error archiving conversation: {e}")
    
    return False