# openai_integration.py - GM Bot OpenAI Integration (v1.0+ API)
import openai
import time
import traceback
from config import openai_api_key, openai_model

# Initialize the new OpenAI client
client = openai.OpenAI(api_key=openai_api_key)

def chat_with_openai(conversation):
    """
    Send conversation to OpenAI and get response.
    Uses the new OpenAI library v1.0+ API structure with proper error handling.
    
    Args:
        conversation: List of message dictionaries with 'role' and 'content'
    
    Returns:
        str: AI response or error message
    """
    print(f"DEBUG: Starting OpenAI chat function (v1.0+ API)")
    print(f"DEBUG: Conversation length: {len(conversation)}")
    print(f"DEBUG: Model: {openai_model}")
    
    try:
        print(f"DEBUG: About to call client.chat.completions.create")
        
        response = client.chat.completions.create(
            model=openai_model,
            messages=conversation,
            max_tokens=500,  # Limit response length to control costs
            temperature=0.7  # Balanced creativity/consistency
        )
        
        print(f"DEBUG: OpenAI call successful")
        return response.choices[0].message.content
        
    except openai.RateLimitError as e:
        print(f"DEBUG: Rate limit error: {e}")
        return "I'm experiencing high demand right now. Please try again in a moment."
        
    except openai.APIError as e:
        print(f"DEBUG: API error: {e}")
        return "I'm having trouble connecting to my AI systems. Please try again shortly."
        
    except openai.AuthenticationError as e:
        print(f"DEBUG: Authentication error: {e}")
        return "I'm having authentication issues. Please contact support."
        
    except openai.APIConnectionError as e:
        print(f"DEBUG: Connection error: {e}")
        return "I'm having network connectivity issues. Please try again in a moment."
        
    except openai.APITimeoutError as e:
        print(f"DEBUG: Timeout error: {e}")
        return "My response is taking too long to generate. Please try again."
        
    except Exception as e:
        print(f"DEBUG: Unexpected error: {type(e).__name__}: {e}")
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        return "Something went wrong on my end. Please try rephrasing your message."

def build_conversation_context(system_prompt, user_profile, conversation_history, current_message):
    """
    Build the complete context for OpenAI including system prompt, 
    user profile, conversation history, and current message.
    
    Args:
        system_prompt: The system personality prompt
        user_profile: User's profile text from Notion
        conversation_history: List of recent conversation lines
        current_message: The current user message
    
    Returns:
        list: Formatted conversation for OpenAI
    """
    print(f"DEBUG: Building conversation context")
    print(f"DEBUG: System prompt length: {len(system_prompt)} chars")
    print(f"DEBUG: User profile length: {len(user_profile)} chars")
    print(f"DEBUG: History length: {len(conversation_history)} lines")
    
    # Build the enhanced system prompt with user profile
    enhanced_system_prompt = f"""{system_prompt}

EMPLOYEE PROFILE DATA:
{user_profile if user_profile.strip() else "No specific profile data available."}

RECENT CONVERSATION HISTORY:
{chr(10).join(conversation_history) if conversation_history else "No previous conversation."}

Instructions:
- Use the employee profile data to personalize your response style and approach
- Reference their personality type, role, goals, or other relevant attributes when appropriate
- Maintain conversation continuity using the history provided
- Be specific and actionable in your guidance
- Keep responses concise but comprehensive
"""
    
    # Build the conversation array
    conversation = [
        {"role": "system", "content": enhanced_system_prompt},
        {"role": "user", "content": current_message}
    ]
    
    print(f"DEBUG: Enhanced system prompt length: {len(enhanced_system_prompt)} chars")
    print(f"DEBUG: Final conversation has {len(conversation)} messages")
    
    return conversation

class RateLimiter:
    """Simple rate limiter to prevent API abuse and control costs"""
    
    def __init__(self, min_interval=2):
        self.min_interval = min_interval
        self.user_last_request = {}
    
    def can_make_request(self, user_id):
        """Check if user can make a request based on rate limiting"""
        now = time.time()
        last_request = self.user_last_request.get(user_id, 0)
        
        if now - last_request < self.min_interval:
            return False, self.min_interval - (now - last_request)
        
        self.user_last_request[user_id] = now
        return True, 0
    
    def get_wait_time(self, user_id):
        """Get remaining wait time for user"""
        now = time.time()
        last_request = self.user_last_request.get(user_id, 0)
        remaining = self.min_interval - (now - last_request)
        return max(0, remaining)

# Global rate limiter instance
rate_limiter = RateLimiter()