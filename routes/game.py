from flask import Blueprint, render_template, jsonify, request, current_app, redirect, url_for
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from app import socketio, db
from app.models import Group, User, Message, Question
from datetime import datetime, timedelta
import json
import random
import string

bp = Blueprint('game', __name__)

@bp.route('/lobby/<group_code>')
@login_required
def lobby(group_code):
    group = Group.query.filter_by(code=group_code).first_or_404()
    
    # Check if user is already in a different group
    if current_user.group_id and current_user.group_id != group.id:
        return redirect(url_for('main.index', error="You are already in another group"))
    
    # If user is not in any group, add them to this group
    if not current_user.group_id:
        if not group.can_join():
            return redirect(url_for('main.index', error="This group is full or the game has already started"))
        
        current_user.group_id = group.id
        db.session.commit()
    
    return render_template('game/lobby.html', group=group)

@bp.route('/game/<group_code>')
@login_required
def game_room(group_code):
    group = Group.query.filter_by(code=group_code).first_or_404()
    
    # Ensure user is in this group
    if current_user.group_id != group.id:
        return redirect(url_for('main.index', error="You are not a member of this group"))
    
    if not group.is_active:
        return redirect(url_for('game.lobby', group_code=group_code))
    
    return render_template('game/game.html', group=group)

@socketio.on('join')
def on_join(data):
    group_code = data['group_code']
    group = Group.query.filter_by(code=group_code).first_or_404()
    
    # Ensure user is in this group
    if current_user.group_id != group.id:
        emit('error', {'msg': 'You are not a member of this group'})
        return
    
    join_room(group_code)
    emit('status', {'msg': f'{current_user.username} has joined the room.'}, room=group_code)
    
    # Update player list for all users
    update_player_list(group_code)

@socketio.on('leave')
def on_leave(data):
    group_code = data['group_code']
    leave_room(group_code)
    emit('status', {'msg': f'{current_user.username} has left the room.'}, room=group_code)

@socketio.on('ready')
def on_ready(data):
    group_code = data['group_code']
    group = Group.query.filter_by(code=group_code).first_or_404()
    
    # Ensure user is in this group
    if current_user.group_id != group.id:
        emit('error', {'msg': 'You are not a member of this group'})
        return
    
    current_user.is_ready = True
    db.session.commit()
    emit('player_ready', {'username': current_user.username}, room=group_code)
    
    # Update player list for all users
    update_player_list(group_code)

@socketio.on('start_game')
def on_start_game(data):
    group_code = data['group_code']
    group = Group.query.filter_by(code=group_code).first_or_404()
    
    # Ensure user is the group owner
    if group.owner_id != current_user.id:
        emit('error', {'msg': 'Only the group owner can start the game'})
        return
    
    # Check if group has minimum players
    if not group.has_minimum_players():
        emit('error', {'msg': f'Need at least {group.MIN_PLAYERS} players to start the game'})
        return
    
    # Check if all players are ready
    all_ready = all(user.is_ready for user in group.users)
    if not all_ready:
        emit('error', {'msg': 'Not all players are ready!'}, room=group_code)
        return
    
    # Reset all users' game state
    for user in group.users:
        user.points = 0
        user.lives = 2
        user.has_vest = False
        user.is_ready = False
        user.last_attacked = None
        user.attack_count = 0
    
    group.is_active = True
    group.current_question = 1
    db.session.commit()
    
    emit('game_started', room=group_code)
    
    # Update player list for all users
    update_player_list(group_code)

@socketio.on('submit_answer')
def on_submit_answer(data):
    group_code = data['group_code']
    answer = data['answer']
    group = Group.query.filter_by(code=group_code).first_or_404()
    
    # Ensure user is in this group
    if current_user.group_id != group.id:
        emit('error', {'msg': 'You are not a member of this group'})
        return
    
    if not group.is_active:
        return
    
    question = Question.query.filter_by(order=group.current_question).first()
    if question and question.answer.lower() == answer.lower():
        current_user.points += 1
        db.session.commit()
        
        emit('correct_answer', {
            'username': current_user.username,
            'points': current_user.points
        }, room=group_code)
        
        if group.current_question == 18:  # Major question
            emit('major_power_available', {
                'username': current_user.username
            }, room=group_code)
        else:
            group.current_question += 1
            db.session.commit()
            emit('next_question', {'question_number': group.current_question}, room=group_code)
            
            # Update player list for all users
            update_player_list(group_code)

