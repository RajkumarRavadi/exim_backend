# OpenRouter Setup Guide

The AI chatbot now supports **OpenRouter**, which gives you access to multiple AI models including Google's Gemini, OpenAI's GPT, Anthropic's Claude, and many more!

## Why Use OpenRouter?

✅ **Access to Multiple Models** - One API key for 100+ AI models  
✅ **Flexible Pricing** - Pay only for what you use  
✅ **Free Models Available** - Some models are completely free  
✅ **Easy to Use** - Simple API similar to OpenAI  
✅ **No Rate Limits** - (on paid models)  

## Quick Setup

### Step 1: Get Your OpenRouter API Key

1. Go to **[OpenRouter](https://openrouter.ai/)**
2. Click "Sign In" (use Google, GitHub, or email)
3. Go to **[Keys](https://openrouter.ai/keys)** section
4. Click "Create Key"
5. Give it a name (e.g., "ERPNext Chatbot")
6. Copy your API key (starts with `sk-or-v1-...`)

### Step 2: Configure Your Site

**Option A: Using Terminal (Recommended)**

```bash
cd /home/frappeuser/frappe-bench-v15
./env/bin/bench --site [your-site-name] set-config openrouter_api_key YOUR_API_KEY_HERE
./env/bin/bench restart
```

**Option B: Manual Configuration**

Edit your site config file:

```bash
nano sites/[your-site-name]/site_config.json
```

Add this line:

```json
{
  "db_name": "...",
  "openrouter_api_key": "sk-or-v1-xxxxxxxxxxxxxxxxxxxxx"
}
```

Save and restart:

```bash
./env/bin/bench restart
```

### Step 3: Test It!

1. Go to `http://127.0.0.1:8002/ai-chat`
2. Send a message: "Hello, can you help me?"
3. You should get an AI response! 🎉

## Available Models

### Free Models (Recommended to Start)

You can use these models for free:

```json
{
  "ai_model": "google/gemini-2.0-flash-exp:free"
}
```

**Other Free Options:**
- `google/gemini-2.0-flash-exp:free` - Fast and capable (Recommended)
- `google/gemini-flash-1.5:free` - Good balance
- `meta-llama/llama-3.2-11b-vision-instruct:free` - Open source
- `nousresearch/hermes-3-llama-3.1-405b:free` - Very capable

### Paid Models (Better Quality)

If you add credits to your OpenRouter account:

- `google/gemini-pro-1.5` - Most capable Gemini
- `openai/gpt-4-turbo` - OpenAI's best
- `anthropic/claude-3.5-sonnet` - Anthropic's Claude
- `openai/gpt-3.5-turbo` - Fast and affordable

### Change the Model

To use a different model:

```bash
./env/bin/bench --site [site-name] set-config ai_model "google/gemini-pro-1.5"
./env/bin/bench restart
```

Or in `site_config.json`:

```json
{
  "openrouter_api_key": "sk-or-v1-...",
  "ai_model": "google/gemini-pro-1.5"
}
```

## Cost & Credits

### Free Tier
- Many models are completely free
- No credit card required
- Rate limits may apply

### Paid Usage
1. Go to **[Account](https://openrouter.ai/account)**
2. Click "Add Credits"
3. Add $5, $10, or more
4. Usage is deducted from your balance

**Pricing Examples:**
- Gemini Flash: ~$0.000001 per token
- GPT-3.5: ~$0.000002 per token
- GPT-4: ~$0.00003 per token

Most chat messages cost less than $0.01!

## Troubleshooting

### Error: "Invalid API Key"

**Solution:**
- Check your API key is correct (starts with `sk-or-v1-`)
- Make sure you copied the entire key
- Regenerate key if needed

### Error: "Insufficient credits"

**Solution:**
- Use a free model: `google/gemini-2.0-flash-exp:free`
- Or add credits to your account

### Error: "Model not found"

**Solution:**
- Check model name spelling
- See available models at: https://openrouter.ai/models
- Use the exact model ID shown on the website

### Slow Responses

**Solution:**
- Use a faster model (Flash vs Pro)
- Check your internet connection
- Free models may have queues during peak times

## Advanced Configuration

### Set Site URL (for tracking)

```bash
./env/bin/bench --site [site-name] set-config site_url "https://yoursite.com"
```

This helps OpenRouter track your usage properly.

### Custom Headers

The code automatically sends:
- `HTTP-Referer`: Your site URL
- `X-Title`: "ERPNext AI Assistant"

This helps with OpenRouter analytics.

## Switching Back to Direct Gemini API

If you want to use Google's Gemini API directly:

1. Remove `openrouter_api_key` from config
2. Add `gemini_api_key` instead:

```bash
./env/bin/bench --site [site-name] set-config gemini_api_key YOUR_GOOGLE_API_KEY
./env/bin/bench restart
```

The code automatically detects which API to use!

## Comparison

### OpenRouter vs Direct Gemini

| Feature | OpenRouter | Direct Gemini |
|---------|-----------|---------------|
| **Setup** | Very Easy | Easy |
| **Models** | 100+ models | Only Gemini |
| **Cost** | Pay per use | Free tier available |
| **Rate Limits** | Generous | Stricter on free tier |
| **API Format** | OpenAI-compatible | Google-specific |

**Recommendation:** Start with OpenRouter free models, then upgrade if needed!

## Example Messages to Test

Try these messages in the chat:

### General Chat
```
"Hello! How can you help me?"
"What can you do?"
```

### Create Documents
```
"Create a new customer named John Doe with email john@example.com"
"Add an item: Laptop, code: LAP-001, price: $999"
"Create a lead for Sarah Smith from ABC Corp"
```

### With Images
1. Upload a business card
2. Message: "Extract information from this card"

## Get Help

- **OpenRouter Docs:** https://openrouter.ai/docs
- **Model List:** https://openrouter.ai/models
- **Discord:** https://discord.gg/openrouter
- **Status Page:** https://status.openrouter.ai/

## Your Current Config

To check your current configuration:

```bash
cd /home/frappeuser/frappe-bench-v15
./env/bin/bench --site [site-name] console
```

Then run:

```python
import frappe
print("OpenRouter Key:", frappe.conf.get("openrouter_api_key")[:20] + "..." if frappe.conf.get("openrouter_api_key") else "Not set")
print("Model:", frappe.conf.get("ai_model") or "default (gemini-2.0-flash-exp:free)")
```

---

**You're all set!** 🚀 Your chatbot now works with OpenRouter and can access multiple AI models!

