def macd(data, fast_period=12, slow_period=26, signal_period=9):
    """
    Calculate the MACD indicator.
    
    Args:
        data (pd.Series): Price data.
        fast_period (int): Fast period for EMA.
        slow_period (int): Slow period for EMA.
        signal_period (int): Signal period for EMA.
        
    Returns:
        pd.Series: MACD line, signal line, and histogram.
    """
    # Calculate the EMA of the data
    ema_fast = data.ewm(span=fast_period, adjust=False).mean()
    ema_slow = data.ewm(span=slow_period, adjust=False).mean()
    
    # Calculate the MACD line
    macd_line = ema_fast - ema_slow
    