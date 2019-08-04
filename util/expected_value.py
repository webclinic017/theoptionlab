from util import util 
import math
from datetime import datetime, time
from py_vollib import black_scholes
from py_vollib.black_scholes import implied_volatility

e_spanne = 3
ratio = 100


def getExpectedValue(connector, underlying, combo, current_date, expiration, use_precomputed = True, include_riskfree = True): 

    current_quote = connector.query_midprice_underlying(underlying, current_date)
    
    expiration_time = datetime.combine(expiration, time(16))
    remaining_time_in_years = util.remaining_time(current_date, expiration_time)
    
    ul_for_ew = []
    sum_legs = []
    prob_touch = []
    
    if (current_quote % 10) < 5:
        atm_strike = int(current_quote / 10) * 10
    else:
        atm_strike = int((current_quote + 10) / 10) * 10

    if use_precomputed: 
        try: 
            atm_iv = connector.select_iv(current_date, underlying, expiration, "p", atm_strike) 
        except: 
            atm_iv = 0.01
            
    else: 
        
        try:
            atm_option = util.Option(connector, current_date, underlying, atm_strike, expiration, "p")
        except ValueError: 
            return None
        midprice = connector.query_midprice(current_date, atm_option)

        rf = util.interest
        if include_riskfree: 
            rf = util.get_riskfree_libor(current_date, remaining_time_in_years)
            
        try: 
            atm_iv = implied_volatility.implied_volatility(midprice, current_quote, atm_strike, remaining_time_in_years, rf, atm_option.type)
        except: 
            atm_iv = 0.01
            
        if (atm_iv == 0): atm_iv = 0.01

    
    one_sd = (atm_iv / math.sqrt(util.yeartradingdays/(remaining_time_in_years * util.yeartradingdays))) * current_quote

    lower_ul = current_quote-e_spanne*one_sd
    upper_ul = current_quote+e_spanne*one_sd
    step = (upper_ul - lower_ul) / 24 # war 1000
    

    for i in range(25): # war 1001
        
        ul_for_ew.insert(i, lower_ul + (i*step))
        
        sum_legs_i = 0 
        positions = combo.getPositions()
        for position in positions: 

#             param sigma: annualized standard deviation, or volatility
#             https://www.etfreplay.com/etf/iwm.aspx

            rf = util.interest
            if include_riskfree: 
                rf = util.get_riskfree_libor(current_date, remaining_time_in_years)
            
            value = black_scholes.black_scholes(position.option.type, ul_for_ew[i], position.option.strike, remaining_time_in_years, rf, 0)
            guv = (value - position.entry_price) * ratio * position.amount 
            sum_legs_i += guv
            
            
        sum_legs.insert(i, sum_legs_i)
        
        prob = util.prob_hit(current_quote, ul_for_ew[i], remaining_time_in_years, 0, atm_iv)
        prob_touch.insert(i, prob)    
    
    sumproduct = sum([a*b for a,b in zip(sum_legs,prob_touch)])
    expected_value = round((sumproduct / sum(prob_touch)),2)
    return expected_value


def getExpectedValueGroup(underlying, group, current_date, expiration): 
    expected_value = 0
    combos = group.getCombos()
    for combo in combos: 
        expected_value += getExpectedValue(underlying, combo, current_date, expiration)
    return expected_value

# ideas: Use cauchy distribution or real history 

