from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from collections import deque
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# In-memory storage for the waitlist
waitlist = []

# Wait time tracking
average_wait_time = 15  # Initial average wait time in minutes
recent_wait_times = []  # Track last 5 wait times

# Estimated wait time per party (in minutes)
ESTIMATED_WAIT_PER_PARTY = 5

class Party:
    def __init__(self, name, party_size, phone='', status='waiting'):
        self.id = len(waitlist) + 1
        self.name = name
        self.party_size = int(party_size)
        self.phone = phone
        self.status = status
        self.arrival_time = datetime.now()
        self.estimated_seat_time = None
        self.calculate_estimated_seat_time()
    
    def calculate_estimated_seat_time(self):
        if not waitlist:
            self.estimated_seat_time = datetime.now() + timedelta(minutes=10)  # Base wait time for first party
        else:
            # Estimate based on parties ahead in line
            parties_ahead = [p for p in waitlist if p.status == 'waiting']
            minutes_ahead = sum(p.party_size for p in parties_ahead) * ESTIMATED_WAIT_PER_PARTY
            self.estimated_seat_time = datetime.now() + timedelta(minutes=minutes_ahead)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'party_size': self.party_size,
            'phone': self.phone,
            'status': self.status,
            'wait_time': self.get_wait_time(),
            'arrival_time': self.arrival_time.strftime('%I:%M %p'),
            'time_elapsed': self.get_time_elapsed(),
            'estimated_seat_time': self.estimated_seat_time.strftime('%I:%M %p') if self.estimated_seat_time else 'N/A'
        }
        
    def get_time_elapsed(self):
        """Returns the time elapsed since the party was added"""
        delta = datetime.now() - self.arrival_time
        minutes = int(delta.total_seconds() // 60)
        hours = minutes // 60
        minutes = minutes % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m ago"
        return f"{minutes}m ago"
    
    def get_wait_duration(self):
        """Returns the total wait duration in minutes"""
        delta = datetime.now() - self.arrival_time
        return int(delta.total_seconds() // 60)
    
    def get_wait_time(self):
        if self.status != 'waiting':
            return 'Seated'
        wait_minutes = (self.estimated_seat_time - datetime.now()).seconds // 60
        return f"{max(0, wait_minutes)} min"

def calculate_average_wait_time():
    if not waitlist:
        return 0
    waiting_parties = [p for p in waitlist if p.status == 'waiting']
    if not waiting_parties:
        return 0
    return sum(p.party_size for p in waiting_parties) * ESTIMATED_WAIT_PER_PARTY // len(waiting_parties)

@app.route('/')
def index():
    # Calculate current wait time based on average and number of parties
    current_wait_time = average_wait_time
    return render_template('index.html', queue=[p.to_dict() for p in waitlist], current_wait_time=current_wait_time)

@app.route('/add', methods=['POST'])
def add_party():
    name = request.form.get('name', '').strip()
    party_size = request.form.get('party_size', '1').strip()
    phone = request.form.get('phone', '').strip()
    status = request.form.get('status', 'waiting')
    
    if not name or not party_size.isdigit():
        flash('Please provide a valid name and party size', 'error')
        return redirect(url_for('index'))
    
    party = Party(name, party_size, phone, status)
    waitlist.append(party)
    
    # Update estimated times for all waiting parties
    for p in waitlist:
        if p.status == 'waiting':
            p.calculate_estimated_seat_time()
    
    flash(f'Added {name} (party of {party_size}) to the waitlist!', 'success')
    return redirect(url_for('index'))

@app.route('/remove/<int:party_id>', methods=['POST'])
def remove_party(party_id):
    global waitlist, average_wait_time, recent_wait_times
    for i, party in enumerate(waitlist):
        if party.id == party_id:
            # Calculate wait duration for this party
            wait_duration = party.get_wait_duration()
            recent_wait_times.append(wait_duration)
            
            # Keep only last 5 wait times
            if len(recent_wait_times) > 5:
                recent_wait_times.pop(0)
            
            # Calculate new average: recent wait times + current waiting parties
            waiting_parties = [p for p in waitlist if p.status == 'waiting' and p.id != party_id]
            current_wait_times = [p.get_wait_duration() for p in waiting_parties]
            
            all_times = recent_wait_times
            if all_times:
                average_wait_time = sum(all_times) / len(all_times)
            
            removed_party = waitlist.pop(i)
            # Update estimated times for remaining waiting parties
            for p in waitlist:
                if p.status == 'waiting':
                    p.calculate_estimated_seat_time()
            flash(f'Removed {removed_party.name} from the waitlist.', 'info')
            break
    return redirect(url_for('index'))

@app.route('/update_status/<int:party_id>/<status>', methods=['POST'])
def update_status(party_id, status):
    for party in waitlist:
        if party.id == party_id:
            party.status = status
            # Update estimated times for all waiting parties
            for p in waitlist:
                if p.status == 'waiting':
                    p.calculate_estimated_seat_time()
            flash(f'Updated status for {party.name} to {status}.', 'success')
            break
    return redirect(url_for('index'))

@app.template_filter('format_phone')
def format_phone(phone):
    if not phone:
        return ''
    # Simple phone number formatting
    phone = ''.join(c for c in phone if c.isdigit())
    if len(phone) == 10:
        return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
    return phone

if __name__ == '__main__':
    # Add some sample data for demonstration
    if not waitlist:
        sample_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Miller', 'Davis', 'Garcia']
        initial_wait_times = [10, 15, 30]  # Specific wait times for first 3 parties
        for i in range(3):
            name = f"{sample_names[i]} Party"
            party_size = random.randint(2, 6)
            phone = f"555-{random.randint(100,999)}-{random.randint(1000,9999)}"
            waitlist.append(Party(name, party_size, phone, 'waiting' if i < 2 else 'seated'))
            
            # Set specific wait times for initial parties
            if i < len(initial_wait_times):
                waitlist[i].arrival_time = datetime.now() - timedelta(minutes=initial_wait_times[i])
                # Add to recent wait times to establish average
                recent_wait_times.append(initial_wait_times[i])
                average_wait_time = sum(recent_wait_times) / len(recent_wait_times)
    
    app.run(debug=True, port=5001)
