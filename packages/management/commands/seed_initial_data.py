from django.core.management.base import BaseCommand
from users.models import Role, User
from packages.models import Company, Branch

class Command(BaseCommand):
    help = 'Seed initial roles, companies, branches, and users'

    def handle(self, *args, **kwargs):
        roles = [
            ('system admin', 'Full access to the platform'),
            ('company admin', 'Manages company operations'),
            ('branch admin', 'Manages a single branch'),
            ('agent', 'Handles package delivery')
        ]

        role_objs = {}
        for name, desc in roles:
            role, _ = Role.objects.get_or_create(name=name, defaults={'description': desc})
            role_objs[name] = role

        # Create company with all required fields
        company, _ = Company.objects.get_or_create(
            name='Acme Corp', 
            defaults={
                'address': '123 Main St', 
                'phone': '0123456789', 
                'email': 'info@acme.com'
            }
        )
        
        # Create branch
        branch, _ = Branch.objects.get_or_create(
            name='Central Branch', 
            company=company, 
            defaults={'location': 'Downtown'}
        )

        users_data = [
            ('sysadmin', 'sysadmin@example.com', 'system admin'),
            ('compadmin', 'compadmin@example.com', 'company admin'),
            ('branchadmin', 'branchadmin@example.com', 'branch admin'),
            ('agent1', 'agent1@example.com', 'agent')
        ]

        for username, email, role_key in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'full_name': username.capitalize(),
                    'role': role_objs[role_key],
                    'company': company if role_key != 'system admin' else None,
                    'branch': branch if role_key == 'branch admin' or role_key == 'agent' else None,
                    'is_staff': role_key == 'system admin',
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                
                # Create Agent record for agent users
                if role_key == 'agent':
                    from packages.models import Agent
                    Agent.objects.get_or_create(user=user, branch=branch)

        self.stdout.write(self.style.SUCCESS('Seeded roles, company, branch, and example users.'))
        