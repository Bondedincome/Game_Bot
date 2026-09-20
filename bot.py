import os
import random
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, InlineQueryHandler, ChosenInlineResultHandler

# Import game data
from game_data import TRUTH_OR_DARE_DATA, NHIE, WYR, CHEATING, TWENTY_Q_WORDS

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# INLINE MODE: THE "GAME CARD" DROP
# ==========================================

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates the menu that pops up when you type @BotName"""
    query = update.inline_query.query
    
    results = [
        InlineQueryResultArticle(
            id="tod", title="🎭 Truth or Dare",
            description="Start a multiplayer Truth or Dare game",
            input_message_content=InputTextMessageContent("🎭 *Truth or Dare*\n\nTap below to choose a category!", parse_mode='Markdown'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📂 Choose Category", callback_data="tod_categories")]])
        ),
        InlineQueryResultArticle(
            id="wyr", title="🤷 Would You Rather",
            description="Start a secret voting game",
            input_message_content=InputTextMessageContent("🤷 *Would You Rather*\n\nTap below to get a scenario!", parse_mode='Markdown'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎲 Get Scenario", callback_data="wyr_start")]])
        ),
        InlineQueryResultArticle(
            id="nhie", title="🙅‍♂️ Never Have I Ever",
            description="Start a secret voting NHIE game",
            input_message_content=InputTextMessageContent("🙅‍♂️ *Never Have I Ever*\n\nTap below to get a prompt!", parse_mode='Markdown'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎲 Get Prompt", callback_data="nhie_start")]])
        ),
        InlineQueryResultArticle(
            id="20q", title="🎮 20 Questions",
            description="Guess the word in 20 tries",
            input_message_content=InputTextMessageContent("🎮 *20 Questions*\n\nTap below to start!", parse_mode='Markdown'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🃏 Start Game", callback_data="start_20q_inline")]])
        )
    ]
    
    await update.inline_query.answer(results, cache_time=0)

async def chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tracks the message ID of the dropped game card so we can edit it later."""
    # We store the chat_id and message_id globally for this chat session
    # so buttons can edit this specific message.
    context.chat_data['inline_game_msg_id'] = update.chosen_inline_result.message_id
    # Note: chat_id is sometimes restricted in inline queries, so we rely on query.message.chat.id in callbacks

# ==========================================
# TRUTH OR DARE FLOW (IN-PLACE EDITING)
# ==========================================

async def tod_edit_message(context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: InlineKeyboardMarkup):
    """Helper to edit the inline game card in place."""
    msg_id = context.chat_data.get('inline_game_msg_id')
    # We need chat_id. If it's an inline message, we can get it from the last known context or we pass it.
    # For safety, we'll fetch it from the active callback if available, otherwise default.
    chat_id = context.chat_data.get('inline_game_chat_id')
    
    if msg_id and chat_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=text, parse_mode='Markdown', reply_markup=reply_markup
            )
        except Exception:
            pass

async def tod_show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    msg_id = query.message.message_id
    context.chat_data['inline_game_chat_id'] = chat_id
    context.chat_data['inline_game_msg_id'] = msg_id
    context.chat_data.pop('tod_category', None)
    
    keyboard = [
        [InlineKeyboardButton("😂 Classic & Funny", callback_data="tod_cat_Classic & Funny")],
        [InlineKeyboardButton("👯 Friends", callback_data="tod_cat_Friends")],
        [InlineKeyboardButton("❤️ Couples", callback_data="tod_cat_Couples")],
        [InlineKeyboardButton("🎈 Party & Kids", callback_data="tod_cat_Party & Kids")],
        [InlineKeyboardButton("🔞 Spicy (18+)", callback_data="tod_cat_Spicy (18+)")]
    ]
    
    text = "🎭 *Truth or Dare*\n\nSelect a category to begin:"
    await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tod_show_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    query = update.callback_query
    await query.answer()
    context.chat_data['tod_category'] = category
    
    keyboard = [
        [InlineKeyboardButton("🤔 Truth", callback_data=f"tod_type_truth_{category}"), 
         InlineKeyboardButton("😈 Dare", callback_data=f"tod_type_dare_{category}")],
        [InlineKeyboardButton("🔙 Change Category", callback_data="tod_categories")]
    ]
    
    text = f"🎭 *Truth or Dare*\n\nCategory: *{category}*\n\nNow, choose your poison:"
    await context.bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id, text=text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tod_show_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, prompt_type: str):
    query = update.callback_query
    await query.answer()
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
    await context.bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id, text=text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ==========================================
# SECRET VOTING MAGIC (WYR / NHIE)
# ==========================================

