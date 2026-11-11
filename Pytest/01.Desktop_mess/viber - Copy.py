import pyautogui



location = pyautogui.locateOnScreen('screens/signal_icon.png', confidence=0.8)



print(location)