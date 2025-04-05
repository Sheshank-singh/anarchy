from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import Group, User
from app import db
import random
import string

bp = Blueprint('main', __name__)

def generate_group_code():
    """Generate a unique 6-character group code"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Group.query.filter_by(code=code).first():
            return code

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/join_group', methods=['POST'])
@login_required
def join_group():
    group_code = request.form.get('group_code')
    group = Group.query.filter_by(code=group_code, is_active=True).first()
    
    if not group:
        flash('Invalid group code or group is not active', 'error')
        return redirect(url_for('main.index'))
    
    if group.game_started:
        flash('Game has already started in this group', 'error')
        return redirect(url_for('main.index'))
    
    current_user.group = group
    db.session.commit()
    return redirect(url_for('game.lobby'))

@bp.route('/create_group', methods=['POST'])
@login_required
def create_group():
    if current_user.group:
        flash('You are already in a group', 'error')
        return redirect(url_for('main.index'))
    
    group = Group(
        code=generate_group_code(),
        owner_id=current_user.id,  # Set the owner_id to current user's ID
        is_active=True
    )
    db.session.add(group)
    db.session.commit()
    
    current_user.group = group
    current_user.is_group_owner = True
    db.session.commit()
    
    return redirect(url_for('game.lobby', group_code=group.code))

@bp.route('/leave_group', methods=['POST'])
@login_required
def leave_group():
    if not current_user.group:
        return redirect(url_for('main.index'))
    
    if current_user.is_group_owner:
        # If owner leaves, disband the group
        group = current_user.group
        for user in group.users:
            user.group = None
            user.is_group_owner = False
        group.is_active = False
    else:
        current_user.group = None
    
    db.session.commit()
    return redirect(url_for('main.index')) 