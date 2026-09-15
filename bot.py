import os
import random
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Import game data
from game_data import TRUTH_OR_DARE_DATA, NHIE, WYR, CHEATING, TWENTY_Q_WORDS

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# TIDY CHAT HELPER FUNCTIONS
# ==========================================

async def cleanup_previous_game(context: ContextTypes.DEFAULT_TYPE):
    """Instantly deletes the previous active game message to keep the chat tidy."""
    msg_id = context.chat_data.get('active_game_msg_id')
    chat_id = context.chat_data.get('active_game_chat_id')
    
    if msg_id and chat_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass
            
    context.chat_data['active_game_msg_id'] = None
    context.chat_data['active_game_chat_id'] = None

async def send_tidy_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, reply_markup=None):
    """Helper to send a new message and track its ID for future cleanup."""
    await cleanup_previous_game(context)
    message = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    context.chat_data['active_game_msg_id'] = message.message_id
    context.chat_data['active_game_chat_id'] = chat_id
    return message

# ==========================================
# TRUTH OR DARE FLOW
# ==========================================

async def tod_show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: Show category selection."""
    chat_id = update.effective_chat.id
    
    # Clear any previous ToD state
    context.chat_data.pop('tod_category', None)
    context.chat_data.pop('tod_type', None)
    
    keyboard = [
        [InlineKeyboardButton("😂 Classic & Funny", callback_data="tod_cat_classic")],
        [InlineKeyboardButton("👯 Friends", callback_data="tod_cat_friends")],
        [InlineKeyboardButton("❤️ Couples", callback_data="tod_cat_couples")],
        [InlineKeyboardButton("🎈 Party & Kids", callback_data="tod_cat_party")],
        [InlineKeyboardButton("🔞 Spicy (18+)", callback_data="tod_cat_spicy")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    text = "🎭 *Truth or Dare*\n\nSelect a category to begin:"
    await send_tidy_message(context, chat_id, text, InlineKeyboardMarkup(keyboard))

async def tod_show_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    """Step 2: Show Truth or Dare selection for the chosen category."""
    chat_id = update.effective_chat.id
    context.chat_data['tod_category'] = category
    
    keyboard = [
        [InlineKeyboardButton("🤔 Truth", callback_data=f"tod_type_truth_{category}"), 
         InlineKeyboardButton("😈 Dare", callback_data=f"tod_type_dare_{category}")],
        [InlineKeyboardButton("🔙 Change Category", callback_data="tod_categories")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    text = f"🎭 *Truth or Dare*\n\nCategory: *{category}*\n\nNow, choose your poison:"
    await send_tidy_message(context, chat_id, text, InlineKeyboardMarkup(keyboard))

async def tod_show_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, prompt_type: str):
    """Step 3: Show the actual prompt."""
    chat_id = update.effective_chat.id
    context.chat_data['tod_category'] = category
    context.chat_data['tod_type'] = prompt_type
    
    # Fetch prompt
    prompt_list = TRUTH_OR_DARE_DATA[category][prompt_type]
    prompt = random.choice(prompt_list)
    
    emoji = "🤔" if prompt_type == "truth" else "😈"
    
    keyboard = [
        [InlineKeyboardButton(f"🔄 Next {prompt_type.capitalize()}", callback_data=f"tod_next_{prompt_type}_{category}")],
        [InlineKeyboardButton("🔙 Change Category", callback_data="tod_categories")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    text = f"{emoji} *{category} - {prompt_type.capitalize()}*\n\n{prompt}"
    await send_tidy_message(context, chat_id, text, InlineKeyboardMarkup(keyboard))

# ==========================================
# OTHER GAME HANDLERS (Simplified for brevity)
# ==========================================

async def show_game_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt_list: list, game_name: str, callback_action: str):
    await cleanup_previous_game(context)
    prompt = random.choice(prompt_list)
    keyboard = [
        [InlineKeyboardButton(f"🔄 Next {game_name}", callback_data=f"next_{callback_action}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    chat_id = update.effective_chat.id
    await send_tidy_message(context, chat_id, f"*{game_name}:*\n{prompt}", InlineKeyboardMarkup(keyboard))

async def handle_20q_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cleanup_previous_game(context)
    game_data = random.choice(TWENTY_Q_WORDS)
    context.chat_data['20q'] = {
        'word': game_data['word'], 'category': game_data['category'], 'hints': game_data['hints'],
        'guesses': 0, 'max_guesses': 20, 'hints_used': 0
    }
    text = (f"🎮 *20 Questions: Guess the Word!*\n\n"
            f"Category: *{game_data['category']}*\n"
            f"You have 20 guesses. Type your guess below!\n(Type 'hint' to use one, but it costs a guess!)")
    keyboard = [[InlineKeyboardButton("🔄 New Word", callback_data="start_20q")]]
    chat_id = update.effective_chat.id
    await send_tidy_message(context, chat_id, text, InlineKeyboardMarkup(keyboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cleanup_previous_game(context)
    text = "🎉 *Welcome to the Party Games Bot!* 🎉\n\nSelect a game below to start playing!"
    keyboard = [
        [InlineKeyboardButton("🎭 Truth or Dare", callback_data="tod_categories")],
        [InlineKeyboardButton("🙅‍♂️ NHIE", callback_data="next_nhie"), InlineKeyboardButton("🤷 WYR", callback_data="next_wyr")],
        [InlineKeyboardButton("💔 Cheating?", callback_data="next_cheating")],
        [InlineKeyboardButton("🎮 20 Questions", callback_data="start_20q")]
    ]
    chat_id = update.effective_chat.id
    await send_tidy_message(context, chat_id, text, InlineKeyboardMarkup(keyboard))

async def stop_20q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if '20q' in context.chat_data:
        word = context.chat_data['20q']['word']
        del context.chat_data['20q']
        msg_id = context.chat_data.get('active_game_msg_id')
        chat_id = context.chat_data.get('active_game_chat_id')
        if msg_id and chat_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=msg_id,
                    text=f"🛑 *Game stopped.*\nThe word was *{word}*.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]])
                )
            except Exception: pass
        context.chat_data['active_game_msg_id'] = None
    else:
        await update.message.reply_text("There is no active 20Q game right now.")

# ==========================================
# CALLBACK QUERY HANDLER (THE BRAIN)
# ==========================================

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    
    # Main Menu
    if action == "main_menu":
        await start(update, context)
        
    # Truth or Dare Flow
    elif action == "tod_categories":
        await tod_show_categories(update, context)
    elif action.startswith("tod_cat_"):
        category = action.replace("tod_cat_", "").replace("_", " & ").title()
        # Fix specific naming mismatches from callback to dict keys
        if category == "Classic & Funny": category = "Classic & Funny"
        elif category == "Party & Kids": category = "Party & Kids"
        elif category == "Spicy (18+)": category = "Spicy (18+)"
        await tod_show_type_selection(update, context, category)
    elif action.startswith("tod_type_"):
        # Format: tod_type_truth_Classic & Funny
        parts = action.split("_", 3)
        prompt_type = parts[2]
        category = parts[3].replace("_", " ").title()
        # Fix specific naming mismatches
        if "Classic" in category: category = "Classic & Funny"
        elif "Party" in category: category = "Party & Kids"
        elif "Spicy" in category: category = "Spicy (18+)"
        await tod_show_prompt(update, context, category, prompt_type)
    elif action.startswith("tod_next_"):
        # Format: tod_next_truth_Classic & Funny
        parts = action.split("_", 3)
        prompt_type = parts[2]
        category = parts[3].replace("_", " ").title()
        if "Classic" in category: category = "Classic & Funny"
        elif "Party" in category: category = "Party & Kids"
        elif "Spicy" in category: category = "Spicy (18+)"
        await tod_show_prompt(update, context, category, prompt_type)

    # Other Games
    elif action == "start_20q":
        await handle_20q_start(update, context)
    elif action.startswith("next_"):
        game_type = action.split("next_")[1]
        if game_type == "nhie":
            await show_game_prompt(update, context, NHIE, "🙅‍♂️ Never Have I Ever", "nhie")
        elif game_type == "wyr":
            await show_game_prompt(update, context, WYR, "🤷 Would You Rather", "wyr")
        elif game_type == "cheating":
            await show_game_prompt(update, context, CHEATING, "💔 Is it cheating?", "cheating")

# ==========================================
# 20 QUESTIONS GUESSING LOGIC (UNCHANGED)
# ==========================================

async def handle_20q_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if '20q' not in context.chat_data:
        return
    game = context.chat_data['20q']
    guess = update.message.text.lower().strip()
    msg_id = context.chat_data.get('active_game_msg_id')
    chat_id = context.chat_data.get('active_game_chat_id')
    
    if not msg_id or not chat_id:
        await update.message.reply_text("Game state lost. Please type /20q to restart.")
        return

    if guess == 'hint':
        if game['hints_used'] < len(game['hints']):
            game['guesses'] += 1
            hint = game['hints'][game['hints_used']]
            game['hints_used'] += 1
            remaining = game['max_guesses'] - game['guesses']
            new_text = f"🎮 *20 Questions: Guess the Word!*\n\nCategory: *{game['category']}*\n💡 Hint: {hint}\n({remaining} guesses left)"
            if game['guesses'] >= game['max_guesses']:
                new_text += f"\n\n💀 Out of guesses! The word was *{game['word']}*."
                del context.chat_data['20q']
                context.chat_data['active_game_msg_id'] = None
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 New Word", callback_data="start_20q")]]))
            except Exception: pass
        else:
            await update.message.reply_text("No more hints available!", reply_to_message_id=update.message.message_id)
        return

    game['guesses'] += 1
    remaining = game['max_guesses'] - game['guesses']

    if guess == game['word']:
        new_text = f"🎉 *Correct!* The word was *{game['word']}*.\nYou got it in {game['guesses']} guesses!"
        del context.chat_data['20q']
        context.chat_data['active_game_msg_id'] = None
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        except Exception: pass
    elif remaining <= 0:
        new_text = f"💀 *Game Over!* You ran out of guesses.\nThe word was *{game['word']}*."
        del context.chat_data['20q']
        context.chat_data['active_game_msg_id'] = None
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        except Exception: pass
    else:
        new_text = f"🎮 *20 Questions: Guess the Word!*\n\nCategory: *{game['category']}*\n❌ Incorrect. ({remaining} guesses left)."
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 New Word", callback_data="start_20q")]]))
        except Exception: pass

# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    load_dotenv()
    TOKEN = os.getenv('BOT_TOKEN')
    if not TOKEN:
        print("❌ Error: BOT_TOKEN not found in your .env file!")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("tod", tod_show_categories))
    application.add_handler(CommandHandler("20q", handle_20q_start))
    application.add_handler(CommandHandler("stop20q", stop_20q))

    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_20q_guess), group=1)

    print("✅ Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()