async def wyr_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    prompt = random.choice(WYR)
    # Store the scenario so the private DM vote knows what it's voting on
    context.chat_data['active_vote'] = {
        'chat_id': query.message.chat.id,
        'msg_id': query.message.message_id,
        'prompt': prompt,
        'votes': {} # Dictionary to store user_id: choice
    }
    
    text = f"🤷 *Would You Rather*\n\n{prompt}"
    keyboard = [[InlineKeyboardButton("🤫 Vote Secretly", callback_data="vote_secret_wyr")]]
    
    await context.bot.edit_message_text(
        chat_id=query.message.chat.id, message_id=query.message.message_id,
        text=text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def vote_secret_wyr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    vote_data = context.chat_data.get('active_vote', {})
    prompt = vote_data.get('prompt', 'this scenario')
    
    # Send a PRIVATE message to the user with the actual voting buttons
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
    
    # Record the vote
    vote_data['votes'][user_id] = choice
    
    # Edit the private message to confirm
    await context.bot.edit_message_text(
        chat_id=query.from_user.id,
        message_id=query.message.message_id,
        text="✅ *Vote Recorded!*\n\nWaiting for your partner to vote...",
        parse_mode='Markdown'
    )
    
    # Check if both players have voted (assuming 2 players)
    if len(vote_data['votes']) >= 2:
        votes = vote_data['votes']
        player1 = list(votes.keys())[0]
        player2 = list(votes.keys())[1]
        
        # Mention them nicely if possible, otherwise just say "Player 1 / Player 2"
        p1_name = f"[User {player1[-4:]}]" # Last 4 chars of ID for privacy
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
        
        # Edit the ORIGINAL inline message in the shared chat
        try:
            await context.bot.edit_message_text(
                chat_id=vote_data['chat_id'],
                message_id=vote_data['msg_id'],
                text=result_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            pass
            
        # Clear the vote data for the next round
        context.chat_data.pop('active_vote', None)

# ==========================================
# 20 QUESTIONS (INLINE VERSION)
# ==========================================

async def start_20q_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    game_data = random.choice(TWENTY_Q_WORDS)
    context.chat_data['20q'] = {
        'word': game_data['word'], 'category': game_data['category'], 'hints': game_data['hints'],
        'guesses': 0, 'max_guesses': 20, 'hints_used': 0
    }
    context.chat_data['inline_game_chat_id'] = query.message.chat.id
    context.chat_data['inline_game_msg_id'] = query.message.message_id
    
    text = (f"🎮 *20 Questions: Guess the Word!*\n\n"
            f"Category: *{game_data['category']}*\n"
            f"You have 20 guesses. Type your guess in this chat!\n(Type 'hint' to use one, but it costs a guess!)")
    keyboard = [[InlineKeyboardButton("🔄 New Word", callback_data="start_20q_inline")]]
    
    await context.bot.edit_message_text(
        chat_id=query.message.chat.id, message_id=query.message.message_id,
        text=text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==========================================
# NORMAL TEXT GUESSING (FOR 20Q)
# ==========================================

async def handle_20q_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if '20q' not in context.chat_data:
        return

    game = context.chat_data['20q']
    guess = update.message.text.lower().strip()
    msg_id = context.chat_data.get('inline_game_msg_id')
    chat_id = context.chat_data.get('inline_game_chat_id')
    
    if not msg_id or not chat_id:
        return # Ignore if not an active inline game

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
            
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 New Word", callback_data="start_20q_inline")]]))
            except Exception: pass
        return

    game['guesses'] += 1
    remaining = game['max_guesses'] - game['guesses']

    if guess == game['word']:
        new_text = f"🎉 *Correct!* The word was *{game['word']}*.\nYou got it in {game['guesses']} guesses!"
        del context.chat_data['20q']
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 New Word", callback_data="start_20q_inline")]]))
        except Exception: pass
    elif remaining <= 0:
        new_text = f"💀 *Game Over!* You ran out of guesses.\nThe word was *{game['word']}*."
        del context.chat_data['20q']
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 New Word", callback_data="start_20q_inline")]]))
        except Exception: pass
    else:
        new_text = f"🎮 *20 Questions*\n\nCategory: *{game['category']}*\n❌ Incorrect. ({remaining} guesses left)."
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 New Word", callback_data="start_20q_inline")]]))
        except Exception: pass

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
        prompt_type = parts[2]
        category = parts[3]
        await tod_show_prompt(update, context, category, prompt_type)
    elif action.startswith("tod_next_"):
        parts = action.split("_", 3)
        prompt_type = parts[2]
        category = parts[3]
        await tod_show_prompt(update, context, category, prompt_type)
        
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
    elif action == "start_20q_inline":
        await start_20q_inline(update, context)

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

    # Inline Mode Handlers
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(ChosenInlineResultHandler(chosen_inline_result))
    
    # Callback Handler (for all inline button clicks)
    application.add_handler(CallbackQueryHandler(button_click))
    
    # Message Handler for 20Q Guesses (only triggers if it's not a command)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_20q_guess), group=1)

    print("✅ Bot is running in Inline Mode! Type @YourBotName in any chat to test.")
    application.run_polling()

if __name__ == '__main__':
    main()