@socketio.on('attack')
def on_attack(data):
    group_code = data['group_code']
    target_username = data['target']
    points_to_use = data['points']
    
    group = Group.query.filter_by(code=group_code).first_or_404()
    
    # Ensure user is in this group
    if current_user.group_id != group.id:
        emit('error', {'msg': 'You are not a member of this group'})
        return
    
    target = User.query.filter_by(username=target_username).first()
    if not target or target.group_id != group.id:
        emit('error', {'msg': 'Invalid target!'}, room=group_code)
        return
    
    if points_to_use > current_user.points:
        emit('error', {'msg': 'Not enough points!'}, room=group_code)
        return
    
    if not target.can_be_attacked():
        emit('error', {'msg': 'Target is under attack cooldown!'}, room=group_code)
        return
    
    # Apply attack
    if target.has_vest:
        target.has_vest = False
    else:
        target.lives -= points_to_use
    
    current_user.points -= points_to_use
    target.last_attacked = datetime.utcnow()
    target.attack_count += 1
    
    db.session.commit()
    
    emit('attack_result', {
        'attacker': current_user.username,
        'target': target_username,
        'points_used': points_to_use,
        'target_lives': target.lives
    }, room=group_code)
    
    # Check if game should end
    active_players = User.query.filter_by(group_id=group.id, lives__gt=0).count()
    if active_players <= 2:
        # Find the winner
        winner = User.query.filter_by(group_id=group.id, lives__gt=0).first()
        if winner:
            emit('game_over', {
                'winner': winner.username,
                'message': f'Game Over! {winner.username} wins!'
            }, room=group_code)
        else:
            emit('game_over', {
                'message': 'Game Over! No winner.'
            }, room=group_code)
    
    # Update player list for all users
    update_player_list(group_code)

@socketio.on('use_major_power')
def on_use_major_power(data):
    group_code = data['group_code']
    power_type = data['power_type']
    target_username = data.get('target')
    
    group = Group.query.filter_by(code=group_code).first_or_404()
    
    # Ensure user is in this group
    if current_user.group_id != group.id:
        emit('error', {'msg': 'You are not a member of this group'})
        return
    
    if power_type == 'revive':
        current_user.lives = 2
        db.session.commit()
        emit('power_used', {
            'username': current_user.username,
            'power_type': 'revive'
        }, room=group_code)
    elif power_type == 'eliminate' and target_username:
        target = User.query.filter_by(username=target_username).first()
        if target and target.group_id == group.id:
            target.lives = 0
            db.session.commit()
            emit('power_used', {
                'username': current_user.username,
                'power_type': 'eliminate',
                'target': target_username
            }, room=group_code)
            
            # Check if game should end
            active_players = User.query.filter_by(group_id=group.id, lives__gt=0).count()
            if active_players <= 2:
                # Find the winner
                winner = User.query.filter_by(group_id=group.id, lives__gt=0).first()
                if winner:
                    emit('game_over', {
                        'winner': winner.username,
                        'message': f'Game Over! {winner.username} wins!'
                    }, room=group_code)
                else:
                    emit('game_over', {
                        'message': 'Game Over! No winner.'
                    }, room=group_code)
    
    # Update player list for all users
    update_player_list(group_code)

@socketio.on('buy_vest')
def on_buy_vest(data):
    group_code = data['group_code']
    
    group = Group.query.filter_by(code=group_code).first_or_404()
    
    # Ensure user is in this group
    if current_user.group_id != group.id:
        emit('error', {'msg': 'You are not a member of this group'})
        return
    
    if current_user.points >= 2:  # Vest costs 2 points
        current_user.points -= 2
        current_user.has_vest = True
        db.session.commit()
        emit('vest_purchased', {
            'username': current_user.username
        }, room=group_code)
        
        # Update player list for all users
        update_player_list(group_code)
    else:
        emit('error', {'msg': 'Not enough points!'}, room=group_code)

@socketio.on('chat_message')
def on_chat_message(data):
    group_code = data['group_code']
    message = data['message']
    
    group = Group.query.filter_by(code=group_code).first_or_404()
    
    # Ensure user is in this group
    if current_user.group_id != group.id:
        emit('error', {'msg': 'You are not a member of this group'})
        return
    
    # Save message to database
    new_message = Message(
        content=message,
        user_id=current_user.id,
        group_id=group.id
    )
    db.session.add(new_message)
    db.session.commit()
    
    # Emit message to all users in the group
    emit('chat_message', {
        'username': current_user.username,
        'message': message,
        'timestamp': datetime.utcnow().strftime('%H:%M:%S')
    }, room=group_code)

def update_player_list(group_code):
    """Update the player list for all users in the group"""
    group = Group.query.filter_by(code=group_code).first_or_404()
    players = []
    
    for user in group.users:
        players.append({
            'id': user.id,
            'username': user.username,
            'points': user.points,
            'lives': user.lives,
            'has_vest': user.has_vest,
            'is_ready': user.is_ready,
            'is_owner': user.id == group.owner_id
        })
    
    emit('update_players', {'players': players}, room=group_code) 