#!/usr/bin/env python3
# BOT PAKET - Telegram Bot untuk Jual Beli Paket
# Versi Lengkap - Nama APK: OTAX.apk

import os
import sqlite3
import json
import logging
import requests
import random
import string
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ==================== KONFIGURASI ====================
BOT_TOKEN = "8715900599:AAFrXWLjFuZH127H1Vpx90F0JlL1O3zyIto"
OWNER_ID = 7293981502
OWNER_URL = "t.me/yanzysaja"
FALLBACK_PHOTO = "yanzy.jpg"

# Paket yang tersedia
PAKET = {
    "member": {"nama": "MEMBER", "harga": 50000},
    "reseller": {"nama": "RESELLER", "harga": 70000},
    "pt": {"nama": "PT", "harga": 90000},
    "tk": {"nama": "TK", "harga": 140000},
    "owner": {"nama": "OWNER", "harga": 190000}
}

# ==================== SETUP ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        status TEXT DEFAULT 'pending',
        paket TEXT,
        password TEXT,
        tanggal_daftar TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        paket TEXT,
        harga INTEGER,
        bukti_path TEXT,
        status TEXT DEFAULT 'pending',
        tanggal TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS temp_paket (
        user_id INTEGER PRIMARY KEY,
        paket TEXT,
        harga INTEGER,
        timestamp REAL
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database terhubung")

def generate_password(length: int = 8) -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def save_user(user_id: int, username: str, full_name: str):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO users (user_id, username, full_name, tanggal_daftar) 
                 VALUES (?, ?, ?, ?)''',
              (user_id, username, full_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_status(user_id: int) -> Dict:
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT status, paket, password FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"status": row[0], "paket": row[1], "password": row[2]}
    return {"status": None, "paket": None, "password": None}

def update_user_status(user_id: int, status: str, paket: str = None, password: str = None):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    if paket and password:
        c.execute('UPDATE users SET status = ?, paket = ?, password = ? WHERE user_id = ?',
                  (status, paket, password, user_id))
    elif paket:
        c.execute('UPDATE users SET status = ?, paket = ? WHERE user_id = ?',
                  (status, paket, user_id))
    else:
        c.execute('UPDATE users SET status = ? WHERE user_id = ?', (status, user_id))
    conn.commit()
    conn.close()

def save_temp_paket(user_id: int, paket_nama: str, paket_harga: int):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO temp_paket (user_id, paket, harga, timestamp) VALUES (?, ?, ?, ?)',
              (user_id, paket_nama, paket_harga, time.time()))
    conn.commit()
    conn.close()

def get_temp_paket(user_id: int) -> Optional[Dict]:
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT paket, harga FROM temp_paket WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"paket": row[0], "harga": row[1]}
    return None

def clear_temp_paket(user_id: int):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('DELETE FROM temp_paket WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def save_transaction(user_id: int, paket: str, harga: int, bukti_path: str) -> int:
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''INSERT INTO transactions (user_id, paket, harga, bukti_path, tanggal) 
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, paket, harga, bukti_path, datetime.now().isoformat()))
    trans_id = c.lastrowid
    conn.commit()
    conn.close()
    return trans_id

def get_transaction_by_id(trans_id: int) -> Optional[Dict]:
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT id, user_id, paket, harga, bukti_path, status, tanggal FROM transactions WHERE id = ?', (trans_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "user_id": row[1], "paket": row[2], "harga": row[3], 
                "bukti_path": row[4], "status": row[5], "tanggal": row[6]}
    return None

def update_transaction_status(trans_id: int, status: str):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE transactions SET status = ? WHERE id = ?', (status, trans_id))
    conn.commit()
    conn.close()

def get_all_user_ids() -> list:
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_stats() -> Dict:
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM transactions')
    total_transactions = c.fetchone()[0]
    
    c.execute('SELECT SUM(harga) FROM transactions WHERE status = "approved"')
    total_revenue = c.fetchone()[0] or 0
    
    conn.close()
    return {"total_users": total_users, "total_transactions": total_transactions, "total_revenue": total_revenue}

def file_exists(filepath: str) -> bool:
    return os.path.exists(filepath)

# ==================== HANDLER USER ====================
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "-"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    
    save_user(user_id, username, full_name)
    
    if user_id == OWNER_ID:
        stats = get_stats()
        msg = f"""👑 SELAMAT DATANG, OWNER! 👑
────────────────
🆔 ID: {user_id}

📊 STATISTIK BOT
────────────────
👤 TOTAL USER : {stats['total_users']}
────────────────
💳 TOTAL TRANSAKSI : {stats['total_transactions']}
────────────────
💰 TOTAL PENDAPATAN : Rp{stats['total_revenue']:,}
────────────────"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 REFRESH", callback_data="owner_stats"),
            InlineKeyboardButton("📢 BROADCAST", callback_data="broadcast_mode")
        ]])
        
        if file_exists(FALLBACK_PHOTO):
            with open(FALLBACK_PHOTO, 'rb') as f:
                await update.message.reply_photo(f, caption=msg, reply_markup=keyboard)
        else:
            await update.message.reply_text(msg, reply_markup=keyboard)
        return
    
    user_status = get_user_status(user_id)
    
    if user_status['status'] == 'active':
        msg = f"""✅ Selamat datang kembali, {full_name}!

👤 Username: @{username}
🆔 ID: `{user_id}`
🏷️ Paket: {user_status['paket']}

Silakan klik tombol di bawah:"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 DATA AKUN + APK", callback_data="data_akun_dan_apk"),
             InlineKeyboardButton("📱 OWNER", url=OWNER_URL),
             InlineKeyboardButton("📋 STATUS", callback_data="cek_status")]
        ])
        
        if file_exists("acctrx.mp4"):
            with open("acctrx.mp4", 'rb') as f:
                await update.message.reply_video(f, caption=msg, reply_markup=keyboard)
        else:
            await update.message.reply_text(msg, reply_markup=keyboard)
    else:
        msg = f"""🎉 Selamat datang, {full_name}! 🎉

👤 Username: @{username}
🆔 ID: `{user_id}`

Silakan pilih menu di bawah:"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 ORDER APK BUG", callback_data="order_apk_bug")],
            [InlineKeyboardButton("📱 OWNER", url=OWNER_URL)]
        ])
        
        if file_exists("menu.mp4"):
            with open("menu.mp4", 'rb') as f:
                await update.message.reply_video(f, caption=msg, reply_markup=keyboard)
        else:
            await update.message.reply_text(msg, reply_markup=keyboard)

async def handle_order_apk_bug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk tombol ORDER APK BUG"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username or "-"
    
    user_status = get_user_status(user_id)
    
    if user_status['status'] == 'active':
        msg = f"""✅ Anda sudah memiliki paket aktif!

👤 @{username}
🏷️ Paket: {user_status['paket']}

Silakan klik tombol di bawah:"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔐 DATA AKUN + APK", callback_data="data_akun_dan_apk")
        ]])
        
        if file_exists("acctrx.mp4"):
            with open("acctrx.mp4", 'rb') as f:
                await query.message.reply_video(f, caption=msg, reply_markup=keyboard)
        else:
            await query.message.reply_text(msg, reply_markup=keyboard)
        return
    
    msg = f"""🔰 DAFTAR HARGA PAKET PERMANEN 🔰

👤 @{username}
🆔 `{user_id}`

Silakan pilih paket di bawah ini:"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 MEMBER - Rp50.000", callback_data="pilih_member")],
        [InlineKeyboardButton("🚀 RESELLER - Rp70.000", callback_data="pilih_reseller")],
        [InlineKeyboardButton("⭐ PT - Rp90.000", callback_data="pilih_pt")],
        [InlineKeyboardButton("👑 TK - Rp140.000", callback_data="pilih_tk")],
        [InlineKeyboardButton("💎 OWNER - Rp190.000", callback_data="pilih_owner")]
    ])
    
    if file_exists("menu_paket.mp4"):
        with open("menu_paket.mp4", 'rb') as f:
            await query.message.reply_video(f, caption=msg, reply_markup=keyboard)
    else:
        await query.message.reply_text(msg, reply_markup=keyboard)

async def handle_pilih_paket(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, paket_kode: str):
    query = update.callback_query
    await query.answer()
    
    user_status = get_user_status(user_id)
    
    if user_status['status'] == 'active':
        await query.answer("❌ Anda sudah memiliki paket aktif!", show_alert=True)
        return
    
    paket = PAKET[paket_kode]
    save_temp_paket(user_id, paket['nama'], paket['harga'])
    
    msg = f"""💳 PEMBAYARAN {paket['nama']}

────────────────────────────────
📱 Paket: {paket['nama']}
💰 Harga: Rp{paket['harga']:,}
🆔 User ID: `{user_id}`
────────────────────────────────

📌 Cara Pembayaran:
1️⃣ Scan QRIS di atas
2️⃣ Lakukan transfer sesuai nominal
3️⃣ Upload bukti transfer disini"""
    
    if file_exists("qris.jpg"):
        with open("qris.jpg", 'rb') as f:
            await query.message.reply_photo(f, caption=msg)
    else:
        await query.message.reply_text("⚠️ QRIS sedang tidak tersedia, hubungi admin.\n\n" + msg)

async def handle_bukti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "-"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    
    save_user(user_id, username, full_name)
    
    temp = get_temp_paket(user_id)
    
    if not temp:
        await update.message.reply_text("❌ Silakan pilih paket terlebih dahulu. Ketik /start dan pilih paket.")
        return
    
    paket_nama = temp['paket']
    paket_harga = temp['harga']
    
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    file = await context.bot.get_file(file_id)
    
    if not os.path.exists('bukti'):
        os.makedirs('bukti')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    bukti_path = f"bukti/{user_id}_{timestamp}.jpg"
    
    await file.download_to_drive(bukti_path)
    
    trans_id = save_transaction(user_id, paket_nama, paket_harga, bukti_path)
    
    await update.message.reply_text(f"""✅ Bukti pembayaran terkirim!
🆔 ID Transaksi: `{trans_id}`

⏳ Menunggu konfirmasi admin...""")
    
    msg = f"""🆕 PERMINTAAN KONFIRMASI PEMBAYARAN

👤 Nama: {full_name}
👤 Username: @{username}
🆔 User ID: `{user_id}`
📱 Paket: {paket_nama}
💰 Harga: Rp{paket_harga:,}
🆔 Transaksi: `{trans_id}`"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ TERIMA", callback_data=f"terima_{trans_id}"),
         InlineKeyboardButton("❌ TOLAK", callback_data=f"tolak_{trans_id}")]
    ])
    
    with open(bukti_path, 'rb') as f:
        await context.bot.send_photo(OWNER_ID, f, caption=msg, reply_markup=keyboard)
    
    clear_temp_paket(user_id)

async def handle_data_akun_dan_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    user_status = get_user_status(user_id)
    
    if user_status['status'] != 'active':
        await query.answer("❌ Anda belum memiliki akses. Silakan beli paket terlebih dahulu!", show_alert=True)
        return
    
    username = query.from_user.username or "-"
    
    msg = f"""🔐 DATA AKUN + APK

👤 Username : @{username}
🔑 Password: `{user_status['password']}`

🏷️ Paket: {user_status['paket']}
🆔 User ID: `{user_id}`

📌 Simpan data akun Anda dengan aman."""
    
    if file_exists("dataakun.mp4"):
        with open("dataakun.mp4", 'rb') as f:
            await query.message.reply_video(f, caption=msg)
    else:
        await query.message.reply_text(msg)
    
    # Kirim APK - NAMA FILE: OTAX.apk
    if file_exists("OTAX.apk"):
        with open("OTAX.apk", 'rb') as f:
            await query.message.reply_document(f, caption="📱 BERIKUT APK ANDA")
    else:
        await query.message.reply_text("❌ File APK sedang tidak tersedia. Silakan hubungi admin.")

async def handle_cek_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    user_status = get_user_status(user_id)
    
    if user_status['status'] == 'active':
        msg = f"""✅ STATUS AKUN

📱 Paket: {user_status['paket']}
🔑 Password: `{user_status['password']}`
🆔 User ID: `{user_id}`

✅ Akun Anda AKTIF
📌 Akses berlaku PERMANEN"""
        await query.message.reply_text(msg)
    else:
        msg = """⏳ STATUS AKUN

Anda belum memiliki paket aktif.

📌 Ketik /start untuk membeli paket."""
        await query.message.reply_text(msg)

# ==================== HANDLER OWNER ====================
async def handle_owner_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    stats = get_stats()
    
    msg = f"""📊 STATISTIK BOT
────────────────
👤 TOTAL USER : {stats['total_users']}
────────────────
💳 TOTAL TRANSAKSI : {stats['total_transactions']}
────────────────
💰 TOTAL PENDAPATAN : Rp{stats['total_revenue']:,}
────────────────"""
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 REFRESH", callback_data="owner_stats"),
        InlineKeyboardButton("📢 BROADCAST", callback_data="broadcast_mode")
    ]])
    
    if file_exists(FALLBACK_PHOTO):
        with open(FALLBACK_PHOTO, 'rb') as f:
            await query.message.reply_photo(f, caption=msg, reply_markup=keyboard)
    else:
        await query.message.reply_text(msg, reply_markup=keyboard)

async def handle_konfirmasi(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_id: int, action: str):
    query = update.callback_query
    await query.answer()
    
    trans = get_transaction_by_id(trans_id)
    
    if not trans:
        await query.answer("❌ Transaksi tidak ditemukan!", show_alert=True)
        return
    
    if action == "terima":
        if trans['status'] == 'approved':
            await query.answer("✅ Transaksi sudah diproses sebelumnya!", show_alert=True)
            return
        
        password_acak = generate_password()
        
        update_transaction_status(trans_id, 'approved')
        update_user_status(trans['user_id'], 'active', trans['paket'], password_acak)
        
        new_caption = f"""✅ PEMBAYARAN TELAH DIVERIFIKASI ✅

📱 Paket: {trans['paket']}
🆔 Transaksi: {trans_id}
👤 User ID: `{trans['user_id']}`

⏰ Diverifikasi pada: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
        
        try:
            await query.edit_message_caption(caption=new_caption)
        except:
            pass
        
        msg = f"""✅ PEMBAYARAN DISETUJUI!

📱 Paket: {trans['paket']}
✅ Akses Anda sudah aktif.

Silakan klik tombol di bawah:"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔐 DATA AKUN + APK", callback_data="data_akun_dan_apk")
        ]])
        
        if file_exists("acctrx.mp4"):
            with open("acctrx.mp4", 'rb') as f:
                await context.bot.send_video(trans['user_id'], f, caption=msg, reply_markup=keyboard)
        else:
            await context.bot.send_message(trans['user_id'], msg, reply_markup=keyboard)
        
        await query.answer("✅ Pembayaran berhasil diverifikasi!")
        
    elif action == "tolak":
        if trans['status'] == 'rejected':
            await query.answer("❌ Transaksi sudah ditolak sebelumnya!", show_alert=True)
            return
        
        update_transaction_status(trans_id, 'rejected')
        
        new_caption = f"""❌ PEMBAYARAN DITOLAK ❌

📱 Paket: {trans['paket']}
🆔 Transaksi: {trans_id}
👤 User ID: `{trans['user_id']}`

⏰ Ditolak pada: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
        
        try:
            await query.edit_message_caption(caption=new_caption)
        except:
            pass
        
        await context.bot.send_message(trans['user_id'], "❌ PEMBAYARAN DITOLAK!\n\nSilakan upload ulang bukti pembayaran yang valid.")
        
        await query.answer("❌ Pembayaran ditolak!")

# ==================== BROADCAST ====================
async def handle_broadcast_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        await query.answer("❌ Hanya untuk owner!", show_alert=True)
        return

    context.user_data['broadcast_mode'] = True

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Batal", callback_data="batal_broadcast")
    ]])

    await query.message.reply_text(
        "📢 MODE BROADCAST AKTIF\n\n"
        "Kirim pesan yang ingin di-broadcast ke semua user.",
        reply_markup=keyboard
    )

async def handle_batal_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    context.user_data.pop('broadcast_mode', None)
    await update.message.reply_text("❌ Broadcast dibatalkan.")

async def handle_batal_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID:
        return
    context.user_data.pop('broadcast_mode', None)
    await query.message.edit_text("❌ Broadcast dibatalkan.")

async def handle_pesan_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        return

    if not context.user_data.get('broadcast_mode'):
        return

    context.user_data.pop('broadcast_mode', None)

    pesan = update.message.text
    semua_user = get_all_user_ids()
    total = len(semua_user)

    if total == 0:
        await update.message.reply_text("❌ Belum ada user yang terdaftar.")
        return

    status_msg = await update.message.reply_text(f"📢 Mengirim broadcast ke {total} user...")

    berhasil = 0
    gagal = 0

    for uid in semua_user:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 PESAN DARI OWNER\n\n{pesan}"
            )
            berhasil += 1
        except Exception:
            gagal += 1

    await status_msg.edit_text(
        f"✅ Broadcast selesai!\n\n"
        f"📨 Total user : {total}\n"
        f"✅ Berhasil   : {berhasil}\n"
        f"❌ Gagal      : {gagal}"
    )

# ==================== MAIN ====================
def main():
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("batal", handle_batal_broadcast))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_order_apk_bug, pattern="^order_apk_bug$"))
    app.add_handler(CallbackQueryHandler(handle_data_akun_dan_apk, pattern="^data_akun_dan_apk$"))
    app.add_handler(CallbackQueryHandler(handle_cek_status, pattern="^cek_status$"))
    app.add_handler(CallbackQueryHandler(handle_owner_stats, pattern="^owner_stats$"))
    app.add_handler(CallbackQueryHandler(handle_broadcast_mode, pattern="^broadcast_mode$"))
    app.add_handler(CallbackQueryHandler(handle_batal_broadcast_callback, pattern="^batal_broadcast$"))

    # Pilih paket handlers
    app.add_handler(CallbackQueryHandler(lambda u, c: handle_pilih_paket(u, c, u.callback_query.from_user.id, "member"), pattern="^pilih_member$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: handle_pilih_paket(u, c, u.callback_query.from_user.id, "reseller"), pattern="^pilih_reseller$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: handle_pilih_paket(u, c, u.callback_query.from_user.id, "pt"), pattern="^pilih_pt$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: handle_pilih_paket(u, c, u.callback_query.from_user.id, "tk"), pattern="^pilih_tk$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: handle_pilih_paket(u, c, u.callback_query.from_user.id, "owner"), pattern="^pilih_owner$"))

    # Konfirmasi handlers
    app.add_handler(CallbackQueryHandler(lambda u, c: handle_konfirmasi(u, c, int(u.callback_query.data.split("_")[1]), "terima"), pattern="^terima_"))
    app.add_handler(CallbackQueryHandler(lambda u, c: handle_konfirmasi(u, c, int(u.callback_query.data.split("_")[1]), "tolak"), pattern="^tolak_"))

    # Message handlers — broadcast harus di atas foto bukti
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pesan_broadcast))
    app.add_handler(MessageHandler(filters.PHOTO, handle_bukti))
    
    print("✅ BOT PAKET AKTIF!")
    print(f"Bot token: {BOT_TOKEN[:10]}...")
    print(f"Owner ID: {OWNER_ID}")
    print("Tekan Ctrl+C untuk berhenti.")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()