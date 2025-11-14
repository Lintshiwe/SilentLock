"""
Real-time activity display for SilentLock password manager.
Shows live updates of when passwords were used, saved, or accessed.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading
import time
from typing import Dict, List, Callable, Optional


class RealTimeActivityWidget:
    """Widget displaying real-time password activity and usage."""
    
    def __init__(self, parent_frame: tk.Widget, realtime_tracker):
        self.parent_frame = parent_frame
        self.realtime_tracker = realtime_tracker
        
        # Activity display components
        self.activity_frame = None
        self.activity_tree = None
        self.last_activity_label = None
        self.status_label = None
        
        # Activity data
        self.displayed_activities = []
        self.max_displayed_activities = 50
        
        # Update control
        self.update_running = False
        self.update_thread = None
        
        # Setup UI
        self._setup_activity_display()
        
        # Register for real-time updates
        self.realtime_tracker.add_callback(self._on_activity_update)
    
    def _setup_activity_display(self):
        """Setup the real-time activity display UI."""
        # Main activity frame
        self.activity_frame = ttk.LabelFrame(self.parent_frame, text="🔄 Real-Time Activity", padding=10)
        self.activity_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Status bar
        status_frame = ttk.Frame(self.activity_frame)
        status_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.status_label = ttk.Label(status_frame, text="🟢 Monitoring Active", foreground="green")
        self.status_label.pack(side=tk.LEFT)
        
        self.last_activity_label = ttk.Label(status_frame, text="Last activity: Never", foreground="gray")
        self.last_activity_label.pack(side=tk.RIGHT)
        
        # Activity tree view
        columns = ("Time", "Action", "Credential", "Details")
        self.activity_tree = ttk.Treeview(self.activity_frame, columns=columns, show="headings", height=8)
        
        # Configure columns
        self.activity_tree.heading("Time", text="Time")
        self.activity_tree.heading("Action", text="Action") 
        self.activity_tree.heading("Credential", text="Credential")
        self.activity_tree.heading("Details", text="Details")
        
        self.activity_tree.column("Time", width=100, minwidth=100)
        self.activity_tree.column("Action", width=80, minwidth=80)
        self.activity_tree.column("Credential", width=150, minwidth=100)
        self.activity_tree.column("Details", width=200, minwidth=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.activity_frame, orient=tk.VERTICAL, command=self.activity_tree.yview)
        self.activity_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        tree_frame = ttk.Frame(self.activity_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.activity_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Control buttons
        button_frame = ttk.Frame(self.activity_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(button_frame, text="🔄 Refresh", command=self._refresh_activity).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🗑️ Clear", command=self._clear_activity).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📊 Statistics", command=self._show_statistics).pack(side=tk.LEFT, padx=5)
        
        # Load initial data
        self._load_initial_activity()
        
        # Start real-time updates
        self._start_realtime_updates()
    
    def _load_initial_activity(self):
        """Load initial activity data."""
        try:
            recent_activities = self.realtime_tracker.get_recent_activity(24)  # Last 24 hours
            
            for activity in recent_activities[-self.max_displayed_activities:]:
                self._add_activity_to_tree(activity)
            
            if recent_activities:
                self._update_last_activity_time(recent_activities[-1]['timestamp'])
            
        except Exception as e:
            print(f"Error loading initial activity: {e}")
    
    def _add_activity_to_tree(self, activity: Dict):
        """Add an activity entry to the tree view."""
        try:
            # Format timestamp
            timestamp = activity['timestamp']
            time_str = timestamp.strftime("%H:%M:%S")
            
            # Format action with icon
            action = activity['action']
            action_icons = {
                'saved': '💾',
                'used': '🔑',
                'accessed': '👁️',
                'auto-filled': '⚡',
                'updated': '✏️',
                'deleted': '🗑️'
            }
            action_display = f"{action_icons.get(action, '📝')} {action.title()}"
            
            # Get credential name
            credential_name = activity.get('details', '').split(' for ')[-1] if ' for ' in activity.get('details', '') else 'Unknown'
            if not credential_name or credential_name == 'Unknown':
                credential_name = f"ID: {activity['credential_id']}"
            
            # Format details
            details = activity.get('details', '')
            if len(details) > 50:
                details = details[:47] + "..."
            
            # Insert into tree
            item_id = self.activity_tree.insert('', 0, values=(time_str, action_display, credential_name, details))
            
            # Color coding based on action
            if action == 'saved':
                self.activity_tree.set(item_id, "Action", action_display)
                # Could add tags for coloring if needed
            
            # Keep only max items
            items = self.activity_tree.get_children()
            if len(items) > self.max_displayed_activities:
                self.activity_tree.delete(items[-1])  # Remove oldest
            
        except Exception as e:
            print(f"Error adding activity to tree: {e}")
    
    def _on_activity_update(self, activity: Dict):
        """Handle real-time activity updates."""
        try:
            # Update UI in main thread
            self.parent_frame.after(0, lambda: self._add_activity_to_tree(activity))
            self.parent_frame.after(0, lambda: self._update_last_activity_time(activity['timestamp']))
            
        except Exception as e:
            print(f"Error handling activity update: {e}")
    
    def _update_last_activity_time(self, timestamp: datetime):
        """Update the last activity time display."""
        try:
            now = datetime.now()
            diff = now - timestamp
            
            if diff.total_seconds() < 60:
                time_str = "Just now"
            elif diff.total_seconds() < 3600:
                minutes = int(diff.total_seconds() / 60)
                time_str = f"{minutes} min ago"
            else:
                time_str = timestamp.strftime("%H:%M")
            
            if hasattr(self, 'last_activity_label'):
                self.last_activity_label.config(text=f"Last activity: {time_str}")
            
        except Exception as e:
            print(f"Error updating last activity time: {e}")
    
    def _start_realtime_updates(self):
        """Start the real-time update thread."""
        self.update_running = True
        
        def update_loop():
            while self.update_running:
                try:
                    # Update status and times every 30 seconds
                    self.parent_frame.after(0, self._update_status)
                    time.sleep(30)
                except Exception as e:
                    print(f"Error in update loop: {e}")
                    time.sleep(5)
        
        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()
    
    def _update_status(self):
        """Update status indicators."""
        try:
            # Update relative times for displayed items
            for item in self.activity_tree.get_children():
                # Could update relative times here if needed
                pass
            
            # Update monitoring status
            if hasattr(self, 'status_label'):
                self.status_label.config(text="🟢 Monitoring Active", foreground="green")
            
        except Exception as e:
            print(f"Error updating status: {e}")
    
    def _refresh_activity(self):
        """Refresh the activity display."""
        try:
            # Clear current items
            for item in self.activity_tree.get_children():
                self.activity_tree.delete(item)
            
            # Reload recent activity
            self._load_initial_activity()
            
        except Exception as e:
            print(f"Error refreshing activity: {e}")
    
    def _clear_activity(self):
        """Clear the activity display."""
        try:
            for item in self.activity_tree.get_children():
                self.activity_tree.delete(item)
            
            if hasattr(self, 'last_activity_label'):
                self.last_activity_label.config(text="Last activity: Never")
            
        except Exception as e:
            print(f"Error clearing activity: {e}")
    
    def _show_statistics(self):
        """Show activity statistics in a popup."""
        try:
            stats_window = tk.Toplevel(self.parent_frame)
            stats_window.title("Activity Statistics")
            stats_window.geometry("400x300")
            stats_window.transient(self.parent_frame.winfo_toplevel())
            stats_window.grab_set()
            
            # Get statistics
            recent_activities = self.realtime_tracker.get_recent_activity(24)
            
            # Calculate stats
            total_activities = len(recent_activities)
            action_counts = {}
            for activity in recent_activities:
                action = activity['action']
                action_counts[action] = action_counts.get(action, 0) + 1
            
            # Display stats
            stats_frame = ttk.Frame(stats_window, padding=20)
            stats_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(stats_frame, text="📊 Activity Statistics (Last 24 Hours)", font=("Arial", 12, "bold")).pack(pady=(0, 20))
            
            ttk.Label(stats_frame, text=f"Total Activities: {total_activities}").pack(anchor=tk.W, pady=2)
            
            if action_counts:
                ttk.Label(stats_frame, text="\\nBreakdown by Action:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
                
                for action, count in sorted(action_counts.items()):
                    percentage = (count / total_activities) * 100 if total_activities > 0 else 0
                    ttk.Label(stats_frame, text=f"  {action.title()}: {count} ({percentage:.1f}%)").pack(anchor=tk.W, pady=1)
            
            # Most active time
            if recent_activities:
                hours = [activity['timestamp'].hour for activity in recent_activities]
                most_active_hour = max(set(hours), key=hours.count)
                ttk.Label(stats_frame, text=f"\\nMost Active Hour: {most_active_hour}:00", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 2))
            
            # Close button
            ttk.Button(stats_frame, text="Close", command=stats_window.destroy).pack(pady=(20, 0))
            
        except Exception as e:
            print(f"Error showing statistics: {e}")
    
    def stop_updates(self):
        """Stop real-time updates."""
        self.update_running = False
        if self.update_thread:
            self.update_thread.join(timeout=1)


class CredentialUsageIndicator:
    """Shows last usage time for individual credentials."""
    
    def __init__(self, realtime_tracker):
        self.realtime_tracker = realtime_tracker
    
    def get_usage_indicator(self, credential_id: int) -> str:
        """Get usage indicator text for a credential."""
        activity = self.realtime_tracker.get_last_activity(credential_id)
        if not activity:
            return "🔹 Never used"
        
        action = activity['action']
        time_str = self.realtime_tracker.format_last_used(credential_id)
        
        action_icons = {
            'saved': '💾',
            'used': '🔑', 
            'accessed': '👁️',
            'auto-filled': '⚡'
        }
        
        icon = action_icons.get(action, '📝')
        return f"{icon} {action.title()} {time_str}"
    
    def get_usage_color(self, credential_id: int) -> str:
        """Get color coding for usage recency."""
        activity = self.realtime_tracker.get_last_activity(credential_id)
        if not activity:
            return "gray"
        
        timestamp = activity['timestamp']
        now = datetime.now()
        diff = now - timestamp
        
        if diff.total_seconds() < 3600:  # Last hour
            return "green"
        elif diff.total_seconds() < 86400:  # Last day
            return "blue"
        elif diff.total_seconds() < 604800:  # Last week
            return "orange"
        else:
            return "gray"