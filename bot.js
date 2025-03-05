const { Bot, session } = require("grammy");
const dotenv = require("dotenv");
const sqlite3 = require("sqlite3");
const yahooFinance = require("yahoo-finance2").default;

// Load environment variables
dotenv.config({ path: ".env.local" });

// Constants
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const DB_PATH = "./stock_alerts.db";

// Initialize bot
const bot = new Bot(BOT_TOKEN);

// Database connection and initialization
const db = new sqlite3.Database(DB_PATH, (err) => {
    if (err) {
        console.error("\x1b[31m%s\x1b[0m", "Error connecting to database:", err);
        process.exit(1);
    }
    console.log("\x1b[32m%s\x1b[0m", "Connected to SQLite database");

    // Create stocks table if it doesn't exist
    db.run(`
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            low_threshold REAL,
            high_threshold REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, user_id)
        )
    `, (err) => {
        if (err) {
            console.error("\x1b[31m%s\x1b[0m", "Error creating stocks table:", err);
            process.exit(1);
        }
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
        await ctx.reply(
            "Welcome to Stock Alerts Bot! 📈\n\n" +
            "Available commands:\n" +
            "/add <ticker> - Add a stock to track (e.g., /add AAPL or /add AAPL MSFT)\n" +
            "/remove <ticker> - Remove a tracked stock\n" +
            "/list - List all tracked stocks\n" +
            "/thresholds <ticker> <low> <high> - Set price alerts\n" +
            "/settings - View current settings"
        );
        console.log("\x1b[32m%s\x1b[0m", `User ${ctx.from.id} started the bot`);
    } catch (error) {
        console.error("\x1b[31m%s\x1b[0m", "Error in /start command:", error);
        await ctx.reply("Sorry, an error occurred. Please try again.");
    }
});

bot.command("add", async (ctx) => {
    try {
        const input = ctx.match;
        if (!input) {
            await ctx.reply("Please provide ticker symbol(s). Example: /add AAPL or /add AAPL MSFT");
            return;
        }

        // Split input into individual tickers and remove duplicates
        const tickers = [...new Set(input.split(/\s+/).map(t => t.toUpperCase()))];
        
        if (tickers.length > 5) {
            await ctx.reply("You can only add up to 5 tickers at once.");
            return;
        }

        // Show "validating" message
        const validatingMsg = await ctx.reply("Validating ticker(s)... ⏳");

        // Validate each ticker
        const validationResults = await Promise.all(
            tickers.map(async (ticker) => ({
                ticker,
                ...(await validateTicker(ticker))
            }))
        );

        const validTickers = validationResults.filter(r => r.isValid);
        const invalidTickers = validationResults.filter(r => !r.isValid);

        // Prepare response message
        let responseMsg = "";

        // Add valid tickers to database
        for (const { ticker, name, price } of validTickers) {
            try {
                await new Promise((resolve, reject) => {
                    db.run(
                        "INSERT OR IGNORE INTO stocks (ticker, user_id) VALUES (?, ?)",
                        [ticker, ctx.from.id],
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

        // Add invalid tickers to response
        if (invalidTickers.length > 0) {
            responseMsg += "\nInvalid tickers:\n";
            invalidTickers.forEach(({ ticker }) => {
                responseMsg += `❌ ${ticker} - Not found or invalid\n`;
            });
        }

        // Delete the validating message and send the final response
        await ctx.api.deleteMessage(ctx.chat.id, validatingMsg.message_id);
        await ctx.reply(responseMsg || "No valid tickers provided.");

    } catch (error) {
        console.error("\x1b[31m%s\x1b[0m", "Error in /add command:", error);
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

        // Remove from database
        db.run("DELETE FROM stocks WHERE ticker = ? AND user_id = ?",
            [ticker, ctx.from.id],
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

bot.command("list", async (ctx) => {
    try {
        db.all("SELECT ticker FROM stocks WHERE user_id = ?",
            [ctx.from.id],
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

                const watchlist = rows.map(row => row.ticker).join("\n");
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

bot.command("thresholds", async (ctx) => {
    try {
        const [ticker, low, high] = ctx.match?.split(" ") || [];
        
        if (!ticker || !low || !high) {
            await ctx.reply(
                "Please provide ticker and thresholds.\n" +
                "Example: /thresholds AAPL 150 200"
            );
            return;
        }

        const lowValue = parseFloat(low);
        const highValue = parseFloat(high);

        if (isNaN(lowValue) || isNaN(highValue)) {
            await ctx.reply("Please provide valid numbers for thresholds.");
            return;
        }

        // Update thresholds in database
        db.run(
            "UPDATE stocks SET low_threshold = ?, high_threshold = ? WHERE ticker = ? AND user_id = ?",
            [lowValue, highValue, ticker.toUpperCase(), ctx.from.id],
            async (err) => {
                if (err) {
                    console.error("\x1b[31m%s\x1b[0m", "Database error:", err);
                    await ctx.reply("Error setting thresholds. Please try again.");
                    return;
                }
                await ctx.reply(
                    `Thresholds set for ${ticker.toUpperCase()}:\n` +
                    `Low: $${lowValue}\n` +
                    `High: $${highValue}`
                );
                console.log("\x1b[32m%s\x1b[0m", `User ${ctx.from.id} set thresholds for ${ticker}`);
            }
        );
    } catch (error) {
        console.error("\x1b[31m%s\x1b[0m", "Error in /thresholds command:", error);
        await ctx.reply("Sorry, an error occurred. Please try again.");
    }
});

bot.command("settings", async (ctx) => {
    try {
        db.all(
            "SELECT ticker, low_threshold, high_threshold FROM stocks WHERE user_id = ?",
            [ctx.from.id],
            async (err, rows) => {
                if (err) {
                    console.error("\x1b[31m%s\x1b[0m", "Database error:", err);
                    await ctx.reply("Error fetching settings. Please try again.");
                    return;
                }

                if (rows.length === 0) {
                    await ctx.reply("You haven't set any thresholds yet.");
                    return;
                }

                const settings = rows
                    .filter(row => row.low_threshold || row.high_threshold)
                    .map(row => 
                        `${row.ticker}:\n` +
                        `Low: $${row.low_threshold || 'Not set'}\n` +
                        `High: $${row.high_threshold || 'Not set'}`
                    )
                    .join("\n\n");

                await ctx.reply(
                    "Your Alert Settings ⚙️\n\n" +
                    (settings || "No thresholds set for any stocks.")
                );
                console.log("\x1b[32m%s\x1b[0m", `User ${ctx.from.id} viewed settings`);
            }
        );
    } catch (error) {
        console.error("\x1b[31m%s\x1b[0m", "Error in /settings command:", error);
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