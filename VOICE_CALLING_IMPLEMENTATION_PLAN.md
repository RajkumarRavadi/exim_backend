# Voice Calling Feature - Implementation Plan

## Executive Summary

This document outlines the implementation plan for adding a **voice calling feature** that allows users to call an AI agent via phone to query order status and other ERPNext data. The system will integrate voice-to-text, process through the existing AI chat system, and respond via text-to-speech.

---

## Current System Analysis

### Existing Capabilities
1. **AI Chat System**: Text-based conversational interface (`ai_chat.py`)
2. **Order Status Queries**: Can query sales order details via `get_document_details()` and `dynamic_search()`
3. **AI Integration**: Google Gemini AI via OpenRouter or direct API
4. **Session Management**: Conversation history stored in Frappe cache
5. **DocType Handlers**: Specialized handlers for Sales Orders, Customers, etc.

### What's Missing
1. **Voice Input**: No speech-to-text capability
2. **Phone Integration**: No telephony service integration
3. **Voice Output**: No text-to-speech for responses
4. **Call Routing**: No webhook endpoints for incoming calls
5. **Call Context**: No call session management separate from chat sessions

---

## Implementation Architecture

### High-Level Flow

```
┌─────────────┐
│   User      │
│  Calls      │
│  Phone #    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Telephony Service (Twilio/Vonage) │
│  • Receives call                    │
│  • Routes to webhook                │
└──────┬──────────────────────────────┘
       │
       │ HTTP POST (webhook)
       ▼
┌─────────────────────────────────────┐
│  Voice Call Handler                 │
│  (voice_call_handler.py)            │
│  • Creates call session             │
│  • Handles call events              │
│  • Manages call state               │
└──────┬──────────────────────────────┘
       │
       ├─► Incoming Call
       │   │
       │   ▼
       │   ┌─────────────────────────────┐
       │   │ Greeting & Prompt            │
       │   │ "Hello, how can I help you?" │
       │   └─────────────────────────────┘
       │
       ├─► User Speaks
       │   │
       │   ▼
       │   ┌─────────────────────────────┐
       │   │ Speech-to-Text (STT)         │
       │   │ • Twilio/Vonage STT          │
       │   │ • Google Speech-to-Text      │
       │   └─────────────────────────────┘
       │   │
       │   ▼
       │   ┌─────────────────────────────┐
       │   │ Process via AI Chat         │
       │   │ • Reuse process_chat()      │
       │   │ • Get AI response           │
       │   │ • Execute actions if needed │
       │   └─────────────────────────────┘
       │   │
       │   ▼
       │   ┌─────────────────────────────┐
       │   │ Text-to-Speech (TTS)          │
       │   │ • Convert response to audio  │
       │   │ • Stream to caller           │
       │   └─────────────────────────────┘
       │
       └─► Call End
           │
           ▼
           ┌─────────────────────────────┐
           │ Save Call Log                │
           │ • Call duration              │
           │ • Transcript                 │
           │ • Order queries              │
           └─────────────────────────────┘
```

---

## Detailed Implementation Plan

### Phase 1: Infrastructure Setup

#### 1.1 Telephony Service Integration

**Option A: Twilio (Recommended)**
- **Pros**: Easy integration, good documentation, reliable
- **Cons**: Paid service (pay-as-you-go)
- **Setup**:
  ```bash
  pip install twilio
  ```

**Option B: Vonage (Nexmo)**
- **Pros**: Competitive pricing, good API
- **Cons**: Slightly more complex setup

**Option C: Google Voice API**
- **Pros**: Integrates with existing Gemini setup
- **Cons**: More complex, requires Google Cloud setup

**Recommendation**: Start with **Twilio** for faster implementation.

#### 1.2 Speech-to-Text (STT) Service

**Options**:
1. **Twilio Speech Recognition** (built-in)
2. **Google Cloud Speech-to-Text** (high accuracy)
3. **OpenAI Whisper** (open-source, self-hosted)

**Recommendation**: Use **Twilio's built-in STT** initially, upgrade to Google Cloud Speech-to-Text for better accuracy.

#### 1.3 Text-to-Speech (TTS) Service

**Options**:
1. **Twilio Text-to-Speech** (built-in, simple)
2. **Google Cloud Text-to-Speech** (natural voices)
3. **Amazon Polly** (high quality)

**Recommendation**: Start with **Twilio TTS**, upgrade to Google Cloud TTS for better voice quality.

---

### Phase 2: Core Components

#### 2.1 Voice Call Handler (`voice_call_handler.py`)

