from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    is_group_owner = db.Column(db.Boolean, default=False)
    lives = db.Column(db.Integer, default=2)
    points = db.Column(db.Integer, default=0)
    has_vest = db.Column(db.Boolean, default=False)
    is_alive = db.Column(db.Boolean, default=True)
    last_attacked = db.Column(db.DateTime)
    attack_count = db.Column(db.Integer, default=0)
    is_ready = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    owned_groups = db.relationship('Group', backref='owner', lazy=True, foreign_keys='Group.owner_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def can_be_attacked(self):
        if not self.last_attacked:
            return True
        if self.attack_count >= 2:
            # Check if 5 minutes have passed since last attack
            time_diff = datetime.utcnow() - self.last_attacked
            if time_diff.total_seconds() < 300:  # 5 minutes cooldown
                return False
            self.attack_count = 0  # Reset attack count after cooldown
        return True

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    game_started = db.Column(db.Boolean, default=False)
    current_question = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='group', lazy=True, foreign_keys='User.group_id')
    messages = db.relationship('Message', backref='group', lazy=True)
    
    # Constants for player limits
    MIN_PLAYERS = 5
    MAX_PLAYERS = 8
    
    def is_full(self):
        """Check if the group has reached the maximum number of players"""
        return len(self.users) >= self.MAX_PLAYERS
    
    def can_join(self):
        """Check if a new player can join the group"""
        return len(self.users) < self.MAX_PLAYERS and not self.is_active
    
    def has_minimum_players(self):
        """Check if the group has the minimum number of players required"""
        return len(self.users) >= self.MIN_PLAYERS

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='messages')

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    answer = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, default=1)
    is_major = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, nullable=False) 