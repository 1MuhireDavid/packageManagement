from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def assign_unique_users(apps, schema_editor):
    """
    Assigns unique user IDs to each driver record.
    This runs as part of the migration.
    """
    Driver = apps.get_model('packages', 'Driver')
    User = apps.get_model('users', 'User')
    
    # Get all drivers
    drivers = Driver.objects.all()
    
    # For each driver, either:
    # 1. If they're the first driver for a user, use that user
    # 2. Otherwise, create a new user for them
    used_user_ids = set()
    
    for i, driver in enumerate(drivers):
        # Try to find a user ID that's not used yet
        # In a real scenario, you would have more sophisticated logic here
        new_user_id = i + 1  # Just to ensure uniqueness for this example
        
        # Make sure we're not reusing a user ID
        while new_user_id in used_user_ids:
            new_user_id += 1
            
        driver.user_id = new_user_id
        driver.save()
        used_user_ids.add(new_user_id)


class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0006_remove_agent_name_remove_agent_phone_and_more'),
        # other dependencies...
    ]

    operations = [
        # First add the field without the unique constraint
        migrations.AddField(
            model_name='driver',
            name='user',
            field=models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE),
        ),
        
        # Add branch field
        migrations.AddField(
            model_name='driver',
            name='branch',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='packages.branch'),
            preserve_default=False,
        ),
        
        # Run the data migration function
        migrations.RunPython(assign_unique_users),
        
        # Now change the ForeignKey to OneToOneField and make it non-nullable
        migrations.AlterField(
            model_name='driver',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        
        # Remove the old fields
        migrations.RemoveField(model_name='driver', name='company'),
        migrations.RemoveField(model_name='driver', name='name'),
        migrations.RemoveField(model_name='driver', name='phone'),
        migrations.RemoveField(model_name='driver', name='plate_number'),
        
        # ... add the rest of your migration operations here
    ]