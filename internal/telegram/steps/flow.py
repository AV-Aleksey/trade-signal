from telegram.ext import filters

SELECT_PAIR, SELECT_TICK, SELECT_SIGNALS, SELECT_FILTERS, MONITORING = range(5)

TEXT_MESSAGE_FILTER = filters.UpdateType.MESSAGE & filters.TEXT & ~filters.COMMAND
