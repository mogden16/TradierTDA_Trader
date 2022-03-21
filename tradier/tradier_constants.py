

API_ENDPOINT = {
    'developer_sandbox': 'https://sandbox.tradier.com',  # /v1/ paths
    'brokerage_sandbox': 'https://sandbox.tradier.com',  # /v1/ paths, paper trading (has full capabilities of brokerage)
    'brokerage': 'https://api.tradier.com',  # /v1/ paths
    'stream': 'https://stream.tradier.com',  # /v1/ paths
    'beta': 'https://api.tradier.com'  # /beta/ paths
}

API_PATH = {
    # User Profile
    'user_profile':         '/v1/user/profile',
    'user_balances':        '/v1/user/balances',
    'user_positions':       '/v1/user/positions',
    'user_history':         '/v1/user/history',
    'user_gainloss':        '/v1/user/gainloss',
    'user_orders':          '/v1/user/orders',

    # Account Profile
    'account_balances':     '/v1/accounts/{account_id}/balances',
    'account_positions':    '/v1/accounts/{account_id}/positions',
    'account_history':      '/v1/accounts/{account_id}/history',
    'account_gainloss':     '/v1/accounts/{account_id}/gainloss',
    'account_orders':       '/v1/accounts/{account_id}/orders',
    'account_order_status': '/v1/accounts/{account_id}/orders/{id}',

    # Market Data
    'quotes':               '/v1/markets/quotes',
    'timesales':            '/v1/markets/timesales',
    'chains':               '/v1/markets/options/chains',
    'strikes':              '/v1/markets/options/strikes',
    'expirations':          '/v1/markets/options/expirations',
    'history':              '/v1/markets/history',
    'clock':                '/v1/markets/clock',
    'calendar':             '/v1/markets/calendar',
    'search':               '/v1/markets/search',
    'lookup':               '/v1/markets/lookup',
    'stream':               '/v1/markets/events/session',

    # Trading
    'orders':               '/v1/accounts/{account_id}/orders',

    # Fundementals
    'company':              '/beta/markets/fundamentals/company',
    'corporate_calendars':  '/beta/markets/fundamentals/calendars',
    'dividends':            '/beta/markets/fundamentals/dividends',
    'corporate_actions':    '/beta/markets/fundamentals/corporate_actions',
    'ratios':               '/beta/markets/fundamentals/ratios',
    'financials':           '/beta/markets/fundamentals/financials',
    'statistics':           '/beta/markets/fundamentals/statistics',

    # Watchlists
    'watchlist':                '/v1/watchlists',
    'watchlist_id':             '/watchlists/{id}',
    'watchlist_add_symbols':    '/v1/watchlists/{id}/symbols',
    'watchlist_remove_symbols': '/v1/watchlists/{id}/symbols/{symbol}',

    # Streaming
    'stream_quote':         '/v1/markets/events'
}

