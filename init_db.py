from app import create_app, db
from app.models import User, Group, Message, Question
import random
import string
import os

def generate_group_code():
    """Generate a random 6-character group code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def init_db():
    """Initialize the database with sample data"""
    app = create_app()
    
    with app.app_context():
        # Drop all tables to start fresh
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Create sample questions
        questions = [
            {
                'content': 'What is the time complexity of binary search?',
                'answer': 'O(log n)',
                'points': 1,
                'is_major': False,
                'order': 1
            },
            {
                'content': 'What is the difference between a stack and a queue?',
                'answer': 'LIFO vs FIFO',
                'points': 1,
                'is_major': False,
                'order': 2
            },
            {
                'content': 'What is the purpose of a primary key in a database?',
                'answer': 'Unique identifier',
                'points': 1,
                'is_major': False,
                'order': 3
            },
            {
                'content': 'What is the difference between HTTP and HTTPS?',
                'answer': 'Encryption',
                'points': 1,
                'is_major': False,
                'order': 4
            },
            {
                'content': 'What is the difference between a compiler and an interpreter?',
                'answer': 'Translation vs Execution',
                'points': 1,
                'is_major': False,
                'order': 5
            },
            {
                'content': 'What is the purpose of a firewall?',
                'answer': 'Network security',
                'points': 1,
                'is_major': False,
                'order': 6
            },
            {
                'content': 'What is the difference between a variable and a constant?',
                'answer': 'Mutable vs Immutable',
                'points': 1,
                'is_major': False,
                'order': 7
            },
            {
                'content': 'What is the purpose of a loop in programming?',
                'answer': 'Repetition',
                'points': 1,
                'is_major': False,
                'order': 8
            },
            {
                'content': 'What is the difference between a function and a method?',
                'answer': 'Object association',
                'points': 1,
                'is_major': False,
                'order': 9
            },
            {
                'content': 'What is the purpose of an API?',
                'answer': 'Interface for communication',
                'points': 1,
                'is_major': False,
                'order': 10
            },
            {
                'content': 'What is the difference between a class and an object?',
                'answer': 'Blueprint vs Instance',
                'points': 1,
                'is_major': False,
                'order': 11
            },
            {
                'content': 'What is the purpose of a database index?',
                'answer': 'Speed up queries',
                'points': 1,
                'is_major': False,
                'order': 12
            },
            {
                'content': 'What is the difference between a synchronous and asynchronous operation?',
                'answer': 'Blocking vs Non-blocking',
                'points': 1,
                'is_major': False,
                'order': 13
            },
            {
                'content': 'What is the purpose of a transaction in a database?',
                'answer': 'Atomic operations',
                'points': 1,
                'is_major': False,
                'order': 14
            },
            {
                'content': 'What is the difference between a static and dynamic website?',
                'answer': 'Pre-rendered vs On-demand',
                'points': 1,
                'is_major': False,
                'order': 15
            },
            {
                'content': 'What is the purpose of a cache?',
                'answer': 'Speed up access',
                'points': 1,
                'is_major': False,
                'order': 16
            },
            {
                'content': 'What is the difference between a client and a server?',
                'answer': 'Request vs Response',
                'points': 1,
                'is_major': False,
                'order': 17
            },
            {
                'content': 'What is the purpose of a virtual machine?',
                'answer': 'Isolation',
                'points': 1,
                'is_major': True,
                'order': 18
            }
        ]
        
        for question_data in questions:
            question = Question(
                content=question_data['content'],
                answer=question_data['answer'],
                points=question_data['points'],
                is_major=question_data['is_major'],
                order=question_data['order']
            )
            db.session.add(question)
        
        # Create a sample group
        group_code = generate_group_code()
        while Group.query.filter_by(code=group_code).first():
            group_code = generate_group_code()
        
        group = Group(
            code=group_code,
            owner_id=1,  # Will be updated after user creation
            is_active=False,
            current_question=1
        )
        db.session.add(group)
        
        # Create a sample admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            is_group_owner=True,
            lives=2,
            points=0,
            has_vest=False,
            is_alive=True,
            is_ready=False
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Commit to get the admin ID
        db.session.commit()
        
        # Update the group owner ID
        group.owner_id = admin.id
        admin.group_id = group.id
        
        # Create a sample message
        message = Message(
            content='Welcome to the game!',
            user_id=admin.id,
            group_id=group.id
        )
        db.session.add(message)
        
        # Commit all changes
        db.session.commit()
        
        print(f"Database initialized successfully!")
        print(f"Admin username: admin, password: admin123")
        print(f"Sample group code: {group_code}")

if __name__ == '__main__':
    init_db() 