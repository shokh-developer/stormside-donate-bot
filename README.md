# ⛏ Stromeside Donation Bot

A production-ready Telegram donation bot for the **Stromeside** Minecraft server.
Sell ranks and coin packages, accept payments via Click/Payme QR codes, and
automatically deliver rewards via RCON + LuckPerms after admin approval.

---

## 📁 Project Structure

```
stromeside_bot/
├── main.py                  # Entry point
├── config.py                # Config loader (.env)
├── requirements.txt
├── .env.example             # Copy → .env and fill in
├── stromeside-bot.service   # systemd unit for production
│
├── db/
│   ├── database.py          # Schema + init
│   └── repository.py        # All DB queries
│
├── handlers/
│   ├── start.py             # /start, profile, nickname binding
│   ├── shop.py              # Product browsing
│   ├── payment.py           # QR display, screenshot capture
│   └── admin.py             # Admin panel (approve/reject)
│
├── services/
│   ├── rcon_service.py      # Async RCON client
│   └── order_service.py     # Approval/rejection business logic
│
├── keyboards/
│   └── keyboards.py         # All inline keyboards
│
├── middlewares/
│   ├── user_middleware.py   # Auto-register users
│   └── admin.py             # @admin_required decorator
│
├── utils/
│   ├── helpers.py           # Formatting, validation, text templates
│   └── logger.py            # Rotating log setup
│
├── assets/
│   ├── click_qr.png         # Your Click payment QR code
│   └── payme_qr.png         # Your Payme payment QR code
│
└── data/
    └── stromeside.db        # SQLite database (auto-created)
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/youruser/stromeside-bot.git
cd stromeside-bot

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
nano .env
```

Fill in:
- `BOT_TOKEN` — get from [@BotFather](https://t.me/BotFather)
- `ADMIN_IDS` — your Telegram user IDs (comma-separated)
- `RCON_HOST`, `RCON_PORT`, `RCON_PASSWORD` — from your `server.properties`
- Payment card numbers and QR code paths
- `ADMIN_CHAT_ID` — Telegram group/channel for order notifications

### 3. Enable RCON on your Minecraft server

In `server.properties`:
```properties
enable-rcon=true
rcon.port=25575
rcon.password=your_secure_password
```

Restart your server after changes.

### 4. Add QR Codes

Place your payment QR images in the `assets/` folder:
- `assets/click_qr.png`
- `assets/payme_qr.png`

### 5. Run

```bash
python main.py
```

---

## 🛠 Production Deployment (systemd)

```bash
# Copy project to server
sudo cp -r . /opt/stromeside_bot
sudo cp stromeside-bot.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable stromeside-bot
sudo systemctl start stromeside-bot

# View logs
sudo journalctl -u stromeside-bot -f
```

---

## 🎮 Bot Commands

| Command  | Description              | Who   |
|----------|--------------------------|-------|
| `/start` | Main menu                | All   |
| `/admin` | Open admin panel         | Admin |

---

## 💡 User Flow

```
/start
  └── 🛒 Shop
        ├── ⚔️ Ranks  →  Select Rank  →  Choose Payment Method
        │                               └── QR Code + Card Info
        │                                     └── 📸 Send Screenshot
        │                                           └── ⏳ Pending (admin review)
        └── 🪙 Coins  →  (same flow)

👤 Profile  →  Link Minecraft Nickname  /  View Orders
```

---

## 🔐 Admin Flow

```
/admin
  └── 📋 Pending Orders
        └── Select Order  →  View Screenshot + Details
              ├── ✅ Approve  →  RCON command executed  →  User notified
              └── ❌ Reject   →  Choose reason  →  User notified
```

---

## 📦 Database Tables

| Table         | Purpose                                      |
|---------------|----------------------------------------------|
| `users`       | Telegram users with Minecraft nickname       |
| `products`    | Ranks and coin packages                      |
| `orders`      | All orders with status tracking              |
| `payments`    | Payment records linked to orders             |
| `admin_logs`  | Full audit trail of admin actions            |

---

## ⚡ LuckPerms Commands Used

```bash
# Give a rank
lp user {nickname} parent add {lp_group}

# Examples:
lp user CoolPlayer_99 parent add vip
lp user CoolPlayer_99 parent add mvp
lp user CoolPlayer_99 parent add legend
lp user CoolPlayer_99 parent add titan
```

---

## 🪙 Adding Custom Products

Edit `db/database.py` in the SCHEMA section, or insert directly:

```sql
INSERT INTO products (name, category, description, price, lp_group, emoji)
VALUES ('GODLIKE', 'rank', 'Ultimate rank with all perks', 499900, 'godlike', '⭐');

INSERT INTO products (name, category, description, price, coins_amount, emoji)
VALUES ('10000 Coins', 'coins', 'Mega coin bundle', 129900, 10000, '💰');
```

---

## 🔒 Security Features

- ✅ Admin-only handlers protected with `@admin_required`
- ✅ Minecraft nickname validation (3-16 chars, `[a-zA-Z0-9_]`)
- ✅ Duplicate pending order prevention
- ✅ All admin actions logged to `admin_logs` table
- ✅ Orders can only be modified by users who created them
- ✅ RCON credentials stored in `.env` only

---

## 🐛 Troubleshooting

| Problem                  | Solution                                          |
|--------------------------|---------------------------------------------------|
| Bot not responding       | Check `BOT_TOKEN` in `.env`                      |
| RCON connection refused  | Ensure `enable-rcon=true` and correct port/pass  |
| QR image not showing     | Verify `CLICK_QR_PATH` / `PAYME_QR_PATH` paths   |
| Admin not getting alerts | Check `ADMIN_IDS` and `ADMIN_CHAT_ID` in `.env`  |
| SQLite locked error      | Only run one bot instance at a time               |

---

## 📜 License

MIT — free to use and modify for your server.