**Location**: `exim_backend/api/voice_call_handler.py`

**Responsibilities**:
- Handle incoming call webhooks
- Manage call sessions
- Process voice input
- Generate voice responses
- Log call data

**Key Functions**:
```python
@frappe.whitelist(allow_guest=True, methods=["POST"])
def handle_incoming_call():
    """Handle incoming call webhook from Twilio"""
    
@frappe.whitelist(allow_guest=True, methods=["POST"])
def handle_voice_input():
    """Process voice input (STT result)"""
    
@frappe.whitelist(allow_guest=True, methods=["POST"])
def handle_call_status():
    """Handle call status updates (answered, ended, etc.)"""
    
def process_voice_query(text, call_sid):
    """Process voice query through AI chat system"""
    
def generate_voice_response(text_response):
    """Convert text response to TwiML for TTS"""
    
def save_call_log(call_sid, transcript, order_queries):
    """Save call log to database"""
```

#### 2.2 Call Session Management

**Storage**: Frappe Cache + Database

**Session Structure**:
```python
{
    "call_sid": "CAxxxxx",
    "phone_number": "+1234567890",
    "session_id": "voice_call_xxx",
    "chat_session_id": "chat_xxx",  # Link to AI chat session
    "transcript": [
        {"role": "user", "text": "...", "timestamp": "..."},
        {"role": "assistant", "text": "...", "timestamp": "..."}
    ],
    "order_queries": ["SAL-ORD-2025-00001", ...],
    "status": "ringing|in_progress|completed|failed",
    "start_time": "...",
    "end_time": "...",
    "duration": 0
}
```

#### 2.3 Integration with Existing AI Chat

**Reuse Existing Components**:
- `process_chat()` function from `ai_chat.py`
- DocType handlers (SalesOrderHandler, etc.)
- AI service (`call_ai_api()`)
- Session management

**Modifications Needed**:
- Add voice-specific system prompt
- Optimize responses for voice (shorter, clearer)
- Handle order status queries specifically

---

### Phase 3: Order Status Query Optimization

#### 3.1 Voice-Optimized System Prompt

**Key Differences from Text Chat**:
- Shorter responses (voice is slower to consume)
- Clear, concise answers
- Avoid complex JSON structures
- Focus on order status queries

**Example Prompt Addition**:
```
VOICE MODE RULES:
- Keep responses under 50 words when possible
- Use simple, conversational language
- For order status: "Order SAL-ORD-2025-00001 is [status]. Total: $X. Delivery: [date]."
- Avoid technical jargon
- Speak naturally, as if talking to a person
```

#### 3.2 Order Status Query Handler

**Specialized Function**:
```python
def get_order_status_voice(order_id, phone_number=None):
    """
    Get order status optimized for voice response.
    
    Returns:
    {
        "order_id": "SAL-ORD-2025-00001",
        "status": "Submitted",
        "customer": "John Doe",
        "total": 1000.00,
        "delivery_date": "2025-01-15",
        "items_count": 3,
        "voice_response": "Order SAL-ORD-2025-00001 for John Doe is currently Submitted. Total amount is $1,000. Expected delivery is January 15th, 2025. The order contains 3 items."
    }
    """
```

#### 3.3 Phone Number to Customer Mapping

**Feature**: Identify caller from phone number
- Look up customer by phone number
- Pre-filter orders by customer
- Personalize responses

**Implementation**:
```python
def get_customer_by_phone(phone_number):
    """Get customer linked to phone number"""
    # Check Contact doctype
    # Check Customer mobile_no field
    # Return customer name and ID
```

---

### Phase 4: API Endpoints

#### 4.1 Twilio Webhook Endpoints

**Incoming Call Webhook**:
```
POST /api/method/exim_backend.api.voice_call_handler.handle_incoming_call
```

**Voice Input Webhook** (Gather):
```
POST /api/method/exim_backend.api.voice_call_handler.handle_voice_input
```

**Call Status Webhook**:
```
POST /api/method/exim_backend.api.voice_call_handler.handle_call_status
```

#### 4.2 TwiML Response Format

**Greeting**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Hello! I'm your AI assistant. How can I help you with your order today?</Say>
    <Gather input="speech" action="/api/method/.../handle_voice_input" method="POST">
        <Say>Please speak your question.</Say>
    </Gather>
</Response>
```

**Response**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Order SAL-ORD-2025-00001 is currently Submitted. Total amount is $1,000. Expected delivery is January 15th, 2025.</Say>
    <Gather input="speech" action="/api/method/.../handle_voice_input" method="POST">
        <Say>Is there anything else I can help you with?</Say>
    </Gather>
</Response>
```

