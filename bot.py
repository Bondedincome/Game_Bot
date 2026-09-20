import os
import random
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, InlineQueryHandler

# Import game data
from game_data import TRUTH_OR_DARE_DATA, WYR, TWENTY_Q_WORDS

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# UNIVERSAL MESSAGE HELPERS
# ==========================================

async def send_new_game_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup):
    """Sends a NEW message (for DM command mode) and tracks it for future edits."""
    message = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    context.chat_data['active_chat_id'] = chat_id
    context.chat_data['active_msg_id'] = message.message_id
    context.chat_data.pop('active_inline_msg_id', None)

async def edit_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: InlineKeyboardMarkup):
    """Edits an EXISTING message, handling both Inline Mode and DM Mode seamlessly."""
    query = update.callback_query
    
    # Determine target: Inline ID first, otherwise fall back to tracked DM IDs
    inline_msg_id = query.inline_message_id if query else None
    chat_id = query.message.chat.id if (query and query.message) else context.chat_data.get('active_chat_id')
    msg_id = query.message.message_id if (query and query.message) else context.chat_data.get('active_msg_id')
    
    try:
        if inline_msg_id:
            await context.bot.edit_message_text(
                inline_message_id=inline_msg_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        elif chat_id and msg_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    except Exception as e:
        logging.error(f"Error editing message: {e}")

# ==========================================
# INLINE MODE: THE "GAME CARD" DROP
# ==========================================

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates the menu that pops up when you type @BotName"""
    results = [
        InlineQueryResultArticle(
            id="tod", title="🎭 Truth or Dare",
            description="Start a multiplayer Truth or Dare game",
            input_message_content=InputTextMessageContent("🎭 *Truth or Dare*\n\nTap below to choose a!", parse_mode='Markdown'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📂 Choose Category", callback_data="tod_categories")]])
        ),
        InlineQueryResultArticle(
            id="wyr", title="🤷 Would You Rather",
            description="Start a secret voting game",
            input_message_content=InputTextMessageContent("🤷 *Would You Rather*\n\nTap below to get a scenario!", parse_mode='Markdown'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎲 Get Scenario", callback_data="wyr_start")]])
        ),
        InlineQueryResultArticle(
            id="20q", title="🎮 20 Questions",
            description="Guess the word in 20 tries",
            input_message_content=InputTextMessageContent("🎮 *20 Questions*\n\nTap below to start!", parse_mode='Markdown'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🃏 Start Game", callback_data="start_20q")]])
        )
    ]
    await update.inline_query.answer(results, cache_time=0)

# ==========================================
# TRUTH OR DARE FLOW
# ==========================================

async def tod_show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    
    context.chat_data.pop('tod_category', None)
    
    keyboard = [
        [InlineKeyboardButton("😂 Classic & Funny", callback_data="tod_cat_Classic & Funny")],
        [InlineKeyboardButton("👯 Friends", callback_data="tod_cat_Friends")],
        [InlineKeyboardButton("❤️ Couples", callback_data="tod_cat_Couples")],
        [InlineKeyboardButton("🎈 Party & Kids", callback_data="tod_cat_Party & Kids")],
        [InlineKeyboardButton("🔞 Spicy (18+)", callback_data="tod_cat_Spicy (18+)")]
    ]
    text = "🎭 *Truth or Dare*\n\nSelect a category to begin:"
    markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await edit_game_message(update, context, text, markup)
    else:
        await send_new_game_message(context, update.effective_chat.id, text, markup)

async def tod_show_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    if update.callback_query:
        await update.callback_query.answer()
    context.chat_data['tod_category'] = category
    
    keyboard = [
        [InlineKeyboardButton("🤔 Truth", callback_data=f"tod_type_truth_{category}"), 
         InlineKeyboardButton("😈 Dare", callback_data=f"tod_type_dare_{category}")],
        [InlineKeyboardButton("🔙 Change Category", callback_data="tod_categories")]
    ]
    text = f"🎭 *Truth or Dare*\n\nCategory: *{category}*\n\nNow, choose your poison:"
    await edit_game_message(update, context, text, InlineKeyboardMarkup(keyboard))

async def tod_show_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, prompt_type: str):
    if update.callback_query:
        await update.callback_query.answer()
    context.chat_data['tod_category'] = category
    context.chat_data['tod_type'] = prompt_type
    
    prompt_list = TRUTH_OR_DARE_DATA[category][prompt_type]
    prompt = random.choice(prompt_list)
    emoji = "🤔" if prompt_type == "truth" else "😈"
    
    keyboard = [
        [InlineKeyboardButton(f"🔄 Next {prompt_type.capitalize()}", callback_data=f"tod_next_{prompt_type}_{category}")],
        [InlineKeyboardButton("🔙 Change Category", callback_data="tod_categories")]
    ]
    text = f"{emoji} *{category} - {prompt_type.capitalize()}*\n\n{prompt}"
    await edit_game_message(update, context, text, InlineKeyboardMarkup(keyboard))

# ==========================================
# SECRET VOTING MAGIC (WYR)
# ==========================================

async def wyr_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    
    prompt = random.choice(WYR)
    
    # Store target info for the final reveal
    query = update.callback_query
    inline_msg_id = query.inline_message_id if query else None
    chat_id = query.message.chat.id if (query and query.message) else context.chat_data.get('active_chat_id')
    msg_id = query.message.message_id if (query and query.message) else context.chat_data.get('active_msg_id')

    context.chat_data['active_vote'] = {
        'chat_id': chat_id,
        'msg_id': msg_id,
        'inline_msg_id': inline_msg_id,
        'prompt': prompt,
        'votes': {} 
    }
    
    text = f"🤷 *Would You Rather*\n\n{prompt}"
    keyboard = [[InlineKeyboardButton("🤫 Vote Secretly", callback_data="vote_secret_wyr")]]
    
    if query:
        await edit_game_message(update, context, text, InlineKeyboardMarkup(keyboard))
    else:
        await send_new_game_message(context, update.effective_chat.id, text, InlineKeyboardMarkup(keyboard))

async def vote_secret_wyr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    vote_data = context.chat_data.get('active_vote', {})
    prompt = vote_data.get('prompt', 'this scenario')
    
    private_text = f"🤫 *Secret Vote*\n\nScenario: {prompt}\n\nTap your choice below:"
    keyboard = [
        [InlineKeyboardButton("Option A", callback_data="vote_wyr_A")],
        [InlineKeyboardButton("Option B", callback_data="vote_wyr_B")]
    ]
    
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=private_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await query.answer("Check your private chat with me to vote! 🤫", show_alert=True)

async def process_wyr_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, choice: str):
    query = update.callback_query
    await query.answer()
    
    vote_data = context.chat_data.get('active_vote', {})
    user_id = str(query.from_user.id)
    vote_data['votes'][user_id] = choice
    
    # Confirm in private DM
    try:
        await context.bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=query.message.message_id,
            text="✅ *Vote Recorded!*\n\nWaiting for your partner to vote...",
            parse_mode='Markdown'
        )
    except Exception: pass
    
    # If 2 votes are in, reveal in the main chat/card
    if len(vote_data['votes']) >= 2:
        votes = vote_data['votes']
        player1 = list(votes.keys())[0]
        player2 = list(votes.keys())[1]
        
        p1_name = f"[User {player1[-4:]}]"
        p2_name = f"[User {player2[-4:]}]"
        
        result_text = (
            f"🤷 *Would You Rather*\n\n"
            f"{vote_data['prompt']}\n\n"
            f"🎉 *Results:*\n"
            f"👤 {p1_name} chose: *{votes[player1]}*\n"
            f"👤 {p2_name} chose: *{votes[player2]}*\n\n"
            f"Tap below to play again!"
        )
        
        keyboard = [[InlineKeyboardButton("🎲 New Scenario", callback_data="wyr_start")]]
        
        try:
            if vote_data.get('inline_msg_id'):
                await context.bot.edit_message_text(
                    inline_message_id=vote_data['inline_msg_id'],
                    text=result_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)
                )
            elif vote_data.get('chat_id') and vote_data.get('msg_id'):
                await context.bot.edit_message_text(
                    chat_id=vote_data['chat_id'], message_id=vote_data['msg_id'],
                    text=result_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            logging.error(f"Error editing vote result: {e}")
            
        context.chat_data.pop('active_vote', None)

# ==========================================
# 20 QUESTIONS
# ==========================================

async def start_20q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        
    game_data = random.choice(TWENTY_Q_WORDS)
    context.chat_data['20q'] = {
        'word': game_data['word'], 'category': game_data['category'], 'hints': game_data['hints'],
        'guesses': 0, 'max_guesses': 20, 'hints_used': 0
    }
    
    text = (f"🎮 *20 Questions: Guess the Word!*\n\n"
            f"Category: *{game_data['category']}*\n"
            f"You have 20 guesses. Type your guess below!\n(Type 'hint' to use one, but it costs a guess!)")
    keyboard = [[InlineKeyboardButton("🔄 New Word", callback_data="start_20q")]]
    markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await edit_game_message(update, context, text, markup)
    else:
        await send_new_game_message(context, update.effective_chat.id, text, markup)

async def handle_20q_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if '20q' not in context.chat_data:
        return

    game = context.chat_data['20q']
    guess = update.message.text.lower().strip()
    
    inline_msg_id = context.chat_data.get('active_inline_msg_id')
    chat_id = context.chat_data.get('active_chat_id')
    msg_id = context.chat_data.get('active_msg_id')
    
    async def edit_it(text, markup):
        try:
            if inline_msg_id:
                await context.bot.edit_message_text(inline_message_id=inline_msg_id, text=text, parse_mode='Markdown', reply_markup=markup)
            elif chat_id and msg_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode='Markdown', reply_markup=markup)
        except Exception:
            pass

    if guess == 'hint':
        if game['hints_used'] < len(game['hints']):
            game['guesses'] += 1
            hint = game['hints'][game['hints_used']]
            game['hints_used'] += 1
            remaining = game['max_guesses'] - game['guesses']
            
            new_text = f"🎮 *20 Questions*\n\nCategory: *{game['category']}*\n💡 Hint: {hint}\n({remaining} guesses left)"
            if game['guesses'] >= game['max_guesses']:
                new_text += f"\n\n💀 Out of guesses! The word was *{game['word']}*."
                del context.chat_data['20q']
            
            await edit_it(new_text, InlineKeyboardMarkup([[InlineKeyboardButton("🔄 New Word", callback_data="start_20q")]]))
        return

    game['guesses'] += 1
    remaining = game['max_guesses'] - game['guesses']

    if guess == game['word']:
        new_text = f"🎉 *Correct!* The word was *{game['word']}*.\nYou got it in {game['guesses']} guesses!"
        del context.chat_data['20q']
        await edit_it(new_text, InlineKeyboardMarkup([[InlineKeyboardButton("🔄 New Word", callback_data="start_20q")]]))
    elif remaining <= 0:
        new_text = f"💀 *Game Over!* You ran out of guesses.\nThe word was *{game['word']}*."
        del context.chat_data['20q']
        await edit_it(new_text, InlineKeyboardMarkup([[InlineKeyboardButton("🔄 New Word", callback_data="start_20q")]]))
    else:
        new_text = f"🎮 *20 Questions*\n\nCategory: *{game['category']}*\n❌ Incorrect. ({remaining} guesses left)."
        await edit_it(new_text, InlineKeyboardMarkup([[InlineKeyboardButton("🔄 New Word", callback_data="start_20q")]]))

# ==========================================
# CALLBACK QUERY HANDLER (THE BRAIN)
# ==========================================

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    
    # Truth or Dare Flow
    if action == "tod_categories":
        await tod_show_categories(update, context)
    elif action.startswith("tod_cat_"):
        category = action.replace("tod_cat_", "")
        await tod_show_type_selection(update, context, category)
    elif action.startswith("tod_type_"):
        parts = action.split("_", 3)
        await tod_show_prompt(update, context, parts[3], parts[2])
    elif action.startswith("tod_next_"):
        parts = action.split("_", 3)
        await tod_show_prompt(update, context, parts[3], parts[2])
        
    # Would You Rather Secret Voting
    elif action == "wyr_start":
        await wyr_start(update, context)
    elif action == "vote_secret_wyr":
        await vote_secret_wyr(update, context)
    elif action == "vote_wyr_A":
        await process_wyr_vote(update, context, "Option A")
    elif action == "vote_wyr_B":
        await process_wyr_vote(update, context, "Option B")
        
    # 20 Questions
    elif action == "start_20q":
        await start_20q(update, context)

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

    # 1. Inline Mode Handler
    application.add_handler(InlineQueryHandler(inline_query))
    
    # 2. Command Handlers (For DM play)
    application.add_handler(CommandHandler("start", tod_show_categories)) # Start goes straight to games
    application.add_handler(CommandHandler("tod", tod_show_categories))
    application.add_handler(CommandHandler("wyr", wyr_start))
    application.add_handler(CommandHandler("20q", start_20q))
    
    # 3. Callback Handler (For all inline button clicks)
    application.add_handler(CallbackQueryHandler(button_click))
    
    # 4. Message Handler for 20Q Guesses
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_20q_guess), group=1)

    print("✅ Bot is running! Supports both DM commands (/start) and Inline Mode (@BotName).")
    application.run_polling()

if __name__ == '__main__':
    main()