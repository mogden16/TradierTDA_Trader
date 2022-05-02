TRADETYPE = "both"      #long, short, both
STAMINA = "afterHours" #lunchBreak, marketHours, afterHours
LOOKAHEAD = "prevbar"   #currentBar, prevBar
EXITTYPE = "exitsignal" #exitsignal, reversal
ORDERPRICE = "open"     #open, close
OFFSET = 0

LUNCHSTART_TIME = "11:30"
LUNCHSTOP_TIME = "13:40"

SMALLEST_AGGREGATION = 1 #1, 5, 10, 15, 30 minutes

#       QQE SETTINGS
QQE_RSI_PERIOD = 6
QQE_SLOW_FACTOR = 3
QQE_SETTING = 2.621


#       HULL SETTINGS
HULL_FAST = 9
HULL_SLOW = 18

#       RSI SETTINGS
RSILENGTH = 16
RSIAVERAGETYPE = "wilders"
RSISUPEROVERSOLD = 20
RSIOVERSOLD = 35
RSILOWNEUTRAL = 45
RSIHIGHNEUTRAL = 55
RSIOVERBOUGHT = 75
RSISUPEROVERBOUGHT = 80
RSIPAINTTYPE = "weighted" #simple, weighted

#       SMI SETTINGS
SMI_FAST = 2
SMI_SLOW = 4
SMI_OVERSOLD = -45
SMI_OVERBOUGHT = 40
