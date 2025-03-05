const { Bot, session } = require("grammy");
const dotenv = require("dotenv");
const sqlite3 = require("sqlite3");
const yahooFinance = require("yahoo-finance2").default;

// Load environment variables
dotenv.config({ path: ".env.local" });

// Constants
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const DB_PATH = "./db/stockalerts.db";

// Initialize bot
const bot = new Bot(BOT_TOKEN);

// Database connection and initialization
const db = new sqlite3.Database(DB_PATH, (err) => {
    if (err) {
        console.error("\x1b[31m%s\x1b[0m", "Error connecting to database:", err);
        process.exit(1);
    }
    console.log("\x1b[32m%s\x1b[0m", "Connected to SQLite database");

    // Create tables with the same schema as Python code
    db.serialize(() => {
        db.run(`
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_notified TIMESTAMP
            )
        `);

        db.run(`
            CREATE TABLE IF NOT EXISTS watchlist_items (
                user_id TEXT,
                symbol TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                alert_threshold_low REAL DEFAULT 5.0,
                alert_threshold_high REAL DEFAULT 95.0,
                last_alerted_at TIMESTAMP,
                PRIMARY KEY (user_id, symbol),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        `);

        db.run(`
            CREATE TABLE IF NOT EXISTS stock_cache (
                symbol TEXT PRIMARY KEY,
                last_check TIMESTAMP NOT NULL,
                ma_200 REAL,
                last_price REAL,
                data_json TEXT,
                CONSTRAINT valid_price CHECK (last_price > 0)
            )
        `);

        console.log("\x1b[32m%s\x1b[0m", "Database tables initialized");
    });
});

// Utility function to validate ticker
async function validateTicker(ticker) {
    try {
        const result = await yahooFinance.quote(ticker);
        return {
            isValid: true,
            price: result.regularMarketPrice,
            name: result.longName || result.shortName
        };
    } catch (error) {
        return { isValid: false };
    }
}

// Middleware for session management
bot.use(session({ initial: () => ({ thresholds: {} }) }));

// Command handlers
bot.command("start", async (ctx) => {
    try {
        // Add user to database
        db.run(
            "INSERT OR REPLACE INTO users (id, name) VALUES (?, ?)",
            [ctx.from.id.toString(), ctx.from.first_name],
            async (err) => {
                if (err) {
                    console.error("\x1b[31m%s\x1b[0m", "Database error:", err);
                    return;
                }
                await ctx.reply(
                    "Welcome to Stock Alerts Bot! 📈\n\n" +
                    "Available commands:\n" +
                    "/add <ticker> - Add a stock to track\n" +
                    "/remove <ticker> - Remove a tracked stock\n" +
                    "/list - List all tracked stocks"
                );
                console.log("\x1b[32m%s\x1b[0m", `User ${ctx.from.id} started the bot`);
            }
        );
    } catch (error) {
        console.error("\x1b[31m%s\x1b[0m", "Error in /start command:", error);
        await ctx.reply("Sorry, an error occurred. Please try again.");
    }
});

bot.command("add", async (ctx) => {
    try {
        const input = ctx.match;
        if (!input) {
            await ctx.reply("Please provide ticker symbol(s). Example: /add AAPL");
            return;
        }

        const tickers = [...new Set(input.split(/\s+/).map(t => t.toUpperCase()))];
        
        if (tickers.length > 5) {
            await ctx.reply("You can only add up to 5 tickers at once.");
            return;
        }

        const validatingMsg = await ctx.reply("Validating ticker(s)... ⏳");

        const validationResults = await Promise.all(
            tickers.map(async (ticker) => ({
                ticker,
                ...(await validateTicker(ticker))
            }))
        );

        const validTickers = validationResults.filter(r => r.isValid);
        const invalidTickers = validationResults.filter(r => !r.isValid);

        let responseMsg = "";

        for (const { ticker, name, price } of validTickers) {
            try {
                await new Promise((resolve, reject) => {
                    db.run(
                        "INSERT OR IGNORE INTO watchlist_items (user_id, symbol) VALUES (?, ?)",
                        [ctx.from.id.toString(), ticker],
                        (err) => {
                            if (err) reject(err);
                            else resolve();
                        }
                    );
                });
                responseMsg += `✅ Added ${ticker} (${name}) - Current price: $${price}\n`;
                console.log("\x1b[32m%s\x1b[0m", `User ${ctx.from.id} added ${ticker}`);
            } catch (err) {
                console.error("\x1b[31m%s\x1b[0m", `Error adding ${ticker}:`, err);
                responseMsg += `❌ Error adding ${ticker}\n`;
            }
        }

        if (invalidTickers.length > 0) {
            responseMsg += "\nInvalid tickers:\n";
            invalidTickers.forEach(({ ticker }) => {
                responseMsg += `❌ ${ticker} - Not found or invalid\n`;
            });
        }

        await ctx.api.deleteMessage(ctx.chat.id, validatingMsg.message_id);
        await ctx.reply(responseMsg || "No valid tickers provided.");

    } catch (error) {
        console.error("\x1b[31m%s\x1b[0m", "Error in /add command:", error);
        await ctx.reply("Sorry, an error occurred. Please try again.");
    }
});

bot.command("list", async (ctx) => {
    try {
        db.all(
            "SELECT symbol, alert_threshold_low, alert_threshold_high FROM watchlist_items WHERE user_id = ?",
            [ctx.from.id.toString()],
            async (err, rows) => {
                if (err) {
                    console.error("\x1b[31m%s\x1b[0m", "Database error:", err);
                    await ctx.reply("Error fetching your watchlist. Please try again.");
                    return;
                }

                if (rows.length === 0) {
                    await ctx.reply("Your watchlist is empty. Add stocks using /add <ticker>");
                    return;
                }

                const watchlist = rows.map(row => 
                    `${row.symbol} (${row.alert_threshold_low}% - ${row.alert_threshold_high}%)`
                ).join("\n");
                
                await ctx.reply(
                    "Your Watchlist 📋\n\n" +
                    watchlist
                );
                console.log("\x1b[32m%s\x1b[0m", `User ${ctx.from.id} listed their stocks`);
            }
        );
    } catch (error) {
        console.error("\x1b[31m%s\x1b[0m", "Error in /list command:", error);
        await ctx.reply("Sorry, an error occurred. Please try again.");
    }
});

bot.command("remove", async (ctx) => {
    try {
        const ticker = ctx.match?.toUpperCase();
        if (!ticker) {
            await ctx.reply("Please provide a ticker symbol. Example: /remove AAPL");
            return;
        }

        db.run(
            "DELETE FROM watchlist_items WHERE symbol = ? AND user_id = ?",
            [ticker, ctx.from.id.toString()],
            async (err) => {
                if (err) {
                    console.error("\x1b[31m%s\x1b[0m", "Database error:", err);
                    await ctx.reply("Error removing stock. Please try again.");
                    return;
                }
                await ctx.reply(`Removed ${ticker} from your watchlist! ✅`);
                console.log("\x1b[32m%s\x1b[0m", `User ${ctx.from.id} removed ${ticker}`);
            }
        );
    } catch (error) {
        console.error("\x1b[31m%s\x1b[0m", "Error in /remove command:", error);
        await ctx.reply("Sorry, an error occurred. Please try again.");
    }
});

// Error handling
bot.catch((err) => {
    console.error("\x1b[31m%s\x1b[0m", "Bot error:", err);
});

// Start the bot
console.log("\x1b[32m%s\x1b[0m", "Starting bot...");
bot.start(); 