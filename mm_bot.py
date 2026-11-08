from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import asyncio, random, re, os

TOKEN = os.environ.get("TOKEN", "METS_TON_TOKEN_ICI")

users_db = {}
sessions = {}
MONTANTS = [1, 1.5, 2, 2.5, 5, 10, 20, 50]
TOURS_CHOIX = [3, 6, 9, 12]

def get_session(user_id):
    if user_id not in sessions:
        sessions[user_id] = {"direction": None, "mode": "DEMO", "montant_base": 1, "montant_actuel": 1, "tours_total": 3, "tours_restants": 0, "actif": False, "solde_demo": 10000.0, "solde_reel": 0.0, "gains": 0.0, "en_attente_resultat": False, "etape": "email"}
    return sessions[user_id]

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {"email": None, "code_verif": None, "inscrit": False, "compte_pocket": None}
    return users_db[user_id]

def clavier_principal(s):
    dir_h = "✅ 🟢 HAUSSIER" if s["direction"] == "HAUSSIER" else "🟢 HAUSSIER"
    dir_b = "✅ 🔴 BAISSIER" if s["direction"] == "BAISSIER" else "🔴 BAISSIER"
    demo_txt = "✅ 🧪 DÉMO" if s["mode"] == "DEMO" else "🧪 DÉMO"
    reel_txt = "✅ 💸 RÉEL" if s["mode"] == "REEL" else "💸 RÉEL"
    clavier = [
        [InlineKeyboardButton(dir_h, callback_data="dir_HAUSSIER"), InlineKeyboardButton(dir_b, callback_data="dir_BAISSIER")],
        [InlineKeyboardButton(demo_txt, callback_data="mode_DEMO"), InlineKeyboardButton(reel_txt, callback_data="mode_REEL")],
        [InlineKeyboardButton(f"💰 Montant: {s['montant_base']}$", callback_data="choix_montant")],
        [InlineKeyboardButton(f"🔁 Tours: {s['tours_total']}", callback_data="choix_tours")],
    ]
    if not s["actif"]:
        clavier.append([InlineKeyboardButton("▶️ START", callback_data="start")])
    else:
        clavier.append([InlineKeyboardButton("⏹️ STOP", callback_data="stop")])
        if s["mode"] == "DEMO":
            clavier.append([InlineKeyboardButton("🎲 TRADE SUIVANT (5s)", callback_data="trade")])
        else:
            if not s["en_attente_resultat"]:
                clavier.append([InlineKeyboardButton(f"📤 SIGNAL {s['direction']} {s['montant_actuel']}$", callback_data="signal_reel")])
            else:
                clavier.append([InlineKeyboardButton("✅ J'AI GAGNÉ", callback_data="reel_gagne"), InlineKeyboardButton("❌ J'AI PERDU", callback_data="reel_perdu")])
    solde = s["solde_demo"] if s["mode"] == "DEMO" else s["solde_reel"]
    label = "DÉMO" if s["mode"] == "DEMO" else "RÉEL"
    clavier.append([InlineKeyboardButton(f"💼 Solde {label}: {solde:.2f}$ | Gains: {s['gains']:.2f}$", callback_data="solde")])
    return InlineKeyboardMarkup(clavier)

def texte_principal(s, u):
    mode_txt = "🧪 DÉMO - Simulation" if s["mode"] == "DEMO" else "💸 RÉEL - Tu places toi-même"
    return f"🔥 **MM - MINI BOT** 🔥\n\n👤 Compte: {u['email']}\n💳 Pocket: {u['compte_pocket']}\nMode: {mode_txt}\nDirection: {s['direction'] or '❓ Choisis en haut'}\nMontant base: {s['montant_base']}$ | Actuel: {s['montant_actuel']}$\nTours: {s['tours_restants']}/{s['tours_total']} | Actif: {'🟢 OUI' if s['actif'] else '🔴 NON'}\n\nPERDU => x2 | GAGNÉ => retour base"

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = get_user(uid)
    s = get_session(uid)
    if u["inscrit"]:
        await update.message.reply_text(texte_principal(s, u), reply_markup=clavier_principal(s), parse_mode="Markdown")
    else:
        s["etape"] = "email"
        await update.message.reply_text("🔥 **Bienvenue sur MM - Comme LionX** 🔥\n\nPour créer ton compte, envoie ton **Email** :\nExemple : `tonemail@gmail.com`", parse_mode="Markdown")

