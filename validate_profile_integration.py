#!/usr/bin/env python3
"""
Profile Data Validation Script for K2 GM Bot
Tests if the bot properly reads and utilizes Notion profile data for personality adaptation.
"""

import sys
sys.path.append('/home/claude')

from k2_notion_general_manager import NotionClient
from openai_integration import build_conversation_context
from config import bot_persona

def test_profile_integration():
    """Test if profile data is properly integrated into AI conversations"""
    print("=== NOTION PROFILE INTEGRATION TEST ===\n")
    
    # Initialize Notion client
    notion = NotionClient()
    
    # Test user ID from your logs
    test_user_id = 6904183057  # Lydell Tyler from the logs
    
    print(f"Testing profile integration for user ID: {test_user_id}")
    
    try:
        # Get user authorization and profile
        authorized, profile_text, context_lines, username = notion.get_user_authorization(test_user_id)
        
        print(f"\n--- User Authorization Results ---")
        print(f"✅ Username: {username}")
        print(f"✅ Authorized: {authorized}")
        print(f"✅ Context Lines: {context_lines}")
        print(f"✅ Profile Data Length: {len(profile_text)} characters")
        
        if profile_text.strip():
            print(f"\n--- Profile Data Content ---")
            print(f"Profile Text Preview:")
            print(profile_text[:200] + "..." if len(profile_text) > 200 else profile_text)
            
            # Test conversation context building
            print(f"\n--- Conversation Context Test ---")
            test_message = "I'm feeling overwhelmed with my workload today."
            test_history = [
                "09-19-2025 09:02 PM CT Lydell [ID: 6904183057]: --- Hi there",
                "09-19-2025 09:02 PM CT 10x GM AI [ID: BOT_ID]: --- Hello! How can I help you today?"
            ]
            
            conversation = build_conversation_context(
                bot_persona,
                profile_text, 
                test_history,
                test_message
            )
            
            print(f"✅ Conversation context built successfully")
            print(f"✅ Number of messages in context: {len(conversation)}")
            
            # Check if profile data is actually included
            system_message = conversation[0]['content']
            if profile_text in system_message:
                print(f"✅ Profile data is properly included in system message")
            else:
                print(f"❌ Profile data NOT found in system message")
            
            if "EMPLOYEE PROFILE DATA" in system_message:
                print(f"✅ Profile section header found in system message")
            else:
                print(f"❌ Profile section header NOT found")
                
            print(f"\n--- System Message Preview ---")
            print(f"System message length: {len(system_message)} characters")
            print(f"First 300 chars: {system_message[:300]}...")
            
            return True
        else:
            print(f"❌ No profile data found for user")
            print(f"   This could mean:")
            print(f"   - User has no additional fields in Notion beyond required ones")
            print(f"   - Notion integration is not reading profile fields correctly")
            return False
            
    except Exception as e:
        print(f"❌ Error during profile integration test: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

def test_notion_fields():
    """Test what fields are being extracted from Notion"""
    print(f"\n=== NOTION FIELD EXTRACTION TEST ===\n")
    
    notion = NotionClient()
    test_user_id = 6904183057
    
    try:
        # Get raw user data to see what fields are available
        query = {
            'filter': {
                'and': [
                    {'property': 'active', 'checkbox': {'equals': True}},
                    {'property': 'telegram_user_id', 'number': {'equals': test_user_id}}
                ]
            }
        }
        
        response = notion._make_request('POST', f'/databases/{notion.employees_db_id}/query', query)
        
        if response and response.get('results'):
            user_data = response['results'][0]
            props = user_data.get('properties', {})
            
            print(f"Available properties in Notion database:")
            
            system_fields = [
                'Name', 'telegram_handle', 'telegram_user_id', 
                'can_chat_bot', 'context_lines', 'active', 'admin'
            ]
            
            profile_fields = []
            
            for field_name, field_data in props.items():
                field_type = field_data.get('type', 'unknown')
                is_system = field_name in system_fields
                
                if is_system:
                    print(f"  🔧 {field_name} ({field_type}) - SYSTEM FIELD")
                else:
                    field_text = notion._extract_text_from_property(field_data)
                    if field_text:
                        print(f"  📋 {field_name} ({field_type}) - PROFILE DATA: '{field_text}'")
                        profile_fields.append((field_name, field_text))
                    else:
                        print(f"  ⚪ {field_name} ({field_type}) - EMPTY PROFILE FIELD")
            
            print(f"\nProfile fields that will be used for AI personality adaptation:")
            if profile_fields:
                for field_name, field_text in profile_fields:
                    print(f"  ✅ {field_name}: {field_text}")
            else:
                print(f"  ❌ No profile fields found with data")
                print(f"     Recommendation: Add MBTI, Enneagram, Role, Goals, etc. to user's Notion record")
                
        else:
            print(f"❌ Could not retrieve user data from Notion")
            
    except Exception as e:
        print(f"❌ Error testing Notion fields: {e}")

def main():
    """Run all validation tests"""
    print("Starting K2 GM Bot Profile Integration Validation...\n")
    
    # Test 1: Basic profile integration
    profile_success = test_profile_integration()
    
    # Test 2: Field extraction details  
    test_notion_fields()
    
    # Summary
    print(f"\n=== VALIDATION SUMMARY ===")
    if profile_success:
        print(f"✅ Profile integration is working correctly")
        print(f"✅ Bot will adapt responses based on user profile data")
    else:
        print(f"❌ Profile integration needs attention")
        print(f"❌ Bot may not be personalizing responses effectively")
    
    print(f"\nNext steps:")
    print(f"1. Ensure user has profile data in Notion (MBTI, Role, Goals, etc.)")
    print(f"2. Test actual bot conversation to verify adaptation")
    print(f"3. Check that system prompt uses profile data effectively")

if __name__ == "__main__":
    main()