---

### Phase 5: Database Schema

#### 5.1 Voice Call Log DocType

**Fields**:
- `call_sid` (Data): Twilio Call SID
- `phone_number` (Data): Caller's phone number
- `customer` (Link): Linked customer (if identified)
- `status` (Select): ringing, in_progress, completed, failed
- `start_time` (Datetime)
- `end_time` (Datetime)
- `duration` (Duration)
- `transcript` (Long Text): Full conversation transcript
- `order_queries` (Table): Orders queried during call
- `ai_session_id` (Data): Linked AI chat session
- `recording_url` (Data): Call recording URL (if enabled)

#### 5.2 Order Query Log (Child Table)

**Fields**:
- `order_id` (Link): Sales Order
- `query_type` (Select): status, details, delivery_date, etc.
- `response_given` (Long Text): What was told to caller

---

### Phase 6: Configuration

#### 6.1 Site Config Settings

```json
{
  "twilio_account_sid": "ACxxxxx",
  "twilio_auth_token": "xxxxx",
  "twilio_phone_number": "+1234567890",
  "voice_call_enabled": true,
  "voice_call_greeting": "Hello! I'm your AI assistant. How can I help you?",
  "voice_call_language": "en-US",
  "voice_call_voice": "alice",
  "voice_call_timeout": 10,
  "voice_call_max_duration": 300
}
```

#### 6.2 DocType Settings

Create **Voice Call Settings** DocType:
- Enable/disable voice calls
- Customize greeting message
- Set business hours
- Configure call routing rules

---

## Implementation Steps

### Step 1: Setup Twilio Account (1-2 hours)
1. Create Twilio account
2. Get phone number
3. Configure webhook URLs
4. Test basic call flow

### Step 2: Create Voice Call Handler (4-6 hours)
1. Create `voice_call_handler.py`
2. Implement webhook endpoints
3. Add TwiML response generation
4. Test with Twilio console

### Step 3: Integrate with AI Chat (3-4 hours)
1. Modify `process_chat()` to support voice mode
2. Add voice-optimized system prompt
3. Create order status query handler
4. Test voice queries

### Step 4: Add Call Logging (2-3 hours)
1. Create Voice Call Log DocType
2. Implement call log saving
3. Add transcript storage
4. Test logging

### Step 5: Phone Number to Customer Mapping (2-3 hours)
1. Implement customer lookup by phone
2. Add customer identification in call handler
3. Personalize responses
4. Test with known customers

### Step 6: Testing & Refinement (4-6 hours)
1. Test various order status queries
2. Test error handling
3. Optimize voice responses
4. Test call quality and latency
5. User acceptance testing

**Total Estimated Time**: 16-24 hours

---

## Code Structure

### New Files to Create

```
exim_backend/
├── api/
│   ├── voice_call_handler.py          # Main voice call handler
│   └── voice_utils.py                  # Voice-specific utilities
├── doctypes/
│   ├── voice_call_log/
│   │   ├── voice_call_log.json
│   │   ├── voice_call_log.py
│   │   └── voice_call_log.js
│   └── voice_call_settings/
│       ├── voice_call_settings.json
│       ├── voice_call_settings.py
│       └── voice_call_settings.js
└── templates/
    └── includes/
        └── voice_call.js               # Frontend for call logs (optional)
```

### Modified Files

```
exim_backend/
└── api/
    └── ai_chat.py                      # Add voice mode support
```

---

## Example Implementation

### Basic Voice Call Handler Structure

