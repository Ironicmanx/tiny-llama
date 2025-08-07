import webbrowser

def try_command(text):
    text = text.lower()
    if "open youtube" in text:
        webbrowser.open("https://youtube.com")
        print("[Command] Opened YouTube")
        return True
    elif "open calculator" in text:
        import os
        os.system("calc" if os.name == "nt" else "gnome-calculator")
        return True
    return False
