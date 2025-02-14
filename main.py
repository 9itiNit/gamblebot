import logging
import sqlite3
import random
import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters

load_dotenv()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def create_db():
    """Creates the users table in the users.db database if it doesn't exist"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            wallet_address TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Database functions
def get_wallet_address(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT wallet_address FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def store_wallet_address(user_id, wallet_address):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (user_id, wallet_address) VALUES (?, ?)', (user_id, wallet_address))
    conn.commit()
    conn.close()

# Wallet generation
def generate_wallet():
    try:
        response = requests.post('http://localhost:3000/generate-wallet')
        response.raise_for_status()  # Raises an HTTPError for bad responses
        wallet_address = response.json().get('walletAddress')
        if wallet_address:
            return wallet_address
        else:
            raise ValueError("No wallet address returned in response")
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
    except ValueError as e:
        logger.error(f"Error processing response: {e}")
    return "Error generating wallet"


# get user balance
def get_balance_from_server(wallet_address):
    url = 'http://localhost:3000/get-balance'  # The URL of your Express server's endpoint
    headers = {'Content-Type': 'application/json'}
    payload = {'walletAddress': wallet_address}

    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            balance_data = response.json()
            balance = balance_data.get('balance')
            if balance is not None:
                return balance
            else:
                print('Error: No balance found in response')
        else:
            print(f'Error: {response.status_code} - {response.text}')
    
    except requests.exceptions.RequestException as e:
        print(f'Error fetching balance from server: {e}')
    
    return None
# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username

    logger.info(f"User {user.first_name} {user.last_name} (@{username}) has started a conversation.")
    await update.message.reply_text('Hello! Welcome to the bot.')

# Register handler
async def register(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id
    
    # Check if the user already has a wallet
    wallet_address = get_wallet_address(user_id)
    balance = get_balance_from_server(wallet_address)
    # balance =2
    if wallet_address:
        await update.message.reply_text(f'You already have a wallet. Your wallet address is: {wallet_address} and {balance}')
    else:
        # If no wallet exists, generate a new one
        wallet_address = generate_wallet()
        store_wallet_address(user_id, wallet_address)
        await update.message.reply_text(f'A new wallet has been created. Your wallet address is: {wallet_address}')

# Game functions
waiting_list = []
user_bets = {}
game_started = {}

def generate_coin_flip():
    """Simulates a coin flip, returning 'Heads' or 'Tails' using Mersenne Twister."""
    return "Heads" if random.randint(0, 1) == 0 else "Tails"

async def start_game(player1, player2, context):
    outcome = generate_coin_flip()

    await context.bot.send_message(chat_id=player1, text=f"The coin flip result is: {outcome}. Your bet: {user_bets.get(player1, 'No bet')}.")
    await context.bot.send_message(chat_id=player2, text=f"The coin flip result is: {outcome}. Your bet: {user_bets.get(player2, 'No bet')}.")
    
    for player in [player1, player2]:
        if user_bets.get(player) == outcome.lower():
            await context.bot.send_message(chat_id=player, text="Congratulations! You won your bet!")
        else:
            await context.bot.send_message(chat_id=player, text="Sorry, you lost your bet.")

async def join(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id

    if user_id in waiting_list:
        await update.message.reply_text("You're already in the waiting list!")
        return

    waiting_list.append(user_id)
    await update.message.reply_text("You've joined the waiting list. Waiting to pair you with another player...")    

    if len(waiting_list) >= 2:
        player1 = waiting_list.pop(0)
        player2 = waiting_list.pop(0)

        await context.bot.send_message(chat_id=player1, text="You've been paired with another player! Let's start the game.")
        await context.bot.send_message(chat_id=player2, text="You've been paired with another player! Let's start the game.")
        
        game_started[player1] = player2
        game_started[player2] = player1

async def place_bet(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id
    bet = update.message.text.lower()

    if bet not in ['heads', 'tails']:
        await update.message.reply_text("Please place a valid bet: 'heads' or 'tails'.")
        return

    user_bets[user_id] = bet
    await update.message.reply_text(f"You have placed a bet on: {bet.capitalize()}.")

    other_player = game_started.get(user_id)
    if other_player and other_player in user_bets:
        await start_game(user_id, other_player, context)
        user_bets.clear()
        del game_started[user_id]
        del game_started[other_player]

def main() -> None:
    application = Application.builder().token(os.getenv("TOKEN")).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("balance", get_balance_from_server))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, place_bet))
    
    application.run_polling()

if __name__ == '__main__':
    create_db()
    main()