```python
# exim_backend/api/voice_call_handler.py

import frappe
from twilio.twiml.voice_response import VoiceResponse, Gather
from exim_backend.api.ai_chat import process_chat

@frappe.whitelist(allow_guest=True, methods=["POST"])
def handle_incoming_call():
    """Handle incoming call from Twilio"""
    call_sid = frappe.form_dict.get("CallSid")
    from_number = frappe.form_dict.get("From")
    to_number = frappe.form_dict.get("To")
    
    # Create call session
    session_id = f"voice_call_{call_sid}"
    call_data = {
        "call_sid": call_sid,
        "phone_number": from_number,
        "status": "ringing",
        "start_time": frappe.utils.now()
    }
    frappe.cache().set_value(f"voice_call:{call_sid}", call_data, expires_in_sec=3600)
    
    # Generate greeting
    response = VoiceResponse()
    response.say(
        "Hello! I'm your AI assistant. How can I help you with your order today?",
        voice="alice"
    )
    
    # Gather voice input
    gather = Gather(
        input="speech",
        action=frappe.utils.get_url(f"/api/method/exim_backend.api.voice_call_handler.handle_voice_input"),
        method="POST",
        speech_timeout="auto",
        language="en-US"
    )
    gather.say("Please speak your question.")
    response.append(gather)
    
    # If no input, say goodbye
    response.say("I didn't hear anything. Goodbye!")
    response.hangup()
    
    return str(response), 200, {"Content-Type": "text/xml"}

@frappe.whitelist(allow_guest=True, methods=["POST"])
def handle_voice_input():
    """Process voice input from caller"""
    call_sid = frappe.form_dict.get("CallSid")
    speech_result = frappe.form_dict.get("SpeechResult", "").strip()
    confidence = frappe.form_dict.get("Confidence", "0")
    
    if not speech_result:
        response = VoiceResponse()
        response.say("I didn't catch that. Could you please repeat?")
        gather = Gather(...)
        response.append(gather)
        return str(response), 200, {"Content-Type": "text/xml"}
    
    # Process through AI chat
    ai_response = process_voice_query(speech_result, call_sid)
    
    # Generate voice response
    response = VoiceResponse()
    response.say(ai_response["voice_text"], voice="alice")
    
    # Ask for more
    gather = Gather(...)
    gather.say("Is there anything else I can help you with?")
    response.append(gather)
    
    response.say("Thank you for calling. Goodbye!")
    response.hangup()
    
    return str(response), 200, {"Content-Type": "text/xml"}

def process_voice_query(text, call_sid):
    """Process voice query through AI system"""
    # Get call session
    call_data = frappe.cache().get_value(f"voice_call:{call_sid}")
    chat_session_id = call_data.get("chat_session_id", f"voice_chat_{call_sid}")
    
    # Process through existing AI chat (with voice mode)
    result = process_chat(
        message=text,
        session_id=chat_session_id,
        voice_mode=True  # New parameter
    )
    
    # Extract voice-optimized response
    ai_text = result.get("message", "I'm sorry, I didn't understand that.")
    
    # Optimize for voice (shorter, clearer)
    voice_text = optimize_for_voice(ai_text)
    
    # Save to transcript
    save_to_transcript(call_sid, "user", text)
    save_to_transcript(call_sid, "assistant", voice_text)
    
    return {
        "voice_text": voice_text,
        "full_response": ai_text,
        "suggested_action": result.get("suggested_action")
    }

def optimize_for_voice(text):
    """Optimize AI response for voice output"""
    # Remove markdown
    # Shorten if too long
    # Convert to natural speech
    # Remove technical jargon
    return text  # Simplified for now
```

---

## Security Considerations

1. **Webhook Authentication**: Verify Twilio webhook signatures
2. **Rate Limiting**: Prevent abuse
3. **Phone Number Validation**: Validate caller numbers
4. **Call Duration Limits**: Prevent long calls
5. **Data Privacy**: Don't expose sensitive data in voice

---

## Testing Plan

### Unit Tests
- Voice call handler functions
- Order status query handler
- Phone number to customer mapping
- Voice response optimization

### Integration Tests
- End-to-end call flow
- AI chat integration
- Call logging
- Error handling

### User Acceptance Tests
- Real phone calls
- Various order status queries
- Error scenarios
- Call quality assessment

---

## Future Enhancements

1. **Multi-language Support**: Support multiple languages
2. **Call Recording**: Record and store calls
3. **Analytics Dashboard**: Call metrics and insights
4. **IVR Menu**: "Press 1 for order status, Press 2 for..."
5. **SMS Integration**: Send order details via SMS
6. **Callback Feature**: Schedule callbacks
7. **Voice Biometrics**: Identify callers by voice

---

## Cost Estimation

### Twilio Costs (Approximate)
- Phone Number: $1-3/month
- Incoming Calls: $0.0085/minute
- Speech Recognition: Included
- Text-to-Speech: $0.005/minute
- **Estimated**: $50-100/month for moderate usage

### Development Costs
- Initial Implementation: 16-24 hours
- Testing & Refinement: 8-12 hours
- **Total**: 24-36 hours

---

## Conclusion

This implementation plan provides a comprehensive roadmap for adding voice calling functionality to the AI chat system. The approach leverages existing infrastructure while adding voice-specific components. The phased approach allows for incremental development and testing.

**Next Steps**:
1. Review and approve this plan
2. Set up Twilio account
3. Begin Phase 1 implementation
4. Iterate based on testing results