async def message_texte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = get_user(uid)
    s = get_session(uid)
    texte = update.message.text.strip()
    if u["inscrit"]:
        return
    if s["etape"] == "email":
        if not re.match(r"[^@]+@[^@]+\.[^@]+", texte):
            await update.message.reply_text("❌ Email invalide. Réessaie : `exemple@gmail.com`", parse_mode="Markdown")
            return
        u["email"] = texte
        code = str(random.randint(100000, 999999))
        u["code_verif"] = code
        s["etape"] = "code"
        await update.message.reply_text(f"📧 **Code envoyé à {texte}**\n\n⚠️ *VERSION TEST : Ton code est :* `{code}`\n\nTape maintenant ton **code à 6 chiffres** :", parse_mode="Markdown")
        return
    if s["etape"] == "code":
        if texte == u["code_verif"]:
            u["inscrit"] = True
            u["compte_pocket"] = f"Pocket-{u['email'].split('@')[0]}-{random.randint(1000,9999)}"
            s["etape"] = "menu"
            await update.message.reply_text(f"✅ **Compte créé !**\n\n👤 Email : {u['email']}\n💳 Compte MM : {u['compte_pocket']}", parse_mode="Markdown")
            await update.message.reply_text(texte_principal(s, u), reply_markup=clavier_principal(s), parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Mauvais code. Ton code est `{u['code_verif']}` (version test). Réessaie :")
        return

async def bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = get_user(uid)
    s = get_session(uid)
    if not u["inscrit"]:
        await q.answer("❌ Inscris-toi d'abord avec /start", show_alert=True)
        return
    data = q.data
    if data.startswith("dir_"):
        if s["actif"]:
            await q.answer("⚠️ Verrouillé ! STOP d'abord.", show_alert=True); return
        s["direction"] = data.split("_")[1]
    elif data.startswith("mode_"):
        if s["actif"]:
            await q.answer("⚠️ STOP d'abord pour changer de mode.", show_alert=True); return
        s["mode"] = data.split("_")[1]
        s["montant_actuel"] = s["montant_base"]; s["gains"] = 0.0
        if s["mode"] == "REEL":
            await q.answer("⚠️ MODE RÉEL : Tu places toi-même sur Pocket Option.", show_alert=True)
    elif data == "choix_montant":
        boutons = [[InlineKeyboardButton(f"{m}$", callback_data=f"mont_{m}")] for m in MONTANTS]
        boutons.append([InlineKeyboardButton("⬅️ Retour", callback_data="retour")])
        await q.edit_message_text("Choisis montant :", reply_markup=InlineKeyboardMarkup(boutons)); return
    elif data.startswith("mont_"):
        if s["actif"]: return
        s["montant_base"] = float(data.split("_")[1]); s["montant_actuel"] = s["montant_base"]
    elif data == "choix_tours":
        boutons = [[InlineKeyboardButton(f"{t} tours", callback_data=f"tours_{t}")] for t in TOURS_CHOIX]
        boutons.append([InlineKeyboardButton("⬅️ Retour", callback_data="retour")])
        await q.edit_message_text("Choisis tours :", reply_markup=InlineKeyboardMarkup(boutons)); return
    elif data.startswith("tours_"):
        s["tours_total"] = int(data.split("_")[1])
    elif data == "start":
        if not s["direction"]:
            await q.answer("❌ Choisis HAUSSIER ou BAISSIER !", show_alert=True); return
        s["actif"] = True; s["tours_restants"] = s["tours_total"]; s["montant_actuel"] = s["montant_base"]; s["en_attente_resultat"] = False
        await q.answer(f"🚀 Session {s['mode']} lancée !", show_alert=True)
    elif data == "stop":
        s["actif"] = False; s["tours_restants"] = 0; s["montant_actuel"] = s["montant_base"]; s["en_attente_resultat"] = False
        await q.answer("⏹️ STOP", show_alert=True)
    elif data == "trade":
        if s["mode"] != "DEMO" or not s["actif"]: return
        await q.edit_message_text(f"⏳ Trade DÉMO... {s['direction']} {s['montant_actuel']}$ - 5s...")
        await asyncio.sleep(5)
        gagne = random.choice([True, False]); montant = s["montant_actuel"]
        if gagne:
            profit = montant * 0.92; s["solde_demo"] += profit; s["gains"] += profit
            resultat = f"✅ GAGNÉ +{profit:.2f}$\nRetour base: {s['montant_base']}$"; s["montant_actuel"] = s["montant_base"]
        else:
            s["solde_demo"] -= montant; s["gains"] -= montant; s["montant_actuel"] = montant * 2
            resultat = f"❌ PERDU -{montant:.2f}$\nMartingale x2 => Prochain: {s['montant_actuel']}$"
        s["tours_restants"] -= 1
        if s["tours_restants"] == 0: s["actif"] = False; resultat += "\n\n🏁 Session terminée !"
        await q.edit_message_text(f"🔥 Résultat DÉMO\n\n{resultat}\n\nTours: {s['tours_restants']}/{s['tours_total']}\nSolde DÉMO: {s['solde_demo']:.2f}$", reply_markup=clavier_principal(s)); return
    elif data == "signal_reel":
        if not s["actif"]: return
        s["en_attente_resultat"] = True
        await q.edit_message_text(f"📤 **SIGNAL RÉEL**\n\nVa sur Pocket Option :\nDirection: **{s['direction']}**\nMontant: **{s['montant_actuel']}$**\nDurée: **5s**\n\nPlace-le, puis clique ✅ ou ❌.", reply_markup=clavier_principal(s), parse_mode="Markdown"); return
    elif data in ["reel_gagne", "reel_perdu"]:
        if not s["en_attente_resultat"]: return
        montant = s["montant_actuel"]
        if data == "reel_gagne":
            profit = montant * 0.92; s["solde_reel"] += profit; s["gains"] += profit
            resultat = f"✅ GAGNÉ RÉEL +{profit:.2f}$"; s["montant_actuel"] = s["montant_base"]
        else:
            s["solde_reel"] -= montant; s["gains"] -= montant; s["montant_actuel"] = montant * 2
            resultat = f"❌ PERDU RÉEL -{montant:.2f}$\nProchain: {s['montant_actuel']}$"
        s["tours_restants"] -= 1; s["en_attente_resultat"] = False
        if s["tours_restants"] == 0: s["actif"] = False; resultat += "\n\n🏁 Session RÉELLE terminée !"
        await q.edit_message_text(f"🔥 Résultat RÉEL\n\n{resultat}\n\nTours: {s['tours_restants']}/{s['tours_total']}", reply_markup=clavier_principal(s)); return
    try:
        await q.edit_message_text(texte_principal(s, u), reply_markup=clavier_principal(s), parse_mode="Markdown")
    except: pass

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(bouton))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_texte))
    print("MM Bot V3 lancé...")
    app.run_polling()
