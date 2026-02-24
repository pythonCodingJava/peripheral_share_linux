import threading
import time
import tkinter as tk
from multiprocessing import Queue, Event,Process

def show_menu(run, queue:Queue):
    root = tk.Tk()
    # Remove window decorations (optional)
    root.overrideredirect(True)
    # Keep window always on top
    root.attributes("-topmost", True)

    size = 200
    # Get screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    # Compute center position
    x = (screen_width // 2) - (size // 2)
    y = (screen_height // 2) - (size // 2)
    # Set geometry
    root.geometry(f"{int(screen_width/10)}x{int(screen_height/10)}+{0}+{0}")
    # Appearance
    root.configure(bg="black")
    label = tk.Label(
        root,
        text="",
        fg="white",
        bg="black",
        font=("Arial", 16)
    )
    label.place(relx=0.5, rely=0.5, anchor="center")


    # root.wait_visibility(root) 
    # root.attributes("-alpha", 0.5)
    # root.withdraw()
    # Square size
    try :
        # t = threading.Thread(root.mainloop)
        # t.start()
        while not run.is_set():
            root.update_idletasks()
            root.update()
            
            # label.config(text="Testchange")
            try :
                q = queue.get_nowait()
                print(q)
                if q[0] == "show":
                    root.deiconify()
                    # root.lift()
                    # root.update_idletasks()
                    # root.update()
                elif q[0] == "destroy":
                    root.destroy()
                    return
                else :
                    label.config(text=q[0])
            except Exception as e :
                pass
        # root.mainloop()
    except Exception as e :
        print("Window closing due to error ", e)
    # finally:
        root.destroy()
        
    # root.mainloop()

def main_loop(run, queue: Queue):
    p = Process(target=show_menu, args=(run,queue,))
    while True :
        q = queue.get()
        if q[0] == "show":
            show_menu(run,queue)
# run = Event()
# run.clear()
# # show_menu("iPad", run)
# q = Queue()
# p = Process(target=show_menu, args=("ipad",run,q))
# p.start()
# time.sleep(2)
# q.put("Testing")
# time.sleep(2)
# q.put("Dynamic")
# time.sleep(2)
# q.put("Notifications")