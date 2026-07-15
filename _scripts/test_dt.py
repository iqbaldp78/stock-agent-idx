import datetime
lrd = datetime.datetime(2026, 7, 10, 16, 21, 43, 96422)
try:
    from datetime import datetime, timedelta
    if isinstance(lrd, str):
        lrd_dt = datetime.strptime(str(lrd)[:19], "%Y-%m-%d %H:%M:%S")
    else:
        lrd_dt = lrd
        
    if lrd_dt.tzinfo:
        lrd_dt = lrd_dt.replace(tzinfo=None)
        
    lrd_wib = lrd_dt + timedelta(hours=7)
    display_lrd = lrd_wib.strftime("%d %b %Y, %H:%M WIB")
    print(display_lrd)
except Exception as e:
    print("Exception:", type(e), e)
