import tkinter as tk
from tkinter import font
from time import strftime
import math

class DigitalClock:
    """Digital Clock with modern UI"""
    def __init__(self, parent, x, y):
        self.parent = parent
        self.frame = tk.Frame(parent, bg='#2c3e50', relief='raised', bd=2)
        self.frame.place(x=x, y=y, width=350, height=200)
        
        # Title
        title_font = font.Font(family="Arial", size=14, weight="bold")
        title_label = tk.Label(self.frame, text="Digital Clock", font=title_font, 
                              bg='#2c3e50', fg='#3498db')
        title_label.pack(pady=10)
        
        # Time display
        self.time_font = font.Font(family="Arial", size=48, weight="bold")
        self.time_label = tk.Label(self.frame, font=self.time_font, 
                                   bg='#2c3e50', fg='#2ecc71')
        self.time_label.pack(pady=10)
        
        # Date display
        self.date_font = font.Font(family="Arial", size=12)
        self.date_label = tk.Label(self.frame, font=self.date_font, 
                                   bg='#2c3e50', fg='#ecf0f1')
        self.date_label.pack()
        
        self.update_time()
    
    def update_time(self):
        """Update the time display"""
        time_string = strftime('%H:%M:%S')
        date_string = strftime('%A, %B %d, %Y')
        
        self.time_label.config(text=time_string)
        self.date_label.config(text=date_string)
        
        # Schedule next update
        self.time_label.after(1000, self.update_time)


class AnalogClock:
    """Analog Clock with moving hands"""
    def __init__(self, parent, x, y):
        self.parent = parent
        self.canvas = tk.Canvas(parent, width=300, height=300, bg='#ecf0f1', 
                               relief='raised', bd=2)
        self.canvas.place(x=x, y=y)
        
        # Clock dimensions
        self.center_x = 150
        self.center_y = 150
        self.radius = 120
        
        # Draw clock face
        self.draw_clock_face()
        self.update_hands()
    
    def draw_clock_face(self):
        """Draw static elements of the clock"""
        # Draw outer circle
        self.canvas.create_oval(self.center_x - self.radius, 
                               self.center_y - self.radius,
                               self.center_x + self.radius, 
                               self.center_y + self.radius,
                               outline='#2c3e50', width=3)
        
        # Draw hour markers
        for i in range(12):
            angle = math.radians(i * 30 - 90)
            x1 = self.center_x + (self.radius - 15) * math.cos(angle)
            y1 = self.center_y + (self.radius - 15) * math.sin(angle)
            x2 = self.center_x + (self.radius - 5) * math.cos(angle)
            y2 = self.center_y + (self.radius - 5) * math.sin(angle)
            self.canvas.create_line(x1, y1, x2, y2, width=3, fill='#2c3e50')
            
            # Add numbers
            text_angle = math.radians(i * 30 - 90)
            text_x = self.center_x + (self.radius - 35) * math.cos(text_angle)
            text_y = self.center_y + (self.radius - 35) * math.sin(text_angle)
            num = 12 if i == 0 else i
            self.canvas.create_text(text_x, text_y, text=str(num), 
                                   font=("Arial", 12, "bold"), fill='#2c3e50')
        
        # Draw center dot
        dot_size = 8
        self.canvas.create_oval(self.center_x - dot_size, self.center_y - dot_size,
                               self.center_x + dot_size, self.center_y + dot_size,
                               fill='#e74c3c', outline='#2c3e50', width=2)
    
    def draw_hand(self, angle, length, width, color, tag):
        """Draw a clock hand"""
        # Delete previous hand
        self.canvas.delete(tag)
        
        # Calculate end point
        x_end = self.center_x + length * math.cos(angle)
        y_end = self.center_y + length * math.sin(angle)
        
        # Draw hand
        self.canvas.create_line(self.center_x, self.center_y, x_end, y_end, 
                               width=width, fill=color, capstyle='round', tag=tag)
    
    def update_hands(self):
        """Update clock hands position"""
        # Get current time
        time_str = strftime('%H:%M:%S')
        hours, minutes, seconds = map(int, time_str.split(':'))
        
        # Convert to 12-hour format
        hours = hours % 12
        
        # Calculate angles (in radians, 0 at 12 o'clock)
        second_angle = math.radians((seconds / 60) * 360 - 90)
        minute_angle = math.radians(((minutes + seconds / 60) / 60) * 360 - 90)
        hour_angle = math.radians(((hours + minutes / 60) / 12) * 360 - 90)
        
        # Draw hands
        # Hour hand (shorter and thicker)
        self.draw_hand(hour_angle, 60, 6, '#2c3e50', 'hour_hand')
        
        # Minute hand (longer and medium)
        self.draw_hand(minute_angle, 85, 4, '#3498db', 'minute_hand')
        
        # Second hand (longest and thin, red)
        self.draw_hand(second_angle, 100, 2, '#e74c3c', 'second_hand')
        
        # Schedule next update
        self.canvas.after(1000, self.update_hands)


class ClockApp:
    """Main Application Window"""
    def __init__(self, root):
        self.root = root
        self.root.title("Clock Application")
        self.root.geometry("700x550")
        self.root.config(bg='#34495e')
        self.root.resizable(False, False)
        
        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (350)
        y = (self.root.winfo_screenheight() // 2) - (275)
        self.root.geometry(f"+{x}+{y}")
        
        # Title
        title_font = font.Font(family="Arial", size=20, weight="bold")
        title_label = tk.Label(self.root, text="⏰ Clock Application", 
                              font=title_font, bg='#34495e', fg='#ecf0f1')
        title_label.pack(pady=15)
        
        # Create digital and analog clocks
        self.digital_clock = DigitalClock(self.root, 25, 80)
        self.analog_clock = AnalogClock(self.root, 380, 80)
        
        # Footer
        footer_font = font.Font(family="Arial", size=10)
        footer_label = tk.Label(self.root, 
                               text="Click Close to Exit • Dual Format Time Display",
                               font=footer_font, bg='#34495e', fg='#95a5a6')
        footer_label.pack(side='bottom', pady=10)


def main():
    """Start the application"""
    root = tk.Tk()
    app = ClockApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
